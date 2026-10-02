"""
resume_parser.py
================

Turns an uploaded resume (PDF or DOCX) into structured, machine-comparable
data. No LLM is involved: extraction is regex + layout heuristics + the shared
skill taxonomy, so the same resume always produces the same structure.

Pipeline
--------
    bytes  ->  raw text  ->  line cleanup  ->  section segmentation
           ->  per-section field extraction  ->  structured dict

The returned dict is the "resume evidence" consumed by the ATS scorer and the
job matcher.
"""

from __future__ import annotations

import io
import re
from typing import Dict, List, Optional, Tuple

from skills_data import extract_skills, skill_category

SUPPORTED_EXTENSIONS = (".pdf", ".docx")
MAX_FILE_BYTES = 10 * 1024 * 1024          # 10 MB is far more than any resume
MIN_MEANINGFUL_CHARS = 120                 # below this the file is effectively empty


class ResumeParseError(Exception):
    """Raised when a resume cannot be read. Carries a user-facing message."""


# ---------------------------------------------------------------------------
# Section vocabulary
#
# Every resume heading we recognise is mapped to one of a small set of
# CANONICAL sections, so the ATS scorer can ask "does this resume have an
# education section?" without caring whether the author wrote "EDUCATION",
# "Academic Background" or "Qualifications".
# ---------------------------------------------------------------------------
SECTION_ALIASES: Dict[str, List[str]] = {
    "summary": ["summary", "objective", "career objective", "professional summary",
                "profile", "about me", "about", "career summary"],
    "education": ["education", "academic background", "academics", "qualifications",
                  "academic qualifications", "educational qualifications", "education details"],
    "experience": ["experience", "work experience", "professional experience",
                   "employment", "employment history", "internship", "internships",
                   "work history", "industrial training", "training"],
    "projects": ["projects", "academic projects", "personal projects", "key projects",
                 "project work", "major projects", "minor projects", "project experience"],
    "skills": ["skills", "technical skills", "technical proficiency", "core competencies",
               "skills summary", "technologies", "tech stack", "areas of expertise",
               "competencies", "technical expertise"],
    "certifications": ["certifications", "certification", "courses", "certificates",
                       "licenses", "online courses", "professional development"],
    "achievements": ["achievements", "awards", "honors", "honours", "accomplishments",
                     "awards and achievements", "achievements and awards", "recognition"],
    "publications": ["publications", "research", "papers", "research papers"],
    "activities": ["extracurricular", "extra curricular", "activities", "volunteer",
                   "leadership", "positions of responsibility", "co-curricular"],
    "languages": ["languages", "languages known"],
    "interests": ["interests", "hobbies", "hobbies and interests"],
    "coursework": ["coursework", "relevant coursework", "subjects"],
}

# Flat lookup: normalised heading text -> canonical section
_HEADING_LOOKUP: Dict[str, str] = {}
for _canonical, _aliases in SECTION_ALIASES.items():
    for _a in _aliases:
        _HEADING_LOOKUP[_a] = _canonical

# Sections the ATS scorer treats as structurally important.
CORE_SECTIONS = ["summary", "education", "experience", "projects", "skills",
                 "certifications", "achievements"]


# ---------------------------------------------------------------------------
# Regexes for contact details
# ---------------------------------------------------------------------------
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
# Indian 10-digit numbers with optional +91, plus generic international forms.
PHONE_RE = re.compile(
    r"(?:(?:\+|00)\d{1,3}[\s.\-]?)?(?:\(\d{2,4}\)[\s.\-]?)?\d{3,5}[\s.\-]?\d{3,5}(?:[\s.\-]?\d{2,4})?"
)
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/(?:in|pub)/[A-Za-z0-9_\-%.]+/?", re.I)
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/([A-Za-z0-9](?:[A-Za-z0-9\-]{0,37}[A-Za-z0-9])?)/?", re.I)
PORTFOLIO_RE = re.compile(r"(?:https?://)(?:www\.)?(?!linkedin\.com|github\.com)[A-Za-z0-9\-]+\.[A-Za-z]{2,}(?:/\S*)?", re.I)

DEGREE_RE = re.compile(
    r"\b(b\.?\s?tech|b\.?\s?e\.?|bachelor|b\.?\s?sc|bca|m\.?\s?tech|m\.?\s?e\.?|master|"
    r"m\.?\s?sc|mca|mba|ph\.?\s?d|doctorate|diploma|intermediate|higher secondary|"
    r"senior secondary|class xii|class 12|12th|10th|high school)\b",
    re.I,
)
CGPA_RE = re.compile(r"\b(?:cgpa|gpa|sgpa)\b[\s:]*([0-9]+(?:\.[0-9]+)?)(?:\s*/\s*([0-9]+(?:\.[0-9]+)?))?", re.I)
PERCENT_RE = re.compile(r"\b(\d{1,3}(?:\.\d+)?)\s?%")
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")

BULLET_RE = re.compile(r"^\s*(?:[-*•▪●⁃∙·◦‣>]|\d+[.)])\s+")

# A quantified achievement contains a number that carries meaning: a
# percentage, a multiplier, a magnitude, a count of people/users, etc.
QUANTIFIER_RE = re.compile(
    r"(\d{1,3}(?:\.\d+)?\s?%"                       # 40%
    r"|\b\d+(?:\.\d+)?\s?[xX]\b"                    # 3x
    r"|\b\d{1,3}(?:,\d{3})+\b"                      # 10,000
    r"|\b\d+\s?(?:k|K|lakh|lakhs|crore|crores|million|billion)\b"   # 50k
    r"|\b(?:rs\.?|inr|usd|\$|₹)\s?\d+"         # $5000
    r"|\b\d+\s?\+"                                  # 500+
    r"|\b\d+\s+(?:users|students|members|clients|customers|hours|days|weeks|months|"
    r"teams|projects|records|images|papers|participants|downloads|requests|queries)\b)",
    re.I,
)

ACTION_VERBS = {
    "built", "designed", "developed", "implemented", "created", "led", "improved",
    "optimized", "optimised", "reduced", "increased", "automated", "deployed",
    "engineered", "architected", "integrated", "migrated", "launched", "managed",
    "collaborated", "analyzed", "analysed", "researched", "trained", "tested",
    "refactored", "delivered", "achieved", "won", "published", "mentored",
}


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def _extract_pdf_text(data: bytes) -> str:
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - dependency guaranteed by requirements
        raise ResumeParseError("PDF support is unavailable: pdfplumber is not installed.") from exc

    pages: List[str] = []
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            if not pdf.pages:
                raise ResumeParseError("The PDF contains no pages.")
            for page in pdf.pages:
                pages.append(page.extract_text() or "")
    except ResumeParseError:
        raise
    except Exception as exc:
        raise ResumeParseError(
            "The PDF could not be read. It may be corrupted or password-protected."
        ) from exc

    text = "\n".join(pages)
    if len(text.strip()) < MIN_MEANINGFUL_CHARS:
        raise ResumeParseError(
            "Almost no text could be extracted from this PDF. If it is a scanned "
            "image, please upload a text-based PDF or a DOCX file instead."
        )
    return text


def _extract_docx_text(data: bytes) -> str:
    try:
        import docx
    except ImportError as exc:  # pragma: no cover
        raise ResumeParseError("DOCX support is unavailable: python-docx is not installed.") from exc

    try:
        document = docx.Document(io.BytesIO(data))
    except Exception as exc:
        raise ResumeParseError(
            "The DOCX file could not be read. It may be corrupted or saved in the "
            "older .doc format, which is not supported."
        ) from exc

    parts: List[str] = []
    for para in document.paragraphs:
        text_ = para.text.strip()
        if not text_:
            continue
        # Word list items store their bullet in the numbering definition, not in
        # the text, so python-docx returns them unmarked. Re-attach a marker
        # from the paragraph style so bullet detection still works.
        style = (para.style.name or "") if para.style is not None else ""
        if style.startswith("List") and not BULLET_RE.match(text_):
            text_ = f"\u2022 {text_}"
        parts.append(text_)
    # Many student resumes lay skills out in tables; python-docx keeps those
    # out of `paragraphs`, so pull them in explicitly.
    for table in document.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                parts.append(" | ".join(cells))

    text = "\n".join(parts)
    if len(text.strip()) < MIN_MEANINGFUL_CHARS:
        raise ResumeParseError("This DOCX file appears to be empty.")
    return text


def extract_text(data: bytes, filename: str) -> Tuple[str, str]:
    """
    Extract raw text from an uploaded resume.

    Returns ``(text, file_type)``. Raises :class:`ResumeParseError` with a
    message suitable for showing to the user.
    """
    if not filename:
        raise ResumeParseError("No filename was provided with the upload.")

    lowered = filename.lower()
    if not lowered.endswith(SUPPORTED_EXTENSIONS):
        raise ResumeParseError(
            f"Unsupported file type. Please upload a PDF or DOCX file "
            f"(received: {filename!r})."
        )
    if not data:
        raise ResumeParseError("The uploaded file is empty.")
    if len(data) > MAX_FILE_BYTES:
        raise ResumeParseError(
            f"File is too large ({len(data) / 1024 / 1024:.1f} MB). The limit is "
            f"{MAX_FILE_BYTES // 1024 // 1024} MB."
        )

    if lowered.endswith(".pdf"):
        # Guard against a file that is merely *named* .pdf.
        if not data.lstrip()[:5].startswith(b"%PDF"):
            raise ResumeParseError("This file is named .pdf but is not a valid PDF document.")
        return _extract_pdf_text(data), "pdf"

    # .docx files are ZIP archives; every valid one starts with "PK".
    if not data[:2] == b"PK":
        raise ResumeParseError("This file is named .docx but is not a valid DOCX document.")
    return _extract_docx_text(data), "docx"


# ---------------------------------------------------------------------------
# Line / section handling
# ---------------------------------------------------------------------------

CID_RE = re.compile(r"\(cid:\d+\)")


def _clean_lines(text: str) -> List[str]:
    """
    Normalise raw extracted text into clean, non-empty lines.

    pdfplumber emits "(cid:NNN)" when a glyph has no usable unicode mapping --
    typically the Symbol-font bullet used by Word. A leading one is a real
    bullet and becomes a bullet character; any others are dropped as noise.
    """
    lines = []
    for raw in text.splitlines():
        line = raw.replace("\xa0", " ").replace("\u200b", "")
        if CID_RE.match(line.strip()):
            line = CID_RE.sub("\u2022", line, count=1)
        line = CID_RE.sub("", line)
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            lines.append(line)
    return lines


def _normalise_heading(line: str) -> str:
    """Strip decoration so 'TECHNICAL SKILLS :' -> 'technical skills'."""
    cleaned = re.sub(r"[^A-Za-z ]+", " ", line)
    return re.sub(r"\s+", " ", cleaned).strip().lower()


def _is_heading(line: str) -> Optional[str]:
    """Return the canonical section name if ``line`` is a section heading."""
    if len(line) > 60 or BULLET_RE.match(line):
        return None
    normalised = _normalise_heading(line)
    if not normalised or len(normalised.split()) > 5:
        return None

    if normalised in _HEADING_LOOKUP:
        return _HEADING_LOOKUP[normalised]

    # Headings like "EDUCATION & CERTIFICATIONS" or "Technical Skills Summary":
    # accept when the line is visually a heading (all-caps or title-case, no
    # trailing sentence punctuation) and contains a known heading word.
    looks_like_heading = line.isupper() or line.istitle() or line.endswith(":")
    if looks_like_heading and not line.endswith("."):
        for alias, canonical in _HEADING_LOOKUP.items():
            if re.search(rf"\b{re.escape(alias)}\b", normalised):
                return canonical
    return None


def _segment_sections(lines: List[str]) -> Tuple[Dict[str, List[str]], List[Dict[str, str]]]:
    """
    Split the resume into sections.

    Returns ``(sections, headings)`` where ``sections`` maps canonical name ->
    content lines, and ``headings`` records the literal heading text found (so
    the UI can show what was actually detected).
    """
    sections: Dict[str, List[str]] = {}
    headings: List[Dict[str, str]] = []
    current = "header"          # everything before the first heading
    sections[current] = []

    for line in lines:
        canonical = _is_heading(line)
        if canonical:
            headings.append({"detected_as": canonical, "text": line})
            current = canonical
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)

    return sections, headings


# ---------------------------------------------------------------------------
# Field extraction
# ---------------------------------------------------------------------------

def _extract_phone(text: str) -> Optional[str]:
    """
    Pick the first candidate that has 10-13 digits. The loose regex also
    matches things like dates and CGPA fragments, so we filter by digit count
    and reject anything that looks like a year range.
    """
    for match in PHONE_RE.finditer(text):
        candidate = match.group(0).strip()
        digits = re.sub(r"\D", "", candidate)
        if not (10 <= len(digits) <= 13):
            continue
        if YEAR_RE.fullmatch(digits):
            continue
        return re.sub(r"\s+", " ", candidate)
    return None


def _extract_name(header_lines: List[str], email: Optional[str]) -> Optional[str]:
    """
    Heuristic: the candidate's name is normally the first header line that is
    short, alphabetic, and not a contact detail or a job title.
    """
    for line in header_lines[:6]:
        if EMAIL_RE.search(line) or LINKEDIN_RE.search(line) or GITHUB_RE.search(line):
            continue
        if re.search(r"\d", line) or "@" in line or "|" in line:
            continue
        words = line.split()
        if not (1 < len(words) <= 5):
            continue
        if not all(re.fullmatch(r"[A-Za-z][A-Za-z.'\-]*", w) for w in words):
            continue
        # Skip lines that are obviously a headline rather than a name.
        if _is_heading(line) or line.lower() in {"curriculum vitae", "resume"}:
            continue
        return line.title() if line.isupper() else line

    # Fall back to the local part of the email address ("john.doe" -> "John Doe").
    if email:
        local = email.split("@")[0]
        guess = re.sub(r"[._\-]+", " ", re.sub(r"\d+", "", local)).strip()
        if len(guess.split()) >= 2:
            return guess.title()
    return None


def _section_text(sections: Dict[str, List[str]], name: str) -> str:
    return "\n".join(sections.get(name, []))


def _split_entries(lines: List[str]) -> List[str]:
    """
    Group section lines into entries. A bullet starts a new entry; unbulleted
    continuation lines are appended to the previous entry so that a wrapped
    sentence is not counted twice.
    """
    entries: List[str] = []
    for line in lines:
        if BULLET_RE.match(line):
            entries.append(BULLET_RE.sub("", line).strip())
        elif entries and line[:1].islower():
            entries[-1] = f"{entries[-1]} {line}".strip()
        else:
            entries.append(line)
    return [e for e in entries if len(e) > 2]


def _extract_education(sections: Dict[str, List[str]], full_text: str) -> List[Dict[str, object]]:
    lines = sections.get("education") or []
    if not lines:
        # Some resumes have no heading; fall back to degree-bearing lines.
        lines = [ln for ln in full_text.splitlines() if DEGREE_RE.search(ln)][:4]

    education: List[Dict[str, object]] = []
    for entry in _split_entries(lines):
        degree_match = DEGREE_RE.search(entry)
        cgpa_match = CGPA_RE.search(entry)
        percent_match = PERCENT_RE.search(entry)
        years = YEAR_RE.findall(entry)
        if not (degree_match or cgpa_match or years or len(entry.split()) > 3):
            continue
        education.append({
            "text": entry,
            "degree": degree_match.group(0).strip() if degree_match else None,
            "score": (cgpa_match.group(0).strip() if cgpa_match
                      else (percent_match.group(0).strip() if percent_match else None)),
            "years": sorted({m.group(0) for m in YEAR_RE.finditer(entry)}),
        })
    return education[:8]


def _extract_listing(sections: Dict[str, List[str]], name: str, limit: int = 12) -> List[Dict[str, object]]:
    """Generic extractor for experience / projects / certifications entries."""
    entries = _split_entries(sections.get(name) or [])
    out: List[Dict[str, object]] = []
    for entry in entries:
        if len(entry) < 8:
            continue
        out.append({
            "text": entry,
            "skills": extract_skills(entry),
            "quantified": bool(QUANTIFIER_RE.search(entry)),
        })
        if len(out) >= limit:
            break
    return out


def _extract_achievements(
    sections: Dict[str, List[str]],
    lines: List[str],
) -> List[Dict[str, object]]:
    """
    Quantifiable achievements: any line carrying a meaningful number. These are
    scored separately because ATS-friendly resumes quantify impact.
    """
    seen: set = set()
    out: List[Dict[str, object]] = []

    declared = _split_entries(sections.get("achievements") or [])
    for entry in declared:
        key = entry.lower()[:80]
        if key in seen:
            continue
        seen.add(key)
        out.append({"text": entry, "quantified": bool(QUANTIFIER_RE.search(entry)),
                    "source_section": "achievements"})

    # Percentages and marks inside the education section are qualifications,
    # not quantified impact, so they are excluded from this count.
    education_lines = {ln.strip().lower() for ln in sections.get("education", [])}

    for line in lines:
        match = QUANTIFIER_RE.search(line)
        if not match:
            continue
        key = line.lower()[:80]
        if key in seen or len(line) < 15:
            continue
        # Skip contact/education noise that merely contains digits.
        if EMAIL_RE.search(line) or CGPA_RE.search(line):
            continue
        if line.strip().lower() in education_lines or DEGREE_RE.search(line):
            continue
        seen.add(key)
        out.append({"text": BULLET_RE.sub("", line).strip(), "quantified": True,
                    "source_section": "body", "metric": match.group(0).strip()})
        if len(out) >= 15:
            break
    return out


def _readability_signals(lines: List[str], text: str, sections: Dict[str, List[str]]) -> Dict[str, object]:
    words = re.findall(r"[A-Za-z']+", text)
    bullets = [ln for ln in lines if BULLET_RE.match(ln)]
    first_words = {
        re.sub(r"[^a-z]", "", BULLET_RE.sub("", b).split()[0].lower())
        for b in bullets if BULLET_RE.sub("", b).split()
    }
    return {
        "word_count": len(words),
        "line_count": len(lines),
        "bullet_count": len(bullets),
        "section_count": len([k for k in sections if k != "header" and sections[k]]),
        "uses_bullets": len(bullets) >= 3,
        "action_verbs_used": sorted(first_words & ACTION_VERBS),
        "avg_bullet_words": (
            round(sum(len(b.split()) for b in bullets) / len(bullets), 1) if bullets else 0.0
        ),
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def parse_resume(data: bytes, filename: str) -> Dict[str, object]:
    """
    Parse an uploaded resume into structured evidence.

    Raises :class:`ResumeParseError` on unsupported / empty / unreadable files.
    """
    raw_text, file_type = extract_text(data, filename)
    lines = _clean_lines(raw_text)
    # Everything downstream -- contact regexes, evidence snippets, the preview
    # shown in the UI -- uses the CLEANED text. The raw extraction still carries
    # pdfplumber's "(cid:NNN)" glyph placeholders, which would otherwise surface
    # verbatim in the evidence quoted back to the user.
    text = "\n".join(lines)
    sections, headings = _segment_sections(lines)

    email_match = EMAIL_RE.search(text)
    email = email_match.group(0) if email_match else None
    linkedin_match = LINKEDIN_RE.search(text)
    github_match = GITHUB_RE.search(text)

    header_lines = sections.get("header", [])
    portfolio = None
    for match in PORTFOLIO_RE.finditer("\n".join(header_lines[:8])):
        portfolio = match.group(0)
        break

    contact = {
        "name": _extract_name(header_lines, email),
        "email": email,
        "phone": _extract_phone(text),
        "linkedin": linkedin_match.group(0) if linkedin_match else None,
        "github": github_match.group(0) if github_match else None,
        "github_username": github_match.group(1) if github_match else None,
        "portfolio": portfolio,
    }

    # Skills are collected from two places and kept distinguishable:
    #  - "declared": listed inside an explicit Skills section
    #  - "contextual": mentioned anywhere else (projects, experience, summary)
    skills_section_text = _section_text(sections, "skills")
    declared_skills = extract_skills(skills_section_text)
    all_skills = extract_skills(text)
    contextual_skills = [s for s in all_skills if s not in set(declared_skills)]

    detected_sections = sorted(
        k for k, v in sections.items() if k != "header" and v
    )

    parsed: Dict[str, object] = {
        "file": {"name": filename, "type": file_type, "size_bytes": len(data)},
        "contact": contact,
        "skills": all_skills,
        "skills_detail": {
            "declared": declared_skills,
            "contextual": contextual_skills,
            "by_category": _group_by_category(all_skills),
        },
        "education": _extract_education(sections, text),
        "experience": _extract_listing(sections, "experience"),
        "projects": _extract_listing(sections, "projects"),
        "certifications": _extract_listing(sections, "certifications", limit=10),
        "achievements": _extract_achievements(sections, lines),
        "sections": detected_sections,
        "section_headings": headings,
        "missing_core_sections": [s for s in CORE_SECTIONS if s not in detected_sections],
        "readability": _readability_signals(lines, text, sections),
        "raw_text": text,
    }
    return parsed


def _group_by_category(skills: List[str]) -> Dict[str, List[str]]:
    grouped: Dict[str, List[str]] = {}
    for skill in skills:
        grouped.setdefault(skill_category(skill), []).append(skill)
    return grouped

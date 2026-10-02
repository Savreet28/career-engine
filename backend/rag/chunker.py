"""
chunker.py
==========

Splits a job-description document into small retrieval units ("chunks").

Why chunk at all?
-----------------
Embedding an entire job description into one vector blurs everything together:
the vector for a 600-word document sits in the "average" of all its topics, so
a query about *required Python skills* retrieves the whole document with no
indication of which part actually matched. Small chunks keep one idea per
vector, which makes retrieval precise and -- crucially for this project --
makes the retrieved text short enough to show the user as evidence.

Chunking strategy
-----------------
Job descriptions here are structured JSON, so we chunk **semantically by
section** rather than blindly by character count:

  * each bullet under required_skills / preferred_skills / responsibilities /
    qualifications becomes its own chunk (these are already one idea each);
  * free-text fields such as about_the_role are split into overlapping
    word windows, because they are prose with no natural boundaries.

Every chunk keeps its provenance (job title, company, role, section), which is
what lets the UI display "AI/ML Engineer - Nexora Labs, required_skills".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import config
from skills_data import extract_skills

# Sections that are lists of one-idea-per-entry strings.
LIST_SECTIONS = ["required_skills", "preferred_skills", "responsibilities", "qualifications"]
# Sections that are free-form prose.
PROSE_SECTIONS = ["about_the_role"]

# Weight given to a requirement depending on where in the JD it was stated.
# Used by the job matcher to separate "must have" from "nice to have".
# Only the "required skills" section states must-have *skills*. Qualifications
# are largely about degrees and portfolios, and responsibilities describe the
# work rather than the entry bar, so neither promotes a skill to must-have.
SECTION_REQUIREMENT_KIND = {
    "required_skills": "core",
    "preferred_skills": "preferred",
    "responsibilities": "preferred",
    "qualifications": "preferred",
    "about_the_role": "context",
}


@dataclass
class Chunk:
    """One retrievable unit of a job description."""

    chunk_id: str
    text: str
    document_id: str
    job_title: str
    company: str
    role_id: str
    section: str
    requirement_kind: str = "context"
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "document_id": self.document_id,
            "job_title": self.job_title,
            "company": self.company,
            "role_id": self.role_id,
            "section": self.section,
            "requirement_kind": self.requirement_kind,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(data: Dict[str, object]) -> "Chunk":
        return Chunk(
            chunk_id=str(data["chunk_id"]),
            text=str(data["text"]),
            document_id=str(data["document_id"]),
            job_title=str(data["job_title"]),
            company=str(data["company"]),
            role_id=str(data["role_id"]),
            section=str(data["section"]),
            requirement_kind=str(data.get("requirement_kind", "context")),
            metadata=dict(data.get("metadata") or {}),  # type: ignore[arg-type]
        )

    @property
    def source_label(self) -> str:
        """Human-readable provenance, e.g. 'AI/ML Engineer - Nexora Labs'."""
        return f"{self.job_title} - {self.company}"


def _split_prose(text: str, max_words: int, overlap_words: int) -> List[str]:
    """
    Sliding word window over prose.

    Overlap matters: without it, a sentence straddling a boundary is split
    across two chunks and neither one embeds its full meaning.
    """
    words = text.split()
    if len(words) <= max_words:
        return [text.strip()] if text.strip() else []

    step = max(1, max_words - overlap_words)
    windows: List[str] = []
    for start in range(0, len(words), step):
        window = words[start:start + max_words]
        if len(window) < 10 and windows:
            break          # trailing scrap: already covered by the overlap
        windows.append(" ".join(window))
        if start + max_words >= len(words):
            break
    return windows


def chunk_job_description(
    document: Dict[str, object],
    max_words: Optional[int] = None,
    overlap_words: Optional[int] = None,
) -> List[Chunk]:
    """Convert one job-description document into a list of :class:`Chunk`."""
    max_words = max_words if max_words is not None else config.CHUNK_MAX_WORDS
    overlap_words = overlap_words if overlap_words is not None else config.CHUNK_OVERLAP_WORDS

    document_id = str(document.get("id") or document.get("job_title") or "unknown")
    job_title = str(document.get("job_title") or "Untitled Role")
    company = str(document.get("company") or "Unknown Company")
    role_id = str(document.get("role_id") or "")
    base_metadata = {
        "location": document.get("location"),
        "experience_required": document.get("experience_required"),
    }

    chunks: List[Chunk] = []

    def add(text: str, section: str) -> None:
        text = re.sub(r"\s+", " ", str(text)).strip()
        if len(text.split()) < 4:       # too short to embed meaningfully
            return
        chunks.append(Chunk(
            chunk_id=f"{document_id}::{section}::{len(chunks)}",
            # Embed the sentence ITSELF, with no title/company prefix.
            # A prefix was tried and measurably hurt retrieval: for the query
            # "vector database embeddings", prefixing dropped the correct chunk
            # ("Experience with vector databases such as FAISS, Chroma...") from
            # cosine 0.58 to 0.30 and let an unrelated SQL chunk outrank it. On
            # short chunks the prefix dominates the averaged representation.
            # Role scoping is handled by the role_id metadata filter instead.
            text=text,
            document_id=document_id,
            job_title=job_title,
            company=company,
            role_id=role_id,
            section=section,
            requirement_kind=SECTION_REQUIREMENT_KIND.get(section, "context"),
            metadata={**base_metadata, "raw_text": text},
        ))

    for section in LIST_SECTIONS:
        for entry in document.get(section) or []:      # type: ignore[union-attr]
            add(entry, section)

    for section in PROSE_SECTIONS:
        value = document.get(section)
        if value:
            for window in _split_prose(str(value), max_words, overlap_words):
                add(window, section)

    return chunks


# Headings commonly used in pasted job descriptions, mapped to how strongly a
# skill mentioned underneath them should count. Without this, every skill in a
# pasted posting would be treated as a must-have, including the ones explicitly
# listed as optional.
PASTED_HEADING_PATTERNS = [
    (re.compile(r"\b(nice[ -]to[ -]have|good[ -]to[ -]have|preferred|desirable|"
                r"bonus|plus(?:es)?|advantageous|optional)\b", re.I), "preferred"),
    (re.compile(r"\b(responsibilit|what you(?:'| wi)ll do|the role|about|"
                r"day[ -]to[ -]day|qualification|education)\b", re.I), "preferred"),
    (re.compile(r"\b(require|must[ -]have|essential|minimum|you have|we expect|"
                r"skills|experience)\b", re.I), "core"),
]


def _looks_like_heading(line: str) -> bool:
    """A short line with no sentence punctuation, optionally ending in a colon."""
    stripped = line.strip()
    if not stripped or len(stripped) > 60:
        return False
    if BULLET_LINE_RE.match(stripped):
        return False
    return stripped.endswith(":") or stripped.isupper() or len(stripped.split()) <= 5


BULLET_LINE_RE = re.compile(r"^\s*(?:[-*\u2022\u25aa\u25cf]|\d+[.)])\s+")


def chunk_free_text(
    text: str,
    label: str = "Pasted job description",
    max_words: Optional[int] = None,
    overlap_words: Optional[int] = None,
) -> List[Chunk]:
    """
    Chunk a job description the user pasted in directly.

    Bullets and paragraphs are natural boundaries, so each becomes a chunk; any
    oversized block is then windowed like prose.

    Pasted text has no structured sections, so headings are detected as we go
    ("Required skills:", "Nice to have:") and used to decide whether the skills
    underneath are must-haves or nice-to-haves. This keeps a pasted posting
    consistent with the knowledge-base documents, where that distinction comes
    from the JSON field the text was stored in.
    """
    max_words = max_words if max_words is not None else config.CHUNK_MAX_WORDS
    overlap_words = overlap_words if overlap_words is not None else config.CHUNK_OVERLAP_WORDS

    chunks: List[Chunk] = []
    current_kind = "core"      # text before any heading is treated as core

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if _looks_like_heading(line):
            matched_heading = False
            for pattern, kind in PASTED_HEADING_PATTERNS:
                if pattern.search(line):
                    current_kind = kind
                    matched_heading = True
                    break
            # A pure section heading ("Nice to have:") states no requirement of
            # its own, so drop it -- unless it names a skill, as a line like
            # "TypeScript:" does.
            if matched_heading and not extract_skills(line):
                continue

        cleaned = BULLET_LINE_RE.sub("", line).strip().rstrip(":")
        for window in _split_prose(cleaned, max_words, overlap_words):
            # Two words is enough: "Next.js server-side rendering" is a real
            # requirement, and a higher floor silently dropped short bullets.
            if len(window.split()) < 2:
                continue
            chunks.append(Chunk(
                chunk_id=f"pasted::{len(chunks)}",
                text=window,
                document_id="pasted_job_description",
                job_title=label,
                company="Provided by user",
                role_id="",
                section="pasted",
                requirement_kind=current_kind,
                metadata={"raw_text": window, "heading_context": current_kind},
            ))
    return chunks

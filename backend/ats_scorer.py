"""
ats_scorer.py
=============

Deterministic, rule-based ATS scoring. **No LLM is involved anywhere in this
file** -- that is the whole point of Objective 1.

Why rule-based?
---------------
An Applicant Tracking System is not intelligent. It parses a document, looks
for fields and keywords, and ranks the result. Modelling it with transparent
rules gives three properties an LLM cannot:

  * *Deterministic*  -- the same resume always produces the same number.
  * *Reproducible*   -- anyone can recompute the score by hand from the report.
  * *Explainable*    -- every point is attributed to a named component with a
    stated reason and the literal evidence that earned it.

Scoring model (total = 100)
---------------------------
=========================  =====  =========================================
Component                  Max    What it measures
=========================  =====  =========================================
Contact Information           10  Can an ATS extract who you are and reach you
Resume Sections               10  Are the expected sections present and labelled
Skills Breadth                12  How many distinct, recognised skills appear
Target Role Relevance         18  Overlap with the skills the target role needs
Job Description Keywords      20  Overlap with THIS job description's keywords
Experience & Projects         10  Is there concrete evidence of building things
Quantifiable Achievements      5  Is impact expressed with numbers
Education                      5  Is the degree parseable
Formatting & Readability       5  Bullets, action verbs, sensible length
GitHub Profile Evidence        5  Public code backing up the claims
=========================  =====  =========================================

The first nine components look only at the resume, because that is all a real
ATS receives. GitHub is included as a small, clearly separated component so
the score reflects the project's stated input of resume + GitHub + role,
without pretending an ATS can see a GitHub profile.

The reported total is the arithmetic sum of the component scores, always.

Career stage
------------
Four components measure *coverage* of a role's skills, and a final-year student
can never cover what a senior candidate covers. Rather than awarding freshers
bonus points -- which would be arbitrary -- the expectation changes: each
experience level declares the coverage at which a component earns full marks
(see ``experience_levels.py``), and coverage is scored against that target.
The weights, the components and the arithmetic are identical at every level.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from experience_levels import (
    DEFAULT_LEVEL,
    expectation_note,
    resolve_level,
    scaled_coverage,
)
from skills_data import extract_skills, skill_category, sort_skills

# ---------------------------------------------------------------------------
# Component weights. Change them here and nowhere else.
# ---------------------------------------------------------------------------
WEIGHTS: Dict[str, int] = {
    "contact_information": 10,
    "resume_sections": 10,
    "skills_breadth": 12,
    "role_relevance": 18,
    "jd_keyword_match": 20,
    "experience_projects": 10,
    "quantifiable_achievements": 5,
    "education": 5,
    "formatting_readability": 5,
    "github_evidence": 5,
}
MAX_TOTAL = sum(WEIGHTS.values())          # 100

# Formatting expectations do not depend on career stage.
IDEAL_WORD_RANGE = (200, 900)


def _component(name: str, label: str, score: float, reason: str,
               evidence: Sequence[str], details: Optional[dict] = None) -> Dict[str, object]:
    """Build one component result. Scores are rounded to whole points here."""
    max_score = WEIGHTS[name]
    rounded = int(round(max(0.0, min(float(score), float(max_score)))))
    return {
        "id": name,
        "component": label,
        "score": rounded,
        "max_score": max_score,
        "percentage": round(100.0 * rounded / max_score, 1) if max_score else 0.0,
        "reason": reason,
        "evidence": list(evidence)[:12],
        "details": details or {},
    }


def _coverage(found: Sequence[str], required: Sequence[str]) -> float:
    """Fraction of ``required`` present in ``found``; 1.0 when nothing required."""
    required_set = set(required)
    if not required_set:
        return 1.0
    return len(required_set & set(found)) / len(required_set)


# ---------------------------------------------------------------------------
# Individual components
# ---------------------------------------------------------------------------

def _score_contact(resume: dict) -> Dict[str, object]:
    contact = resume.get("contact") or {}
    # Points per field, weighted by how badly an ATS needs it.
    fields = [("email", 3, "Email address"), ("phone", 2, "Phone number"),
              ("name", 2, "Candidate name"), ("linkedin", 2, "LinkedIn profile"),
              ("github", 1, "GitHub profile")]

    score = 0.0
    found, missing = [], []
    for key, points, label in fields:
        if contact.get(key):
            score += points
            found.append(f"{label}: {contact[key]}")
        else:
            missing.append(label)

    if missing:
        reason = (f"{len(found)} of {len(fields)} contact fields were detected. "
                  f"Missing: {', '.join(missing)}.")
    else:
        reason = "All five contact fields were detected and are machine-readable."
    return _component("contact_information", "Contact Information", score, reason,
                      found, {"missing": missing})


def _score_sections(resume: dict) -> Dict[str, object]:
    sections = set(resume.get("sections") or [])
    # An ATS looks for labelled blocks. Weighted by how essential each is.
    checks = [
        ("skills", 3, "Skills"),
        ("education", 2, "Education"),
        ("summary", 1, "Summary / Objective"),
    ]
    score = 0.0
    found, missing = [], []
    for key, points, label in checks:
        if key in sections:
            score += points
            found.append(f"{label} section found")
        else:
            missing.append(label)

    # Experience OR projects -- a student with strong projects is not penalised
    # for having no formal work experience.
    if "experience" in sections or "projects" in sections:
        score += 3
        found.append("Experience and/or Projects section found")
    else:
        missing.append("Experience or Projects")

    if "certifications" in sections or "achievements" in sections:
        score += 1
        found.append("Certifications and/or Achievements section found")
    else:
        missing.append("Certifications or Achievements")

    reason = (f"{len(found)} of 5 expected resume sections were detected."
              + (f" Missing: {', '.join(missing)}." if missing else
                 " Every expected section is present."))
    return _component("resume_sections", "Resume Sections", score, reason, found,
                      {"detected": sorted(sections), "missing": missing})


def _score_skills_breadth(resume: dict, level: dict) -> Dict[str, object]:
    skills: List[str] = resume.get("skills") or []
    categories = {skill_category(s) for s in skills}

    skills_target = int(level["skills_for_full_breadth"])
    categories_target = int(level["categories_for_full_diversity"])

    # Two thirds for how many skills, one third for how varied they are: a
    # resume listing eighteen JavaScript libraries is narrower than one listing
    # a language, a framework, a database and a deployment tool.
    breadth_max = WEIGHTS["skills_breadth"] * 2 / 3
    diversity_max = WEIGHTS["skills_breadth"] - breadth_max
    breadth = min(1.0, len(skills) / skills_target) * breadth_max
    diversity = min(1.0, len(categories) / categories_target) * diversity_max

    declared = (resume.get("skills_detail") or {}).get("declared") or []
    reason = (
        f"{len(skills)} recognised skills across {len(categories)} categories. "
        f"At {level['label']} level, {skills_target} skills and {categories_target} "
        f"categories earn full marks. {len(declared)} are listed in an explicit "
        f"skills section."
    )
    return _component("skills_breadth", "Skills Breadth", breadth + diversity, reason,
                      skills, {"categories": sorted(categories),
                               "declared_count": len(declared),
                               "total_count": len(skills),
                               "skills_target": skills_target,
                               "categories_target": categories_target})


def _score_role_relevance(resume: dict, role: dict, level: dict) -> Dict[str, object]:
    skills = set(resume.get("skills") or [])
    core = list(role.get("core_skills") or [])
    preferred = list(role.get("preferred_skills") or [])

    core_hits = sort_skills(skills & set(core))
    preferred_hits = sort_skills(skills & set(preferred))
    core_missing = sort_skills(set(core) - skills)

    # Core skills carry three quarters of the weight: missing a must-have hurts
    # more than missing a nice-to-have helps.
    core_max = WEIGHTS["role_relevance"] * 0.75
    preferred_max = WEIGHTS["role_relevance"] - core_max
    target = float(level["skill_coverage_target"])

    core_raw = _coverage(skills, core)
    preferred_raw = _coverage(skills, preferred)
    score = (scaled_coverage(core_raw, target) * core_max
             + scaled_coverage(preferred_raw, target) * preferred_max)

    reason = (
        f"Matched {len(core_hits)}/{len(core)} core skills ({core_raw:.0%}) and "
        f"{len(preferred_hits)}/{len(preferred)} preferred skills for "
        f"{role.get('title')}. {expectation_note(level)}"
        + (f" Core skills not found: {', '.join(core_missing)}." if core_missing else "")
    )
    evidence = [f"Core: {s}" for s in core_hits] + [f"Preferred: {s}" for s in preferred_hits]
    return _component("role_relevance", "Target Role Relevance", score, reason, evidence,
                      {"core_matched": core_hits, "core_missing": core_missing,
                       "preferred_matched": preferred_hits,
                       "core_total": len(core), "preferred_total": len(preferred),
                       "core_coverage": round(core_raw, 3),
                       "preferred_coverage": round(preferred_raw, 3),
                       "coverage_target": target})


def _score_jd_keywords(resume: dict, jd_text: str, jd_source: str,
                       level: dict) -> Dict[str, object]:
    """
    Keyword overlap against the actual job description.

    This is the component closest to how a real ATS ranks applicants: it
    compares the resume against *this* posting rather than a generic role.
    """
    jd_skills = extract_skills(jd_text or "")
    if not jd_skills:
        reason = ("No recognised skill keywords could be extracted from the job "
                  "description, so this component could not be assessed.")
        return _component("jd_keyword_match", "Job Description Keyword Match", 0,
                          reason, [], {"jd_source": jd_source, "jd_keywords": []})

    resume_skills = set(resume.get("skills") or [])
    matched = sort_skills(resume_skills & set(jd_skills))
    missing = sort_skills(set(jd_skills) - resume_skills)
    coverage = len(matched) / len(jd_skills)
    target = float(level["skill_coverage_target"])
    scaled = scaled_coverage(coverage, target)

    reason = (
        f"The resume covers {len(matched)} of {len(jd_skills)} skill keywords found "
        f"in the job description ({coverage:.0%}). Keywords come from {jd_source}. "
        f"{expectation_note(level)}"
        + (f" Not found in the resume: {', '.join(missing[:10])}"
           f"{'...' if len(missing) > 10 else ''}." if missing else "")
    )
    return _component("jd_keyword_match", "Job Description Keyword Match",
                      scaled * WEIGHTS["jd_keyword_match"], reason, matched,
                      {"jd_source": jd_source, "jd_keywords": jd_skills,
                       "matched": matched, "missing": missing,
                       "coverage": round(coverage, 3),
                       "coverage_target": target})


def _score_experience_projects(resume: dict, level: dict) -> Dict[str, object]:
    experience = resume.get("experience") or []
    projects = resume.get("projects") or []

    # How the 10 points divide depends on career stage. A fresher with no
    # formal employment would otherwise forfeit half this component by
    # definition, so projects carry most of it for them.
    experience_max = float(level["experience_points"])
    project_max = float(level["project_points"])

    def side_score(entries: List[dict], max_points: float) -> float:
        if not entries or max_points <= 0:
            return 0.0
        count_points = min(1.0, len(entries) / 3.0) * (max_points * 0.6)
        # A bullet that names a technology is stronger evidence than prose.
        with_skills = sum(1 for e in entries if e.get("skills"))
        detail_points = min(1.0, with_skills / 2.0) * (max_points * 0.4)
        return count_points + detail_points

    score = side_score(experience, experience_max) + side_score(projects, project_max)
    evidence = [e["text"][:160] for e in (experience + projects)[:6]]
    reason = (
        f"{len(experience)} experience entr{'y' if len(experience) == 1 else 'ies'} and "
        f"{len(projects)} project entr{'y' if len(projects) == 1 else 'ies'} were parsed. "
        f"{sum(1 for e in experience + projects if e.get('skills'))} of them name "
        f"specific technologies. At {level['label']} level these are worth up to "
        f"{experience_max:.0f} and {project_max:.0f} points respectively."
    )
    return _component("experience_projects", "Experience & Projects", score, reason, evidence,
                      {"experience_count": len(experience), "project_count": len(projects),
                       "experience_max": experience_max, "project_max": project_max})


def _score_achievements(resume: dict, level: dict) -> Dict[str, object]:
    achievements = [a for a in (resume.get("achievements") or []) if a.get("quantified")]
    target = int(level["achievements_for_full_marks"])
    score = min(1.0, len(achievements) / target) * WEIGHTS["quantifiable_achievements"]
    reason = (
        f"{len(achievements)} quantified achievement(s) detected. At "
        f"{level['label']} level, {target} earn full marks. Quantified means the "
        f"line contains a measurable figure such as a percentage, a multiplier or a count."
        if achievements else
        "No quantified achievements were detected. Adding measurable outcomes "
        "(percentages, counts, time saved) is the fastest way to gain these points."
    )
    return _component("quantifiable_achievements", "Quantifiable Achievements", score, reason,
                      [a["text"][:160] for a in achievements],
                      {"count": len(achievements), "target": target})


def _score_education(resume: dict) -> Dict[str, object]:
    education = resume.get("education") or []
    score, evidence, notes = 0.0, [], []

    if education:
        score += 2
        evidence.extend(e["text"][:160] for e in education[:3])
    else:
        notes.append("no education entries parsed")

    if any(e.get("degree") for e in education):
        score += 2
        degrees = [e["degree"] for e in education if e.get("degree")]
        evidence.append(f"Degree detected: {', '.join(degrees[:3])}")
    else:
        notes.append("no recognisable degree name")

    if any(e.get("score") for e in education):
        score += 1
        scores = [e["score"] for e in education if e.get("score")]
        evidence.append(f"Academic score detected: {', '.join(str(s) for s in scores[:3])}")
    else:
        notes.append("no CGPA or percentage")

    reason = (f"{len(education)} education entr{'y' if len(education) == 1 else 'ies'} parsed."
              + (f" Points were lost for: {', '.join(notes)}." if notes else
                 " Degree and academic score were both detected."))
    return _component("education", "Education", score, reason, evidence,
                      {"entries": len(education)})


def _score_readability(resume: dict) -> Dict[str, object]:
    signals = resume.get("readability") or {}
    score, evidence, issues = 0.0, [], []

    if signals.get("uses_bullets"):
        score += 2
        evidence.append(f"{signals.get('bullet_count', 0)} bullet points detected")
    else:
        issues.append("fewer than 3 bullet points (ATS parsers handle bullets better than prose)")

    verbs = signals.get("action_verbs_used") or []
    if len(verbs) >= 3:
        score += 1
        evidence.append(f"Bullets start with action verbs: {', '.join(verbs[:6])}")
    else:
        issues.append("fewer than 3 distinct action verbs starting bullets")

    words = int(signals.get("word_count") or 0)
    low, high = IDEAL_WORD_RANGE
    if low <= words <= high:
        score += 1
        evidence.append(f"Length is {words} words, within the {low}-{high} word target")
    else:
        issues.append(f"length is {words} words, outside the {low}-{high} word target")

    avg_bullet = float(signals.get("avg_bullet_words") or 0)
    if 0 < avg_bullet <= 30:
        score += 1
        evidence.append(f"Bullets average {avg_bullet} words, which stays scannable")
    elif avg_bullet > 30:
        issues.append(f"bullets average {avg_bullet} words, which is long for a scan")

    reason = ("Formatting signals look healthy." if not issues
              else "Points were lost for: " + "; ".join(issues) + ".")
    return _component("formatting_readability", "Formatting & Readability", score, reason,
                      evidence, {"signals": signals})


def _score_github(github: Optional[dict], role: dict) -> Dict[str, object]:
    max_score = WEIGHTS["github_evidence"]
    if not github or github.get("unavailable") or not github.get("profile"):
        reason = (github or {}).get("reason") or (
            "No GitHub profile was analysed. Adding your GitHub username can earn "
            f"up to {max_score} points here."
        )
        return _component("github_evidence", "GitHub Profile Evidence", 0, reason, [],
                          {"analysed": False})

    stats = github.get("stats") or {}
    github_skills = set(github.get("skills") or [])
    role_skills = set(role.get("core_skills") or []) | set(role.get("preferred_skills") or [])
    relevant = sort_skills(github_skills & role_skills)

    score, evidence = 0.0, []
    score += 1
    evidence.append(f"Public profile found: @{(github['profile'] or {}).get('username')}")

    originals = int(stats.get("original_repositories") or 0)
    if originals >= 3:
        score += 1
        evidence.append(f"{originals} original (non-forked) public repositories")

    documented = int(stats.get("repositories_with_description") or 0)
    if documented >= 2:
        score += 1
        evidence.append(f"{documented} repositories have a description, which ATS-style "
                        f"keyword scanning can read")

    if relevant:
        score += min(2.0, len(relevant) / 3.0 * 2.0)
        evidence.append(f"Role-relevant skills evidenced in code: {', '.join(relevant[:8])}")

    reason = (
        f"GitHub shows {originals} original repositories and evidence for "
        f"{len(relevant)} skill(s) relevant to {role.get('title')}."
        if relevant else
        f"GitHub profile analysed, but no skills relevant to {role.get('title')} "
        f"were evidenced in public repositories."
    )
    return _component("github_evidence", "GitHub Profile Evidence", score, reason, evidence,
                      {"analysed": True, "relevant_skills": relevant})


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def score_resume(
    resume: dict,
    role: dict,
    jd_text: str = "",
    jd_source: str = "the selected job description",
    github: Optional[dict] = None,
    experience_level: str = DEFAULT_LEVEL,
) -> Dict[str, object]:
    """
    Compute the full ATS report.

    ``jd_text``           -- the job description to match keywords against. When
                             the user supplies none, the caller passes the text
                             of the role's job descriptions from the knowledge base.
    ``github``            -- the result of :func:`github_analyzer.analyze_github`,
                             or ``None`` if GitHub analysis was skipped or failed.
    ``experience_level``  -- career stage, which sets the coverage expected for
                             full marks. See ``experience_levels.py``.
    """
    level = resolve_level(experience_level)

    components = [
        _score_contact(resume),
        _score_sections(resume),
        _score_skills_breadth(resume, level),
        _score_role_relevance(resume, role, level),
        _score_jd_keywords(resume, jd_text, jd_source, level),
        _score_experience_projects(resume, level),
        _score_achievements(resume, level),
        _score_education(resume),
        _score_readability(resume),
        _score_github(github, role),
    ]

    # The headline number is, by construction, the sum of the parts.
    total = sum(int(c["score"]) for c in components)

    return {
        "score": total,
        "max_score": MAX_TOTAL,
        "band": _band(total),
        "components": components,
        "weights": dict(WEIGHTS),
        "experience_level": {
            "id": level["id"],
            "label": level["label"],
            "description": level["description"],
            "skill_coverage_target": level["skill_coverage_target"],
        },
        "methodology": (
            "Rule-based and deterministic. Each component is computed from parsed "
            "resume fields using fixed weights; the total is the arithmetic sum of "
            "the component scores. Coverage-based components are scored against the "
            f"{float(level['skill_coverage_target']):.0%} coverage expected at "
            f"{level['label']} level, not against an unreachable 100%. No language "
            "model contributes to this number."
        ),
        "biggest_opportunities": _opportunities(components),
    }


def _band(total: int) -> Dict[str, str]:
    if total >= 80:
        return {"label": "Strong", "summary": "This resume should pass most ATS filters for this role."}
    if total >= 65:
        return {"label": "Good", "summary": "Competitive, with a few clear gaps worth closing."}
    if total >= 50:
        return {"label": "Moderate", "summary": "Likely to be filtered out by stricter ATS screens."}
    return {"label": "Needs Work", "summary": "Significant gaps in structure, keywords or evidence."}


def _opportunities(components: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """The components losing the most points -- i.e. where to improve first."""
    losses = [
        {
            "component": c["component"],
            "points_available": int(c["max_score"]) - int(c["score"]),
            "reason": c["reason"],
        }
        for c in components if int(c["score"]) < int(c["max_score"])
    ]
    losses.sort(key=lambda d: d["points_available"], reverse=True)
    return losses[:4]

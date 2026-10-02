"""
summary_builder.py
==================

Turns the computed ATS and job-match reports into a short, scannable summary.

No language model is involved anywhere in this project. Every sentence below is
assembled from numbers that ``ats_scorer`` and ``job_matcher`` have already
produced, by fixed rules in this file. That means the summary is deterministic
(same analysis, same words), cannot invent a skill or a requirement that was
not computed, and can be traced line by line back to a component score.

Output shape
------------
Three sections, each a title plus a few one-line bullets:

    1. ATS Score      -- what the resume scored and where the points went
    2. Job Match      -- which requirements are evidenced and which are not
    3. Do these next  -- the highest-impact fixes, in priority order
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

# Keep bullets to a single line: long skill lists are truncated.
MAX_SKILLS_IN_BULLET = 6
MAX_ACTIONS = 3


def _join(items: Sequence[str], limit: int = MAX_SKILLS_IN_BULLET) -> str:
    """Comma-join a list, trimming the tail to keep the bullet one line long."""
    items = list(items)
    if not items:
        return ""
    shown = items[:limit]
    text = ", ".join(shown)
    remaining = len(items) - len(shown)
    return f"{text} (+{remaining} more)" if remaining > 0 else text


def _first_sentence(text: str) -> str:
    """The leading clause of a component reason, for use inside a bullet."""
    cleaned = " ".join((text or "").split())
    for stop in (". ", "; "):
        if stop in cleaned:
            cleaned = cleaned.split(stop, 1)[0]
            break
    return cleaned.rstrip(".")


# ---------------------------------------------------------------------------
# Section 1 -- ATS
# ---------------------------------------------------------------------------

def _ats_section(ats: dict) -> Dict[str, object]:
    components = ats["components"]
    full_marks = [c for c in components if c["score"] == c["max_score"]]
    lost = sorted(components, key=lambda c: c["max_score"] - c["score"], reverse=True)
    weakest = [c for c in lost if c["score"] < c["max_score"]]

    bullets: List[str] = []

    if full_marks:
        bullets.append(
            f"Full marks on {_join([c['component'] for c in full_marks], 5)}."
        )
    else:
        bullets.append("No component scored full marks yet.")

    if weakest:
        worst = weakest[0]
        bullets.append(
            f"Weakest: {worst['component']} at {worst['score']}/{worst['max_score']} "
            f"- {_first_sentence(worst['reason'])}."
        )
        available = sum(c["max_score"] - c["score"] for c in weakest)
        bullets.append(
            f"{available} points are still available across "
            f"{len(weakest)} component{'' if len(weakest) == 1 else 's'}."
        )
    else:
        bullets.append("Every component scored full marks - nothing left to fix here.")

    return {
        "id": "ats",
        "title": f"ATS Score - {ats['score']}/{ats['max_score']} ({ats['band']['label']})",
        "bullets": bullets,
        "ordered": False,
    }


# ---------------------------------------------------------------------------
# Section 2 -- Job match
# ---------------------------------------------------------------------------

def _match_section(match: dict, github: Optional[dict]) -> Dict[str, object]:
    core = match["core_skills"]
    matched, missing = core["matched"], core["missing"]
    level = match.get("experience_level") or {}

    bullets: List[str] = []

    if matched:
        bullets.append(
            f"{len(matched)} of {core['total']} core requirements evidenced: "
            f"{_join(matched)}."
        )
    else:
        bullets.append(f"None of the {core['total']} core requirements are evidenced yet.")

    if missing:
        bullets.append(f"Not evidenced: {_join(missing)}.")
    else:
        bullets.append("Every core requirement is evidenced.")

    if level:
        target = float(level.get("skill_coverage_target") or 0)
        bullets.append(
            f"Scored at {level.get('label')} level, where {target:.0%} coverage "
            f"earns full marks."
        )

    # One line on evidence quality, which is what GitHub actually buys you.
    both = match["evidence_summary"]["both"]
    if github and github.get("profile"):
        if both:
            bullets.append(
                f"Backed by public code as well as the resume: {_join(both, 4)}."
            )
        else:
            bullets.append(
                "No skill appears in both your resume and your public repositories, "
                "so nothing is corroborated."
            )
    else:
        bullets.append("No GitHub profile was analysed, so nothing could be corroborated.")

    return {
        "id": "match",
        "title": f"Job Match - {match['score']}/{match['max_score']} "
                 f"({match['verdict']['label']})",
        "bullets": bullets,
        "ordered": False,
    }


# ---------------------------------------------------------------------------
# Section 3 -- Actions
# ---------------------------------------------------------------------------

def _action_section(ats: dict, match: dict, resume: dict) -> Dict[str, object]:
    """
    The highest-impact fixes, derived from which components actually lost points.

    Ordered by points recoverable, so the first item is always the one worth
    doing first.
    """
    missing_core = match["core_skills"]["missing"]
    actions: List[str] = []

    if missing_core:
        actions.append(
            f"Build and document one project that genuinely uses "
            f"{_join(missing_core[:3], 3)}, then name those technologies in the "
            f"project bullet."
        )

    for opportunity in ats.get("biggest_opportunities") or []:
        name = opportunity["component"]
        points = opportunity["points_available"]
        if name == "Job Description Keyword Match":
            actions.append(
                f"Mirror the job description's own wording in your skills section "
                f"- it is the heaviest component at {points} points recoverable."
            )
        elif name == "GitHub Profile Evidence":
            actions.append(
                f"Add your GitHub username, and give your best repositories a "
                f"one-line description and topic tags (+{points})."
            )
        elif name == "Quantifiable Achievements":
            actions.append(
                f"Rewrite your strongest bullets to include a number - a percentage, "
                f"a count of users or records, or time saved (+{points})."
            )
        elif name == "Contact Information":
            actions.append(
                f"Add the missing contact fields as plain text, not inside an image "
                f"or a header (+{points})."
            )
        elif name == "Resume Sections":
            missing_sections = resume.get("missing_core_sections") or []
            actions.append(
                f"Add clearly labelled headings for "
                f"{_join(missing_sections, 3) or 'the missing sections'} (+{points})."
            )
        elif name == "Formatting & Readability":
            actions.append(
                f"Convert dense paragraphs into bullets that start with an action "
                f"verb (+{points})."
            )
        elif name == "Experience & Projects":
            actions.append(
                f"Describe each project with what you built and which technologies "
                f"you used (+{points})."
            )
        elif name == "Skills Breadth":
            actions.append(
                f"List the tools you have actually used across languages, frameworks "
                f"and databases (+{points})."
            )

    if not actions:
        actions.append(
            "Nothing critical is missing - tailor the skills section per application "
            "and keep this resume."
        )

    # De-duplicate while preserving priority order.
    seen, ordered = set(), []
    for action in actions:
        if action not in seen:
            seen.add(action)
            ordered.append(action)

    return {
        "id": "actions",
        "title": "Do these next",
        "bullets": ordered[:MAX_ACTIONS],
        "ordered": True,
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_summary(
    ats: dict,
    match: dict,
    resume: dict,
    github: Optional[dict] = None,
) -> Dict[str, object]:
    """Assemble the three-section summary from already-computed results."""
    return {
        "sections": [
            _ats_section(ats),
            _match_section(match, github),
            _action_section(ats, match, resume),
        ],
        "generated_by": "rules",
        "note": (
            "Generated from the computed scores by fixed rules. No language model "
            "is used anywhere in this application."
        ),
    }

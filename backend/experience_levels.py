"""
experience_levels.py
====================

Career-stage expectations used by the scorers.

Why this exists
---------------
A final-year student will never evidence every skill in a job description, and
scoring them against a senior candidate's bar makes the number meaningless --
a fresher matching 20 of 55 requirements is doing *well*, not badly.

The fix is deliberately NOT "add bonus points to freshers", which would be
arbitrary and impossible to defend. Instead the *expectation* changes while the
arithmetic stays identical: each level declares the coverage at which a
component earns full marks, and coverage is scored relative to that target
rather than against an unreachable 100%.

    scaled_coverage = min(1.0, actual_coverage / expected_coverage)

So a fresher covering 36% of requirements scores 36/50 = 72% of the available
points, while a senior candidate at the same 36% scores 36/85 = 42%. The rule
is one line, the numbers are published below, and every component reports which
expectation it applied.
"""

from __future__ import annotations

from typing import Dict, List

DEFAULT_LEVEL = "fresher"

# ---------------------------------------------------------------------------
# The levels.
#
#   skill_coverage_target        coverage at which skill components max out
#   skills_for_full_breadth      distinct skills for full "Skills Breadth" marks
#   categories_for_full_diversity  distinct skill categories for full marks
#   achievements_for_full_marks  quantified achievements for full marks
#   project_points /             how the 10-point Experience & Projects
#   experience_points            component is split between the two
# ---------------------------------------------------------------------------
EXPERIENCE_LEVELS: Dict[str, Dict[str, object]] = {
    "fresher": {
        "id": "fresher",
        "label": "Fresher (0-1 years)",
        "description": "Final-year student or recent graduate.",
        "skill_coverage_target": 0.50,
        "skills_for_full_breadth": 10,
        "categories_for_full_diversity": 4,
        "achievements_for_full_marks": 2,
        # Freshers usually have no formal employment, so academic and personal
        # projects carry most of this component instead of costing them half of
        # it by default. Internships still count as experience.
        "project_points": 7,
        "experience_points": 3,
    },
    "mid": {
        "id": "mid",
        "label": "2-4 years",
        "description": "Early-career professional with delivery experience.",
        "skill_coverage_target": 0.70,
        "skills_for_full_breadth": 15,
        "categories_for_full_diversity": 5,
        "achievements_for_full_marks": 3,
        "project_points": 5,
        "experience_points": 5,
    },
    "senior": {
        "id": "senior",
        "label": "5+ years",
        "description": "Experienced professional expected to cover most requirements.",
        "skill_coverage_target": 0.85,
        "skills_for_full_breadth": 20,
        "categories_for_full_diversity": 5,
        "achievements_for_full_marks": 4,
        "project_points": 5,
        "experience_points": 5,
    },
}

ORDERED_LEVEL_IDS: List[str] = ["fresher", "mid", "senior"]


def resolve_level(level_id: str | None) -> Dict[str, object]:
    """Return a level definition, falling back to the default when unknown."""
    return EXPERIENCE_LEVELS.get((level_id or "").strip().lower()) \
        or EXPERIENCE_LEVELS[DEFAULT_LEVEL]


def is_valid_level(level_id: str | None) -> bool:
    return (level_id or "").strip().lower() in EXPERIENCE_LEVELS


def scaled_coverage(actual: float, target: float) -> float:
    """
    Score ``actual`` coverage against the level's expectation.

    Returns a ratio in [0, 1]: 1.0 once the candidate reaches (or exceeds) the
    coverage expected at their career stage.
    """
    if target <= 0:
        return 1.0
    return min(1.0, max(0.0, actual) / target)


def expectation_note(level: Dict[str, object]) -> str:
    """One clause explaining the bar applied, for inclusion in a reason string."""
    target = float(level["skill_coverage_target"])       # type: ignore[arg-type]
    return (f"At {level['label']} level, {target:.0%} coverage earns full marks "
            f"on this component.")


def public_levels() -> List[Dict[str, object]]:
    """The level list exposed to the frontend."""
    return [
        {
            "id": EXPERIENCE_LEVELS[level_id]["id"],
            "label": EXPERIENCE_LEVELS[level_id]["label"],
            "description": EXPERIENCE_LEVELS[level_id]["description"],
            "skill_coverage_target": EXPERIENCE_LEVELS[level_id]["skill_coverage_target"],
        }
        for level_id in ORDERED_LEVEL_IDS
    ]

"""
interview_prep.py
=================

Objective 3: which interview questions is this candidate likely to face?

Questions live in ``data/interview_questions/*.json``, each tagged with the
taxonomy skills it tests, a kind, and a difficulty that matches the experience
levels used elsewhere in the project.

Why this does NOT use RAG
-------------------------
Objective 2 uses semantic retrieval because the job-description corpus is
large, varied, and written by other people -- embeddings find relevance that no
one labelled. The question bank is the opposite: it is small and *we* wrote the
tags. Looking up a tag we set ourselves is exact, while embedding the questions
and retrieving them by similarity would only be approximate. Using the weaker
tool because it is the more impressive one would be the wrong call.

RAG still does the ordering: questions are ranked by how strongly the retrieved
job descriptions demanded the skill they test, which is a number the matcher
has already computed.

Three groups
------------
*Prove these*   -- skills the candidate has that the role requires. They will
                   be asked to demonstrate them.
*Handle these*  -- required skills the candidate is missing. They will probably
                   still be asked, and "not yet, but here is what I know" is a
                   far better answer prepared than improvised.
*About you*     -- project and behavioural questions, which apply to everyone.
"""

from __future__ import annotations

import json
import logging
import pathlib
from functools import lru_cache
from typing import Dict, List, Optional, Sequence

import config
from experience_levels import ORDERED_LEVEL_IDS, resolve_level

logger = logging.getLogger("career_engine.interview_prep")

QUESTIONS_DIR = config.DATA_DIR / "interview_questions"

MAX_PER_GROUP = 6
MAX_PER_SKILL = 2


@lru_cache(maxsize=1)
def load_questions() -> List[Dict[str, object]]:
    """Load and cache the question bank."""
    questions: List[Dict[str, object]] = []
    if not QUESTIONS_DIR.exists():
        logger.warning("No interview question bank at %s", QUESTIONS_DIR)
        return questions

    for path in sorted(QUESTIONS_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            logger.error("Skipping malformed question file %s: %s", path.name, exc)
            continue
        area = payload.get("area", path.stem)
        for question in payload.get("questions") or []:
            question["area"] = area
            questions.append(question)
    return questions


def _level_rank(level_id: str) -> int:
    try:
        return ORDERED_LEVEL_IDS.index(level_id)
    except ValueError:
        return 0


def _pick(
    pool: Sequence[dict],
    skills: Sequence[str],
    level_id: str,
    demand: Dict[str, float],
    limit: int,
) -> List[dict]:
    """
    Choose questions covering ``skills``, preferring the candidate's level.

    A question above the candidate's level is included only when that skill has
    nothing at or below it -- otherwise a skill whose only question is marked
    "mid" would silently vanish for a fresher. Those are flagged as a stretch.
    """
    wanted = list(skills)
    ceiling = _level_rank(level_id)
    chosen: List[dict] = []
    seen_ids: set = set()
    per_skill: Dict[str, int] = {}

    # Loudest-demanded skills first, so the most likely questions lead.
    for skill in sorted(wanted, key=lambda s: -demand.get(s, 0.0)):
        matching = [q for q in pool if skill in (q.get("skills") or [])]
        at_level = [q for q in matching if _level_rank(q["difficulty"]) <= ceiling]
        usable = at_level or matching          # fall back to a stretch question

        for question in usable:
            if question["id"] in seen_ids:
                continue
            if per_skill.get(skill, 0) >= MAX_PER_SKILL:
                break
            stretch = _level_rank(question["difficulty"]) > ceiling
            chosen.append({
                **{k: v for k, v in question.items() if k != "roles"},
                "matched_skill": skill,
                "stretch": stretch,
                "demand": round(demand.get(skill, 0.0), 3),
            })
            seen_ids.add(question["id"])
            per_skill[skill] = per_skill.get(skill, 0) + 1
            if len(chosen) >= limit:
                return chosen
    return chosen


def build_interview_prep(
    match: dict,
    role: dict,
    experience_level: str,
) -> Dict[str, object]:
    """Assemble the three question groups from an already-computed match."""
    level = resolve_level(experience_level)
    level_id = str(level["id"])
    pool = load_questions()

    demand = {
        entry["skill"]: float(entry.get("max_similarity") or 0.0)
        for entry in (match.get("requirements_derived_from_rag") or [])
    }

    have = list(match["core_skills"]["matched"]) + list(match["preferred_skills"]["matched"])
    missing = list(match["core_skills"]["missing"])

    general = [q for q in pool if not q.get("skills")]
    skill_pool = [q for q in pool if q.get("skills")]

    prove = _pick(skill_pool, have, level_id, demand, MAX_PER_GROUP)
    gaps = _pick([q for q in skill_pool if q["id"] not in {p["id"] for p in prove}],
                 missing, level_id, demand, MAX_PER_GROUP)

    ceiling = _level_rank(level_id)
    about_you = [
        {**{k: v for k, v in q.items() if k != "roles"},
         "matched_skill": None, "stretch": False, "demand": None}
        for q in general if _level_rank(q["difficulty"]) <= ceiling
    ][:MAX_PER_GROUP]

    groups = [
        {
            "id": "prove",
            "title": "Be ready to prove these",
            "why": ("Skills you claim that this role requires. Expect to be asked to "
                    "demonstrate them, not just list them."),
            "questions": prove,
        },
        {
            "id": "gaps",
            "title": "Be ready to handle these gaps",
            "why": ("Requirements you cannot yet evidence. You will probably still be "
                    "asked. Prepare an honest answer now rather than improvising one."),
            "questions": gaps,
        },
        {
            "id": "about_you",
            "title": "About you and your projects",
            "why": "Asked in almost every interview, regardless of the role.",
            "questions": about_you,
        },
    ]
    groups = [g for g in groups if g["questions"]]
    total = sum(len(g["questions"]) for g in groups)

    return {
        "target_role": role.get("title"),
        "experience_level": {"id": level_id, "label": level["label"]},
        "groups": groups,
        "total_questions": total,
        "bank_size": len(pool),
        "headline": _headline(total, prove, gaps, role),
        "methodology": (
            "Questions are selected by the skill tags in the local question bank, "
            "filtered to your experience level, and ordered by how strongly the "
            "retrieved job descriptions demanded each skill. Selection is by tag "
            "rather than semantic search because the bank is small and curated, so "
            "an exact tag beats an approximate embedding match. No answers are "
            "provided: each question states what the interviewer is checking for, "
            "so you can prepare your own."
        ),
    }


def _headline(total: int, prove: List[dict], gaps: List[dict], role: dict) -> str:
    if not total:
        return f"No questions available for {role.get('title')} yet."
    parts = [f"{total} questions to prepare for {role.get('title')}"]
    if gaps:
        skills = sorted({q["matched_skill"] for q in gaps if q.get("matched_skill")})
        parts.append(f"including {len(gaps)} on gaps you cannot yet evidence "
                     f"({', '.join(skills[:3])})")
    return ". ".join(parts) + "."

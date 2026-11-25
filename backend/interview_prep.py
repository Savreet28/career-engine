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

Questions from the candidate's own resume
-----------------------------------------
The bank is written in advance, so it cannot ask about work it has never seen.
An interviewer, however, opens the resume and asks about the projects on it.
``_resume_questions`` closes that gap: for each parsed project or role it takes
the skills found inside that entry and builds a question from a fixed template
chosen by skill category, carrying the resume line it came from as evidence.

Nothing is invented. The templates are written here, the skills come from the
shared taxonomy, and the entry text is quoted from the resume -- so a generated
question is as traceable as a selected one. They are marked ``source:
"resume"`` to keep them distinguishable from the curated bank.
"""

from __future__ import annotations

import json
import logging
import pathlib
from functools import lru_cache
from typing import Dict, List, Optional, Sequence

import config
from experience_levels import ORDERED_LEVEL_IDS, resolve_level
from skills_data import skill_category

logger = logging.getLogger("career_engine.interview_prep")

QUESTIONS_DIR = config.DATA_DIR / "interview_questions"

MAX_PER_GROUP = 6
MAX_PER_SKILL = 2
MAX_RESUME_QUESTIONS = 6

# How long a quoted project title may get before it is cut.
LABEL_CHARS = 52


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
        # Hardest first among those the level allows: a senior candidate should
        # meet senior questions, not the fresher ones that happen to be listed
        # first in the bank. Python's sort is stable, so a fresher -- for whom
        # every allowed question is already "fresher" -- sees no change.
        at_level.sort(key=lambda q: -_level_rank(q["difficulty"]))
        # Nothing at or below the level: take the gentlest stretch available,
        # so a fresher whose only question on a skill is hard gets the mid one
        # rather than the senior one.
        usable = at_level or sorted(matching,
                                    key=lambda q: _level_rank(q["difficulty"]))

        for question in usable:
            if question["id"] in seen_ids:
                continue
            if per_skill.get(skill, 0) >= MAX_PER_SKILL:
                break
            stretch = _level_rank(question["difficulty"]) > ceiling
            chosen.append({
                **{k: v for k, v in question.items() if k != "roles"},
                "source": "bank",
                "evidence": None,
                "matched_skill": skill,
                "stretch": stretch,
                "demand": round(demand.get(skill, 0.0), 3),
            })
            seen_ids.add(question["id"])
            per_skill[skill] = per_skill.get(skill, 0) + 1
            if len(chosen) >= limit:
                return chosen
    return chosen


# ---------------------------------------------------------------------------
# Questions built from the candidate's own resume
#
# One template per skill category. The wording is fixed here; only the skill,
# the quoted project label and the resume line vary. That keeps a generated
# question exactly as defensible as a curated one -- it states a rule, and it
# carries the evidence the rule fired on.
# ---------------------------------------------------------------------------
CHOICE_TEMPLATES: Dict[str, tuple] = {
    "ml": (
        "Your {kind} \"{label}\" uses {skill}. Why {skill} rather than a simpler "
        "baseline, and how did you measure that it actually helped?",
        "Whether the method was chosen deliberately and can be shown to have "
        "worked, rather than picked because it was the most advanced option.",
    ),
    "backend": (
        "Your {kind} \"{label}\" uses {skill}. What happens to it under load, and "
        "what would you fix first?",
        "Whether you have thought past 'it works on my machine' to failure and "
        "scale.",
    ),
    "frontend": (
        "Your {kind} \"{label}\" uses {skill}. Which part of the interface was "
        "hardest to get right, and how did you structure it?",
        "Whether you made real design decisions or followed a tutorial layout.",
    ),
    "data": (
        "Your {kind} \"{label}\" uses {skill}. How did you check the data was "
        "correct before you trusted the result?",
        "Whether you validate inputs, or assume a clean dataset and inherit its "
        "errors silently.",
    ),
    "devops": (
        "Your {kind} \"{label}\" uses {skill}. What breaks if that step fails, and "
        "how would you find out it had?",
        "Whether you understand the tool's role in the system rather than the "
        "commands you ran.",
    ),
    "language": (
        "Your {kind} \"{label}\" is written in {skill}. Which part would you "
        "rewrite now that it is finished, and why?",
        "Whether you can criticise your own code, which is what separates a "
        "finished project from a submitted one.",
    ),
    "concept": (
        "Your {kind} \"{label}\" relies on {skill}. Explain it to someone who has "
        "never seen your project.",
        "Whether you understand the idea itself or only the implementation you "
        "copied it into.",
    ),
    "tool": (
        "Your {kind} \"{label}\" uses {skill}. What did it save you, and what did "
        "it cost you?",
        "Whether tools are chosen for a reason or added because they are "
        "popular.",
    ),
}

MEASURE_TEMPLATE = (
    "Your {kind} \"{label}\" does not state a measurable result. What number "
    "would you put on it, and how would you measure it?",
    "Whether you can quantify your own work. An interviewer reads the same line "
    "and asks the same thing.",
)

TRADEOFF_TEMPLATE = (
    "Your {kind} \"{label}\" combines {skills}. Which of those decisions would "
    "you defend hardest, and which would you drop?",
    "Whether the stack was designed or accumulated, and whether you can rank "
    "your own choices.",
)


def _label(text: str) -> str:
    """
    A short, quotable title for a resume entry.

    Cuts at the earliest structural separator rather than the first one in a
    fixed order: "Intern, Acme (Jun 2024 - Aug 2024)" must cut at the bracket,
    not at the dash inside the dates. A cut that would leave almost nothing is
    skipped, so "Node.js API - built for X" does not become "Node".
    """
    head = str(text or "").strip().splitlines()[0] if text else ""
    head = " ".join(head.split())

    # ". " rather than "." so that "Node.js" is never split.
    separators = ("  -  ", " - ", " \u2014 ", " \u2013 ", " | ", " (", ": ", ". ")
    cuts = sorted(head.find(sep) for sep in separators if head.find(sep) > 0)
    for cut in cuts:
        if cut >= 8:
            head = head[:cut].strip()
            break

    if len(head) > LABEL_CHARS:
        head = head[:LABEL_CHARS].rstrip(" ,;:-") + "..."
    return head


def _resume_entries(resume: Optional[dict]) -> List[tuple]:
    """Parsed projects first, then roles -- the order an interviewer reads them."""
    entries: List[tuple] = []
    for kind, key in (("project", "projects"), ("role", "experience")):
        for index, entry in enumerate((resume or {}).get(key) or [], start=1):
            if _label(str(entry.get("text") or "")):
                entries.append((kind, index, entry))
    return entries


def _resume_questions(
    resume: Optional[dict],
    demand: Dict[str, float],
    level_id: str,
    limit: int = MAX_RESUME_QUESTIONS,
) -> List[dict]:
    """
    Build questions about the candidate's own projects and roles.

    Two passes, so several different projects are covered before any one of
    them is asked about twice.
    """
    entries = _resume_entries(resume)
    if not entries:
        return []

    def ask(kind, index, entry, slug, template, skill=None, skills=None):
        label = _label(str(entry.get("text") or ""))
        text, checking = template
        line = " ".join(str(entry.get("text") or "").split())
        return {
            "id": f"resume_{kind}_{index}_{slug}",
            "question": text.format(kind=kind, label=label, skill=skill,
                                    skills=skills),
            "what_they_are_checking": checking,
            "skills": [skill] if skill else list(entry.get("skills") or [])[:3],
            "difficulty": level_id,
            "kind": "project",
            "area": "Your own resume",
            "source": "resume",
            "evidence": line[:200] + ("..." if len(line) > 200 else ""),
            "matched_skill": skill,
            "stretch": False,
            "demand": round(demand.get(skill, 0.0), 3) if skill else None,
        }

    def lead_skill(entry) -> Optional[str]:
        skills = [s for s in (entry.get("skills") or [])]
        if not skills:
            return None
        # Most-demanded first so the question lands on what the job cares about;
        # alphabetical tie-break keeps it deterministic.
        return sorted(skills, key=lambda s: (-demand.get(s, 0.0), s))[0]

    first_pass: List[dict] = []
    second_pass: List[dict] = []
    for kind, index, entry in entries:
        skill = lead_skill(entry)
        if skill:
            template = CHOICE_TEMPLATES.get(skill_category(skill),
                                            CHOICE_TEMPLATES["concept"])
            first_pass.append(ask(kind, index, entry, "choice", template,
                                  skill=skill))

        if not entry.get("quantified"):
            second_pass.append(ask(kind, index, entry, "measure",
                                   MEASURE_TEMPLATE, skill=skill))
        elif len(entry.get("skills") or []) >= 3:
            named = (entry.get("skills") or [])[:3]
            listed = ", ".join(named[:-1]) + " and " + named[-1]
            second_pass.append(ask(kind, index, entry, "tradeoff",
                                   TRADEOFF_TEMPLATE, skill=lead_skill(entry),
                                   skills=listed))

    return (first_pass + second_pass)[:limit]


def build_interview_prep(
    match: dict,
    role: dict,
    experience_level: str,
    resume: Optional[dict] = None,
) -> Dict[str, object]:
    """
    Assemble the question groups from an already-computed match.

    ``resume`` is optional so the function still works for callers that only
    have a match; supplying it adds the questions drawn from the candidate's
    own projects, which is the part an interviewer actually opens with.
    """
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

    from_resume = _resume_questions(resume, demand, level_id)
    prove = _pick(skill_pool, have, level_id, demand, MAX_PER_GROUP)
    gaps = _pick([q for q in skill_pool if q["id"] not in {p["id"] for p in prove}],
                 missing, level_id, demand, MAX_PER_GROUP)

    ceiling = _level_rank(level_id)
    about_you = [
        {**{k: v for k, v in q.items() if k != "roles"},
         "source": "bank", "evidence": None,
         "matched_skill": None, "stretch": False, "demand": None}
        for q in general if _level_rank(q["difficulty"]) <= ceiling
    ][:MAX_PER_GROUP]

    groups = [
        {
            "id": "your_work",
            "title": "About your own projects",
            "why": ("Built from the projects and roles on your resume. An "
                    "interviewer reads the same lines and asks the same things, "
                    "so these come first."),
            "questions": from_resume,
        },
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
        "from_resume": len(from_resume),
        "headline": _headline(total, prove, gaps, role, len(from_resume)),
        "methodology": (
            "Questions about your own projects are built from the entries parsed "
            "out of your resume, using a fixed template chosen by the category of "
            "the skill found inside each entry; the resume line that produced the "
            "question travels with it. The rest are selected by skill tag from the "
            "local question bank, filtered to your experience level -- hardest "
            "first among those it allows -- and ordered by how strongly the "
            "retrieved job descriptions demanded each skill. Selection is by tag "
            "rather than semantic search because the bank is small and curated, so "
            "an exact tag beats an approximate embedding match. No answers are "
            "provided: each question states what the interviewer is checking for, "
            "so you can prepare your own."
        ),
    }


def _headline(total: int, prove: List[dict], gaps: List[dict], role: dict,
              from_resume: int = 0) -> str:
    if not total:
        return f"No questions available for {role.get('title')} yet."
    parts = [f"{total} questions to prepare for {role.get('title')}"]
    if from_resume:
        parts.append(f"{from_resume} of them are about your own projects")
    if gaps:
        skills = sorted({q["matched_skill"] for q in gaps if q.get("matched_skill")})
        parts.append(f"{len(gaps)} cover gaps you cannot yet evidence "
                     f"({', '.join(skills[:3])})")
    return ". ".join(parts) + "."

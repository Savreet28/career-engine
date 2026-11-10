"""
roadmap.py
==========

Objective 3: turn the gap list into an ordered learning plan.

The matcher produces a *set* of missing skills. A set is not actionable --
"learn PyTorch" is useless to someone who does not yet know Python. This module
adds order, using three signals that already exist or are derived, never
invented:

1. **Prerequisites** (``skill_graph.py``) -- what must come first.
2. **Demand** -- how strongly the retrieved job descriptions asked for a skill,
   taken from the RAG similarity scores the matcher already computed.
3. **Requirement level** -- core before preferred.

Hidden prerequisites
--------------------
A missing skill often depends on something the candidate also lacks but which
the job description never named. Someone missing PyTorch may also be missing
Deep Learning, which no posting listed because it is assumed. The roadmap
surfaces those, because skipping them is exactly how a learning plan fails.

No time estimates
-----------------
There are deliberately no "learn this in 3 weeks" figures. Nothing in this
project supports such a number, and inventing one would be the least
defensible thing in the application. Ordering is the real value.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from skill_graph import OFFICIAL_DOCS, all_prerequisites_of, depth_of, prerequisites_of
from skills_data import skill_category, sort_skills

# A soft cap: a phase shows at most this many steps, but the cap is relaxed
# wherever cutting a step would leave a later step referring to a blocker that
# is nowhere in the plan. See _close_over_prerequisites.
MAX_STEPS_PER_PHASE = 6


def _demand_map(match: dict) -> Dict[str, float]:
    """
    How strongly each skill was demanded, from the RAG retrieval the matcher
    already performed. Higher means the job descriptions asked for it more
    insistently.
    """
    demand: Dict[str, float] = {}
    for entry in match.get("requirements_derived_from_rag") or []:
        demand[entry["skill"]] = float(entry.get("max_similarity") or 0.0)
    return demand


def _why(skill: str, match: dict, level: str) -> str:
    """A one-line reason this skill is on the plan, quoting real evidence."""
    for row in match.get("skill_breakdown") or []:
        if row["skill"] != skill:
            continue
        evidence = (row.get("job_description_evidence") or [])
        if evidence:
            text = evidence[0]
            if len(text) > 150:
                text = text[:147].rstrip() + "..."
            return f'Asked for in the job description: "{text}"'
        reasons = row.get("why_required") or []
        if reasons:
            return reasons[0]
    if level == "prerequisite":
        return "Needed before the skills above it can be learned."
    return f"A {level} requirement for this role."


def _step(skill: str, requirement_level: str, match: dict,
          have: set, unlocks: Dict[str, List[str]]) -> Dict[str, object]:
    missing_prereqs = [p for p in prerequisites_of(skill) if p not in have]
    return {
        "skill": skill,
        "category": skill_category(skill),
        "requirement_level": requirement_level,
        "depth": depth_of(skill),
        "why": _why(skill, match, requirement_level),
        "prerequisites": prerequisites_of(skill),
        "missing_prerequisites": missing_prereqs,
        "ready_to_start": not missing_prereqs,
        "unlocks": sorted(unlocks.get(skill, [])),
        "docs": OFFICIAL_DOCS.get(skill),
    }


def build_roadmap(
    resume: dict,
    match: dict,
    role: dict,
    github: Optional[dict] = None,
) -> Dict[str, object]:
    """
    Build a phased learning plan from an already-computed match result.

    Phase 1 is whatever unlocks other work, Phase 2 the remaining must-haves,
    Phase 3 the nice-to-haves. Within a phase, shallower skills come first and
    ties break on how strongly the job descriptions demanded them.
    """
    have = set(resume.get("skills") or []) | set((github or {}).get("skills") or [])
    missing_core = list(match["core_skills"]["missing"])
    missing_preferred = list(match["preferred_skills"]["missing"])
    demand = _demand_map(match)

    # Prerequisites the candidate lacks, that no posting named because they are
    # assumed. These gate everything above them, so they lead the plan.
    hidden: set = set()
    for skill in missing_core + missing_preferred:
        for prereq in all_prerequisites_of(skill):
            if prereq not in have and prereq not in missing_core \
                    and prereq not in missing_preferred:
                hidden.add(prereq)

    # What each skill unlocks, so a step can say why it is worth doing first.
    everything = set(missing_core) | set(missing_preferred) | hidden
    unlocks: Dict[str, List[str]] = {}
    for skill in everything:
        for prereq in prerequisites_of(skill):
            unlocks.setdefault(prereq, []).append(skill)

    def order(skills: Sequence[str]) -> List[str]:
        # Shallow before deep so prerequisites precede dependants; then by how
        # loudly the job descriptions asked for it.
        return sorted(skills,
                      key=lambda s: (depth_of(s), -demand.get(s, 0.0), s))

    # Foundations: the hidden prerequisites, plus any missing core skill that
    # other missing skills depend on.
    gating_core = [s for s in missing_core if unlocks.get(s)]
    foundations = order(hidden | set(gating_core))
    rest_core = order([s for s in missing_core if s not in set(foundations)])
    rest_preferred = order([s for s in missing_preferred if s not in set(foundations)])

    buckets = [
        ("foundations", "Phase 1 — Foundations",
         "Everything else depends on these. Some were never named in the job "
         "description because employers assume them.", foundations),
        ("role_critical", "Phase 2 — Role-critical skills",
         "The remaining must-have requirements for this role.", rest_core),
        ("differentiators", "Phase 3 — Differentiators",
         "Nice-to-haves that separate you from other candidates once the "
         "must-haves are covered.", rest_preferred),
    ]
    selected = _close_over_prerequisites(
        {bucket_id: skills[:MAX_STEPS_PER_PHASE] for bucket_id, _, _, skills in buckets},
        {bucket_id: skills for bucket_id, _, _, skills in buckets},
        order,
    )
    omitted = sum(len(skills) - len(selected[bucket_id])
                  for bucket_id, _, _, skills in buckets)

    def level_of(skill: str) -> str:
        if skill in hidden:
            return "prerequisite"
        return "core" if skill in missing_core else "preferred"

    phases = [
        {
            "id": bucket_id,
            "title": title,
            "why": why,
            "steps": [_step(s, level_of(s), match, have, unlocks)
                      for s in selected[bucket_id]],
        }
        for bucket_id, title, why, _ in buckets
    ]
    phases = [p for p in phases if p["steps"]]
    _annotate_blockers(phases)

    total = sum(len(p["steps"]) for p in phases)
    role_skills = set(role.get("core_skills") or []) | set(role.get("preferred_skills") or [])

    return {
        "target_role": role.get("title"),
        "phases": phases,
        "total_steps": total,
        "omitted_steps": max(0, omitted),
        "hidden_prerequisites": sort_skills(hidden),
        "already_have": sort_skills(have & role_skills),
        "headline": _headline(total, phases, role),
        "methodology": (
            "Ordered by a prerequisite graph, then by how strongly the retrieved job "
            "descriptions demanded each skill. Skills the job description never named "
            "but that other gaps depend on are surfaced as foundations. There are no "
            "time estimates, because nothing in this analysis supports one."
        ),
    }


def _close_over_prerequisites(selected: Dict[str, List[str]],
                              available: Dict[str, List[str]],
                              order) -> Dict[str, List[str]]:
    """
    Make the shown plan self-contained.

    Capping each phase at a fixed length can cut a skill that a later, shown
    skill depends on -- leaving a step that reads "blocked by Machine Learning"
    when Machine Learning appears nowhere in the plan. This pulls any such
    blocker back in, from whichever bucket it belongs to, and repeats until
    nothing shown depends on something hidden.
    """
    chosen = {k: list(v) for k, v in selected.items()}
    bucket_of = {skill: bucket
                 for bucket, skills in available.items() for skill in skills}

    for _ in range(10):                     # converges well before this
        shown = {s for skills in chosen.values() for s in skills}
        missing_blockers = {
            prereq
            for skill in shown
            for prereq in all_prerequisites_of(skill)
            if prereq in bucket_of and prereq not in shown
        }
        if not missing_blockers:
            break
        for prereq in missing_blockers:
            chosen[bucket_of[prereq]].append(prereq)

    return {bucket: order(skills) for bucket, skills in chosen.items()}


def _annotate_blockers(phases: List[dict]) -> None:
    """
    Say whether a step's missing prerequisite is handled earlier in this plan.

    Without this a step reads "needs LLMs" while LLMs is already Phase 1, which
    looks like a contradiction rather than a sequence.
    """
    position = {}
    for phase_index, phase in enumerate(phases):
        for step_index, step in enumerate(phase["steps"]):
            position[step["skill"]] = (phase_index, step_index, phase["title"])

    for phase_index, phase in enumerate(phases):
        for step_index, step in enumerate(phase["steps"]):
            covered, outside = [], []
            for prereq in step["missing_prerequisites"]:
                at = position.get(prereq)
                if at and (at[0], at[1]) < (phase_index, step_index):
                    covered.append({"skill": prereq, "phase": at[2]})
                else:
                    outside.append(prereq)
            step["blockers_covered_earlier"] = covered
            step["blockers_outside_plan"] = outside
            # "Ready" means nothing outside this plan is in the way.
            step["ready_to_start"] = not outside


def _headline(total: int, phases: List[dict], role: dict) -> str:
    if not total:
        return (f"No gaps to close for {role.get('title')} — every requirement is "
                f"already evidenced.")
    first = phases[0]["steps"][0]["skill"] if phases and phases[0]["steps"] else None
    return (f"{total} skills to work through for {role.get('title')}, across "
            f"{len(phases)} phase{'' if len(phases) == 1 else 's'}"
            + (f". Start with {first}." if first else "."))

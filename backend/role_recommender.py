"""
role_recommender.py
===================

Objective 3, part 1: "which roles am I actually closest to?"

A student picks one target role, but their resume may fit a different one
better. This module scores the candidate against **every** role in the
catalogue and ranks them, so the answer is evidence-based rather than a guess.

No new machinery is involved. It reuses the Objective 2 pipeline exactly as it
stands: retrieve each role's job-description chunks, derive that role's
requirements from them, and run the same deterministic matcher. The only
difference is that it does so six times instead of once.

Two deliberate choices
----------------------
1. **Every role is scored role-generically**, with no pasted job description.
   A posting the student pasted describes one specific job; feeding it into the
   other five roles would contaminate their requirements and make the ranking
   meaningless. So the comparison is "against typical requirements for each
   role", and the UI says so. This is why a role's number here can differ from
   the headline match score, which *does* use the pasted posting.

2. **A shallower retrieval depth** than the headline match. The ranking needs a
   reliable ordering, not a full audit trail per role, so it reads fewer chunks
   per role and keeps the whole sweep fast.

3. **Roles are ranked by RAW core coverage, not by the match score.** The
   experience-level adjustment exists to make a fresher's *absolute* score fair,
   and it caps a component once the expected coverage is reached. That is right
   for one role, but it destroys the ordering across six: at fresher level a
   candidate covering 62% and one covering 67% of core requirements both reach
   the 50% target, both components max out, and the ranking then turns on
   incidental preferred skills. Ranking on the unadjusted "how many of this
   role's must-haves can I evidence" keeps the comparison meaningful. The
   adjusted match score is still reported alongside it.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import config
from experience_levels import DEFAULT_LEVEL
from job_matcher import match_candidate_to_role
from skills_data import ROLES

logger = logging.getLogger("career_engine.role_recommender")

# How many missing skills to name per role in the summary row.
TOP_GAPS_SHOWN = 3


def recommend_roles(
    resume: dict,
    github: Optional[dict],
    retriever,
    target_role_id: str,
    experience_level: str = DEFAULT_LEVEL,
) -> Dict[str, object]:
    """
    Score the candidate against every role and rank the results.

    ``retriever`` is the shared RAG retriever, passed in rather than fetched so
    the caller controls when the index is built.
    """
    rows: List[Dict[str, object]] = []

    for role in ROLES:
        try:
            retrieval = retriever.retrieve_for_role(
                role_title=str(role["title"]),
                role_id=str(role["id"]),
                job_description_text=None,      # role-generic, by design
                top_k=config.RAG_RECOMMENDATION_TOP_K,
                seed_skills=list(role.get("core_skills") or [])[:8],
            )
            match = match_candidate_to_role(
                resume, github, role, retrieval["results"],
                jd_text="", experience_level=experience_level,
            )
        except Exception as exc:
            # One role failing must not lose the whole ranking.
            logger.warning("Could not score role %s: %s", role.get("id"), exc)
            continue

        core = match["core_skills"]
        preferred = match["preferred_skills"]
        rows.append({
            "role_id": role["id"],
            "title": role["title"],
            "description": role["description"],
            "score": match["score"],
            "max_score": match["max_score"],
            "verdict": match["verdict"]["label"],
            "core_matched": len(core["matched"]),
            "core_total": core["total"],
            # Raw, unadjusted: the ranking signal. See note 3 in the module docstring.
            "core_coverage": core["coverage"],
            "preferred_matched": len(preferred["matched"]),
            "preferred_total": preferred["total"],
            "top_gaps": core["missing"][:TOP_GAPS_SHOWN],
            "top_strengths": core["matched"][:TOP_GAPS_SHOWN],
            "is_target": role["id"] == target_role_id,
        })

    # Rank on raw core coverage; the match score only breaks ties.
    rows.sort(key=lambda r: (r["core_coverage"], r["score"]), reverse=True)
    for position, row in enumerate(rows, start=1):
        row["rank"] = position

    target = next((r for r in rows if r["is_target"]), None)
    best = rows[0] if rows else None
    better = [r for r in rows
              if target and r["core_coverage"] > target["core_coverage"]]

    return {
        "roles": rows,
        "target_role_id": target_role_id,
        "target_rank": target["rank"] if target else None,
        "best_fit_role_id": best["role_id"] if best else None,
        "stronger_alternatives": [r["role_id"] for r in better],
        "headline": _headline(target, best, better),
        "ranked_by": "core_coverage",
        "methodology": (
            "Every role is scored with the same deterministic matcher used for your "
            "target role, against requirements retrieved from that role's job "
            "descriptions. No pasted job description is used here, so all six roles "
            "are compared on equal terms -- which is why a score here can differ from "
            "the headline match score for your target role. Roles are ranked by the "
            "share of each role's core requirements you can evidence, before the "
            "experience-level adjustment, because that adjustment caps a component "
            "once the expected coverage is reached and would flatten the ranking."
        ),
    }


def _headline(target: Optional[dict], best: Optional[dict],
              better: List[dict]) -> str:
    """One sentence stating what the ranking actually shows."""
    if not target or not best:
        return "No roles could be scored."
    if not better:
        return (f"{target['title']} is your strongest fit of the "
                f"{len(ROLES)} roles assessed, with "
                f"{target['core_matched']}/{target['core_total']} core requirements "
                f"evidenced.")
    if len(better) == 1:
        return (f"{best['title']} fits you better: "
                f"{best['core_matched']}/{best['core_total']} core requirements "
                f"evidenced against {target['core_matched']}/{target['core_total']} "
                f"for {target['title']}.")
    return (f"{len(better)} roles fit you better than {target['title']} "
            f"({target['core_matched']}/{target['core_total']} core requirements), "
            f"led by {best['title']} at "
            f"{best['core_matched']}/{best['core_total']}.")

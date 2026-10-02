"""
job_matcher.py
==============

Explainable job/role matching -- the second half of Objective 2.

The rule this file exists to enforce
------------------------------------
We do **not** hand a resume and a job description to an LLM and ask "is this a
good match?". Instead:

  1. The requirement set is *derived from the RAG-retrieved job-description
     chunks* (plus the role catalogue as a baseline).
  2. Candidate evidence is taken from the parsed resume and the GitHub
     analysis, kept separately labelled by source.
  3. The two are compared with a fixed, published formula.
  4. Only afterwards is an LLM optionally asked to *describe* the result.

So the match score is computed arithmetic, and every skill row can be traced
to the job-description sentence that required it and the resume line or
repository that evidenced it.

Match score model (total = 100)
-------------------------------
====================================  =====  ================================
Component                             Max    What it measures
====================================  =====  ================================
Core skill coverage                      55  Must-have skills the candidate has
Preferred skill coverage                 20  Nice-to-have skills
Retrieved JD requirement coverage        15  Coverage of what RAG actually
                                             retrieved for this exact query
Evidence corroboration                   10  Claims backed by public code
====================================  =====  ================================

Career stage
------------
The first three components measure coverage, and the coverage a candidate can
realistically reach depends on how long they have been working. Each experience
level declares the coverage at which a component earns full marks (see
``experience_levels.py``); the weights and the arithmetic never change.
Corroboration is deliberately NOT scaled -- it measures evidence quality, not
how many skills someone has had time to accumulate.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Set

from experience_levels import (
    DEFAULT_LEVEL,
    expectation_note,
    resolve_level,
    scaled_coverage,
)
from skills_data import extract_skills, find_skill_mentions, skill_category, sort_skills

# Component weights for the match score.
MATCH_WEIGHTS: Dict[str, int] = {
    "core_coverage": 55,
    "preferred_coverage": 20,
    "retrieved_requirement_coverage": 15,
    "evidence_corroboration": 10,
}
MATCH_MAX = sum(MATCH_WEIGHTS.values())      # 100

# A retrieved chunk must be at least this similar to the query before we treat
# the skills inside it as requirements. Filters out weak, off-topic matches.
MIN_SIMILARITY_FOR_REQUIREMENT = 0.20


def _requirement_kind_from_chunk(chunk: dict) -> str:
    """
    Map a chunk's section to a requirement strength.

    'required_skills' and 'qualifications' state must-haves; 'responsibilities'
    and 'preferred_skills' describe the rest of the job. A pasted job
    description has no sections, so it is treated as core throughout.
    """
    return str(chunk.get("requirement_kind") or "context")


def derive_requirements_from_retrieval(
    retrieved_chunks: Sequence[dict],
    min_similarity: float = MIN_SIMILARITY_FOR_REQUIREMENT,
) -> Dict[str, Dict[str, object]]:
    """
    Turn retrieved JD chunks into a skill -> requirement mapping.

    This is the step that makes RAG *functional* rather than decorative: the
    requirements the candidate is scored against come from the documents the
    retriever actually returned for this query.

    Each entry records the evidence chunks that mentioned the skill, the
    strongest similarity seen, and whether any of those chunks was a
    "must-have" section.
    """
    requirements: Dict[str, Dict[str, object]] = {}

    for chunk in retrieved_chunks:
        similarity = float(chunk.get("similarity") or 0.0)
        # The similarity floor filters weak, off-topic matches out of the
        # knowledge base. It must NOT apply to a job description the user
        # pasted in: they explicitly supplied that posting, so every
        # requirement in it counts regardless of how it ranks against the
        # query. Short bullets ("Familiarity with Vite as a build tool")
        # score low and were being dropped.
        user_supplied = chunk.get("section") == "pasted"
        if not user_supplied and similarity < min_similarity:
            continue
        text = str(chunk.get("text") or "")
        kind = _requirement_kind_from_chunk(chunk)

        for skill in extract_skills(text):
            entry = requirements.setdefault(skill, {
                "skill": skill,
                "kind": "preferred",
                "max_similarity": 0.0,
                "evidence": [],
            })
            if kind == "core":
                entry["kind"] = "core"
            entry["max_similarity"] = max(float(entry["max_similarity"]), similarity)
            evidence: List[dict] = entry["evidence"]          # type: ignore[assignment]
            # Collect generously; the best sentences are chosen below.
            if len(evidence) < 8:
                evidence.append({
                    "text": text,
                    "source": chunk.get("source"),
                    "section": chunk.get("section"),
                    "similarity": round(similarity, 4),
                    "rank": chunk.get("rank"),
                    "kind": kind,
                })

    # Pick the sentence that best explains WHY a skill is required, in this
    # order of preference:
    #   1. the posting the user actually pasted -- it is the job they are
    #      applying to, so the employer's own wording beats a sample JD's;
    #   2. a "required skills" line over a "nice to have" line, even when the
    #      latter ranks higher against the query -- otherwise React's evidence
    #      reads "Component testing with Jest" rather than "Deep React
    #      experience including hooks";
    #   3. higher similarity to the query.
    for entry in requirements.values():
        evidence = entry["evidence"]                          # type: ignore[assignment]
        evidence.sort(
            key=lambda e: (
                e.get("section") == "pasted",
                e.get("kind") == "core",
                float(e.get("similarity") or 0.0),
            ),
            reverse=True,
        )
        entry["evidence"] = evidence[:3]

    return requirements


def _resume_evidence_for(skill: str, mentions: Dict[str, List[str]],
                         declared: Set[str]) -> List[str]:
    evidence: List[str] = []
    if skill in declared:
        evidence.append("Listed in the resume's skills section")
    evidence.extend(mentions.get(skill, [])[:2])
    return evidence


def match_candidate_to_role(
    resume: dict,
    github: Optional[dict],
    role: dict,
    retrieved_chunks: Sequence[dict],
    jd_text: str = "",
    experience_level: str = DEFAULT_LEVEL,
) -> Dict[str, object]:
    """
    Compare candidate evidence against role requirements.

    ``retrieved_chunks`` is the output of the RAG retriever. ``jd_text`` is the
    job description the user selected or pasted; skills named in it are also
    treated as requirements, since that is the posting they are applying to.
    ``experience_level`` sets the coverage expected for full marks.
    """
    level = resolve_level(experience_level)
    target = float(level["skill_coverage_target"])
    # ---- 1. candidate evidence, kept separated by source ------------------
    resume_skills: Set[str] = set(resume.get("skills") or [])
    declared_skills: Set[str] = set((resume.get("skills_detail") or {}).get("declared") or [])
    github_skills: Set[str] = set((github or {}).get("skills") or [])
    github_evidence: Dict[str, List[str]] = (github or {}).get("skill_evidence") or {}

    # ---- 2. requirements, from three sources ------------------------------
    catalogue_core = set(role.get("core_skills") or [])
    catalogue_preferred = set(role.get("preferred_skills") or [])
    retrieved_requirements = derive_requirements_from_retrieval(retrieved_chunks)
    jd_skills = set(extract_skills(jd_text)) if jd_text else set()

    retrieved_core = {s for s, r in retrieved_requirements.items() if r["kind"] == "core"}
    retrieved_preferred = set(retrieved_requirements) - retrieved_core

    # A skill is CORE only if the role catalogue lists it as core, or if RAG
    # found it inside a must-have section of a job description.
    #
    # Being merely *mentioned* somewhere in the posting is NOT enough: a
    # technology named under "preferred skills" or in a responsibility sentence
    # is a nice-to-have, and promoting those to must-have collapsed the
    # preferred set to almost nothing and made the core coverage ratio
    # unreasonably harsh.
    core_skills = sort_skills(catalogue_core | retrieved_core)
    preferred_skills = sort_skills(
        (catalogue_preferred | retrieved_preferred | jd_skills) - set(core_skills)
    )

    # ---- 3. skill-by-skill breakdown --------------------------------------
    all_requirements = list(core_skills) + list(preferred_skills)
    resume_mentions = find_skill_mentions(
        str(resume.get("raw_text") or ""), all_requirements, max_per_skill=2
    )

    breakdown: List[Dict[str, object]] = []
    for skill in all_requirements:
        is_core = skill in set(core_skills)
        in_resume = skill in resume_skills
        in_github = skill in github_skills

        sources: List[str] = []
        if in_resume:
            sources.append("resume")
        if in_github:
            sources.append("github")

        requirement = retrieved_requirements.get(skill, {})
        jd_evidence = [e["text"] for e in (requirement.get("evidence") or [])]
        why_required: List[str] = []
        if skill in catalogue_core:
            why_required.append("Core skill for this role in the role catalogue")
        elif skill in catalogue_preferred:
            why_required.append("Preferred skill for this role in the role catalogue")
        if skill in retrieved_requirements:
            why_required.append(
                f"Named in {len(requirement.get('evidence') or [])} retrieved "
                f"job-description chunk(s)"
            )
        if skill in jd_skills:
            why_required.append("Named in the selected job description")

        breakdown.append({
            "skill": skill,
            "category": skill_category(skill),
            "required": is_core,
            "requirement_level": "core" if is_core else "preferred",
            "matched": bool(sources),
            "sources": sources,
            "resume_evidence": _resume_evidence_for(skill, resume_mentions, declared_skills),
            "github_evidence": (github_evidence.get(skill) or [])[:3],
            "job_description_evidence": jd_evidence,
            "why_required": why_required,
            "retrieval_similarity": (
                round(float(requirement["max_similarity"]), 4)
                if requirement.get("max_similarity") else None
            ),
        })

    # ---- 4. the score ------------------------------------------------------
    matched_core = [b["skill"] for b in breakdown if b["requirement_level"] == "core" and b["matched"]]
    missing_core = [b["skill"] for b in breakdown if b["requirement_level"] == "core" and not b["matched"]]
    matched_preferred = [b["skill"] for b in breakdown
                         if b["requirement_level"] == "preferred" and b["matched"]]
    missing_preferred = [b["skill"] for b in breakdown
                         if b["requirement_level"] == "preferred" and not b["matched"]]

    core_coverage = len(matched_core) / len(core_skills) if core_skills else 0.0
    preferred_coverage = (len(matched_preferred) / len(preferred_skills)
                          if preferred_skills else 0.0)

    # Coverage measured ONLY against what the retriever returned for this query.
    retrieved_matched = [s for s in retrieved_requirements
                         if s in resume_skills or s in github_skills]
    retrieved_coverage = (len(retrieved_matched) / len(retrieved_requirements)
                          if retrieved_requirements else 0.0)

    # Corroboration: of the requirements the candidate claims, how many are
    # also visible in public code? Rewards demonstrated over declared skill.
    corroborated = [b["skill"] for b in breakdown
                    if "resume" in b["sources"] and "github" in b["sources"]]
    all_matched = matched_core + matched_preferred
    corroboration = len(corroborated) / len(all_matched) if all_matched else 0.0

    components = [
        _match_component(
            "core_coverage", "Core Skill Coverage",
            scaled_coverage(core_coverage, target),
            f"{len(matched_core)} of {len(core_skills)} core requirements are evidenced "
            f"in the resume or on GitHub ({core_coverage:.0%}). {expectation_note(level)}",
            matched_core, raw_coverage=core_coverage,
        ),
        _match_component(
            "preferred_coverage", "Preferred Skill Coverage",
            scaled_coverage(preferred_coverage, target),
            f"{len(matched_preferred)} of {len(preferred_skills)} preferred requirements "
            f"are evidenced ({preferred_coverage:.0%}). {expectation_note(level)}",
            matched_preferred, raw_coverage=preferred_coverage,
        ),
        _match_component(
            "retrieved_requirement_coverage", "Retrieved JD Requirement Coverage",
            scaled_coverage(retrieved_coverage, target),
            f"{len(retrieved_matched)} of {len(retrieved_requirements)} skills named in the "
            f"job-description chunks retrieved by the RAG index are evidenced "
            f"({retrieved_coverage:.0%}). {expectation_note(level)}",
            sort_skills(retrieved_matched), raw_coverage=retrieved_coverage,
        ),
        _match_component(
            # Not scaled: this measures how well claims are backed up, which does
            # not get easier or harder with years of experience.
            "evidence_corroboration", "Evidence Corroboration", corroboration,
            f"{len(corroborated)} of {len(all_matched)} matched skills appear in BOTH the "
            f"resume and public GitHub activity."
            if all_matched else "No matched skills to corroborate.",
            corroborated,
        ),
    ]
    score = sum(int(c["score"]) for c in components)

    return {
        "score": score,
        "max_score": MATCH_MAX,
        "verdict": _verdict(score, scaled_coverage(core_coverage, target)),
        "components": components,
        "weights": dict(MATCH_WEIGHTS),
        "experience_level": {
            "id": level["id"],
            "label": level["label"],
            "description": level["description"],
            "skill_coverage_target": target,
        },
        "core_skills": {
            "total": len(core_skills),
            "matched": sort_skills(matched_core),
            "missing": sort_skills(missing_core),
            "coverage": round(core_coverage, 3),
        },
        "preferred_skills": {
            "total": len(preferred_skills),
            "matched": sort_skills(matched_preferred),
            "missing": sort_skills(missing_preferred),
            "coverage": round(preferred_coverage, 3),
        },
        "skill_breakdown": breakdown,
        "evidence_summary": {
            "resume_only": sort_skills(resume_skills - github_skills),
            "github_only": sort_skills(github_skills - resume_skills),
            "both": sort_skills(resume_skills & github_skills),
            "resume_skill_count": len(resume_skills),
            "github_skill_count": len(github_skills),
        },
        "requirements_derived_from_rag": [
            {
                "skill": skill,
                "kind": entry["kind"],
                "max_similarity": round(float(entry["max_similarity"]), 4),
                "evidence_count": len(entry["evidence"]),          # type: ignore[arg-type]
            }
            for skill, entry in sorted(
                retrieved_requirements.items(),
                key=lambda kv: float(kv[1]["max_similarity"]), reverse=True
            )
        ],
        "methodology": (
            "Requirements are derived from the job-description chunks retrieved by the "
            "RAG index (plus the role catalogue and the selected job description). "
            "Candidate evidence comes from the parsed resume and the GitHub analysis, "
            "kept separately labelled. The score is a fixed weighted sum of four "
            f"coverage ratios, measured against the {target:.0%} coverage expected at "
            f"{level['label']} level; no language model contributes to it."
        ),
    }


def _match_component(component_id: str, label: str, ratio: float,
                     reason: str, evidence: Sequence[str],
                     raw_coverage: Optional[float] = None) -> Dict[str, object]:
    """
    ``ratio`` is the expectation-scaled value that earns points; ``raw_coverage``
    is the unscaled fraction, reported alongside so the adjustment is visible
    rather than hidden inside the number.
    """
    max_score = MATCH_WEIGHTS[component_id]
    clamped = max(0.0, min(1.0, ratio))
    score = int(round(clamped * max_score))
    return {
        "id": component_id,
        "component": label,
        "score": score,
        "max_score": max_score,
        "coverage": round(clamped, 3),
        "raw_coverage": round(raw_coverage, 3) if raw_coverage is not None else None,
        "reason": reason,
        "evidence": list(evidence)[:15],
    }


def _verdict(score: int, core_coverage: float) -> Dict[str, str]:
    """
    The headline verdict deliberately considers core coverage as well as the
    total: a candidate can accumulate points on preferred skills while missing
    the must-haves, and that should not read as a strong match.
    """
    if score >= 75 and core_coverage >= 0.75:
        return {"label": "Strong Match",
                "summary": "Most core requirements are evidenced. This is a credible application."}
    if score >= 55 and core_coverage >= 0.5:
        return {"label": "Moderate Match",
                "summary": "A solid base, but several core requirements are not yet evidenced."}
    if core_coverage >= 0.3:
        return {"label": "Partial Match",
                "summary": "Some relevant skills, but the majority of core requirements are missing."}
    return {"label": "Weak Match",
            "summary": "Few of the role's core requirements are evidenced in the resume or on GitHub."}


def build_jd_text(documents: Sequence[dict]) -> str:
    """
    Flatten job-description documents into plain text.

    Used for the ATS keyword component when the user has not pasted their own
    job description: the keywords then come from the local knowledge base
    entries for the selected role.
    """
    parts: List[str] = []
    for document in documents:
        for field in ("about_the_role",):
            if document.get(field):
                parts.append(str(document[field]))
        for field in ("required_skills", "preferred_skills", "responsibilities", "qualifications"):
            for entry in document.get(field) or []:
                parts.append(str(entry))
    return "\n".join(parts)

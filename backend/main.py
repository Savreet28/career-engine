"""
main.py
=======

The Career Engine FastAPI application.

The full pipeline, in the order it runs:

    resume file ──> resume_parser ──┐
                                    │
    github username ──> github_analyzer ──┐
                                          │
    target role + job description ──> rag.retriever ──┐
                                                      │
                        ats_scorer  <─────────────────┤
                        job_matcher <─────────────────┘
                             │
                             ▼
                      summary_builder (rule-based, no LLM)

``run_pipeline`` is written as a generator that yields progress events and
finally the result. ``POST /api/analyze`` drains it and returns the result;
``POST /api/analyze/stream`` forwards each event to the browser as Server-Sent
Events, so the UI can show genuine stage progress instead of a fake progress
bar. One implementation, two transports.

Interactive API docs: http://localhost:8000/docs
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, Generator, List, Optional, Tuple

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

import config
from ats_scorer import score_resume
from experience_levels import DEFAULT_LEVEL, is_valid_level, public_levels, resolve_level
from github_analyzer import GitHubError, analyze_github, empty_analysis
from job_matcher import build_jd_text, match_candidate_to_role
from models import GitHubRequest, HealthOut, RoleOut
from rag import get_retriever
from rag.ingest import load_job_descriptions
from resume_parser import ResumeParseError, parse_resume
from summary_builder import build_summary
from skills_data import ROLES, ROLES_BY_ID

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("career_engine")

VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Warm the RAG index at startup.

    Loading the embedding model and building the FAISS index takes a few
    seconds. Doing it here means the first real request is fast, and any
    problem with the knowledge base surfaces immediately in the server log
    rather than inside a user's analysis.
    """
    logger.info("Starting Career Engine %s", VERSION)
    try:
        retriever = get_retriever()
        logger.info("RAG index ready: %s", retriever.store.stats())
    except Exception as exc:
        logger.error("RAG index could not be built at startup: %s", exc)
        logger.error("The API will still start; /api/rag/status will report the problem.")
    yield
    logger.info("Career Engine stopped.")


app = FastAPI(
    title="Career Engine API",
    version=VERSION,
    description=(
        "Resume + GitHub + target role analysis with a deterministic ATS score, "
        "and RAG over job-description data for explainable job/role matching."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

@app.exception_handler(ResumeParseError)
async def resume_error_handler(request, exc: ResumeParseError):
    return JSONResponse(status_code=422,
                        content={"detail": str(exc), "error_type": "resume_parse_error"})


@app.exception_handler(GitHubError)
async def github_error_handler(request, exc: GitHubError):
    return JSONResponse(status_code=exc.status,
                        content={"detail": str(exc), "error_type": "github_error"})


@app.exception_handler(Exception)
async def unhandled_error_handler(request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred. See the backend log "
                           "for details.", "error_type": "internal_error"},
    )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _resolve_role(role_id: str) -> dict:
    role = ROLES_BY_ID.get((role_id or "").strip())
    if not role:
        raise HTTPException(
            status_code=400,
            detail=(f"Unknown role '{role_id}'. Valid roles: "
                    f"{', '.join(sorted(ROLES_BY_ID))}."),
        )
    return role


def _resolve_experience_level(level_id: Optional[str]) -> str:
    """Validate the career stage, defaulting when the field is omitted."""
    if level_id is None or not str(level_id).strip():
        return DEFAULT_LEVEL
    if not is_valid_level(level_id):
        raise HTTPException(
            status_code=400,
            detail=(f"Unknown experience level '{level_id}'. Valid levels: "
                    f"{', '.join(l['id'] for l in public_levels())}."),
        )
    return str(level_id).strip().lower()


async def _read_resume(resume: UploadFile) -> Tuple[bytes, str]:
    if resume is None or not resume.filename:
        raise HTTPException(status_code=400, detail="A resume file is required.")
    data = await resume.read()
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded resume file is empty.")
    return data, resume.filename


def _documents_for_role(role_id: str) -> List[dict]:
    try:
        return [d for d in load_job_descriptions() if d.get("role_id") == role_id]
    except Exception as exc:
        logger.warning("Could not load job descriptions: %s", exc)
        return []


def _resolve_job_description(
    role: dict,
    job_description_id: Optional[str],
    job_description_text: Optional[str],
) -> Tuple[str, str, Optional[dict]]:
    """
    Decide which job-description text to score keywords against.

    Priority:
      1. text the user pasted (most specific to their application),
      2. a document they selected from the local knowledge base,
      3. every knowledge-base document for the target role (a role-level baseline).

    Returns ``(text, human_readable_source, selected_document_or_None)``.
    """
    if job_description_text and job_description_text.strip():
        return (job_description_text.strip(), "the job description you provided", None)

    documents = _documents_for_role(str(role["id"]))

    if job_description_id:
        for document in documents:
            if document.get("id") == job_description_id:
                return (build_jd_text([document]),
                        f"{document['job_title']} at {document['company']}", document)
        raise HTTPException(
            status_code=404,
            detail=f"No job description with id '{job_description_id}' exists for this role.",
        )

    if documents:
        return (build_jd_text(documents),
                f"all {len(documents)} sample job descriptions for {role['title']}", None)

    return ("", "no job description (none available for this role)", None)


def _stage(name: str, label: str, status: str, **extra: Any) -> Dict[str, Any]:
    return {"stage": name, "label": label, "status": status, **extra}


def _component_details(report: dict, component_id: str) -> dict:
    """Fetch one scoring component's `details` by id rather than by position."""
    for component in report.get("components") or []:
        if component.get("id") == component_id:
            return component.get("details") or {}
    return {}


def _diversified(results: List[dict], limit: int, max_per_document: int = 3) -> List[dict]:
    """
    Pick the chunks to SHOW the user, spreading them across job descriptions.

    The matcher reads a deep slice of the retrieved chunks, and within one role
    a single document usually occupies the whole top of that ranking. Slicing
    the first N for display would therefore show evidence from one employer
    only. Capping per document keeps the displayed evidence representative;
    leftover slots fall back to plain score order so we never show fewer
    results than we have.
    """
    chosen: List[dict] = []
    overflow: List[dict] = []
    seen: Dict[str, int] = {}
    for result in results:
        document_id = str(result.get("document_id"))
        if seen.get(document_id, 0) < max_per_document:
            seen[document_id] = seen.get(document_id, 0) + 1
            chosen.append(result)
        else:
            overflow.append(result)
        if len(chosen) >= limit:
            break
    if len(chosen) < limit:
        chosen.extend(overflow[: limit - len(chosen)])
    # Re-rank for display so the numbering the user sees is 1..N in score order.
    chosen.sort(key=lambda r: float(r.get("similarity") or 0.0), reverse=True)
    return [{**r, "rank": i} for i, r in enumerate(chosen, start=1)]


# ---------------------------------------------------------------------------
# The pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    resume_bytes: bytes,
    filename: str,
    role: dict,
    github_username: Optional[str],
    job_description_id: Optional[str],
    job_description_text: Optional[str],
    experience_level: str = DEFAULT_LEVEL,
) -> Generator[Tuple[str, Dict[str, Any]], None, None]:
    """
    Run the complete analysis, yielding ``(event_type, payload)`` as it goes.

    Event types are ``"stage"`` (progress) and ``"result"`` (the final report).
    Stage timings are measured, not simulated.
    """
    timings: Dict[str, float] = {}
    started = time.perf_counter()
    checkpoint = started

    def mark(name: str) -> float:
        """Record the wall-clock milliseconds spent since the previous stage."""
        nonlocal checkpoint
        now = time.perf_counter()
        timings[name] = round((now - checkpoint) * 1000, 1)
        checkpoint = now
        return timings[name]

    # -- 1. resume ---------------------------------------------------------
    yield "stage", _stage("parse_resume", "Parsing resume", "running")
    resume = parse_resume(resume_bytes, filename)
    yield "stage", _stage(
        "parse_resume", "Parsing resume", "done", ms=mark("parse_resume"),
        detail=f"{len(resume['skills'])} skills, {len(resume['sections'])} sections detected",
    )

    # -- 2. github (optional; never fatal) ---------------------------------
    github: Optional[dict] = None
    github_error: Optional[str] = None
    if github_username and github_username.strip():
        yield "stage", _stage("analyze_github", "Analysing GitHub profile", "running")
        try:
            github = analyze_github(github_username)
            detail = (f"{(github['stats'] or {}).get('original_repositories', 0)} repositories, "
                      f"{len(github['skills'])} skills evidenced")
            yield "stage", _stage("analyze_github", "Analysing GitHub profile", "done",
                                  ms=mark("analyze_github"), detail=detail)
        except GitHubError as exc:
            # A GitHub failure degrades the analysis, it does not fail it.
            github_error = str(exc)
            github = empty_analysis(str(exc))
            yield "stage", _stage("analyze_github", "Analysing GitHub profile", "warning",
                                  ms=mark("analyze_github"), detail=str(exc))
    else:
        github = empty_analysis("No GitHub username was provided.")
        yield "stage", _stage("analyze_github", "Analysing GitHub profile", "skipped",
                              detail="No GitHub username provided")

    # -- 3. job description + RAG retrieval --------------------------------
    jd_text, jd_source, selected_document = _resolve_job_description(
        role, job_description_id, job_description_text
    )

    yield "stage", _stage("rag_retrieval", "Retrieving job-description evidence", "running")
    retriever = get_retriever()
    retrieval = retriever.retrieve_for_role(
        role_title=str(role["title"]),
        role_id=str(role["id"]),
        job_description_text=jd_text or None,
        top_k=config.RAG_DERIVATION_TOP_K,
        seed_skills=list(role.get("core_skills") or [])[:8],
    )
    # The matcher reads a deep slice of the retrieved chunks; the user is shown
    # a smaller, diversified selection of the same results.
    derivation_results = retrieval["results"]

    if job_description_text and job_description_text.strip():
        # Rank the user's own posting with the same machinery, against the SAME
        # query, so its cosine scores are comparable with the knowledge-base
        # ones and the two can be merged into one honestly-ranked list.
        # No top_k: every chunk of their posting feeds requirement derivation,
        # because they supplied it deliberately. Only the display list is cut.
        pasted = retriever.rank_pasted_chunks(
            job_description_text, str(role["title"]), query=retrieval["query"]
        )
        derivation_results = pasted + derivation_results
        # Reserve a few slots for their own posting, then sort everything by
        # similarity so the displayed order always matches the displayed scores.
        merged = pasted[:3] + _diversified(retrieval["results"], max(1, config.RAG_TOP_K - 3))
        merged.sort(key=lambda r: float(r.get("similarity") or 0.0), reverse=True)
        display_results = [
            {**r, "rank": i} for i, r in enumerate(merged[: config.RAG_TOP_K], start=1)
        ]
    else:
        display_results = _diversified(derivation_results, config.RAG_TOP_K)

    yield "stage", _stage("rag_retrieval", "Retrieving job-description evidence", "done",
                          ms=mark("rag_retrieval"),
                          detail=f"{len(derivation_results)} chunks retrieved from "
                                 f"{retrieval['index']['documents']} job descriptions")

    # -- 4. ATS score ------------------------------------------------------
    yield "stage", _stage("ats_score", "Calculating ATS score", "running")
    ats = score_resume(resume, role, jd_text=jd_text, jd_source=jd_source, github=github,
                       experience_level=experience_level)
    yield "stage", _stage("ats_score", "Calculating ATS score", "done",
                          ms=mark("ats_score"), detail=f"{ats['score']}/{ats['max_score']}")

    # -- 5. job matching ---------------------------------------------------
    yield "stage", _stage("job_match", "Matching skills against requirements", "running")
    match = match_candidate_to_role(resume, github, role, derivation_results, jd_text=jd_text,
                                    experience_level=experience_level)
    yield "stage", _stage("job_match", "Matching skills against requirements", "done",
                          ms=mark("job_match"), detail=f"{match['score']}/{match['max_score']}")

    # -- 6. summary --------------------------------------------------------
    yield "stage", _stage("summary", "Preparing summary", "running")
    summary = build_summary(ats, match, resume, github)
    yield "stage", _stage("summary", "Preparing summary", "done",
                          ms=mark("summary"),
                          detail=f"{len(summary['sections'])} sections")

    # -- result ------------------------------------------------------------
    resume_public = {k: v for k, v in resume.items() if k != "raw_text"}
    resume_public["text_preview"] = str(resume.get("raw_text") or "")[:1500]

    level = resolve_level(experience_level)
    yield "result", {
        "experience_level": {
            "id": level["id"], "label": level["label"],
            "description": level["description"],
            "skill_coverage_target": level["skill_coverage_target"],
        },
        "role": {
            "id": role["id"], "title": role["title"], "description": role["description"],
            "core_skills": role["core_skills"], "preferred_skills": role["preferred_skills"],
        },
        "resume": resume_public,
        "github": github,
        "github_error": github_error,
        "ats": ats,
        "job_match": match,
        "rag": {
            "query": retrieval["query"],
            "top_k_displayed": len(display_results),
            "top_k_used_for_matching": len(derivation_results),
            "role_filter": retrieval["role_filter"],
            "index": retrieval["index"],
            "results": display_results,
        },
        "job_description": {
            "source": jd_source,
            "selected": selected_document,
            "provided_by_user": bool(job_description_text and job_description_text.strip()),
            # Look the component up by id: positional indexing would silently
            # break if the scoring components were ever reordered.
            "keyword_count": len(_component_details(ats, "jd_keyword_match").get("jd_keywords") or []),
        },
        "summary": summary,
        "timings_ms": {**timings, "total": round((time.perf_counter() - started) * 1000, 1)},
    }


# ---------------------------------------------------------------------------
# Metadata endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health", response_model=HealthOut, tags=["meta"])
def health():
    """Liveness check plus which optional integrations are configured."""
    try:
        index = get_retriever().store.stats()
    except Exception as exc:
        index = {"error": str(exc)}
    return {
        "status": "ok",
        "version": VERSION,
        **config.integration_status(),
        "rag_index": index,
    }


@app.get("/api/roles", response_model=List[RoleOut], tags=["meta"])
def list_roles():
    """Supported target roles, with the baseline skills each one expects."""
    counts: Dict[str, int] = {}
    try:
        for document in load_job_descriptions():
            role_id = str(document.get("role_id"))
            counts[role_id] = counts.get(role_id, 0) + 1
    except Exception:
        counts = {}
    return [
        {
            "id": r["id"], "title": r["title"], "description": r["description"],
            "core_skills": r["core_skills"], "preferred_skills": r["preferred_skills"],
            "job_description_count": counts.get(str(r["id"]), 0),
        }
        for r in ROLES
    ]


@app.get("/api/experience-levels", tags=["meta"])
def list_experience_levels():
    """
    Career stages the scorers understand.

    Each level declares the skill coverage at which a component earns full
    marks, so a fresher is not measured against a senior candidate's bar.
    """
    return public_levels()


@app.get("/api/job-descriptions", tags=["meta"])
def list_job_descriptions(role_id: Optional[str] = None):
    """The local job-description knowledge base that RAG indexes."""
    documents = load_job_descriptions()
    if role_id:
        _resolve_role(role_id)
        documents = [d for d in documents if d.get("role_id") == role_id]
    return [
        {
            "id": d["id"], "job_title": d["job_title"], "company": d["company"],
            "role_id": d["role_id"], "location": d.get("location"),
            "experience_required": d.get("experience_required"),
            "required_skill_count": len(d.get("required_skills") or []),
            "preferred_skill_count": len(d.get("preferred_skills") or []),
        }
        for d in documents
    ]


@app.get("/api/job-descriptions/{document_id}", tags=["meta"])
def get_job_description(document_id: str):
    """One full job description, so the UI can preview what it is matching against."""
    for document in load_job_descriptions():
        if document.get("id") == document_id:
            return document
    raise HTTPException(status_code=404,
                        detail=f"No job description with id '{document_id}'.")


@app.get("/api/rag/status", tags=["rag"])
def rag_status():
    """
    Inspect the vector index: chunk counts, dimensions, embedding backend.

    Exposed deliberately -- the RAG stage should be observable, not a black box.
    """
    retriever = get_retriever()
    return {
        "index": retriever.store.stats(),
        "embedder": retriever.embedder.describe(),
        "build_report": retriever.report,
        "settings": {
            "top_k_displayed": config.RAG_TOP_K,
            "top_k_used_for_matching": config.RAG_DERIVATION_TOP_K,
            "chunk_max_words": config.CHUNK_MAX_WORDS,
            "chunk_overlap_words": config.CHUNK_OVERLAP_WORDS,
        },
    }


@app.post("/api/rag/reindex", tags=["rag"])
def rag_reindex():
    """Rebuild the vector index, e.g. after editing the job-description files."""
    retriever = get_retriever(force_rebuild=True)
    return {"status": "rebuilt", "index": retriever.store.stats(),
            "report": retriever.report}


@app.get("/api/rag/search", tags=["rag"])
def rag_search(q: str, top_k: int = 8, role_id: Optional[str] = None):
    """
    Raw retrieval against the index. Useful for demonstrating, in isolation,
    that semantic search returns sensible chunks for an arbitrary query.
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' cannot be empty.")
    if role_id:
        _resolve_role(role_id)
    retriever = get_retriever()
    return {
        "query": q,
        "results": retriever.retrieve(q, top_k=max(1, min(top_k, 25)), role_id=role_id),
        "index": retriever.store.stats(),
    }


# ---------------------------------------------------------------------------
# Analysis endpoints
# ---------------------------------------------------------------------------

@app.post("/api/parse-resume", tags=["analysis"])
async def api_parse_resume(resume: UploadFile = File(..., description="PDF or DOCX resume")):
    """Stage 1 in isolation: structured data extracted from a resume file."""
    data, filename = await _read_resume(resume)
    parsed = parse_resume(data, filename)
    preview = str(parsed.pop("raw_text", ""))[:2000]
    return {**parsed, "text_preview": preview}


@app.post("/api/analyze-github", tags=["analysis"])
def api_analyze_github(payload: GitHubRequest):
    """Stage 2 in isolation: public GitHub profile turned into skill evidence."""
    return analyze_github(payload.username)


@app.post("/api/ats-score", tags=["analysis"])
async def api_ats_score(
    resume: UploadFile = File(...),
    role_id: str = Form(...),
    job_description: Optional[str] = Form(None),
    job_description_id: Optional[str] = Form(None),
    github_username: Optional[str] = Form(None),
    experience_level: Optional[str] = Form(None),
):
    """Stage 3 in isolation: the deterministic ATS score and its breakdown."""
    data, filename = await _read_resume(resume)
    role = _resolve_role(role_id)
    level_id = _resolve_experience_level(experience_level)
    parsed = parse_resume(data, filename)

    github = None
    if github_username and github_username.strip():
        try:
            github = analyze_github(github_username)
        except GitHubError as exc:
            github = empty_analysis(str(exc))

    jd_text, jd_source, _ = _resolve_job_description(role, job_description_id, job_description)
    ats = score_resume(parsed, role, jd_text=jd_text, jd_source=jd_source, github=github,
                       experience_level=level_id)
    return {"role": {"id": role["id"], "title": role["title"]},
            "job_description_source": jd_source, "ats": ats}


@app.post("/api/job-match", tags=["analysis"])
async def api_job_match(
    resume: UploadFile = File(...),
    role_id: str = Form(...),
    github_username: Optional[str] = Form(None),
    job_description: Optional[str] = Form(None),
    job_description_id: Optional[str] = Form(None),
    experience_level: Optional[str] = Form(None),
):
    """Stage 4 in isolation: RAG retrieval plus explainable job/role matching."""
    data, filename = await _read_resume(resume)
    role = _resolve_role(role_id)
    level_id = _resolve_experience_level(experience_level)
    parsed = parse_resume(data, filename)

    github = None
    if github_username and github_username.strip():
        try:
            github = analyze_github(github_username)
        except GitHubError as exc:
            github = empty_analysis(str(exc))

    jd_text, jd_source, _ = _resolve_job_description(role, job_description_id, job_description)
    retriever = get_retriever()
    retrieval = retriever.retrieve_for_role(
        role_title=str(role["title"]), role_id=str(role["id"]),
        job_description_text=jd_text or None, top_k=config.RAG_DERIVATION_TOP_K,
        seed_skills=list(role.get("core_skills") or [])[:8],
    )
    match = match_candidate_to_role(parsed, github, role, retrieval["results"], jd_text=jd_text,
                                    experience_level=level_id)
    return {
        "role": {"id": role["id"], "title": role["title"]},
        "job_description_source": jd_source,
        "job_match": match,
        "rag": {"query": retrieval["query"], "index": retrieval["index"],
                "results": retrieval["results"][: config.RAG_TOP_K]},
    }


@app.post("/api/analyze", tags=["analysis"])
async def api_analyze(
    resume: UploadFile = File(..., description="PDF or DOCX resume"),
    role_id: str = Form(..., description="Role id from GET /api/roles"),
    github_username: Optional[str] = Form(None),
    job_description: Optional[str] = Form(None, description="Pasted job description text"),
    job_description_id: Optional[str] = Form(None, description="Id from GET /api/job-descriptions"),
    experience_level: Optional[str] = Form(None, description="Id from GET /api/experience-levels"),
):
    """
    The complete pipeline in one call: parse, analyse, retrieve, score, match,
    explain. This is what the React dashboard uses when streaming is
    unavailable.
    """
    data, filename = await _read_resume(resume)
    role = _resolve_role(role_id)
    level_id = _resolve_experience_level(experience_level)

    stages: List[dict] = []
    result: Optional[dict] = None
    for event_type, payload in run_pipeline(
        data, filename, role, github_username, job_description_id, job_description, level_id
    ):
        if event_type == "stage":
            stages.append(payload)
        else:
            result = payload

    if result is None:      # defensive: the generator always yields a result
        raise HTTPException(status_code=500, detail="The analysis produced no result.")
    return {**result, "stages": stages}


@app.post("/api/analyze/stream", tags=["analysis"])
async def api_analyze_stream(
    resume: UploadFile = File(...),
    role_id: str = Form(...),
    github_username: Optional[str] = Form(None),
    job_description: Optional[str] = Form(None),
    job_description_id: Optional[str] = Form(None),
    experience_level: Optional[str] = Form(None),
):
    """
    The same pipeline, streamed as Server-Sent Events.

    Each stage emits an event the moment it actually starts and finishes, so
    the dashboard reports real progress rather than an invented percentage.
    The final ``result`` event carries the identical payload as /api/analyze.
    """
    data, filename = await _read_resume(resume)
    role = _resolve_role(role_id)
    level_id = _resolve_experience_level(experience_level)

    def event_stream():
        try:
            for event_type, payload in run_pipeline(
                data, filename, role, github_username, job_description_id,
                job_description, level_id
            ):
                yield f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"
        except ResumeParseError as exc:
            yield ("event: error\ndata: "
                   + json.dumps({"detail": str(exc), "error_type": "resume_parse_error"})
                   + "\n\n")
        except HTTPException as exc:
            yield ("event: error\ndata: "
                   + json.dumps({"detail": exc.detail, "error_type": "request_error"}) + "\n\n")
        except Exception as exc:
            logger.exception("Streaming analysis failed")
            yield ("event: error\ndata: "
                   + json.dumps({"detail": f"Analysis failed: {exc}",
                                 "error_type": "internal_error"}) + "\n\n")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/", include_in_schema=False)
def root():
    return {
        "name": "Career Engine API",
        "version": VERSION,
        "docs": "/docs",
        "frontend": "http://localhost:5173",
    }

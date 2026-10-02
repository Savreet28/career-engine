"""
test_api.py
===========

End-to-end test suite for Career Engine.

It exercises the running backend the way the React frontend does, plus the
module-level logic that has no HTTP surface. No test framework is required:

    # terminal 1
    cd backend && uvicorn main:app --reload

    # terminal 2
    cd backend && python tests/test_api.py

Tests that need the network (GitHub) are skipped automatically when the public
API rate limit has been exhausted, so a rate-limited run still reports
meaningful results rather than spurious failures.
"""

from __future__ import annotations

import io
import json
import pathlib
import sys
import time

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

BASE = "http://127.0.0.1:8000"
FIXTURES = pathlib.Path(__file__).parent / "fixtures"

PASSED: list[str] = []
FAILED: list[tuple[str, str]] = []
SKIPPED: list[tuple[str, str]] = []


# ---------------------------------------------------------------------------
# Tiny test harness
# ---------------------------------------------------------------------------
def check(name: str, condition: bool, detail: str = "") -> bool:
    if condition:
        PASSED.append(name)
        print(f"  \033[32mPASS\033[0m  {name}")
    else:
        FAILED.append((name, detail))
        print(f"  \033[31mFAIL\033[0m  {name}" + (f"\n          {detail}" if detail else ""))
    return condition


def skip(name: str, reason: str) -> None:
    SKIPPED.append((name, reason))
    print(f"  \033[33mSKIP\033[0m  {name} ({reason})")


def section(title: str) -> None:
    print(f"\n\033[1m{title}\033[0m")


def resume_file(name: str = "sample_resume.pdf"):
    return {"resume": (name, (FIXTURES / name).read_bytes(), "application/octet-stream")}


def github_rate_limited() -> bool:
    try:
        data = requests.get("https://api.github.com/rate_limit", timeout=8).json()
        return data["resources"]["core"]["remaining"] < 10
    except Exception:
        return True


# ---------------------------------------------------------------------------
# 1. Backend availability
# ---------------------------------------------------------------------------
def test_backend_up() -> dict | None:
    section("1. Backend availability")
    try:
        response = requests.get(f"{BASE}/api/health", timeout=10)
    except requests.RequestException as exc:
        check("backend is reachable", False, f"{exc}\n          Start it: uvicorn main:app --reload")
        return None
    if not check("GET /api/health returns 200", response.status_code == 200):
        return None
    health = response.json()
    check("health reports status ok", health.get("status") == "ok")
    check("RAG index is built at startup",
          (health.get("rag_index") or {}).get("chunks", 0) > 0,
          json.dumps(health.get("rag_index")))
    return health


# ---------------------------------------------------------------------------
# 2. Roles + knowledge base
# ---------------------------------------------------------------------------
def test_roles_and_kb() -> list:
    section("2. Roles and job-description knowledge base")
    roles = requests.get(f"{BASE}/api/roles", timeout=10).json()
    check("GET /api/roles returns roles", len(roles) >= 6, f"got {len(roles)}")
    check("every role exposes core and preferred skills",
          all(r.get("core_skills") and r.get("preferred_skills") for r in roles))
    check("every role has at least one job description",
          all(r.get("job_description_count", 0) > 0 for r in roles),
          str([(r["id"], r["job_description_count"]) for r in roles]))

    documents = requests.get(f"{BASE}/api/job-descriptions", timeout=10).json()
    check("GET /api/job-descriptions lists the corpus", len(documents) >= 6, f"got {len(documents)}")

    one = requests.get(f"{BASE}/api/job-descriptions/{documents[0]['id']}", timeout=10)
    check("GET /api/job-descriptions/{id} returns a full document",
          one.status_code == 200 and "required_skills" in one.json())
    check("unknown job description id returns 404",
          requests.get(f"{BASE}/api/job-descriptions/does-not-exist", timeout=10).status_code == 404)
    return roles


# ---------------------------------------------------------------------------
# 3. Resume parsing (PDF + DOCX + failure modes)
# ---------------------------------------------------------------------------
def test_resume_parsing() -> None:
    section("3. Resume parsing")
    for filename, label in [("sample_resume.pdf", "PDF"), ("sample_resume.docx", "DOCX")]:
        response = requests.post(f"{BASE}/api/parse-resume", files=resume_file(filename), timeout=30)
        if not check(f"{label} parses successfully", response.status_code == 200,
                     response.text[:200]):
            continue
        parsed = response.json()
        check(f"{label}: contact details extracted",
              parsed["contact"]["email"] == "ananya.sharma@gndec.ac.in"
              and parsed["contact"]["name"] == "Ananya Sharma"
              and bool(parsed["contact"]["phone"]),
              json.dumps(parsed["contact"]))
        check(f"{label}: all seven sections detected", len(parsed["sections"]) == 7,
              str(parsed["sections"]))
        check(f"{label}: skills extracted", len(parsed["skills"]) >= 30, str(len(parsed["skills"])))
        check(f"{label}: projects and experience parsed",
              len(parsed["projects"]) >= 3 and len(parsed["experience"]) >= 3)
        check(f"{label}: quantified achievements detected",
              sum(1 for a in parsed["achievements"] if a["quantified"]) >= 4)

    # PDF and DOCX of the same resume must agree -- proves format-independence.
    pdf = requests.post(f"{BASE}/api/parse-resume", files=resume_file("sample_resume.pdf")).json()
    docx = requests.post(f"{BASE}/api/parse-resume", files=resume_file("sample_resume.docx")).json()
    check("PDF and DOCX of the same resume yield identical skills",
          pdf["skills"] == docx["skills"],
          f"pdf-only={set(pdf['skills']) - set(docx['skills'])} "
          f"docx-only={set(docx['skills']) - set(pdf['skills'])}")

    section("3b. Invalid resume handling")
    cases = [
        ("unsupported extension", ("resume.txt", b"just text", "text/plain"), 422),
        ("file named .pdf that is not a PDF", ("resume.pdf", b"NOT A PDF" * 40, "application/pdf"), 422),
        ("empty file", ("resume.pdf", b"", "application/pdf"), 400),
        ("legacy .doc format", ("resume.doc", b"PK\x03\x04junk", "application/msword"), 422),
    ]
    for label, file_tuple, expected in cases:
        response = requests.post(f"{BASE}/api/parse-resume", files={"resume": file_tuple}, timeout=20)
        check(f"{label} -> HTTP {expected}", response.status_code == expected,
              f"got {response.status_code}: {response.text[:140]}")
        if response.status_code >= 400:
            check(f"{label} returns a readable message",
                  isinstance(response.json().get("detail"), (str, list)))

    response = requests.post(f"{BASE}/api/parse-resume", timeout=20)
    check("missing file field -> HTTP 422", response.status_code == 422)


# ---------------------------------------------------------------------------
# 4. GitHub analysis
# ---------------------------------------------------------------------------
def test_github(rate_limited: bool) -> None:
    section("4. GitHub analysis")
    if rate_limited:
        skip("live GitHub profile analysis", "public API rate limit reached")
    else:
        response = requests.post(f"{BASE}/api/analyze-github", json={"username": "octocat"}, timeout=40)
        if check("valid username returns 200", response.status_code == 200, response.text[:200]):
            data = response.json()
            check("profile fields present",
                  data["profile"]["username"].lower() == "octocat"
                  and "followers" in data["profile"])
            check("repository stats present", "original_repositories" in data["stats"])
            check("skill evidence carries a reason for every skill",
                  all(data["skill_evidence"].get(s) for s in data["skills"]),
                  str(data["skills"]))

        response = requests.post(f"{BASE}/api/analyze-github",
                                 json={"username": "definitely-not-a-user-zz99xq"}, timeout=40)
        check("unknown username -> HTTP 404", response.status_code == 404,
              f"got {response.status_code}")

    # These never touch the network.
    response = requests.post(f"{BASE}/api/analyze-github", json={"username": "bad name!"}, timeout=20)
    check("invalid username characters -> HTTP 400", response.status_code == 400,
          f"got {response.status_code}")
    response = requests.post(f"{BASE}/api/analyze-github", json={"username": "   "}, timeout=20)
    check("blank username -> HTTP 422 (validation)", response.status_code == 422,
          f"got {response.status_code}")


# ---------------------------------------------------------------------------
# 5. RAG
# ---------------------------------------------------------------------------
def test_rag() -> None:
    section("5. RAG ingestion and retrieval")
    status = requests.get(f"{BASE}/api/rag/status", timeout=30).json()
    index = status["index"]
    check("index contains chunks from every document",
          index["chunks"] > 100 and index["documents"] >= 6, json.dumps(index))
    check("index uses cosine similarity over normalised vectors",
          "cosine" in index["similarity"] and status["embedder"]["normalised"])
    check("chunks are labelled by job-description section",
          {"required_skills", "preferred_skills"} <= set(index["chunks_per_section"]),
          str(index["chunks_per_section"]))
    check("matching reads more chunks than it displays",
          status["settings"]["top_k_used_for_matching"] > status["settings"]["top_k_displayed"])

    # Retrieval must be semantically sensible, not keyword-coincidental.
    expectations = [
        ("PyTorch deep learning models", "pytorch"),
        ("vector database embeddings similarity search", "vector databases"),
        ("accessible responsive user interface", "responsive"),
        ("A/B testing and experiment design", "a/b test"),
    ]
    for query, expected_substring in expectations:
        results = requests.get(f"{BASE}/api/rag/search",
                               params={"q": query, "top_k": 3}, timeout=30).json()["results"]
        top_text = " ".join(r["text"].lower() for r in results[:3])
        check(f"query {query!r} retrieves relevant chunks",
              expected_substring in top_text,
              f"top result: {results[0]['text'][:90] if results else 'none'}")
        check(f"query {query!r} returns descending similarities",
              all(results[i]["similarity"] >= results[i + 1]["similarity"]
                  for i in range(len(results) - 1)))

    check("empty query -> HTTP 400",
          requests.get(f"{BASE}/api/rag/search", params={"q": ""}, timeout=20).status_code == 400)

    # Role filtering must restrict results to that role's documents.
    results = requests.get(f"{BASE}/api/rag/search",
                           params={"q": "required skills", "role_id": "data_scientist", "top_k": 6},
                           timeout=30).json()["results"]
    check("role filter restricts retrieval to that role",
          all(r["role_id"] == "data_scientist" for r in results),
          str({r["role_id"] for r in results}))


# ---------------------------------------------------------------------------
# 5b. Experience levels
# ---------------------------------------------------------------------------
def test_experience_levels() -> None:
    section("5b. Experience levels")
    levels = requests.get(f"{BASE}/api/experience-levels", timeout=20).json()
    check("GET /api/experience-levels lists the career stages", len(levels) >= 3,
          str(levels))
    ids = [l["id"] for l in levels]
    check("fresher is the first option", ids and ids[0] == "fresher", str(ids))
    targets = [l["skill_coverage_target"] for l in levels]
    check("coverage expectations rise with seniority",
          targets == sorted(targets) and len(set(targets)) == len(targets), str(targets))

    # The point of the feature: the same resume must not be punished for being
    # a fresher's. Use a posting the sample resume matches poorly.
    jd = pathlib.Path(__file__).parent.joinpath("sample_pasted_jd.txt").read_text()
    scores = {}
    for level_id in ids:
        response = requests.post(f"{BASE}/api/analyze", files=resume_file(),
                                 data={"role_id": "frontend_developer",
                                       "job_description": jd,
                                       "experience_level": level_id}, timeout=120)
        if response.status_code != 200:
            check(f"analysis at level {level_id}", False, response.text[:160])
            return
        data = response.json()
        scores[level_id] = (data["ats"]["score"], data["job_match"]["score"])
        check(f"level {level_id} is echoed back",
              data["experience_level"]["id"] == level_id)
        check(f"level {level_id}: ATS total still equals the sum of components",
              data["ats"]["score"] == sum(c["score"] for c in data["ats"]["components"]))
        check(f"level {level_id}: match total still equals the sum of components",
              data["job_match"]["score"] == sum(c["score"] for c in data["job_match"]["components"]))

    check("a fresher scores higher than a senior on the same resume",
          scores["fresher"][0] > scores["senior"][0]
          and scores["fresher"][1] > scores["senior"][1],
          str(scores))
    check("expectations are monotonic across levels",
          scores["fresher"][1] >= scores["mid"][1] >= scores["senior"][1], str(scores))

    # Transparency: the adjustment must be visible, not hidden in the number.
    data = requests.post(f"{BASE}/api/analyze", files=resume_file(),
                         data={"role_id": "frontend_developer", "job_description": jd,
                               "experience_level": "fresher"}, timeout=120).json()
    coverage_components = [c for c in data["job_match"]["components"]
                           if c.get("raw_coverage") is not None]
    check("match components report raw coverage alongside the scaled value",
          len(coverage_components) == 3, str(len(coverage_components)))
    check("corroboration is deliberately not scaled by experience",
          all(c.get("raw_coverage") is None for c in data["job_match"]["components"]
              if c["id"] == "evidence_corroboration"))
    check("every scaled component states the expectation it applied",
          all("earns full marks" in c["reason"] for c in coverage_components),
          str([c["reason"][:80] for c in coverage_components]))
    ats_scaled = [c for c in data["ats"]["components"]
                  if c["id"] in {"role_relevance", "jd_keyword_match"}]
    check("ATS coverage components state the expectation too",
          all("earns full marks" in c["reason"] for c in ats_scaled))

    section("5c. Experience level validation")
    check("unknown level -> HTTP 400",
          requests.post(f"{BASE}/api/analyze", files=resume_file(),
                        data={"role_id": "ai_ml_engineer", "experience_level": "wizard"},
                        timeout=60).status_code == 400)
    omitted = requests.post(f"{BASE}/api/analyze", files=resume_file(),
                            data={"role_id": "ai_ml_engineer"}, timeout=120).json()
    check("omitted level defaults to fresher",
          omitted["experience_level"]["id"] == "fresher",
          str(omitted["experience_level"]))


# ---------------------------------------------------------------------------
# 6. ATS scoring
# ---------------------------------------------------------------------------
def test_ats() -> None:
    section("6. ATS scoring")
    response = requests.post(f"{BASE}/api/ats-score",
                             files=resume_file(),
                             data={"role_id": "ai_ml_engineer"}, timeout=60)
    if not check("POST /api/ats-score returns 200", response.status_code == 200, response.text[:200]):
        return
    ats = response.json()["ats"]

    check("total equals the sum of component scores",
          ats["score"] == sum(c["score"] for c in ats["components"]),
          f'{ats["score"]} != {sum(c["score"] for c in ats["components"])}')
    check("maximum is 100", ats["max_score"] == 100)
    check("component maxima sum to 100", sum(c["max_score"] for c in ats["components"]) == 100)
    check("every component reports score, max, reason and evidence",
          all({"component", "score", "max_score", "reason", "evidence"} <= set(c) for c in ats["components"]))
    check("no component exceeds its maximum",
          all(0 <= c["score"] <= c["max_score"] for c in ats["components"]))

    # Determinism: identical input, identical output.
    again = requests.post(f"{BASE}/api/ats-score", files=resume_file(),
                          data={"role_id": "ai_ml_engineer"}, timeout=60).json()["ats"]
    check("scoring is deterministic across requests",
          json.dumps(ats, sort_keys=True) == json.dumps(again, sort_keys=True))

    # Discrimination: a weak resume must score far below a strong one.
    weak = requests.post(f"{BASE}/api/ats-score", files=resume_file("weak_resume.docx"),
                         data={"role_id": "ai_ml_engineer"}, timeout=60).json()["ats"]
    check("a weak resume scores far below a strong one",
          weak["score"] < ats["score"] - 40, f'weak={weak["score"]} strong={ats["score"]}')
    check("weak resume is banded as needing work", weak["band"]["label"] == "Needs Work",
          weak["band"]["label"])

    # The score must respond to the target role.
    scores = {}
    for role_id in ["ai_ml_engineer", "frontend_developer", "data_scientist"]:
        scores[role_id] = requests.post(f"{BASE}/api/ats-score", files=resume_file(),
                                        data={"role_id": role_id}, timeout=60).json()["ats"]["score"]
    check("an ML resume scores highest for the ML role",
          scores["ai_ml_engineer"] == max(scores.values()), str(scores))

    check("unknown role -> HTTP 400",
          requests.post(f"{BASE}/api/ats-score", files=resume_file(),
                        data={"role_id": "nope"}, timeout=30).status_code == 400)
    check("unknown job description id -> HTTP 404",
          requests.post(f"{BASE}/api/ats-score", files=resume_file(),
                        data={"role_id": "ai_ml_engineer", "job_description_id": "nope"},
                        timeout=30).status_code == 404)


# ---------------------------------------------------------------------------
# 7. Job matching
# ---------------------------------------------------------------------------
def test_job_match() -> None:
    section("7. Job/role matching")
    response = requests.post(f"{BASE}/api/job-match", files=resume_file(),
                             data={"role_id": "ai_ml_engineer"}, timeout=60)
    if not check("POST /api/job-match returns 200", response.status_code == 200, response.text[:200]):
        return
    payload = response.json()
    match = payload["job_match"]

    check("match total equals the sum of its components",
          match["score"] == sum(c["score"] for c in match["components"]))
    check("match component maxima sum to 100",
          sum(c["max_score"] for c in match["components"]) == 100)
    check("requirements were derived from retrieved chunks",
          len(match["requirements_derived_from_rag"]) >= 8,
          str(len(match["requirements_derived_from_rag"])))
    check("core and preferred requirement sets are disjoint",
          not (set(match["core_skills"]["matched"] + match["core_skills"]["missing"])
               & set(match["preferred_skills"]["matched"] + match["preferred_skills"]["missing"])))
    check("matched + missing equals the requirement total",
          len(match["core_skills"]["matched"]) + len(match["core_skills"]["missing"])
          == match["core_skills"]["total"])

    rows = match["skill_breakdown"]
    check("every skill row names its sources when matched",
          all(bool(r["sources"]) == r["matched"] for r in rows))
    check("at least one skill row carries job-description evidence",
          any(r["job_description_evidence"] for r in rows))
    check("every requirement states why it is required",
          all(r["why_required"] for r in rows))
    check("a skill matched from the resume carries resume evidence",
          all(r["resume_evidence"] for r in rows if "resume" in r["sources"]))

    # Evidence is quoted verbatim to the user, so it must not carry extraction
    # artefacts: pdfplumber's "(cid:NNN)" placeholders or list markers.
    all_evidence = [e for r in rows for e in r["resume_evidence"] + r["job_description_evidence"]]
    check("evidence quoted to the user has no PDF glyph artefacts",
          not any("(cid:" in e for e in all_evidence),
          next((e for e in all_evidence if "(cid:" in e), ""))
    check("evidence quoted to the user has no leading bullet markers",
          not any(e.lstrip().startswith(("\u2022", "- ", "* ")) for e in all_evidence),
          next((e for e in all_evidence if e.lstrip().startswith(("\u2022", "- ", "* "))), ""))

    # RAG must actually influence the requirement set, not just decorate it.
    from skills_data import ROLES_BY_ID
    catalogue = set(ROLES_BY_ID["ai_ml_engineer"]["core_skills"]) | \
        set(ROLES_BY_ID["ai_ml_engineer"]["preferred_skills"])
    derived = {r["skill"] for r in match["requirements_derived_from_rag"]}
    check("RAG contributes requirements absent from the role catalogue",
          bool(derived - catalogue), f"derived={sorted(derived)}")

    # Matching must respond to the target role.
    frontend = requests.post(f"{BASE}/api/job-match", files=resume_file(),
                             data={"role_id": "frontend_developer"}, timeout=60).json()["job_match"]
    check("an ML resume matches the ML role better than the frontend role",
          match["score"] > frontend["score"], f'ml={match["score"]} fe={frontend["score"]}')


# ---------------------------------------------------------------------------
# 8. Full pipeline
# ---------------------------------------------------------------------------
def test_full_pipeline(rate_limited: bool) -> None:
    section("8. Complete /api/analyze pipeline")
    started = time.perf_counter()
    response = requests.post(f"{BASE}/api/analyze", files=resume_file(),
                             data={"role_id": "ai_ml_engineer"}, timeout=120)
    elapsed = time.perf_counter() - started
    if not check("POST /api/analyze returns 200", response.status_code == 200, response.text[:200]):
        return
    result = response.json()

    check("response contains every pipeline section",
          {"resume", "github", "ats", "job_match", "rag", "summary", "timings_ms", "stages"}
          <= set(result))
    check("all six stages reported", len({s["stage"] for s in result["stages"]}) == 6,
          str({s["stage"] for s in result["stages"]}))
    check("the final stage is the rule-based summary",
          "summary" in {s["stage"] for s in result["stages"]},
          str({s["stage"] for s in result["stages"]}))
    check("stage timings are positive and plausible",
          all(v >= 0 for v in result["timings_ms"].values())
          and result["timings_ms"]["total"] < 120_000,
          json.dumps(result["timings_ms"]))
    check("raw resume text is not returned wholesale",
          "raw_text" not in result["resume"] and len(result["resume"]["text_preview"]) <= 1500)
    check("completed in reasonable time", elapsed < 90, f"{elapsed:.1f}s")

    section("8b. Pasted job description")
    pasted = pathlib.Path(__file__).parent / "sample_pasted_jd.txt"
    response = requests.post(f"{BASE}/api/analyze", files=resume_file(),
                             data={"role_id": "frontend_developer",
                                   "job_description": pasted.read_text()}, timeout=120)
    if check("pasted job description is accepted", response.status_code == 200, response.text[:200]):
        data = response.json()
        check("pasted JD is recorded as user-provided",
              data["job_description"]["provided_by_user"] is True)
        keywords = [c for c in data["ats"]["components"] if c["id"] == "jd_keyword_match"][0]
        check("keywords come from the pasted text",
              {"TypeScript", "Tailwind CSS", "Vite"} <= set(keywords["details"]["jd_keywords"]),
              str(keywords["details"]["jd_keywords"]))
        check("pasted text is chunked and retrieved over",
              any(r["section"] == "pasted" for r in data["rag"]["results"]),
              str([r["section"] for r in data["rag"]["results"]]))
        match = data["job_match"]
        kinds = {r["skill"]: r["kind"] for r in match["requirements_derived_from_rag"]}
        check("skills under 'Required skills:' become core requirements",
              kinds.get("TypeScript") == "core" and kinds.get("React") == "core",
              str({k: kinds.get(k) for k in ["TypeScript", "React"]}))
        check("skills under 'Nice to have:' stay preferred",
              kinds.get("Next.js") == "preferred"
              and kinds.get("Web Accessibility") == "preferred",
              str({k: kinds.get(k) for k in ["Next.js", "Web Accessibility"]}))
        check("short bullets from the pasted posting are still captured",
              "Vite" in kinds and "REST APIs" in kinds,
              str(sorted(kinds)))
        check("core and preferred requirements are reasonably balanced",
              match["preferred_skills"]["total"] >= 4 and match["core_skills"]["total"] >= 4,
              f'core={match["core_skills"]["total"]} preferred={match["preferred_skills"]["total"]}')
        check("retrieved evidence is ordered by similarity",
              all(data["rag"]["results"][i]["similarity"] >= data["rag"]["results"][i + 1]["similarity"]
                  for i in range(len(data["rag"]["results"]) - 1)),
              str([r["similarity"] for r in data["rag"]["results"]]))

    section("8c. GitHub failure must degrade, not break")
    response = requests.post(f"{BASE}/api/analyze", files=resume_file(),
                             data={"role_id": "ai_ml_engineer",
                                   "github_username": "definitely-not-a-user-zz99xq"}, timeout=120)
    if check("pipeline still returns 200 with a bad GitHub username",
             response.status_code == 200, response.text[:200]):
        data = response.json()
        check("the GitHub problem is reported to the user", bool(data["github_error"]))
        check("ATS and match scores were still produced",
              data["ats"]["score"] > 0 and data["job_match"]["score"] > 0)

    if not rate_limited:
        section("8d. Pipeline with a real GitHub profile")
        response = requests.post(f"{BASE}/api/analyze", files=resume_file(),
                                 data={"role_id": "ai_ml_engineer", "github_username": "octocat"},
                                 timeout=120)
        if check("pipeline with GitHub returns 200", response.status_code == 200):
            data = response.json()
            check("GitHub evidence is kept separate from resume evidence",
                  "github_only" in data["job_match"]["evidence_summary"])
            github_component = [c for c in data["ats"]["components"] if c["id"] == "github_evidence"][0]
            check("the GitHub ATS component scored", github_component["score"] > 0,
                  github_component["reason"])
    else:
        skip("pipeline with a real GitHub profile", "public API rate limit reached")

    section("8e. Validation")
    check("missing role_id -> HTTP 422",
          requests.post(f"{BASE}/api/analyze", files=resume_file(), timeout=30).status_code == 422)
    check("missing resume -> HTTP 422",
          requests.post(f"{BASE}/api/analyze", data={"role_id": "ai_ml_engineer"},
                        timeout=30).status_code == 422)
    check("unknown role -> HTTP 400",
          requests.post(f"{BASE}/api/analyze", files=resume_file(),
                        data={"role_id": "nope"}, timeout=30).status_code == 400)


# ---------------------------------------------------------------------------
# 9. Streaming
# ---------------------------------------------------------------------------
def test_streaming() -> None:
    section("9. Streaming pipeline (Server-Sent Events)")
    response = requests.post(f"{BASE}/api/analyze/stream", files=resume_file(),
                             data={"role_id": "backend_developer"}, stream=True, timeout=120)
    if not check("stream endpoint returns 200", response.status_code == 200):
        return
    check("content type is text/event-stream",
          "text/event-stream" in response.headers.get("content-type", ""))

    events, result = [], None
    event_name = None
    for raw in response.iter_lines(decode_unicode=True):
        if raw is None:
            continue
        if raw.startswith("event: "):
            event_name = raw[7:].strip()
        elif raw.startswith("data: "):
            payload = json.loads(raw[6:])
            if event_name == "stage":
                events.append(payload)
            elif event_name == "result":
                result = payload

    check("stage events were streamed", len(events) >= 10, f"got {len(events)}")
    check("each stage reports running then a terminal status",
          {"running"} <= {e["status"] for e in events}
          and {"done"} <= {e["status"] for e in events})
    check("a final result event was delivered", result is not None)
    if result:
        check("streamed result matches the shape of /api/analyze",
              {"ats", "job_match", "rag", "summary"} <= set(result))

    # Errors must arrive as an SSE error event, not a dropped connection.
    response = requests.post(f"{BASE}/api/analyze/stream",
                             files={"resume": ("bad.pdf", b"NOT A PDF" * 30, "application/pdf")},
                             data={"role_id": "ai_ml_engineer"}, stream=True, timeout=60)
    body = response.text
    check("an invalid resume produces an SSE error event",
          "event: error" in body and "resume_parse_error" in body, body[:200])


# ---------------------------------------------------------------------------
# 10. Summary (rule-based; this project uses no language model)
# ---------------------------------------------------------------------------
def test_summary(health: dict) -> None:
    section("10. Rule-based summary")
    check("health reports that no language model is used",
          health.get("uses_language_model") is False, str(health))
    check("health no longer advertises an Anthropic integration",
          "anthropic_configured" not in health, str(list(health)))

    result = requests.post(f"{BASE}/api/analyze", files=resume_file(),
                           data={"role_id": "ai_ml_engineer"}, timeout=120).json()
    check("the response carries a summary, not an explanation",
          "summary" in result and "explanation" not in result, str(list(result)))

    summary = result["summary"]
    sections = summary["sections"]
    check("the summary has exactly three sections", len(sections) == 3,
          str([s["id"] for s in sections]))
    check("sections are ATS, match and actions, in that order",
          [s["id"] for s in sections] == ["ats", "match", "actions"],
          str([s["id"] for s in sections]))
    check("every section has a title and at least two bullets",
          all(s["title"] and len(s["bullets"]) >= 2 for s in sections),
          str([(s["id"], len(s["bullets"])) for s in sections]))
    check("the action list is marked as ordered",
          sections[2]["ordered"] is True and all(not s["ordered"] for s in sections[:2]))
    check("it declares that rules produced it", summary["generated_by"] == "rules")

    # Bullets must stay short enough to scan.
    bullets = [b for s in sections for b in s["bullets"]]
    check("no bullet is longer than 240 characters",
          all(len(b) <= 240 for b in bullets),
          max(bullets, key=len)[:160] if bullets else "")
    check("the whole summary stays under 120 words",
          sum(len(b.split()) for b in bullets) < 120,
          str(sum(len(b.split()) for b in bullets)))

    # The summary must quote the computed numbers, never contradict them.
    check("the ATS section quotes the computed ATS score",
          str(result["ats"]["score"]) in sections[0]["title"], sections[0]["title"])
    check("the match section quotes the computed match score",
          str(result["job_match"]["score"]) in sections[1]["title"], sections[1]["title"])
    check("the match section names the experience level",
          result["experience_level"]["label"] in " ".join(sections[1]["bullets"]),
          str(sections[1]["bullets"]))

    # Determinism: no model, so identical input must give identical words.
    again = requests.post(f"{BASE}/api/analyze", files=resume_file(),
                          data={"role_id": "ai_ml_engineer"}, timeout=120).json()["summary"]
    check("the same analysis produces exactly the same summary",
          json.dumps(summary, sort_keys=True) == json.dumps(again, sort_keys=True))


def test_no_language_model_anywhere() -> None:
    """The project claims to use no LLM. Verify that structurally."""
    section("10b. No language model in the codebase")
    backend = pathlib.Path(__file__).resolve().parent.parent

    check("llm_explainer.py has been removed",
          not (backend / "llm_explainer.py").exists())
    check("anthropic is not a dependency",
          "anthropic" not in (backend / "requirements.txt").read_text().lower())
    check(".env.example requests no model API key",
          "ANTHROPIC" not in (backend / ".env.example").read_text())

    offenders = []
    for path in list(backend.glob("*.py")) + list((backend / "rag").glob("*.py")):
        text = path.read_text().lower()
        if "anthropic" in text or "import openai" in text:
            offenders.append(path.name)
    check("no backend module imports a model provider", not offenders, str(offenders))


# ---------------------------------------------------------------------------
# 11. Offline-only module tests
# ---------------------------------------------------------------------------
def test_modules_directly() -> None:
    section("11. Module-level behaviour")
    from ats_scorer import MAX_TOTAL, WEIGHTS
    from job_matcher import MATCH_MAX
    from resume_parser import ResumeParseError, parse_resume
    from skills_data import ROLES, SKILLS, extract_skills

    check("ATS weights sum to 100", MAX_TOTAL == 100 and sum(WEIGHTS.values()) == 100)

    from experience_levels import EXPERIENCE_LEVELS, scaled_coverage
    check("every experience level defines a coverage target in (0, 1]",
          all(0 < float(l["skill_coverage_target"]) <= 1 for l in EXPERIENCE_LEVELS.values()))
    check("coverage scaling caps at 1.0", scaled_coverage(0.9, 0.5) == 1.0)
    check("coverage scaling is proportional below the target",
          abs(scaled_coverage(0.25, 0.5) - 0.5) < 1e-9)
    check("a fresher is scored more leniently than a senior at equal coverage",
          scaled_coverage(0.4, EXPERIENCE_LEVELS["fresher"]["skill_coverage_target"])
          > scaled_coverage(0.4, EXPERIENCE_LEVELS["senior"]["skill_coverage_target"]))
    check("match weights sum to 100", MATCH_MAX == 100)
    check("every role skill exists in the taxonomy",
          all(s in SKILLS for r in ROLES for s in r["core_skills"] + r["preferred_skills"]))

    # Skill extraction must not fire on look-alike words.
    check("'Java' does not match inside 'JavaScript'",
          extract_skills("JavaScript developer") == ["JavaScript"])
    check("'Go' does not match the English verb",
          "Go" not in extract_skills("we go to production every friday"))
    check("'R' does not match inside 'R&D'", "R" not in extract_skills("worked in R&D"))
    check("'Testing' does not match inside 'hypothesis testing'",
          extract_skills("hypothesis testing") == ["Statistics"],
          str(extract_skills("hypothesis testing")))
    check("capitalised single-letter languages are still detected",
          {"C", "C++", "Go", "R"} <= set(extract_skills("Languages: C, C++, Go, R")))

    check("oversized upload is rejected",
          _raises(lambda: parse_resume(b"%PDF" + b"x" * (11 * 1024 * 1024), "big.pdf"),
                  ResumeParseError))


def _raises(fn, exception_type) -> bool:
    try:
        fn()
    except exception_type:
        return True
    except Exception:
        return False
    return False


# ---------------------------------------------------------------------------
def main() -> int:
    print("\033[1mCareer Engine — end-to-end test suite\033[0m")
    print(f"Target: {BASE}")

    health = test_backend_up()
    if health is None:
        print("\n\033[31mBackend is not running; aborting.\033[0m")
        print("Start it with:  cd backend && uvicorn main:app --reload")
        return 1

    rate_limited = github_rate_limited()
    if rate_limited:
        print("\n\033[33mNote: the GitHub public API rate limit is exhausted; "
              "live GitHub tests will be skipped.\033[0m")

    test_roles_and_kb()
    test_resume_parsing()
    test_github(rate_limited)
    test_rag()
    test_experience_levels()
    test_ats()
    test_job_match()
    test_full_pipeline(rate_limited)
    test_streaming()
    test_summary(health)
    test_no_language_model_anywhere()
    test_modules_directly()

    print("\n" + "=" * 62)
    print(f"\033[1mPassed: {len(PASSED)}   Failed: {len(FAILED)}   Skipped: {len(SKIPPED)}\033[0m")
    if FAILED:
        print("\n\033[31mFailures:\033[0m")
        for name, detail in FAILED:
            print(f"  - {name}")
            if detail:
                print(f"      {detail}")
    if SKIPPED:
        print("\n\033[33mSkipped:\033[0m")
        for name, reason in SKIPPED:
            print(f"  - {name} ({reason})")
    print("=" * 62)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())

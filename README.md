# Career Engine

A local web application that analyses a student's **resume**, **GitHub profile**
and **target job role** and returns two things: a transparent **ATS score**, and
an **explainable job match** built with RAG over job-description data.

Every number it reports is computed by rules you can read in this repository.


---

# how to run -

// stop servers - 

pkill -f "uvicorn main:app" && pkill -f "Career-Engine-Project/frontend"

// backend 

cd backend && source .venv/bin/activate && uvicorn main:app --reload

// frontend

cd frontend && npm run dev



## Table of contents

1. [What it does](#1-what-it-does)
2. [Objectives](#2-objectives)
3. [Run it in 5 minutes](#3-run-it-in-5-minutes)
4. [How the app is put together](#4-how-the-app-is-put-together)
5. [Feature 1 — Resume parsing](#5-feature-1--resume-parsing)
6. [Feature 2 — GitHub analysis](#6-feature-2--github-analysis)
7. [Feature 3 — ATS scoring](#7-feature-3--ats-scoring)
8. [Feature 4 — Experience levels](#8-feature-4--experience-levels)
9. [Feature 5 — The RAG pipeline](#9-feature-5--the-rag-pipeline)
10. [Feature 6 — Job matching](#10-feature-6--job-matching)
11. [Feature 7 — The summary](#11-feature-7--the-summary)
12. [The frontend](#12-the-frontend)
13. [API reference](#13-api-reference)
14. [Folder structure](#14-folder-structure)
15. [Configuration](#15-configuration)
16. [Testing](#16-testing)
17. [Limitations](#17-limitations)
18. [Future scope](#18-future-scope)
19. [Troubleshooting](#19-troubleshooting)

---

## 1. What it does

A student uploads their resume, optionally gives their GitHub username, picks a
target role and experience level, and pastes the job description they are
applying to. In about a second they get back:

**An ATS score out of 100.** Ten weighted components — contact details, resume
sections, skill breadth, role relevance, job-description keyword overlap,
projects and experience, quantified achievements, education, formatting, and
public GitHub evidence. The total is the arithmetic sum of the ten, and each one
states the reason it scored what it did plus the literal text that earned it.

**A job match score out of 100.** The requirements the candidate is measured
against are not hard-coded. They are extracted from job-description passages
that a semantic search retrieved for this exact role and posting. Each skill row
shows the job-description sentence that demanded it and the resume line or
repository that satisfied it.

**A short summary.** Three sections of one-line bullets: what the ATS score
means, which requirements are and are not evidenced, and the two or three
highest-impact things to fix, ranked by points recoverable.

### The problem it solves

Most applications are filtered by an Applicant Tracking System before a human
reads them, and students get no visibility into why they were rejected. Existing
tools are opaque — they return a number with no derivation, or they hand the
whole resume to a language model and repeat whatever it says. Neither tells a
student what to actually change.

### The one distinction to understand

| | How it is produced |
|---|---|
| **ATS score** | Deterministic rule-based calculation over parsed resume fields. |
| **Job match score** | Fixed weighted formula comparing structured candidate evidence against RAG-retrieved requirements. |
| **Summary** | Plain-language bullets assembled from the two reports above by fixed rules. |

Nothing in that table involves a model. That is deliberate, and it is the point
of the project: the same resume always produces the same number, anyone can
recompute it by hand from the report, and every point is attributable.

---

## 2. Objectives

**Objective 1** — To develop a web application that analyzes a student's resume,
GitHub profile, and target job role to generate an ATS score.

**Objective 2** — To implement a feature that uses RAG over job description data
for explainable job/role matching.

A third objective (career roadmap and interview preparation) is intentionally
out of scope for this phase.

---

## 3. Run it in 5 minutes

You need **Python 3.10+** and **Node.js 18+**. Everything runs on your machine;
there is no deployment and no account to create.

### First time only

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # optional — it runs fine with an empty .env
```

```bash
cd frontend
npm install
```

### Every time — two terminals

**Terminal 1 (backend):**

```bash
cd backend && source .venv/bin/activate && uvicorn main:app --reload
```

**Terminal 2 (frontend):**

```bash
cd frontend && npm run dev
```

Then open **<http://localhost:5173>**.

Interactive API docs live at **<http://localhost:8000/docs>** — useful for
seeing every endpoint and trying them without the UI.

> **First run takes ~10 seconds longer.** The embedding model (~90 MB) downloads
> once from Hugging Face and the vector index is built. Both are cached
> afterwards. With no internet it falls back to an offline embedding backend and
> still works.

### Using the app

1. **Sign in** with any email. No password, no server — the email is stored in
   your browser to label the session.
2. **Enter your details** — resume (PDF or DOCX), GitHub username (optional),
   target role, experience level, and the job description you are applying to.
3. **Read the analysis** — scores up top, then tabs for Overview, ATS Breakdown,
   Job Match, and Resume & GitHub.

---

## 4. How the app is put together

```
                    React + Vite + Tailwind   (localhost:5173)
                                 |
                                 |  fetch /api/...  (Vite proxies to :8000)
                                 v
                    FastAPI + Uvicorn         (localhost:8000)
                                 |
     +----------------+----------+-----------+--------------------+
     |                |                      |                    |
     v                v                      v                    v
resume_parser.py  github_analyzer.py   data/job_descriptions/   config.py
  pdfplumber        GitHub REST API      12 JSON documents
  python-docx            |                      |
     |                   |                      v
     |                   |              rag/chunker.py     split into 261 chunks
     |                   |                      |
     |                   |              rag/embedder.py    384-dim vectors
     |                   |                      |
     |                   |              rag/vector_store.py  FAISS index
     |                   |                      |
     |                   |              rag/retriever.py   cosine search
     |                   |                      |
     +--------+----------+                      |
              |                                 |
              v                                 |
      ats_scorer.py  <------------------------- +
   (deterministic, 10 components)               |
              |                                 v
              |                        job_matcher.py
              |            (candidate evidence vs retrieved requirements)
              |                                 |
              +---------------+-----------------+
                              v
                      summary_builder.py
                 three sections of bullets, by rules
                              |
                              v
                      Explainable results
```

### The pipeline, step by step

Defined in `backend/main.py` as `run_pipeline()`. It is written as a **generator**
that yields progress events and finally the result, so the same code serves both
the plain JSON endpoint and the streaming one.

| # | Stage | Module | What happens |
|---|---|---|---|
| 1 | Parse resume | `resume_parser.py` | PDF/DOCX → structured fields |
| 2 | Analyse GitHub | `github_analyzer.py` | Public API → skill evidence (skipped if no username; a failure degrades, never breaks) |
| 3 | Retrieve JD evidence | `rag/retriever.py` | Semantic search → relevant job-description chunks |
| 4 | Score ATS | `ats_scorer.py` | 10 weighted components → 0–100 |
| 5 | Match | `job_matcher.py` | Candidate evidence vs retrieved requirements → 0–100 |
| 6 | Summarise | `summary_builder.py` | Three sections of bullets |

Each stage's real wall-clock duration is measured and reported — the UI shows
genuine progress, not a simulated bar.

### The idea that holds it together: one shared vocabulary

`skills_data.py` defines **112 canonical skills**, each with aliases. Resume
text, GitHub metadata and job-description text are all resolved to the *same*
canonical names. That is what makes "Python in the resume", "Python on GitHub"
and "Python required by the JD" directly comparable.

Matching is alias + word-boundary regex — deterministic, and careful about
look-alikes:

```python
extract_skills("JavaScript developer")      # ['JavaScript']   not Java
extract_skills("we go to production")       # []               not Go
extract_skills("worked in R&D")             # []               not R
extract_skills("hypothesis testing")        # ['Statistics']   not Software Testing
extract_skills("Languages: C, C++, Go, R")  # all four, correctly
```

---

## 5. Feature 1 — Resume parsing

**File:** `backend/resume_parser.py`

```
bytes → raw text → clean lines → section segmentation → field extraction
```

**Text extraction.** `pdfplumber` for PDF, `python-docx` for DOCX (including
tables, since students often lay skills out in them).

**Section segmentation.** Resume headings vary wildly, so a vocabulary maps them
to canonical sections — "EDUCATION", "Academic Background" and "Qualifications"
all become `education`.

**Field extraction.** Regex for email, phone (Indian and international formats),
LinkedIn and GitHub URLs; degree and CGPA patterns for education; the shared
taxonomy for skills.

Skills are tracked in two buckets so the scorer can tell them apart:

* **declared** — listed inside an explicit Skills section
* **contextual** — mentioned anywhere else, e.g. in a project bullet

**Quantified achievements.** Lines carrying a real metric — a percentage, a
multiplier, a magnitude, a count of users or records. Education percentages are
excluded, since a CGPA is a qualification, not impact.

**Two fixes worth knowing about**, because they look like bugs otherwise:

* pdfplumber emits `(cid:127)` where a glyph has no unicode mapping — usually a
  Word bullet. A leading one becomes a bullet character; the rest are stripped.
* Word stores list bullets in the numbering definition, not the text, so
  `python-docx` returns them unmarked. The parser re-attaches a marker from the
  paragraph style, otherwise every DOCX would score zero on bullet formatting.

**Error handling.** Unsupported extension, empty file, oversized file, a file
merely *named* `.pdf`, a scanned image PDF with no text layer — each returns a
specific, actionable message rather than a stack trace.

---

## 6. Feature 2 — GitHub analysis

**File:** `backend/github_analyzer.py`

Reads a **public** profile through the GitHub REST API and derives skill evidence
from three signals:

1. repository language (plus the byte-level breakdown for top repositories)
2. repository topics
3. repository name and description text

Forked repositories are excluded — forking something is not proof you wrote it.

**The important design rule:** GitHub evidence is **never merged** into resume
skills. A skill found only on GitHub is recorded as `source: "github"`, and the
UI shows resume-only, GitHub-only and both. A skill in both columns is a claim
backed by public code, which is stronger evidence than either alone.

Every piece of evidence carries *why* it matched — `"Topic 'react' on repository
X"`, `"Primary language of 4 repositories"`. That matters because a repository
description mentioning a technology is not proof of proficiency, and the
interface says so rather than over-claiming.

**Failures degrade, they don't break.** Unknown username, rate limit, auth
problem, network timeout — each maps to the right HTTP status on the standalone
endpoint, and inside the full pipeline it becomes a warning while the analysis
completes with resume evidence only.

> **Set a `GITHUB_TOKEN` before any demo.** Anonymous access is 60 requests/hour
> and one analysis uses up to 7. A free token raises it to 5000/hour. See
> [Configuration](#15-configuration).

---

## 7. Feature 3 — ATS scoring

**File:** `backend/ats_scorer.py` — **no model is involved anywhere in it.**

An ATS is not intelligent. It parses a document, looks for fields and keywords,
and ranks the result. Modelling that with transparent rules gives three
properties a model cannot:

* **Deterministic** — the same resume always produces the same number.
* **Reproducible** — anyone can recompute the score by hand from the report.
* **Explainable** — every point is attributed to a named component with a stated
  reason and the literal evidence that earned it.

### The ten components

| # | Component | Max | What it measures |
|---|---|---:|---|
| A | Contact Information | 10 | Email 3, phone 2, name 2, LinkedIn 2, GitHub 1 |
| B | Resume Sections | 10 | Skills 3, Experience-or-Projects 3, Education 2, Summary 1, Certifications-or-Achievements 1 |
| C | Skills Breadth | 12 | 8 for how many skills, 4 for category diversity |
| D | Target Role Relevance | 18 | 13.5 core coverage + 4.5 preferred coverage |
| E | Job Description Keyword Match | 20 | Share of the posting's skill keywords present |
| F | Experience & Projects | 10 | Entry count plus whether entries name technologies |
| G | Quantifiable Achievements | 5 | Lines carrying a real metric |
| H | Education | 5 | Entry parsed 2, degree recognised 2, CGPA/percentage 1 |
| I | Formatting & Readability | 5 | Bullets 2, action verbs 1, length 1, bullet length 1 |
| J | GitHub Profile Evidence | 5 | Profile 1, ≥3 original repos 1, ≥2 described 1, relevant skills 2 |
| | **Total** | **100** | |

### Why these weights

A, B and I model what an ATS **parser** needs — if it cannot find your email or
read your sections, nothing else matters. **E carries the largest single weight
(20)** because keyword matching against the specific posting is the closest
analogue to how real ATS ranking works, and D (18) generalises that to the role.
C, F, G and H reward the substance a human reviewer looks for once the parser
lets you through.

**J is only 5 points on purpose.** A real ATS never sees a GitHub profile.
Weighting it heavily would make the score less faithful to the thing it models.
It is included because the project's stated input is *resume + GitHub + role*,
and it is kept small and clearly separated rather than blended in.

### Where the job-description keywords come from

Paste a job description and its keywords are used. Omit it and the keywords come
from the knowledge-base documents for the target role. The response always
states which, in `job_description.source`.

---

## 8. Feature 4 — Experience levels

**File:** `backend/experience_levels.py`

A final-year student will never evidence every skill in a job description.
Scoring them against a senior candidate's bar makes the number meaningless — a
fresher matching 20 of 55 requirements is doing *well*, not badly.

The fix is deliberately **not** "give freshers bonus points", which would be
arbitrary and impossible to defend. Instead the **expectation** changes while the
arithmetic stays identical:

```python
scaled_coverage = min(1.0, actual_coverage / expected_coverage)
```

| Level | Expected coverage | Skills for full breadth | Achievements | Experience / Projects split |
|---|---:|---:|---:|---|
| Fresher (0–1 years) | 50% | 10 | 2 | 3 / 7 |
| 2–4 years | 70% | 15 | 3 | 5 / 5 |
| 5+ years | 85% | 20 | 4 | 5 / 5 |

A fresher covering 36% of a role's requirements scores 36/50 = **72%** of the
available points. A senior candidate at the same 36% scores 36/85 = **42%**.

This applies to the coverage-based components (Skills Breadth, Role Relevance,
JD Keyword Match, Quantifiable Achievements) and to the Experience & Projects
split — freshers rarely have formal employment, so projects carry 7 of its 10
points instead of 5. Internships still count as experience.

**Structural components never change with career stage** — contact details,
sections, education, formatting, GitHub. A missing email is missing at any level.

Every affected component states the expectation it applied in its reason, and
the job-match components report the raw coverage next to the scaled value, so
the adjustment is visible rather than hidden inside the score.

---

## 9. Feature 5 — The RAG pipeline

**Files:** `backend/rag/` — this is Objective 2.

```
data/job_descriptions/*.json      12 documents across 6 roles
          |
          v
   chunker.py                     261 chunks, one idea each, labelled with
          |                       job title, company, role and section
          v
   embedder.py                    each chunk → a 384-dimensional unit vector
          |                       (all-MiniLM-L6-v2, runs locally)
          v
   vector_store.py                FAISS IndexFlatIP + chunk metadata, persisted
          |
          v
   retriever.py                   query → embed → cosine search → top-k chunks
```

### Document loading

Job descriptions are JSON with explicit fields — `required_skills`,
`preferred_skills`, `responsibilities`, `qualifications`, `about_the_role`. The
structure is kept rather than flattened, because *where* a requirement appears
determines how strongly it counts.

### Chunking

Each bullet becomes its own chunk — bullets are already one idea each. Free
prose is split into overlapping 70-word windows (15-word overlap) so a sentence
spanning a boundary is still fully represented somewhere.

**Why chunk at all?** Embedding a whole 600-word document produces a vector
sitting in the "average" of all its topics. A query about required Python skills
would then match the entire document with no indication of which part was
relevant. Small chunks keep one idea per vector, which makes retrieval precise
*and* keeps the retrieved text short enough to show the user as evidence.

### Embeddings

An embedding maps text to a fixed-length list of numbers — here 384 — such that
texts with similar *meaning* land close together. That is why the query
`vector database embeddings` retrieves *"Experience with vector databases such as
FAISS, Chroma, Pinecone or Qdrant"* even though the wording differs.

All vectors are **L2-normalised** to unit length. For unit vectors the dot
product **is** the cosine similarity — which is what lets the index use a plain
inner-product search and still be doing cosine search.

### Vector store

FAISS `IndexFlatIP`:

* **Flat** — vectors are stored as-is and each query is compared against all of
  them. Exact, no approximation error, instantaneous at this corpus size.
* **IP** — inner product, which equals cosine similarity on normalised vectors.

The index and its chunk metadata persist to `data/vector_store/` and rebuild
automatically when the corpus content hash or the embedding backend changes —
vectors from one model are meaningless to another, so mixing them would silently
corrupt retrieval.

### Retrieval

The query is embedded with the **same** model as the corpus — a different one
would put the query in a different vector space and the scores would be
meaningless. The query is built by expansion: any pasted job description first,
then the role's catalogue skills as vocabulary seeds, then intent words. Results
are filtered by `role_id` and diversified so evidence spans more than one
employer.

### Two decisions worth knowing

**Chunks are embedded without a title prefix.** An earlier version prefixed each
chunk with `"<job title> at <company> | <section>:"`. Measured on the query
`vector database embeddings`, that prefix dropped the correct chunk's similarity
from **0.58 to 0.30** and let an unrelated SQL chunk outrank it — on a short
chunk, the prefix dominates the averaged representation. Role scoping is handled
by the `role_id` metadata filter instead.

**The matcher reads deeper than the UI shows.** Requirements are derived from the
top 24 chunks (`RAG_DERIVATION_TOP_K`) while 8 are displayed. A handful of chunks
names too few skills to compute a coverage ratio against reliably.

### Offline fallback

If `sentence-transformers` cannot load the model — typically no internet on the
first run — the system switches to a **TF-IDF + Truncated SVD** embedder.
Classical Latent Semantic Analysis, pure scikit-learn, no download. Weaker on
paraphrases, but the whole pipeline keeps working. Force it with
`FORCE_OFFLINE_EMBEDDINGS=1`.

### Seeing it for yourself

```bash
curl -s "http://localhost:8000/api/rag/search?q=PyTorch%20deep%20learning&top_k=3"
curl -s "http://localhost:8000/api/rag/status"
```

---

## 10. Feature 6 — Job matching

**File:** `backend/job_matcher.py`

### The rule this file exists to enforce

We do **not** hand a resume and a job description to a model and ask "is this a
good match?". Instead:

1. The requirement set is **derived from the RAG-retrieved chunks** (plus the
   role catalogue as a baseline).
2. Candidate evidence comes from the parsed resume and the GitHub analysis, kept
   separately labelled.
3. The two are compared with a fixed, published formula.

### How requirements are derived

Each retrieved chunk is scanned with the shared skill taxonomy:

* a skill in a **`required_skills`** chunk becomes a **core** requirement
* skills from `preferred_skills`, `responsibilities` and `qualifications` become
  **preferred**
* skills named in the selected job description are added as preferred

A skill is **not** promoted to core merely because the posting mentions it
somewhere — a technology listed under "nice to have" is a nice-to-have.

For a job description you **paste in**, there are no JSON fields to read, so
headings are detected as the text is chunked: bullets under "Required skills:"
or "Must have" become core; bullets under "Nice to have:", "Preferred",
"Responsibilities" or "Qualifications" become preferred.

### The score

| Component | Max | Meaning |
|---|---:|---|
| Core skill coverage | 55 | Share of must-have requirements evidenced |
| Preferred skill coverage | 20 | Share of nice-to-haves evidenced |
| Retrieved JD requirement coverage | 15 | Coverage measured *only* against what RAG retrieved for this query |
| Evidence corroboration | 10 | Share of matched skills appearing in both resume and GitHub |
| **Total** | **100** | |

The first three are scaled by experience level exactly as in the ATS score.
**Corroboration is deliberately not scaled** — it measures how well claims are
backed up, which does not get easier with years of experience.

The headline verdict considers core coverage as well as the total, so a candidate
cannot read as a "Strong Match" by accumulating preferred skills while missing
the must-haves.

### Every row is auditable

```json
{
  "skill": "React",
  "required": true,
  "matched": true,
  "sources": ["resume"],
  "why_required": ["Core skill for this role in the role catalogue",
                   "Named in 2 retrieved job-description chunk(s)"],
  "job_description_evidence": [
    "Deep React experience including hooks and performance profiling"
  ],
  "resume_evidence": ["Listed in the resume's skills section"],
  "retrieval_similarity": 0.536
}
```

When choosing which sentence to show as evidence, the matcher prefers: the
posting **you** pasted over a sample JD, then a "required skills" line over a
"nice to have" line, then higher similarity.

---

## 11. Feature 7 — The summary

**File:** `backend/summary_builder.py`

Three sections of one-line bullets, assembled by fixed rules from the two
reports:

```
ATS Score - 92/100 (Strong)
 • Full marks on Contact Information, Resume Sections, Skills Breadth (+3 more).
 • Weakest: GitHub Profile Evidence at 0/5 - No GitHub username was provided.
 • 8 points are still available across 2 components.

Job Match - 66/100 (Moderate Match)
 • 6 of 9 core requirements evidenced: JavaScript, CSS, React, Tailwind CSS, …
 • Not evidenced: TypeScript, HTML, Responsive Design.
 • Scored at Fresher (0-1 years) level, where 50% coverage earns full marks.
 • No GitHub profile was analysed, so nothing could be corroborated.

Do these next
 1. Build and document one project that genuinely uses TypeScript, HTML,
    Responsive Design, then name those technologies in the project bullet.
 2. Add your GitHub username, and give your best repositories a one-line
    description and topic tags (+5).
```

Actions are ranked by points recoverable, so the first item is always worth
doing first.

### Why rules instead of an LLM

A language model is not deterministic: the same resume could be described
differently on two runs, and nothing it wrote could be traced back to a
component score. Rules give three properties that matter more here:

* **Deterministic** — the same analysis produces the same words, every time.
* **Grounded** — the summary can only state facts that were computed. It cannot
  invent a skill or a number, because it has no way to produce one.
* **Free and offline** — no API key, no account, no per-request cost.

The trade-off is honest: the phrasing is formulaic, and the summary will not
notice a pattern that no rule looks for. For a tool whose entire purpose is
explaining *why* a score is what it is, that is the right trade.

---

## 12. The frontend

React 19 + Vite 7 + Tailwind CSS 4. Three steps:

| Page | Component | What it does |
|---|---|---|
| 1. Sign in | `Welcome.jsx` | Email only, stored in `localStorage` as a session label. No password, no server. |
| 2. Your details | `AnalysisForm.jsx` | Resume upload, GitHub username, role, experience level, job description |
| 3. Analysis | `App.jsx` + result components | Scores and four tabs |

### The results tabs

* **Overview** — the bullet summary, plus a Key Skills panel showing the top
  gaps and the strongest matches (about 8 skills, not the full list)
* **ATS Breakdown** — all ten components with meters, reasons, and expandable
  evidence, plus a "Where the points went" equation
* **Job Match** — the four match components, core and preferred skills
* **Resume & GitHub** — what the parser and the GitHub analyser actually found

### Real streaming progress

`POST /api/analyze/stream` emits Server-Sent Events as each stage genuinely
starts and finishes. `LoadingStages.jsx` renders those events. There is no timer
and no invented percentage anywhere in the frontend — a stage that has not
reported yet is simply "pending".

If streaming fails for a non-HTTP reason, the client falls back to the plain
`POST /api/analyze`.

### Dev proxy

`vite.config.js` proxies `/api/*` to `http://127.0.0.1:8000`, so the frontend
makes same-origin requests and no CORS round-trip is needed in development.

---

## 13. API reference

Interactive docs: <http://localhost:8000/docs>

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Status, version, GitHub token presence, RAG index stats |
| `GET` | `/api/roles` | Supported target roles with their baseline skills |
| `GET` | `/api/experience-levels` | Career stages and the coverage each expects |
| `GET` | `/api/job-descriptions` | The knowledge base (optional `?role_id=`) |
| `GET` | `/api/job-descriptions/{id}` | One full job description |
| `GET` | `/api/rag/status` | Index size, dimensions, embedding backend, settings |
| `GET` | `/api/rag/search?q=` | Raw semantic search — demonstrates retrieval alone |
| `POST` | `/api/rag/reindex` | Rebuild the index after editing the corpus |
| `POST` | `/api/parse-resume` | Resume file → structured data |
| `POST` | `/api/analyze-github` | `{"username": "..."}` → GitHub analysis |
| `POST` | `/api/ats-score` | Resume + role → ATS score and breakdown |
| `POST` | `/api/job-match` | Resume + role → RAG-based match result |
| `POST` | `/api/analyze` | **The complete pipeline**, one response |
| `POST` | `/api/analyze/stream` | The same pipeline as Server-Sent Events |

Analysis endpoints use `multipart/form-data`. Errors return
`{"detail": "...", "error_type": "..."}` with the right status: `400` bad input,
`404` not found, `422` unparseable resume or failed validation, `429` GitHub rate
limit, `503`/`504` network problems.

Quick try:

```bash
curl -X POST http://localhost:8000/api/analyze \
  -F "resume=@backend/tests/fixtures/sample_resume.pdf" \
  -F "role_id=ai_ml_engineer" \
  -F "experience_level=fresher"
```

---

## 14. Folder structure

```
Career-Engine-Project/
├── README.md
├── .gitignore
│
├── backend/
│   ├── main.py                  FastAPI app, endpoints, the pipeline generator
│   ├── config.py                Environment/config loading
│   ├── models.py                Pydantic request/response models
│   ├── skills_data.py           Skill taxonomy + role catalogue (shared vocabulary)
│   ├── experience_levels.py     Career stages and their coverage expectations
│   ├── resume_parser.py         PDF/DOCX → structured resume data
│   ├── github_analyzer.py       GitHub REST API → skill evidence
│   ├── ats_scorer.py            Deterministic ATS scoring
│   ├── job_matcher.py           Explainable job/role matching
│   ├── summary_builder.py       Rule-based bullet summary (no LLM)
│   ├── requirements.txt
│   ├── requirements-dev.txt     Only needed to regenerate test fixtures
│   ├── .env.example
│   │
│   ├── rag/
│   │   ├── chunker.py           Job description → labelled chunks
│   │   ├── embedder.py          Text → normalised vectors (2 backends)
│   │   ├── vector_store.py      FAISS index + persistence
│   │   ├── ingest.py            Load → chunk → embed → index → save
│   │   └── retriever.py         Query → top-k chunks with scores
│   │
│   ├── data/
│   │   ├── job_descriptions/    12 JSON job descriptions (the RAG corpus)
│   │   └── vector_store/        Generated FAISS index (gitignored)
│   │
│   └── tests/
│       ├── test_api.py          End-to-end test suite (161 checks)
│       ├── make_fixtures.py     Generates sample resumes
│       └── fixtures/            Generated resume files (gitignored)
│
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.js           Dev server + /api proxy to :8000
    └── src/
        ├── main.jsx
        ├── App.jsx              Three-step flow, tabs, pipeline orchestration
        ├── index.css            Tailwind import + dark navy design tokens
        ├── services/api.js      All backend calls, including the SSE client
        └── components/
            ├── ui.jsx               Shared primitives (Card, Meter, Pill, …)
            ├── Navbar.jsx
            ├── Welcome.jsx          Step 1 — landing + email
            ├── AnalysisForm.jsx     Step 2 — all analysis inputs
            ├── ResumeUpload.jsx     Drag & drop + validation
            ├── LoadingStages.jsx    Real streamed stage progress
            ├── ScoreCard.jsx        Step 3 — the two headline dials
            ├── SummaryCard.jsx      The three-section bullet summary
            ├── ATSBreakdown.jsx
            ├── JobMatch.jsx
            ├── KeySkills.jsx        Condensed top gaps / strengths
            ├── ResumeInsights.jsx
            └── GitHubInsights.jsx
```

### Where to make common changes

| You want to… | Edit |
|---|---|
| Add a skill or alias | `backend/skills_data.py` → `SKILLS` |
| Add a target role | `backend/skills_data.py` → `ROLES` |
| Add a job description | New JSON in `backend/data/job_descriptions/`, then `POST /api/rag/reindex` |
| Change ATS weights | `backend/ats_scorer.py` → `WEIGHTS` |
| Change match weights | `backend/job_matcher.py` → `MATCH_WEIGHTS` |
| Change experience expectations | `backend/experience_levels.py` |
| Change chunk size or top-k | `backend/.env` (see below) |
| Change colours or spacing | `frontend/src/index.css` → `@theme` |

---

## 15. Configuration

Everything in `backend/.env` is **optional**. Copy `.env.example` to `.env` and
fill in only what you need. There are **no API keys required** — the only
credential the app accepts is a GitHub token, and that is just a rate limit.

| Variable | Default | Purpose |
|---|---|---|
| `GITHUB_TOKEN` | *(empty)* | Raises the GitHub limit from 60 to 5000 requests/hour. **Strongly recommended** — one analysis uses up to 7 requests. |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Local embedding model |
| `FORCE_OFFLINE_EMBEDDINGS` | `0` | Set to `1` to skip the download and use TF-IDF + SVD |
| `RAG_TOP_K` | `8` | Chunks shown as evidence |
| `RAG_DERIVATION_TOP_K` | `24` | Chunks the matcher reads to derive requirements |
| `CHUNK_MAX_WORDS` | `70` | Word window for prose chunks |
| `CHUNK_OVERLAP_WORDS` | `15` | Overlap between prose windows |
| `ALLOWED_ORIGINS` | `http://localhost:5173,…` | CORS origins |

### Getting a GitHub token (free, 2 minutes)

1. **github.com → Settings → Developer settings → Personal access tokens →
   Tokens (classic)**
2. **Generate new token (classic)**, name it, set an expiry
3. **Select no scopes at all** — leave every checkbox unticked. The app only
   reads public data, and an unscoped token still gets the full 5000/hour.
4. Paste into `backend/.env` as `GITHUB_TOKEN=ghp_…` and restart the backend

Verify with `curl -s http://localhost:8000/api/health` →
`"github_token_configured": true`.

> **`.env` is gitignored and must never be committed.** If a token is ever
> exposed, revoke it on GitHub and generate a new one.

---

## 16. Testing

With the backend running:

```bash
cd backend
source .venv/bin/activate
python tests/make_fixtures.py       # first time only; needs requirements-dev.txt
python tests/test_api.py
```

**161 checks**, covering:

* resume parsing in both formats, and every failure mode
* PDF and DOCX of the same resume producing identical skills
* GitHub analysis and its error paths
* RAG ingestion, retrieval relevance, and role filtering
* ATS determinism, discrimination (a weak resume must score far lower), and
  that the total always equals the sum of its components
* experience-level scaling and monotonicity across levels
* job matching and evidence traceability
* the full pipeline, SSE streaming, and validation
* that no backend module imports a model provider — the "no LLM" claim is
  verified structurally, not just asserted

Live GitHub tests skip automatically when the rate limit is exhausted, and the
summary says so.

---

## 17. Limitations

Stated plainly, because knowing them matters more than hiding them.

* **The job-description corpus is sample data.** Twelve documents written for
  this project across six roles. Match scores are relative, not absolute.
* **Skill extraction is alias-based.** It finds the 112 skills the taxonomy
  knows. A technology not in `skills_data.py` is invisible, and a skill
  *mentioned* in passing counts the same as one used in depth.
* **GitHub evidence is shallow.** It reads repository metadata, not code. A
  repository whose description mentions a technology counts as evidence even if
  the author only consumed it — which is why it is labelled with its reason and
  kept separate from resume claims.
* **The ATS score models an ATS; it is not one.** Real systems are proprietary
  and differ between vendors. This is a transparent approximation of the
  documented behaviours they share.
* **Scanned/image PDFs are rejected** — there is no OCR step.
* **Resume parsing is heuristic.** Heavy multi-column layouts, headings rendered
  as images, or tables used for layout will parse less cleanly.
* **The sign-in is not authentication.** No user database, no password, no
  session server. Anyone opening the app can use it.
* **The 161 tests are correctness and integration tests**, not a measured
  retrieval-accuracy benchmark. Do not claim a precision@k figure.
* **Local development only.** No deployment config, and no persistence — closing
  the tab discards the result.

---

## 18. Future scope

Scoped to the two objectives.

**Objective 1 — ATS analysis**

* OCR (e.g. Tesseract) so scanned PDFs parse instead of being rejected
* Multi-column layout and reading-order detection
* Learn skill aliases from the corpus so the taxonomy extends without manual edits
* Weight a skill by how substantively it is used, not just that it appears
* Configurable component weights, with a view of the score's sensitivity to them
* A before/after mode that re-scores an edited resume and attributes the change

**Objective 2 — RAG and job matching**

* Expand the corpus with real postings; import a job description from a URL
* A re-ranking stage (cross-encoder) over the top-k results
* A small labelled query set, so precision@k can be *measured* rather than claimed
* Compare embedding backends on that labelled set as a documented experiment
* Hybrid retrieval (BM25 + dense) — exact technology names match better lexically
* Show which retrieved chunk contributed to each point of the match score

---

## 19. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| **"Backend unavailable"** in the UI | The backend isn't running. Start it with `uvicorn main:app --reload` from `backend/`, then click retry. |
| **"GitHub API rate limit has been reached"** | Anonymous limit (60/hour) exhausted. It resets within the hour by itself; set a `GITHUB_TOKEN` to avoid it entirely. |
| **Backend edits seem to do nothing** | You started uvicorn without `--reload`. Restart with it. |
| **Red underlines on imports in VS Code** | Interpreter not selected. Cmd+Shift+P → *Python: Select Interpreter* → `./backend/.venv/bin/python`. |
| **"address already in use"** | A server is already running on that port. `pkill -f "uvicorn main:app"` or close the other terminal. |
| **First run is slow / seems stuck** | The embedding model is downloading (~90 MB), once. Watch the backend terminal. |
| **Retrieval looks wrong after editing a JD** | Rebuild the index: `curl -X POST http://localhost:8000/api/rag/reindex`, or restart the backend. |
| **"Almost no text could be extracted"** | The PDF is a scanned image with no text layer. Upload a text-based PDF or a DOCX. |

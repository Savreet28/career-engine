"""
skills_data.py
==============

The single source of truth for *what a skill is* in Career Engine.

Everything downstream -- resume extraction, GitHub evidence, ATS keyword
scoring, RAG requirement derivation and job matching -- resolves raw text to
the SAME canonical skill names defined here. That is what lets us say
"Python found in resume" and "Python found in GitHub" and "Python required by
the JD" and know we are talking about one identical thing.

Design notes (useful for the viva):

*  A skill has ONE canonical name ("JavaScript") and many aliases ("js",
   "java script"). Matching is alias-based, not fuzzy/ML, so it is
   deterministic and reproducible.
*  Matching uses word-boundary regular expressions, so "Java" does not match
   inside "JavaScript" and "Go" does not match inside "Google".
*  A few aliases are genuinely ambiguous English words ("Go", "R", "C").
   Those are matched CASE-SENSITIVELY against the original text, so the
   sentence "go to the dashboard" does not award the Go language.
"""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Set

# ---------------------------------------------------------------------------
# Skill categories -- used only for grouping/labelling in the UI.
# ---------------------------------------------------------------------------
CATEGORY_LANGUAGE = "language"
CATEGORY_FRONTEND = "frontend"
CATEGORY_BACKEND = "backend"
CATEGORY_DATA = "data"
CATEGORY_ML = "ml"
CATEGORY_DEVOPS = "devops"
CATEGORY_TOOL = "tool"
CATEGORY_CONCEPT = "concept"


# ---------------------------------------------------------------------------
# The skill taxonomy.
#
#   canonical name -> {"aliases": [...], "category": ...}
#
# The canonical name is ALWAYS included as an implicit alias, so it does not
# need to be repeated in the alias list.
# ---------------------------------------------------------------------------
SKILLS: Dict[str, Dict[str, object]] = {
    # ----- Programming languages -------------------------------------------
    "Python": {"aliases": ["python3", "py3"], "category": CATEGORY_LANGUAGE},
    "Java": {"aliases": ["java8", "java 8", "core java"], "category": CATEGORY_LANGUAGE},
    "JavaScript": {"aliases": ["js", "java script", "ecmascript", "es6"], "category": CATEGORY_LANGUAGE},
    "TypeScript": {"aliases": ["ts"], "category": CATEGORY_LANGUAGE},
    "C++": {"aliases": ["cpp", "c plus plus"], "category": CATEGORY_LANGUAGE},
    "C": {"aliases": [], "category": CATEGORY_LANGUAGE},
    "C#": {"aliases": ["csharp", "c sharp", "dotnet", ".net"], "category": CATEGORY_LANGUAGE},
    "Go": {"aliases": ["golang"], "category": CATEGORY_LANGUAGE},
    "Rust": {"aliases": [], "category": CATEGORY_LANGUAGE},
    "Ruby": {"aliases": [], "category": CATEGORY_LANGUAGE},
    "PHP": {"aliases": [], "category": CATEGORY_LANGUAGE},
    "Swift": {"aliases": [], "category": CATEGORY_LANGUAGE},
    "Kotlin": {"aliases": [], "category": CATEGORY_LANGUAGE},
    "R": {"aliases": [], "category": CATEGORY_LANGUAGE},
    "Scala": {"aliases": [], "category": CATEGORY_LANGUAGE},
    "MATLAB": {"aliases": [], "category": CATEGORY_LANGUAGE},
    "Shell Scripting": {"aliases": ["bash", "shell", "zsh", "shell script"], "category": CATEGORY_LANGUAGE},

    # ----- Frontend ---------------------------------------------------------
    "HTML": {"aliases": ["html5"], "category": CATEGORY_FRONTEND},
    "CSS": {"aliases": ["css3"], "category": CATEGORY_FRONTEND},
    "React": {"aliases": ["react.js", "reactjs", "react js"], "category": CATEGORY_FRONTEND},
    "Next.js": {"aliases": ["nextjs", "next js"], "category": CATEGORY_FRONTEND},
    "Vue.js": {"aliases": ["vue", "vuejs", "vue js"], "category": CATEGORY_FRONTEND},
    "Angular": {"aliases": ["angularjs", "angular js"], "category": CATEGORY_FRONTEND},
    "Svelte": {"aliases": ["sveltekit"], "category": CATEGORY_FRONTEND},
    "Redux": {"aliases": ["redux toolkit"], "category": CATEGORY_FRONTEND},
    "Tailwind CSS": {"aliases": ["tailwind", "tailwindcss"], "category": CATEGORY_FRONTEND},
    "Bootstrap": {"aliases": [], "category": CATEGORY_FRONTEND},
    "Responsive Design": {"aliases": ["responsive web design", "mobile first"], "category": CATEGORY_FRONTEND},
    "Web Accessibility": {"aliases": ["accessibility", "a11y", "wcag"], "category": CATEGORY_FRONTEND},
    "Vite": {"aliases": [], "category": CATEGORY_FRONTEND},
    "Webpack": {"aliases": [], "category": CATEGORY_FRONTEND},
    "React Native": {"aliases": ["react-native"], "category": CATEGORY_FRONTEND},

    # ----- Backend ----------------------------------------------------------
    "Node.js": {"aliases": ["nodejs", "node js", "node"], "category": CATEGORY_BACKEND},
    "Express.js": {"aliases": ["express", "expressjs"], "category": CATEGORY_BACKEND},
    "FastAPI": {"aliases": ["fast api"], "category": CATEGORY_BACKEND},
    "Django": {"aliases": ["django rest framework", "drf"], "category": CATEGORY_BACKEND},
    "Flask": {"aliases": [], "category": CATEGORY_BACKEND},
    "Spring Boot": {"aliases": ["spring", "springboot"], "category": CATEGORY_BACKEND},
    "REST APIs": {"aliases": ["rest", "restful", "rest api", "restful api", "restful apis"], "category": CATEGORY_BACKEND},
    "GraphQL": {"aliases": [], "category": CATEGORY_BACKEND},
    "gRPC": {"aliases": [], "category": CATEGORY_BACKEND},
    "Microservices": {"aliases": ["micro services", "microservice"], "category": CATEGORY_BACKEND},
    "Authentication": {"aliases": ["jwt", "oauth", "oauth2", "auth", "authorization"], "category": CATEGORY_BACKEND},
    "WebSockets": {"aliases": ["websocket", "socket.io", "socketio"], "category": CATEGORY_BACKEND},
    "Celery": {"aliases": [], "category": CATEGORY_BACKEND},
    "Message Queues": {"aliases": ["rabbitmq", "message queue", "pub/sub", "pubsub"], "category": CATEGORY_BACKEND},
    "Kafka": {"aliases": ["apache kafka"], "category": CATEGORY_BACKEND},

    # ----- Databases / data -------------------------------------------------
    "SQL": {"aliases": ["structured query language"], "category": CATEGORY_DATA},
    "PostgreSQL": {"aliases": ["postgres", "psql"], "category": CATEGORY_DATA},
    "MySQL": {"aliases": ["mariadb"], "category": CATEGORY_DATA},
    "SQLite": {"aliases": [], "category": CATEGORY_DATA},
    "MongoDB": {"aliases": ["mongo", "mongoose"], "category": CATEGORY_DATA},
    "Redis": {"aliases": [], "category": CATEGORY_DATA},
    "Elasticsearch": {"aliases": ["elastic search", "opensearch"], "category": CATEGORY_DATA},
    "Database Design": {"aliases": ["schema design", "data modeling", "data modelling", "normalization", "er diagram"], "category": CATEGORY_DATA},
    "Pandas": {"aliases": [], "category": CATEGORY_DATA},
    "NumPy": {"aliases": ["numpy"], "category": CATEGORY_DATA},
    "Data Analysis": {"aliases": ["data analytics", "exploratory data analysis", "eda"], "category": CATEGORY_DATA},
    "Data Visualization": {"aliases": ["matplotlib", "seaborn", "plotly", "data viz", "dashboards"], "category": CATEGORY_DATA},
    "Statistics": {"aliases": ["statistical analysis", "statistical modeling", "probability",
                               "hypothesis testing", "significance testing"], "category": CATEGORY_DATA},
    "ETL": {"aliases": ["data pipeline", "data pipelines", "etl pipeline"], "category": CATEGORY_DATA},
    "Apache Spark": {"aliases": ["spark", "pyspark"], "category": CATEGORY_DATA},
    "Airflow": {"aliases": ["apache airflow"], "category": CATEGORY_DATA},
    "Excel": {"aliases": ["ms excel", "spreadsheets"], "category": CATEGORY_DATA},
    "Tableau": {"aliases": [], "category": CATEGORY_DATA},
    "Power BI": {"aliases": ["powerbi"], "category": CATEGORY_DATA},
    "Data Warehousing": {"aliases": ["snowflake", "bigquery", "redshift", "data warehouse"], "category": CATEGORY_DATA},

    # ----- Machine learning / AI -------------------------------------------
    "Machine Learning": {"aliases": ["ml", "supervised learning", "unsupervised learning"], "category": CATEGORY_ML},
    "Deep Learning": {"aliases": ["neural networks", "neural network", "cnn", "rnn", "lstm"], "category": CATEGORY_ML},
    "PyTorch": {"aliases": ["torch"], "category": CATEGORY_ML},
    "TensorFlow": {"aliases": ["tensor flow", "keras"], "category": CATEGORY_ML},
    "Scikit-learn": {"aliases": ["sklearn", "scikit learn"], "category": CATEGORY_ML},
    "NLP": {"aliases": ["natural language processing", "text mining"], "category": CATEGORY_ML},
    "Computer Vision": {"aliases": ["opencv", "image processing", "object detection"], "category": CATEGORY_ML},
    "LLMs": {"aliases": ["large language model", "large language models", "llm", "gpt", "transformer", "transformers"], "category": CATEGORY_ML},
    "RAG": {"aliases": ["retrieval augmented generation", "retrieval-augmented generation"], "category": CATEGORY_ML},
    "Vector Databases": {"aliases": ["faiss", "chroma", "chromadb", "pinecone", "vector store", "vector search", "weaviate", "qdrant"], "category": CATEGORY_ML},
    "Embeddings": {"aliases": ["word embeddings", "sentence embeddings", "word2vec", "sentence transformers"], "category": CATEGORY_ML},
    "Prompt Engineering": {"aliases": ["prompting", "prompt design"], "category": CATEGORY_ML},
    "LangChain": {"aliases": ["langchain", "llamaindex", "llama index"], "category": CATEGORY_ML},
    "Hugging Face": {"aliases": ["huggingface", "hugging face transformers"], "category": CATEGORY_ML},
    "MLOps": {"aliases": ["ml ops", "mlflow", "model deployment", "model serving"], "category": CATEGORY_ML},
    "Feature Engineering": {"aliases": ["feature selection", "feature extraction"], "category": CATEGORY_ML},
    "Model Evaluation": {"aliases": ["cross validation", "cross-validation", "hyperparameter tuning", "model validation"], "category": CATEGORY_ML},
    "Recommendation Systems": {"aliases": ["recommender system", "recommender systems", "recommendation engine"], "category": CATEGORY_ML},
    "Time Series": {"aliases": ["time series analysis", "forecasting"], "category": CATEGORY_ML},
    "A/B Testing": {"aliases": ["ab testing", "a b testing", "split testing", "experimentation"], "category": CATEGORY_ML},

    # ----- DevOps / cloud ---------------------------------------------------
    "Git": {"aliases": ["github", "gitlab", "version control"], "category": CATEGORY_DEVOPS},
    "Docker": {"aliases": ["containerization", "containers"], "category": CATEGORY_DEVOPS},
    "Kubernetes": {"aliases": ["k8s"], "category": CATEGORY_DEVOPS},
    "CI/CD": {"aliases": ["continuous integration", "continuous deployment", "github actions", "jenkins", "ci cd"], "category": CATEGORY_DEVOPS},
    "AWS": {"aliases": ["amazon web services", "ec2", "s3", "lambda"], "category": CATEGORY_DEVOPS},
    "Azure": {"aliases": ["microsoft azure"], "category": CATEGORY_DEVOPS},
    "Google Cloud": {"aliases": ["gcp", "google cloud platform"], "category": CATEGORY_DEVOPS},
    "Linux": {"aliases": ["unix", "ubuntu"], "category": CATEGORY_DEVOPS},
    "Nginx": {"aliases": [], "category": CATEGORY_DEVOPS},
    "Terraform": {"aliases": ["infrastructure as code", "iac"], "category": CATEGORY_DEVOPS},
    "Monitoring": {"aliases": ["prometheus", "grafana", "observability", "logging"], "category": CATEGORY_DEVOPS},

    # ----- Tools / practices ------------------------------------------------
    # NOTE: the canonical name is "Software Testing", not "Testing". A bare
    # "testing" also appears inside phrases such as "hypothesis testing" and
    # "penetration testing", which have nothing to do with test automation.
    "Software Testing": {"aliases": ["unit testing", "unit tests", "pytest", "jest", "junit",
                                     "integration testing", "test automation", "automated testing",
                                     "tdd", "test driven development"], "category": CATEGORY_TOOL},
    "Agile": {"aliases": ["scrum", "kanban", "sprint"], "category": CATEGORY_TOOL},
    "Jira": {"aliases": [], "category": CATEGORY_TOOL},
    "Postman": {"aliases": [], "category": CATEGORY_TOOL},
    "Figma": {"aliases": [], "category": CATEGORY_TOOL},
    "Code Review": {"aliases": ["peer review", "pull request", "pull requests"], "category": CATEGORY_TOOL},

    # ----- CS fundamentals / concepts --------------------------------------
    "Data Structures": {"aliases": ["data structure", "dsa"], "category": CATEGORY_CONCEPT},
    "Algorithms": {"aliases": ["algorithm", "algorithmic", "problem solving", "competitive programming"], "category": CATEGORY_CONCEPT},
    "Object-Oriented Programming": {"aliases": ["oop", "object oriented programming", "object oriented design"], "category": CATEGORY_CONCEPT},
    "Operating Systems": {"aliases": ["operating system", "os concepts"], "category": CATEGORY_CONCEPT},
    "Computer Networks": {"aliases": ["networking", "computer networking", "tcp/ip"], "category": CATEGORY_CONCEPT},
    "System Design": {"aliases": ["software architecture", "scalability", "distributed systems"], "category": CATEGORY_CONCEPT},
    "Web Security": {"aliases": ["security", "cybersecurity", "owasp", "encryption"], "category": CATEGORY_CONCEPT},
    "Cloud Computing": {"aliases": ["cloud"], "category": CATEGORY_CONCEPT},
}


# Aliases that collide with ordinary English words. These are matched against
# the ORIGINAL text case-sensitively so that "Go" (the language) is accepted
# but "go" (the verb) is not.
CASE_SENSITIVE_ALIASES: Set[str] = {"Go", "R", "C"}


# ---------------------------------------------------------------------------
# Role catalogue.
#
# NOTE: these core/preferred lists are a *baseline*. The job matcher combines
# them with requirements derived from the RAG-retrieved job-description
# chunks, so the real requirement set is data-driven, not hard-coded.
# ---------------------------------------------------------------------------
ROLES: List[Dict[str, object]] = [
    {
        "id": "ai_ml_engineer",
        "title": "AI/ML Engineer",
        "description": "Builds and ships machine-learning and LLM-powered systems.",
        "core_skills": [
            "Python", "Machine Learning", "Deep Learning", "PyTorch",
            "Scikit-learn", "NLP", "SQL", "Statistics",
        ],
        "preferred_skills": [
            "TensorFlow", "LLMs", "RAG", "Vector Databases", "Embeddings",
            "Hugging Face", "MLOps", "Docker", "AWS", "FastAPI",
            "Feature Engineering", "Model Evaluation",
        ],
    },
    {
        "id": "software_engineer",
        "title": "Software Engineer",
        "description": "General-purpose software development across the stack.",
        "core_skills": [
            "Data Structures", "Algorithms", "Object-Oriented Programming",
            "Git", "SQL", "REST APIs", "Software Testing",
        ],
        "preferred_skills": [
            "Python", "Java", "JavaScript", "System Design", "Docker",
            "CI/CD", "Linux", "Agile", "Code Review", "Cloud Computing",
        ],
    },
    {
        "id": "backend_developer",
        "title": "Backend Developer",
        "description": "Designs and operates server-side services, APIs and databases.",
        "core_skills": [
            "Python", "REST APIs", "SQL", "Database Design", "Git", "Software Testing",
        ],
        "preferred_skills": [
            "FastAPI", "Django", "Node.js", "PostgreSQL", "MongoDB", "Redis",
            "Docker", "Microservices", "Authentication", "CI/CD", "AWS",
            "System Design", "Message Queues",
        ],
    },
    {
        "id": "frontend_developer",
        "title": "Frontend Developer",
        "description": "Builds accessible, responsive user interfaces for the web.",
        "core_skills": [
            "HTML", "CSS", "JavaScript", "React", "Git", "Responsive Design",
        ],
        "preferred_skills": [
            "TypeScript", "Next.js", "Tailwind CSS", "Redux", "Software Testing",
            "Web Accessibility", "Vite", "REST APIs", "Figma", "Webpack",
        ],
    },
    {
        "id": "full_stack_developer",
        "title": "Full Stack Developer",
        "description": "Owns features end to end, from database to user interface.",
        "core_skills": [
            "JavaScript", "React", "Node.js", "SQL", "REST APIs", "Git", "HTML", "CSS",
        ],
        "preferred_skills": [
            "TypeScript", "Express.js", "MongoDB", "PostgreSQL", "Docker",
            "Authentication", "CI/CD", "Software Testing", "Tailwind CSS", "System Design",
        ],
    },
    {
        "id": "data_scientist",
        "title": "Data Scientist",
        "description": "Turns data into models, experiments and business decisions.",
        "core_skills": [
            "Python", "SQL", "Statistics", "Machine Learning",
            "Pandas", "Data Analysis", "Data Visualization",
        ],
        "preferred_skills": [
            "NumPy", "Scikit-learn", "A/B Testing", "Deep Learning",
            "Feature Engineering", "Model Evaluation", "Time Series",
            "Apache Spark", "Tableau", "Data Warehousing", "R",
        ],
    },
]

ROLES_BY_ID: Dict[str, Dict[str, object]] = {r["id"]: r for r in ROLES}


# ---------------------------------------------------------------------------
# Alias -> canonical lookup, compiled once at import time.
# ---------------------------------------------------------------------------

def _boundary_pattern(alias: str) -> re.Pattern:
    """
    Build a word-boundary regex for one alias.

    Plain ``\\b`` does not work for skills such as "C++" or "C#" because ``+``
    and ``#`` are not word characters. We therefore use explicit lookarounds
    over the set of characters that can legitimately appear inside a technology
    name, which prevents "Java" matching inside "JavaScript", "C" matching
    inside "C++", and "R" matching inside "R&D".
    """
    return re.compile(
        r"(?<![A-Za-z0-9+#.&])" + re.escape(alias) + r"(?![A-Za-z0-9+#&])",
        re.UNICODE,
    )


def _build_matchers():
    insensitive = []   # (canonical, compiled pattern) matched on lowercased text
    sensitive = []     # (canonical, compiled pattern) matched on original text
    for canonical, meta in SKILLS.items():
        aliases = [canonical] + list(meta.get("aliases", []))  # type: ignore[arg-type]
        for alias in aliases:
            if alias in CASE_SENSITIVE_ALIASES:
                sensitive.append((canonical, _boundary_pattern(alias)))
            else:
                insensitive.append((canonical, _boundary_pattern(alias.lower())))
    return insensitive, sensitive


_INSENSITIVE_MATCHERS, _SENSITIVE_MATCHERS = _build_matchers()

# Ordered canonical list -- used to keep output stable/reproducible.
ALL_SKILLS: List[str] = list(SKILLS.keys())
_SKILL_ORDER: Dict[str, int] = {s: i for i, s in enumerate(ALL_SKILLS)}


def skill_category(skill: str) -> str:
    """Return the category of a canonical skill, or 'other' if unknown."""
    meta = SKILLS.get(skill)
    return str(meta["category"]) if meta else "other"


def sort_skills(skills: Iterable[str]) -> List[str]:
    """Deterministic ordering: taxonomy order first, then anything unknown."""
    return sorted(set(skills), key=lambda s: (_SKILL_ORDER.get(s, 10_000), s))


def extract_skills(text: str) -> List[str]:
    """
    Find every canonical skill mentioned in ``text``.

    Purely rule-based: alias table + word-boundary regex. The same function is
    used for resume text, GitHub metadata and job-description chunks, which is
    what makes the three evidence sources directly comparable.
    """
    if not text:
        return []

    lowered = text.lower()
    found: Set[str] = set()

    for canonical, pattern in _INSENSITIVE_MATCHERS:
        if canonical in found:
            continue
        if pattern.search(lowered):
            found.add(canonical)

    for canonical, pattern in _SENSITIVE_MATCHERS:
        if canonical in found:
            continue
        if pattern.search(text):
            found.add(canonical)

    return sort_skills(found)


_LEADING_BULLET_RE = re.compile(
    r"^\s*(?:[-*\u2022\u25aa\u25cf\u2043\u2219\u00b7\u25e6\u2023>]|\d+[.)])\s+"
)


def find_skill_mentions(text: str, skills: Iterable[str], max_per_skill: int = 2) -> Dict[str, List[str]]:
    """
    For each skill, return short snippets of ``text`` where it appears.

    Used to attach *evidence* to a match rather than just a boolean, e.g. the
    exact job-description sentence that requires a skill.
    """
    if not text:
        return {}

    sentences = [s.strip() for s in re.split(r"(?<=[.!?;])\s+|\n+", text) if s.strip()]
    wanted = set(skills)
    out: Dict[str, List[str]] = {}

    for sentence in sentences:
        for skill in extract_skills(sentence):
            if skill not in wanted:
                continue
            bucket = out.setdefault(skill, [])
            if len(bucket) < max_per_skill:
                # Evidence is quoted back to the user, so drop the list marker
                # the sentence was carrying.
                snippet = _LEADING_BULLET_RE.sub("", sentence)
                snippet = re.sub(r"\s+", " ", snippet).strip()
                if len(snippet) > 240:
                    snippet = snippet[:237].rstrip() + "..."
                bucket.append(snippet)
    return out

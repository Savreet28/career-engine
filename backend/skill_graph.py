"""
skill_graph.py
==============

Objective 3: what you need to learn *before* you can learn something else.

The matcher tells a student which skills they are missing. That is a set, not
a plan -- and a set is not actionable, because "learn PyTorch" is useless
advice to someone who does not yet know Python. This module adds the one piece
of information needed to turn a set into an order: a prerequisite graph.

Two things live here:

* ``PREREQUISITES``  -- skill -> the skills that should come first.
* ``OFFICIAL_DOCS``  -- skill -> the official documentation site, where one
  exists and is stable. Deliberately limited to first-party sites, and to the
  domain rather than a deep path, so the links do not rot.

What is deliberately NOT here
-----------------------------
**Time estimates.** "Learn Docker in 3 weeks" would be invented precision --
it depends entirely on the learner, and no data in this project supports a
number. Instead, each skill gets a *depth* computed from the graph itself
(how many prerequisites deep it sits), which is a real, derived property.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Dict, List, Set

from skills_data import SKILLS

# ---------------------------------------------------------------------------
# The prerequisite graph.
#
#   skill -> skills that should be learned first
#
# Only genuine dependencies are listed: you cannot meaningfully use React
# without JavaScript, or PyTorch without Python. Skills absent from this map
# have no prerequisites and are entry points.
# ---------------------------------------------------------------------------
PREREQUISITES: Dict[str, List[str]] = {
    # --- frontend ---------------------------------------------------------
    "CSS": ["HTML"],
    "Responsive Design": ["CSS"],
    "Web Accessibility": ["HTML"],
    "Tailwind CSS": ["CSS"],
    "Bootstrap": ["CSS"],
    "TypeScript": ["JavaScript"],
    "React": ["JavaScript", "HTML", "CSS"],
    "Vue.js": ["JavaScript"],
    "Angular": ["TypeScript"],
    "Svelte": ["JavaScript"],
    "Next.js": ["React"],
    "Redux": ["React"],
    "React Native": ["React"],
    "Vite": ["JavaScript"],
    "Webpack": ["JavaScript"],

    # --- backend ----------------------------------------------------------
    "Node.js": ["JavaScript"],
    "Express.js": ["Node.js"],
    "FastAPI": ["Python", "REST APIs"],
    "Django": ["Python", "REST APIs"],
    "Flask": ["Python"],
    "Spring Boot": ["Java"],
    "GraphQL": ["REST APIs"],
    "gRPC": ["REST APIs"],
    "Authentication": ["REST APIs"],
    "WebSockets": ["REST APIs"],
    "Celery": ["Python"],
    "Kafka": ["Message Queues"],
    "Microservices": ["REST APIs", "Docker"],

    # --- data -------------------------------------------------------------
    "PostgreSQL": ["SQL"],
    "MySQL": ["SQL"],
    "SQLite": ["SQL"],
    "Database Design": ["SQL"],
    "Data Warehousing": ["SQL"],
    "ETL": ["SQL"],
    "Pandas": ["Python"],
    "NumPy": ["Python"],
    "Data Analysis": ["Python", "Statistics"],
    "Data Visualization": ["Data Analysis"],
    "Apache Spark": ["Python"],
    "Airflow": ["Python"],
    "Tableau": ["Data Analysis"],
    "Power BI": ["Data Analysis"],

    # --- machine learning -------------------------------------------------
    "Machine Learning": ["Python", "Statistics"],
    "Scikit-learn": ["Machine Learning", "NumPy"],
    "Feature Engineering": ["Machine Learning"],
    "Model Evaluation": ["Machine Learning"],
    "Deep Learning": ["Machine Learning"],
    "PyTorch": ["Deep Learning"],
    "TensorFlow": ["Deep Learning"],
    "NLP": ["Machine Learning"],
    "Computer Vision": ["Deep Learning"],
    "Embeddings": ["NLP"],
    "LLMs": ["Deep Learning", "NLP"],
    "Prompt Engineering": ["LLMs"],
    "RAG": ["LLMs", "Embeddings"],
    "Vector Databases": ["Embeddings"],
    "LangChain": ["LLMs"],
    "Hugging Face": ["Deep Learning"],
    "MLOps": ["Machine Learning", "Docker"],
    "Recommendation Systems": ["Machine Learning"],
    "Time Series": ["Statistics"],
    "A/B Testing": ["Statistics"],

    # --- devops / fundamentals -------------------------------------------
    "Algorithms": ["Data Structures"],
    "System Design": ["Data Structures", "Algorithms", "Database Design"],
    "Kubernetes": ["Docker"],
    "CI/CD": ["Git"],
    "Terraform": ["Cloud Computing"],
    "AWS": ["Cloud Computing"],
    "Azure": ["Cloud Computing"],
    "Google Cloud": ["Cloud Computing"],
    "Monitoring": ["Linux"],
    "Nginx": ["Linux"],
    "Web Security": ["Computer Networks"],
    "Code Review": ["Git"],
}

# ---------------------------------------------------------------------------
# Official documentation. First-party sites only, domain level, so they stay
# valid. A skill with no confident official home is simply absent -- the
# roadmap then names the skill without pretending to have a link.
# ---------------------------------------------------------------------------
OFFICIAL_DOCS: Dict[str, str] = {
    "Python": "https://docs.python.org/3/tutorial/",
    "JavaScript": "https://developer.mozilla.org/en-US/docs/Web/JavaScript",
    "TypeScript": "https://www.typescriptlang.org/docs/",
    "HTML": "https://developer.mozilla.org/en-US/docs/Web/HTML",
    "CSS": "https://developer.mozilla.org/en-US/docs/Web/CSS",
    "React": "https://react.dev/learn",
    "Next.js": "https://nextjs.org/docs",
    "Vue.js": "https://vuejs.org/guide/introduction.html",
    "Tailwind CSS": "https://tailwindcss.com/docs",
    "Vite": "https://vite.dev/guide/",
    "Node.js": "https://nodejs.org/docs/latest/api/",
    "Express.js": "https://expressjs.com/",
    "FastAPI": "https://fastapi.tiangolo.com/",
    "Django": "https://docs.djangoproject.com/",
    "Flask": "https://flask.palletsprojects.com/",
    "PostgreSQL": "https://www.postgresql.org/docs/",
    "MongoDB": "https://www.mongodb.com/docs/",
    "Redis": "https://redis.io/docs/latest/",
    "Pandas": "https://pandas.pydata.org/docs/",
    "NumPy": "https://numpy.org/doc/stable/",
    "Scikit-learn": "https://scikit-learn.org/stable/user_guide.html",
    "PyTorch": "https://pytorch.org/tutorials/",
    "TensorFlow": "https://www.tensorflow.org/tutorials",
    "Hugging Face": "https://huggingface.co/docs",
    "Docker": "https://docs.docker.com/get-started/",
    "Kubernetes": "https://kubernetes.io/docs/home/",
    "Git": "https://git-scm.com/doc",
    "Linux": "https://www.kernel.org/doc/html/latest/",
    "Web Accessibility": "https://www.w3.org/WAI/WCAG22/quickref/",
    "GraphQL": "https://graphql.org/learn/",
    "Terraform": "https://developer.hashicorp.com/terraform/docs",
    "Apache Spark": "https://spark.apache.org/docs/latest/",
    "Airflow": "https://airflow.apache.org/docs/",
}


def prerequisites_of(skill: str) -> List[str]:
    """Direct prerequisites of a skill, in the order they should be learned."""
    return list(PREREQUISITES.get(skill, []))


@lru_cache(maxsize=None)
def depth_of(skill: str) -> int:
    """
    How many prerequisites deep a skill sits.

    0 means it is an entry point. This is a *derived* property of the graph,
    not an invented difficulty rating, and it is what orders the roadmap.
    """
    return _depth(skill, frozenset())


def _depth(skill: str, seen: frozenset) -> int:
    parents = PREREQUISITES.get(skill)
    if not parents or skill in seen:
        return 0
    return 1 + max(_depth(p, seen | {skill}) for p in parents)


def all_prerequisites_of(skill: str) -> List[str]:
    """Every skill that must come before this one, nearest first."""
    out: List[str] = []
    stack: List[str] = list(PREREQUISITES.get(skill, []))
    seen: Set[str] = {skill}
    while stack:
        current = stack.pop(0)
        if current in seen:
            continue
        seen.add(current)
        out.append(current)
        stack.extend(PREREQUISITES.get(current, []))
    return out


def validate_graph() -> Dict[str, List[str]]:
    """
    Sanity checks, run by the test suite.

    Returns a dict of problem -> offending skills. An empty dict means the
    graph is well formed.
    """
    problems: Dict[str, List[str]] = {}

    unknown = sorted({s for s in PREREQUISITES if s not in SKILLS}
                     | {p for ps in PREREQUISITES.values() for p in ps if p not in SKILLS})
    if unknown:
        problems["not in the skill taxonomy"] = unknown

    undocumented = sorted(s for s in OFFICIAL_DOCS if s not in SKILLS)
    if undocumented:
        problems["documented but not a known skill"] = undocumented

    self_refs = sorted(s for s, ps in PREREQUISITES.items() if s in ps)
    if self_refs:
        problems["lists itself as a prerequisite"] = self_refs

    # A cycle would make "learn this first" meaningless.
    cycles: List[str] = []
    for skill in PREREQUISITES:
        if skill in all_prerequisites_of(skill):
            cycles.append(skill)
    if cycles:
        problems["is part of a prerequisite cycle"] = sorted(cycles)

    return problems

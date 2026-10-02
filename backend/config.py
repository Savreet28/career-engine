"""
config.py
=========

Central configuration. Environment variables are read from ``backend/.env``
(see ``.env.example``). Every external service is optional -- the application
is fully functional with no keys configured at all.
"""

from __future__ import annotations

import os
import pathlib

from dotenv import load_dotenv

BASE_DIR = pathlib.Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
JOB_DESCRIPTIONS_DIR = DATA_DIR / "job_descriptions"
VECTOR_STORE_DIR = DATA_DIR / "vector_store"

# ``override=False`` means a variable already exported in the shell wins over
# the .env file, which is the usual expectation during development.
load_dotenv(BASE_DIR / ".env", override=False)


def _clean(value: str | None) -> str | None:
    """Treat empty strings and placeholder values as 'not configured'."""
    if value is None:
        return None
    value = value.strip()
    if not value or value.lower() in {"none", "null", "your_key_here", "changeme"}:
        return None
    return value


# --- Optional integrations --------------------------------------------------
# A GitHub token is the only external credential this application accepts, and
# it is optional: without one, GitHub is read anonymously at a lower rate limit.
GITHUB_TOKEN = _clean(os.getenv("GITHUB_TOKEN"))

# --- RAG --------------------------------------------------------------------
EMBEDDING_MODEL = _clean(os.getenv("EMBEDDING_MODEL")) or "sentence-transformers/all-MiniLM-L6-v2"
# Set to "1" to skip the sentence-transformers download and use the offline
# TF-IDF + SVD embedding backend instead.
FORCE_OFFLINE_EMBEDDINGS = _clean(os.getenv("FORCE_OFFLINE_EMBEDDINGS")) == "1"
# How many chunks are SHOWN to the user as retrieved evidence.
RAG_TOP_K = int(_clean(os.getenv("RAG_TOP_K")) or 8)
# How many chunks the job matcher reads to derive the requirement set. Deeper
# than the display slice: a handful of chunks names too few skills to score
# coverage against reliably.
RAG_DERIVATION_TOP_K = int(_clean(os.getenv("RAG_DERIVATION_TOP_K")) or 24)
CHUNK_MAX_WORDS = int(_clean(os.getenv("CHUNK_MAX_WORDS")) or 70)
CHUNK_OVERLAP_WORDS = int(_clean(os.getenv("CHUNK_OVERLAP_WORDS")) or 15)

# --- HTTP -------------------------------------------------------------------
GITHUB_API = "https://api.github.com"
GITHUB_TIMEOUT = int(_clean(os.getenv("GITHUB_TIMEOUT")) or 12)
GITHUB_MAX_REPOS = int(_clean(os.getenv("GITHUB_MAX_REPOS")) or 100)

# --- CORS -------------------------------------------------------------------
ALLOWED_ORIGINS = [
    o.strip()
    for o in (_clean(os.getenv("ALLOWED_ORIGINS")) or
              "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]


def integration_status() -> dict:
    """Reported by /api/health so the UI can show what is enabled."""
    return {
        "github_token_configured": GITHUB_TOKEN is not None,
        "uses_language_model": False,
    }

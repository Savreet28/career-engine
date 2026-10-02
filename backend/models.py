"""
models.py
=========

Pydantic models for request validation and for documenting responses in the
auto-generated OpenAPI schema at http://localhost:8000/docs.

Analysis responses are returned as plain dictionaries rather than strictly
typed models: the report structure is deeply nested and evolves with the
scoring rules, and forcing it through rigid schemas would add a lot of
declaration for no validation benefit on the way out. Requests, where input
actually needs validating, are typed.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------

class GitHubRequest(BaseModel):
    username: str = Field(..., description="Public GitHub username, or a profile URL.",
                          examples=["tiangolo"])

    @field_validator("username")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("A GitHub username is required.")
        return value.strip()


class RoleQuery(BaseModel):
    role_id: str = Field(..., description="Role identifier from GET /api/roles.",
                         examples=["ai_ml_engineer"])
    job_description: Optional[str] = Field(
        None, description="Optional job description text to match against."
    )


# ---------------------------------------------------------------------------
# Responses (documentation-oriented)
# ---------------------------------------------------------------------------

class RoleOut(BaseModel):
    id: str
    title: str
    description: str
    core_skills: List[str]
    preferred_skills: List[str]
    job_description_count: int


class JobDescriptionSummary(BaseModel):
    id: str
    job_title: str
    company: str
    role_id: str
    location: Optional[str] = None
    experience_required: Optional[str] = None


class ScoreComponent(BaseModel):
    id: str
    component: str
    score: int
    max_score: int
    reason: str
    evidence: List[str]


class HealthOut(BaseModel):
    status: str
    version: str
    github_token_configured: bool
    # Always False: scoring and the written summary are entirely rule-based.
    uses_language_model: bool
    rag_index: dict


class ErrorOut(BaseModel):
    detail: str
    error_type: Optional[str] = None

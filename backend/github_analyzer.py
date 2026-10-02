"""
github_analyzer.py
==================

Reads a candidate's *public* GitHub profile through the GitHub REST API and
turns it into skill evidence.

Why this exists
---------------
A resume states what a candidate claims. GitHub shows what they actually
built. Career Engine keeps the two **separate** on purpose: a skill found only
on GitHub is recorded as ``source: "github"``, never merged into the resume's
declared skills. The job matcher then reports which sources back each skill,
so "Python (resume + github)" is visibly stronger evidence than
"Python (resume only)".

Evidence is derived from three public signals per repository:
  1. the repository language (and the full language byte breakdown for the
     top repositories),
  2. repository topics,
  3. repository name + description text.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import requests

import config
from skills_data import extract_skills, sort_skills

# Repositories whose language breakdown is fetched individually. Each costs one
# extra API call, so we only do it for the most significant repositories.
DEEP_INSPECT_REPOS = 5


class GitHubError(Exception):
    """A GitHub lookup failed. ``status`` mirrors the HTTP status to return."""

    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status


def _headers() -> Dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "career-engine-local",
    }
    if config.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"
    return headers


def _get(path: str, params: Optional[dict] = None) -> requests.Response:
    url = f"{config.GITHUB_API}{path}"
    try:
        return requests.get(url, headers=_headers(), params=params,
                            timeout=config.GITHUB_TIMEOUT)
    except requests.Timeout as exc:
        raise GitHubError(
            "GitHub did not respond in time. Please check your connection and try again.",
            status=504,
        ) from exc
    except requests.RequestException as exc:
        raise GitHubError(
            "Could not reach GitHub. Please check your internet connection.",
            status=503,
        ) from exc


def _raise_for_api_error(response: requests.Response, username: str) -> None:
    if response.status_code == 200:
        return
    if response.status_code == 404:
        raise GitHubError(f"GitHub user '{username}' was not found.", status=404)
    if response.status_code in (403, 429):
        remaining = response.headers.get("X-RateLimit-Remaining")
        if remaining == "0":
            hint = ("The GitHub API rate limit has been reached. Add a GITHUB_TOKEN "
                    "to backend/.env to raise the limit from 60 to 5000 requests/hour.")
        else:
            hint = "GitHub refused the request (403). It may be a temporary block."
        raise GitHubError(hint, status=429)
    if response.status_code == 401:
        raise GitHubError(
            "GitHub rejected the configured GITHUB_TOKEN. Check that it is valid.",
            status=401,
        )
    raise GitHubError(
        f"GitHub returned an unexpected status ({response.status_code}).",
        status=502,
    )


def validate_username(username: str) -> str:
    """Validate against GitHub's own username rules before spending a request."""
    username = (username or "").strip().lstrip("@")
    if username.startswith("http"):
        # Accept a pasted profile URL.
        username = username.rstrip("/").split("/")[-1]
    if not username:
        raise GitHubError("A GitHub username is required.", status=400)
    if len(username) > 39:
        raise GitHubError("That is not a valid GitHub username (too long).", status=400)
    if not all(c.isalnum() or c == "-" for c in username) or username.startswith("-"):
        raise GitHubError(f"'{username}' is not a valid GitHub username.", status=400)
    return username


# ---------------------------------------------------------------------------
# Evidence extraction
# ---------------------------------------------------------------------------

def _evidence_from_repos(repos: List[dict], languages: Dict[str, int]) -> Dict[str, List[str]]:
    """
    Map canonical skills -> human-readable reasons, e.g.

        "Python": ["Primary language of 4 repositories",
                   "Topic on 'resume-analyzer'"]
    """
    evidence: Dict[str, List[str]] = {}

    def add(skill: str, reason: str) -> None:
        bucket = evidence.setdefault(skill, [])
        if reason not in bucket and len(bucket) < 4:
            bucket.append(reason)

    # 1. Languages reported by GitHub across the account.
    language_repo_count: Dict[str, int] = {}
    for repo in repos:
        if repo.get("language"):
            language_repo_count[repo["language"]] = language_repo_count.get(repo["language"], 0) + 1

    for language, count in language_repo_count.items():
        for skill in extract_skills(language):
            add(skill, f"Primary language of {count} repositor{'y' if count == 1 else 'ies'}")

    for language, byte_count in languages.items():
        for skill in extract_skills(language):
            add(skill, f"{byte_count:,} bytes of {language} across top repositories")

    # 2. Topics the author tagged the repository with.
    for repo in repos:
        for topic in repo.get("topics") or []:
            for skill in extract_skills(topic.replace("-", " ")):
                add(skill, f"Topic '{topic}' on repository '{repo['name']}'")

    # 3. Repository names and descriptions.
    for repo in repos:
        text = f"{repo.get('name', '').replace('-', ' ')} {repo.get('description') or ''}"
        for skill in extract_skills(text):
            add(skill, f"Mentioned in repository '{repo['name']}'")

    return evidence


def _summarise_repo(repo: dict) -> dict:
    return {
        "name": repo.get("name"),
        "full_name": repo.get("full_name"),
        "url": repo.get("html_url"),
        "description": repo.get("description"),
        "language": repo.get("language"),
        "topics": repo.get("topics") or [],
        "stars": repo.get("stargazers_count", 0),
        "forks": repo.get("forks_count", 0),
        "is_fork": bool(repo.get("fork")),
        "updated_at": repo.get("pushed_at") or repo.get("updated_at"),
        "size_kb": repo.get("size", 0),
    }


def analyze_github(username: str) -> Dict[str, object]:
    """
    Fetch and analyse a public GitHub profile.

    Raises :class:`GitHubError` (carrying an appropriate HTTP status) for a
    missing user, rate limiting, auth problems or network failure.
    """
    username = validate_username(username)

    profile_response = _get(f"/users/{username}")
    _raise_for_api_error(profile_response, username)
    profile = profile_response.json()

    if profile.get("type") == "Organization":
        raise GitHubError(
            f"'{username}' is a GitHub organisation, not a user account.", status=400
        )

    repos_response = _get(
        f"/users/{username}/repos",
        params={"per_page": min(config.GITHUB_MAX_REPOS, 100), "sort": "pushed", "type": "owner"},
    )
    _raise_for_api_error(repos_response, username)
    raw_repos = repos_response.json()
    if not isinstance(raw_repos, list):
        raw_repos = []

    repos = [_summarise_repo(r) for r in raw_repos]
    original_repos = [r for r in repos if not r["is_fork"]]
    # Forks are excluded from evidence: forking a repository is not proof of
    # having written it.
    evidence_repos = original_repos or []

    # Rank by a simple, explainable signal: stars, then forks, then recency.
    top_repos = sorted(
        evidence_repos,
        key=lambda r: (r["stars"], r["forks"], r["updated_at"] or ""),
        reverse=True,
    )[:10]

    # Byte-level language breakdown for the most significant repositories.
    languages: Dict[str, int] = {}
    language_errors = 0
    for repo in top_repos[:DEEP_INSPECT_REPOS]:
        try:
            response = _get(f"/repos/{username}/{repo['name']}/languages")
            if response.status_code != 200:
                language_errors += 1
                continue
            for language, byte_count in (response.json() or {}).items():
                languages[language] = languages.get(language, 0) + int(byte_count)
        except GitHubError:
            # A per-repository failure must not fail the whole analysis.
            language_errors += 1

    evidence = _evidence_from_repos(evidence_repos, languages)
    skills = sort_skills(evidence.keys())

    topics_counter: Dict[str, int] = {}
    for repo in evidence_repos:
        for topic in repo["topics"]:
            topics_counter[topic] = topics_counter.get(topic, 0) + 1

    total_stars = sum(r["stars"] for r in evidence_repos)

    return {
        "profile": {
            "username": profile.get("login"),
            "name": profile.get("name"),
            "bio": profile.get("bio"),
            "company": profile.get("company"),
            "location": profile.get("location"),
            "blog": profile.get("blog") or None,
            "avatar_url": profile.get("avatar_url"),
            "url": profile.get("html_url"),
            "followers": profile.get("followers", 0),
            "following": profile.get("following", 0),
            "public_repos": profile.get("public_repos", 0),
            "created_at": profile.get("created_at"),
        },
        "stats": {
            "repositories_fetched": len(repos),
            "original_repositories": len(original_repos),
            "forked_repositories": len(repos) - len(original_repos),
            "total_stars": total_stars,
            "total_forks": sum(r["forks"] for r in evidence_repos),
            "repositories_with_description": sum(1 for r in evidence_repos if r["description"]),
            "repositories_with_topics": sum(1 for r in evidence_repos if r["topics"]),
            "distinct_languages": len(
                {r["language"] for r in evidence_repos if r["language"]}
            ),
        },
        "languages": dict(sorted(languages.items(), key=lambda kv: kv[1], reverse=True)),
        "topics": dict(sorted(topics_counter.items(), key=lambda kv: (-kv[1], kv[0]))),
        "top_repositories": top_repos,
        "skills": skills,
        "skill_evidence": {s: evidence[s] for s in skills},
        "notes": _notes(profile, evidence_repos, language_errors),
    }


def _notes(profile: dict, repos: List[dict], language_errors: int) -> List[str]:
    """Honest caveats shown in the UI so the analysis is not over-claimed."""
    notes: List[str] = []
    if not repos:
        notes.append(
            "This account has no original public repositories, so no GitHub "
            "skill evidence could be collected."
        )
    if profile.get("public_repos", 0) > len(repos):
        notes.append("Forked repositories are excluded from skill evidence.")
    if language_errors:
        notes.append(
            f"Language details for {language_errors} repository/ies could not be "
            "fetched; evidence still uses their primary language and topics."
        )
    if not config.GITHUB_TOKEN:
        notes.append(
            "Running without a GITHUB_TOKEN (60 requests/hour). Add one to "
            "backend/.env if you hit the rate limit."
        )
    return notes


def empty_analysis(reason: str) -> Dict[str, object]:
    """
    A neutral, well-formed result used when GitHub analysis is skipped or
    fails. Lets the rest of the pipeline continue with resume evidence only.
    """
    return {
        "profile": None,
        "stats": {},
        "languages": {},
        "topics": {},
        "top_repositories": [],
        "skills": [],
        "skill_evidence": {},
        "notes": [reason],
        "unavailable": True,
        "reason": reason,
    }

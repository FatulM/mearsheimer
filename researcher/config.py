#!/usr/bin/env python3
"""Configuration for the researcher agent.

Loads the shared `.env` and resolves one model per agent role. Each
`LLM_MODEL_AGENT_*` variable falls back to the base `LLM_MODEL` when unset,
following the convention used by the other scripts in this repo. Optional
`RESEARCHER_*` variables tune the run with sensible defaults.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

import requests
from dotenv import load_dotenv

RESEARCHER_DIR = Path(__file__).resolve().parent
ROOT = RESEARCHER_DIR.parent
ENV_PATH = ROOT / ".env"

CONTENT_DIR = ROOT / "content"
PROCESSED_DIR = ROOT / "processed"
PROMPTS_DIR = RESEARCHER_DIR / "prompts"
FILES_DIR = RESEARCHER_DIR / "files"
RESULT_DIR = FILES_DIR / "result"
RUNS_DIR = FILES_DIR / "runs"

PLANNER = "planner"
LEAD = "lead"
RESEARCH = "research"
REVIEWER = "reviewer"

ROLE_ENV = {
    PLANNER: "LLM_MODEL_AGENT_PLANNER",
    LEAD: "LLM_MODEL_AGENT_LEAD",
    RESEARCH: "LLM_MODEL_AGENT_RESEARCH",
    REVIEWER: "LLM_MODEL_AGENT_REVIEWER",
}

DEFAULT_MAX_TOPICS = 8
DEFAULT_MAX_TOOL_CALLS = 25
DEFAULT_MAX_REVIEW_ROUNDS = 3
DEFAULT_REQUEST_TIMEOUT = 120


@dataclass(frozen=True)
class Settings:
    """Resolved runtime settings for a researcher run."""

    base_url: str
    api_key: str
    models: dict[str, str]
    max_topics: int
    max_tool_calls: int
    max_review_rounds: int
    request_timeout: int

    def model(self, role: str) -> str:
        """Return the model configured for an agent role."""
        return self.models[role]


def _int_env(name: str, default: int) -> int:
    """Read an integer env var, falling back to a default when unset/invalid."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        sys.exit(f"[error] {name} must be an integer, got {raw!r}")
    if value < 1:
        sys.exit(f"[error] {name} must be >= 1, got {value}")
    return value


def load_settings(
    *,
    max_topics: int | None = None,
    max_tool_calls: int | None = None,
    max_review_rounds: int | None = None,
    request_timeout: int | None = None,
) -> Settings:
    """Load `.env` and resolve settings, applying CLI overrides when given."""
    load_dotenv(ENV_PATH)

    base_url = os.environ.get("LLM_BASE_URL", "").rstrip("/")
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    fallback = os.environ.get("LLM_MODEL", "").strip()

    problems: list[str] = []
    if not base_url:
        problems.append("LLM_BASE_URL")
    if not api_key:
        problems.append("LLM_API_KEY")

    models: dict[str, str] = {}
    for role, env_key in ROLE_ENV.items():
        model = os.environ.get(env_key, "").strip() or fallback
        if not model:
            problems.append(f"{env_key} (or LLM_MODEL)")
        models[role] = model

    if problems:
        sys.exit(
            "[error] missing environment variables: "
            + ", ".join(problems)
            + " (check .env)"
        )

    return Settings(
        base_url=base_url,
        api_key=api_key,
        models=models,
        max_topics=max_topics
        if max_topics is not None
        else _int_env("RESEARCHER_MAX_TOPICS", DEFAULT_MAX_TOPICS),
        max_tool_calls=max_tool_calls
        if max_tool_calls is not None
        else _int_env("RESEARCHER_MAX_TOOL_CALLS", DEFAULT_MAX_TOOL_CALLS),
        max_review_rounds=max_review_rounds
        if max_review_rounds is not None
        else _int_env("RESEARCHER_MAX_REVIEW_ROUNDS", DEFAULT_MAX_REVIEW_ROUNDS),
        request_timeout=request_timeout
        if request_timeout is not None
        else _int_env("RESEARCHER_REQUEST_TIMEOUT", DEFAULT_REQUEST_TIMEOUT),
    )


def check_endpoint(settings: Settings) -> None:
    """Warn (do not fail) when the endpoint's `/models` probe is unreachable."""
    try:
        response = requests.get(
            f"{settings.base_url}/models",
            headers={"Authorization": f"Bearer {settings.api_key}"},
            timeout=settings.request_timeout,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(
            f"[warn] preflight check against {settings.base_url}/models failed: {exc}"
        )

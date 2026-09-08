#!/usr/bin/env python3
"""
Check that a Persian blog post summarises and translates its source transcript correctly.

Reads the minified English transcript from processed/episode-N.md and the Persian
summary from content/episode-N.md (N>=1), sends both to the configured LLM (using
LLM_MODEL, not LLM_MODEL_CRITIQUE) with prompts/check-translation.md as the system
prompt, and writes the resulting Persian fidelity report to reports/episode-N.md.

No web search is used for this check; the model judges only from the two inputs.

The endpoint is configured via .env:
    LLM_BASE_URL=https://api.avalai.org/v1
    LLM_API_KEY=<key>
    LLM_MODEL=<model>

Usage:
    python3 scripts/check_translation.py 1        # check episode 1
"""

import argparse
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
PROCESSED_DIR = ROOT / "processed"
CONTENT_DIR = ROOT / "content"
PROMPTS_DIR = ROOT / "prompts"
REPORTS_DIR = ROOT / "reports"

ENV_KEYS = ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL")
SEPARATOR = "\n\n--\n\n"


def load_config() -> tuple[str, str, str]:
    """Load and return (base_url, api_key, model) from .env."""
    load_dotenv(ENV_PATH)
    base_url = os.environ.get("LLM_BASE_URL", "").rstrip("/")
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    model = os.environ.get("LLM_MODEL", "").strip()
    missing = [
        key for key, value in zip(ENV_KEYS, (base_url, api_key, model)) if not value
    ]
    if missing:
        sys.exit(
            f"[error] missing environment variables: {', '.join(missing)} (check .env)"
        )
    return base_url, api_key, model


def read_inputs(n: int) -> tuple[str, str]:
    """Read and return (system_prompt, user_content) for episode N."""
    processed_path = PROCESSED_DIR / f"episode-{n}.md"
    content_path = CONTENT_DIR / f"episode-{n}.md"
    prompt_path = PROMPTS_DIR / "check-translation.md"
    missing = [p for p in (processed_path, content_path, prompt_path) if not p.exists()]
    if missing:
        sys.exit(
            "[error] missing input file(s): "
            + ", ".join(str(p.relative_to(ROOT)) for p in missing)
        )

    system_prompt = prompt_path.read_text("utf-8")
    transcript = processed_path.read_text("utf-8")
    content = content_path.read_text("utf-8")
    user_content = SEPARATOR.join((transcript, content))
    return system_prompt, user_content


def check_endpoint(base_url: str, api_key: str) -> None:
    """Verify the endpoint is reachable with the configured key."""
    try:
        response = requests.get(
            f"{base_url}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"[warn] preflight check against {base_url}/models failed: {exc}")


def generate(
    base_url: str, api_key: str, model: str, system_prompt: str, user_content: str
) -> str:
    """Call the OpenAI-compatible endpoint and return the report."""
    print(f"[ok] calling model '{model}' at {base_url} ...")
    client = OpenAI(base_url=base_url, api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )
    content = response.choices[0].message.content
    if not content:
        sys.exit("[error] the model returned an empty response")
    return content


def normalize_content(content: str) -> str:
    """Strip Markdown code fences and trailing whitespace, end with a blank line."""
    fence = "```"
    if content.strip().startswith(fence):
        lines = content.splitlines()
        if lines and lines[0].strip() == fence:
            lines = lines[1:]
        if lines and lines[-1].strip() == fence:
            lines = lines[:-1]
        content = "\n".join(lines)
    return f"{content.strip()}\n\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check that a Persian post summarises its source transcript correctly."
    )
    parser.add_argument("episode", type=int, help="episode number to check (>= 1)")
    args = parser.parse_args()

    if args.episode < 1:
        sys.exit("[error] episode number must be >= 1")

    base_url, api_key, model = load_config()
    system_prompt, user_content = read_inputs(args.episode)
    check_endpoint(base_url, api_key)
    content = generate(base_url, api_key, model, system_prompt, user_content)

    REPORTS_DIR.mkdir(exist_ok=True)
    out_path = REPORTS_DIR / f"episode-{args.episode}.md"
    out_path.write_text(normalize_content(content), "utf-8")
    print(f"[ok] wrote {out_path}")


if __name__ == "__main__":
    main()

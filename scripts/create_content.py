#!/usr/bin/env python3
"""
Generate the Persian blog post for an episode using an OpenAI-compatible LLM.

Reads the minified transcript from processed/episode-N.md and the matching
system prompt (prompts/generate-post-0.md for episode 0 or
prompts/generate-post-N.md for episodes 1 and up), then calls the
OpenAI-compatible endpoint configured in .env to produce the post and
writes the result to content/episode-N.md.

The endpoint is configured via .env:
    LLM_BASE_URL=https://api.avalai.org/v1
    LLM_API_KEY=<key>
    LLM_MODEL=gemini-3.8-flash

Usage:
    python3 scripts/create_content.py 3        # generate content/episode-3.md
"""

import argparse
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
PROCESSED_DIR = ROOT / "processed"
PROMPTS_DIR = ROOT / "prompts"
CONTENT_DIR = ROOT / "content"

ENV_KEYS = ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL")
FENCE_RE = re.compile(r"^\s*```(?:\w*)\s*$", re.MULTILINE)


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
    """Read and return (system_prompt, processed_content) for episode N."""
    processed_path = PROCESSED_DIR / f"episode-{n}.md"
    prompt_name = "generate-post-0.md" if n == 0 else "generate-post-N.md"
    prompt_path = PROMPTS_DIR / prompt_name
    missing = [p for p in (processed_path, prompt_path) if not p.exists()]
    if missing:
        sys.exit(f"[error] missing input file(s): {', '.join(str(p) for p in missing)}")
    return prompt_path.read_text("utf-8"), processed_path.read_text("utf-8")


def check_endpoint(base_url: str, api_key: str) -> None:
    """Verify the endpoint is reachable with the configured key."""
    try:
        response = requests.get(
            f"{base_url}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=300,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"[warn] preflight check against {base_url}/models failed: {exc}")


def generate(
    base_url: str, api_key: str, model: str, system_prompt: str, user_content: str
) -> str:
    """Call the OpenAI-compatible endpoint and return the generated post."""
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
    content = FENCE_RE.sub("", content).strip()
    return f"{content}\n\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a Persian post for an episode."
    )
    parser.add_argument("episode", type=int, help="episode number to generate")
    args = parser.parse_args()

    base_url, api_key, model = load_config()
    system_prompt, processed_content = read_inputs(args.episode)
    check_endpoint(base_url, api_key)
    content = generate(base_url, api_key, model, system_prompt, processed_content)

    CONTENT_DIR.mkdir(exist_ok=True)
    out_path = CONTENT_DIR / f"episode-{args.episode}.md"
    out_path.write_text(normalize_content(content), "utf-8")
    print(f"[ok] wrote {out_path}")


if __name__ == "__main__":
    main()

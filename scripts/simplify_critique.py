#!/usr/bin/env python3
"""
Simplify the language of a Persian fact-check critique in plain Persian (Farsi).

This is a post-generation refinement pass: reads the current critique from
critique/episode-N.md (N>=1), sends it with prompts/simplify-critique.md as the
system prompt to the configured LLM (using LLM_MODEL_SIMPLIFY, falling back to
LLM_MODEL — never LLM_MODEL_CRITIQUE), and rewrites critique/episode-N.md with
the simplified text.

The pass is language simplification, not summarization: the critique keeps its
structure (H1 title, the overall assessment, and every chapter heading
byte-identical, with the same timestamps and titles) and all of its content —
including every judgement and verdict; only the wording is made simpler and
more natural for Iranian readers.

No web search is used; the model rewrites only the text it is given.

The endpoint is configured via .env; LLM_MODEL_SIMPLIFY takes precedence and
falls back to the base LLM_MODEL when unset:
    LLM_BASE_URL=https://api.avalai.org/v1
    LLM_API_KEY=<key>
    LLM_MODEL_SIMPLIFY=<model>
    LLM_MODEL=<model> (fallback)

Usage:
    python3 scripts/simplify_critique.py 1        # simplify critique for episode 1
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
CRITIQUE_DIR = ROOT / "critique"
PROMPTS_DIR = ROOT / "prompts"

ENV_KEYS = ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL_SIMPLIFY")


def load_config() -> tuple[str, str, str]:
    """Load and return (base_url, api_key, model) from .env.

    LLM_MODEL_SIMPLIFY takes precedence; the base LLM_MODEL is the fallback.
    """
    load_dotenv(ENV_PATH)
    base_url = os.environ.get("LLM_BASE_URL", "").rstrip("/")
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    model = (
        os.environ.get("LLM_MODEL_SIMPLIFY", "").strip()
        or os.environ.get("LLM_MODEL", "").strip()
    )
    missing = [
        key for key, value in zip(ENV_KEYS, (base_url, api_key, model)) if not value
    ]
    if missing:
        sys.exit(
            f"[error] missing environment variables: {', '.join(missing)} (check .env)"
        )
    return base_url, api_key, model


def read_inputs(n: int) -> tuple[str, str]:
    """Read and return (system_prompt, critique) for episode N."""
    critique_path = CRITIQUE_DIR / f"episode-{n}.md"
    prompt_path = PROMPTS_DIR / "simplify-critique.md"
    missing = [p for p in (critique_path, prompt_path) if not p.exists()]
    if missing:
        sys.exit(
            "[error] missing input file(s): "
            + ", ".join(str(p.relative_to(ROOT)) for p in missing)
        )
    return prompt_path.read_text("utf-8"), critique_path.read_text("utf-8")


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
    """Call the OpenAI-compatible endpoint and return the simplified critique."""
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
        description="Simplify the Persian wording of a critique post."
    )
    parser.add_argument("episode", type=int, help="episode number to simplify (>= 1)")
    args = parser.parse_args()

    if args.episode < 1:
        sys.exit("[error] episode number must be >= 1")

    base_url, api_key, model = load_config()
    system_prompt, critique = read_inputs(args.episode)
    check_endpoint(base_url, api_key)
    simplified = generate(base_url, api_key, model, system_prompt, critique)
    simplified = normalize_content(simplified)

    critique_path = CRITIQUE_DIR / f"episode-{args.episode}.md"
    critique_path.write_text(simplified, "utf-8")
    print(f"[ok] wrote {critique_path}")


if __name__ == "__main__":
    main()

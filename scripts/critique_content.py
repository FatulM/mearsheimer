#!/usr/bin/env python3
"""
Fact-check and critique a Persian blog post for an episode using an OpenAI-compatible LLM.

Reads the Persian content from content/episode-N.md and the matching system
prompt (prompts/research-critique.md by default, or prompts/research-critique-full.md
with --full which also passes the English transcript from processed/episode-N.md),
then calls the OpenAI-compatible endpoint configured in .env and writes the
result to critique/episode-N.md.

The endpoint is configured via .env:
    LLM_BASE_URL=https://api.avalai.org/v1
    LLM_API_KEY=<key>
    LLM_MODEL_CRITIQUE=<model>

Usage:
    python3 scripts/critique_content.py 3        # light critique (content only)
    python3 scripts/critique_content.py 3 --full # full critique (content + transcript)
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
CONTENT_DIR = ROOT / "content"
PROCESSED_DIR = ROOT / "processed"
PROMPTS_DIR = ROOT / "prompts"
CRITIQUE_DIR = ROOT / "critique"

ENV_KEYS = ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL_CRITIQUE")
FENCE_RE = re.compile(r"^\s*```(?:\w*)\s*$", re.MULTILINE)


def load_config() -> tuple[str, str, str]:
    """Load and return (base_url, api_key, model) from .env."""
    load_dotenv(ENV_PATH)
    base_url = os.environ.get("LLM_BASE_URL", "").rstrip("/")
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    model = os.environ.get("LLM_MODEL_CRITIQUE", "").strip()
    missing = [
        key for key, value in zip(ENV_KEYS, (base_url, api_key, model)) if not value
    ]
    if missing:
        sys.exit(
            f"[error] missing environment variables: {', '.join(missing)} (check .env)"
        )
    return base_url, api_key, model


def read_inputs(n: int, full: bool) -> tuple[str, str]:
    """Read and return (system_prompt, user_content) for episode N."""
    content_path = CONTENT_DIR / f"episode-{n}.md"
    prompt_name = "research-critique-full.md" if full else "research-critique.md"
    prompt_path = PROMPTS_DIR / prompt_name
    missing = [p for p in (content_path, prompt_path) if not p.exists()]
    if missing:
        sys.exit(f"[error] missing input file(s): {', '.join(str(p) for p in missing)}")

    system_prompt = prompt_path.read_text("utf-8")
    user_content = content_path.read_text("utf-8")

    if full:
        processed_path = PROCESSED_DIR / f"episode-{n}.md"
        if not processed_path.exists():
            sys.exit(f"[error] missing transcript file: {processed_path}")
        transcript = processed_path.read_text("utf-8")
        user_content = (
            f"## Persian blog post\n\n{user_content}\n\n"
            f"## English transcript\n\n{transcript}"
        )

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


def report_tool_usage(response) -> None:
    """Report whether the web_search hosted tool actually ran."""
    try:
        tools = response.usage.tools
        if tools is not None and hasattr(tools, "web_search_tool"):
            ws = tools.web_search_tool
            searches = getattr(ws, "searches", 0)
            sessions = getattr(ws, "sessions", 0)
            print(
                f"[ok] web_search tool ran: {searches} searches in {sessions} sessions"
            )
            return
    except AttributeError:
        pass

    try:
        annotations = [
            a.url_citation.url
            for a in (response.choices[0].message.annotations or [])
            if getattr(a, "type", None) == "url_citation"
        ]
    except AttributeError:
        annotations = []
    if annotations:
        print(f"[ok] web_search tool ran: {len(annotations)} URL citation(s) returned")
        for url in annotations[:5]:
            print(f"      - {url}")
        return

    print(
        "[warn] no web_search evidence found — no tool usage or URL citations "
        "reported; the endpoint likely ignored the tools parameter"
    )


def generate(
    base_url: str, api_key: str, model: str, system_prompt: str, user_content: str
) -> str:
    """Call the OpenAI-compatible endpoint and return the critique."""
    print(f"[ok] calling model '{model}' at {base_url} ...")
    client = OpenAI(base_url=base_url, api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        tools=[{"type": "web_search"}],
    )
    report_tool_usage(response)
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
        description="Critique a Persian blog post for an episode."
    )
    parser.add_argument("episode", type=int, help="episode number to critique (>= 1)")
    parser.add_argument(
        "--full",
        action="store_true",
        help="include the English transcript for cross-referencing",
    )
    args = parser.parse_args()

    if args.episode < 1:
        sys.exit("[error] episode number must be >= 1")

    base_url, api_key, model = load_config()
    system_prompt, user_content = read_inputs(args.episode, args.full)
    check_endpoint(base_url, api_key)
    content = generate(base_url, api_key, model, system_prompt, user_content)

    CRITIQUE_DIR.mkdir(exist_ok=True)
    out_path = CRITIQUE_DIR / f"episode-{args.episode}.md"
    out_path.write_text(normalize_content(content), "utf-8")
    print(f"[ok] wrote {out_path}")


if __name__ == "__main__":
    main()

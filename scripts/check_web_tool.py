#!/usr/bin/env python3
"""
Compare two model calls to check whether the endpoint actually runs web search.

Calls the OpenAI-compatible endpoint configured in .env with the
LLM_MODEL_CRITIQUE model, asking a question that requires up-to-date
information (the current gold price). The first call passes the
`web_search` hosted tool; the second does not. Both answers and the
reported tool usage are printed so you can judge whether the endpoint
really executes web searches or silently ignores the tools parameter.

The endpoint is configured via .env:
    LLM_BASE_URL=https://api.avalai.org/v1
    LLM_API_KEY=<key>
    LLM_MODEL_CRITIQUE=<model>

Usage:
    python3 scripts/check_web_tool.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"

ENV_KEYS = ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL_CRITIQUE")

QUESTION = "Offer price per ounce of gold right now?"


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
    print(
        "[warn] no web_search tool usage reported — the endpoint may have "
        "silently ignored the tools parameter (model likely answered from memory)"
    )


def ask(client: OpenAI, model: str, use_tool: bool) -> str:
    """Ask the question once, with or without the web_search tool."""
    kwargs = {"tools": [{"type": "web_search"}]} if use_tool else {}
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": QUESTION}],
        **kwargs,
    )
    return response


def main() -> None:
    base_url, api_key, model = load_config()
    print(f"[ok] model '{model}' at {base_url}")
    print(f"[info] question: {QUESTION}\n")

    client = OpenAI(base_url=base_url, api_key=api_key)

    print("=== call WITH web_search tool ===")
    with_tool = ask(client, model, use_tool=True)
    report_tool_usage(with_tool)
    print(f"answer: {with_tool.choices[0].message.content}\n")

    print("=== call WITHOUT web_search tool ===")
    without_tool = ask(client, model, use_tool=False)
    answer = without_tool.choices[0].message.content
    print(f"answer: {answer}\n")


if __name__ == "__main__":
    main()

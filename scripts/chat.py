#!/usr/bin/env python3
"""
Interactive chat with the OpenAI-compatible LLM.

Reads LLM_BASE_URL, LLM_API_KEY, and LLM_MODEL_CHAT (falling back to the base
LLM_MODEL when unset) from .env.
Enter sends the message, Option+Enter inserts a newline.
Type /exit or exit to quit.

Option+Enter emits ESC plus a newline in the terminal; canonical line mode
stashes the ESC at the end of the read line, so a trailing ESC marks a
line continuation while a plain Enter submits the message.

Usage:
    python3 scripts/chat.py                      # system prompt from prompts/chat.md
    python3 scripts/chat.py --system prompts/x.md  # custom system prompt
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

PROMPTS_DIR = ROOT / "prompts"
QUIT_COMMANDS = {"exit", "/exit"}
ESC = "\x1b"


def load_system_prompt(path: str | None) -> str:
    """Load and return the system prompt from the given prompt file."""
    prompt_path = Path(path).expanduser() if path else PROMPTS_DIR / "chat.md"
    if not prompt_path.exists():
        sys.exit(f"[error] system prompt file not found: {prompt_path}")
    return prompt_path.read_text("utf-8").strip()


def read_message() -> str | None:
    """Read a multi-line user message. Returns None on EOF/exit."""
    lines: list[str] = []

    while True:
        try:
            line = input("you> " if not lines else "... ")
        except EOFError:
            print()
            return None
        except KeyboardInterrupt:
            print()
            return None

        if line.strip().lower() in QUIT_COMMANDS:
            return None

        if line.endswith(ESC):
            lines.append(line[:-1])
            continue

        lines.append(line)
        break

    message = "\n".join(lines).strip()
    return message or None


def main() -> None:
    parser = argparse.ArgumentParser(description="Chat with the LLM.")
    parser.add_argument(
        "--system",
        metavar="FILE",
        help="system prompt file to use (default: prompts/chat.md)",
    )
    args = parser.parse_args()

    base_url = os.environ.get("LLM_BASE_URL", "").rstrip("/")
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    model = (
        os.environ.get("LLM_MODEL_CHAT", "").strip()
        or os.environ.get("LLM_MODEL", "").strip()
    )

    missing = [
        key
        for key, value in (
            ("LLM_BASE_URL", base_url),
            ("LLM_API_KEY", api_key),
            ("LLM_MODEL_CHAT / LLM_MODEL", model),
        )
        if not value
    ]
    if missing:
        sys.exit(
            f"[error] missing environment variables: {', '.join(missing)} (check .env)"
        )

    system_prompt = load_system_prompt(args.system)
    client = OpenAI(base_url=base_url, api_key=api_key)
    messages = [{"role": "system", "content": system_prompt}]

    print(f"[ok] chatting with '{model}' at {base_url}")
    print("    Enter sends, Option+Enter adds a newline, /exit quits.\n")

    while True:
        user_input = read_message()
        if user_input is None:
            print("\nbye!")
            break

        messages.append({"role": "user", "content": user_input})
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
            )
        except OpenAIError as exc:
            print(f"[error] {exc}\n")
            messages.pop()
            continue

        reply = response.choices[0].message.content or ""
        messages.append({"role": "assistant", "content": reply})
        print(f"\n{reply}\n")


if __name__ == "__main__":
    main()

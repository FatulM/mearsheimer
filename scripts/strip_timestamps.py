#!/usr/bin/env python3
"""
Strip timestamps from the section headings of a Persian blog post.

Reads the content of content/episode-N.md (N>=1), removes the `{mm:ss} - `
prefix from every `## {mm:ss} - {TITLE}` chapter heading, and prints the
result to stdout.

Usage:
    python3 scripts/strip_timestamps.py 3
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content"

TIMESTAMP_RE = re.compile(r"^(\s*##\s*)\d{1,2}:\d{2}(?::\d{2})?\s*-\s*", re.MULTILINE)


def strip_timestamps(text: str) -> str:
    """Return the article text with timestamps removed from section headings."""
    return TIMESTAMP_RE.sub(r"\1", text)


def read_content(n: int) -> str:
    """Read and return the content of content/episode-N.md for episode N."""
    content_path = CONTENT_DIR / f"episode-{n}.md"
    if not content_path.exists():
        sys.exit(f"[error] missing content file: {content_path}")
    return content_path.read_text("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Strip timestamps from a Persian blog post's section headings."
    )
    parser.add_argument("episode", type=int, help="episode number (>= 1)")
    args = parser.parse_args()

    if args.episode < 1:
        sys.exit("[error] episode number must be >= 1")

    content = read_content(args.episode)
    print(strip_timestamps(content), end="")


if __name__ == "__main__":
    main()

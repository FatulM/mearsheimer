#!/usr/bin/env python3
"""
Count the number of OpenAI-style tokens in a UTF-8 text file.

Usage:
    python scripts/count_tokens.py path/to/file.md
"""

import sys

import tiktoken


def main():
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <file_path>")
        sys.exit(1)

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        print(f"File not found: {path}")
        sys.exit(1)

    enc = tiktoken.get_encoding("o200k_base")
    count = len(enc.encode(text))
    print(f"{count:,}")


if __name__ == "__main__":
    main()

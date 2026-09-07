#!/usr/bin/env python3
"""
Check the structure of critique/episode-N.md files against their content sources.

For each critique/episode-N.md (N>=1), verifies:

1. Markdown structure:
   - file ends with a blank line
   - exactly one H1 heading, and it is followed by a blank line
   - only H1 and H2 headings are used
   - every H2 heading is followed by a blank line
   - no horizontal rules (---), which the critique prompts forbid
2. Heading fidelity: the critique H1 title and every `## {mm:ss} - {TITLE}`
   chapter heading must be byte-identical, in the same order, to the matching
   content/episode-N.md, so no chapter is dropped, reworded, or retimed.

Prints one line per critique file and exits non-zero if any file has problems.

Usage:
    python3 scripts/check_critiques.py             # all critiques
    python3 scripts/check_critiques.py 1 3         # only episodes 1 and 3
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CRITIQUE_DIR = ROOT / "critique"
CONTENT_DIR = ROOT / "content"

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
HORIZONTAL_RULE_RE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")


def extract_headings(text: str) -> list[tuple[int, str]]:
    """Return (level, raw_line) pairs for every heading in the text."""
    return [
        (len(m.group(1)), m.group(0).strip())
        for m in (HEADING_RE.match(ln) for ln in text.splitlines())
        if m
    ]


def check_markdown(text: str) -> list[str]:
    """Return a list of markdown structure problems for the critique text."""
    problems = []
    lines = text.splitlines()

    if not text.endswith("\n"):
        problems.append("file does not end with a newline")
    if not text.endswith("\n\n") and text.strip():
        problems.append("file does not end with a blank line")

    if any(HORIZONTAL_RULE_RE.match(ln) for ln in lines):
        problems.append("contains horizontal rules (---)")

    headings = extract_headings(text)
    if not headings or headings[0][0] != 1:
        problems.append("missing the H1 title heading")
    h1s = [h for h in headings if h[0] == 1]
    if len(h1s) > 1:
        problems.append(f"multiple H1 headings ({len(h1s)})")
    els = [h for h in headings if h[0] not in (1, 2)]
    if els:
        levels = sorted({h[0] for h in els})
        problems.append(f"heading levels other than H1/H2 used: {levels}")

    for i, raw in enumerate(lines):
        if not HEADING_RE.match(raw):
            continue
        if i + 1 >= len(lines) or lines[i + 1].strip():
            problems.append(f"heading at line {i + 1} is not followed by a blank line")

    return problems


def check_headings_match(
    critique_heads: list[tuple[int, str]], content_text: str
) -> list[str]:
    """Return heading-fidelity problems comparing critique to content."""
    problems = []
    content_heads = extract_headings(content_text)
    c_h1 = [h for h in content_heads if h[0] == 1]
    k_h1 = [h for h in critique_heads if h[0] == 1]
    if k_h1 != c_h1:
        problems.append(
            f"H1 title mismatch: critique={k_h1[0][1] if k_h1 else '<none>'}"
            f" content={c_h1[0][1] if c_h1 else '<none>'}"
        )
    c_h2 = [h[1] for h in content_heads if h[0] == 2]
    k_h2 = [h[1] for h in critique_heads if h[0] == 2]
    if k_h2 != c_h2:
        if len(k_h2) != len(c_h2):
            problems.append(
                f"chapter count mismatch: critique has {len(k_h2)} chapters, "
                f"content has {len(c_h2)}"
            )
        for i in range(max(len(c_h2), len(k_h2))):
            exp = c_h2[i] if i < len(c_h2) else "<missing>"
            act = k_h2[i] if i < len(k_h2) else "<extra>"
            if exp != act:
                problems.append(
                    f"chapter {i + 1} mismatch: content={exp} critique={act}"
                )
    return problems


def check_critique(n: int) -> tuple[list[str], Path, Path]:
    """Return (problems, critique_path, content_path) for episode N."""
    critique_path = CRITIQUE_DIR / f"episode-{n}.md"
    content_path = CONTENT_DIR / f"episode-{n}.md"
    if not critique_path.exists():
        return ["missing critique file"], critique_path, content_path
    if not content_path.exists():
        return (
            [f"missing content file {content_path.relative_to(ROOT)}"],
            critique_path,
            content_path,
        )

    critique_text = critique_path.read_text("utf-8")
    content_text = content_path.read_text("utf-8")
    problems = check_markdown(critique_text)
    problems += check_headings_match(extract_headings(critique_text), content_text)
    return problems, critique_path, content_path


def main() -> int:
    args = [int(a) for a in sys.argv[1:]]
    has_error = False
    found_any = False
    for critique_path in sorted(CRITIQUE_DIR.glob("episode-*.md")):
        m = re.match(r"episode-(\d+)\.md$", critique_path.name)
        if not m:
            continue
        n = int(m.group(1))
        if n < 1 or (args and n not in args):
            continue
        found_any = True
        problems, critique_path, content_path = check_critique(n)
        rel = critique_path.relative_to(ROOT)
        if problems:
            has_error = True
            print(f"[error] {rel}:")
            for problem in problems:
                print(f"        - {problem}")
        else:
            print(f"[ok] {rel} matches {content_path.relative_to(ROOT)}")
    if not found_any:
        print("[error] no critique/episode-*.md files found")
        return 1
    return 1 if has_error else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Check that content/episode-N.md section timestamps match info/episode-N.txt chapters.

Extracts the chapter timestamps from the CHAPTERS section of each
info/episode-N.txt and the `## {mm:ss} - {TITLE}` heading timestamps from
the matching content/episode-N.md, then verifies the two lists are exactly
equal (same order and same values). Titles are not compared, since content
titles are Persian translations of the English chapter titles.

Prints one line per episode showing the file names and whether the
timestamps match; mismatches are reported as errors and make the script
exit with a non-zero status.

Usage:
    python3 scripts/check_timestamps.py              # all episodes
    python3 scripts/check_timestamps.py 1 3          # only episodes 1 and 3
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INFO_DIR = ROOT / "info"
CONTENT_DIR = ROOT / "content"

CHAPTER_RE = re.compile(r"^(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+)$")
SEPARATOR_RE = re.compile(r"^—+|-{3,}$")
SECTION_RE = re.compile(r"^##\s+(\d{1,2}:\d{2})\s+-\s+")


def parse_chapters(info_path: Path) -> list[str]:
    """Extract normalized timestamps from the CHAPTERS section of an info file."""
    timestamps = []
    in_chapters = False
    for raw in info_path.read_text("utf-8").splitlines():
        line = raw.strip()
        if SEPARATOR_RE.match(line):
            in_chapters = False
            continue
        if line.lower() == "chapters":
            in_chapters = True
            continue
        if in_chapters:
            m = CHAPTER_RE.match(line)
            if m:
                timestamps.append(normalize_ts(m.group(1)))
    return timestamps


def parse_sections(content_path: Path) -> list[str]:
    """Extract the H2 heading timestamps from a content file."""
    timestamps = []
    for raw in content_path.read_text("utf-8").splitlines():
        m = SECTION_RE.match(raw.strip())
        if m:
            timestamps.append(normalize_ts(m.group(1)))
    return timestamps


def normalize_ts(ts: str) -> str:
    """Pad to mm:ss (or h:mm:ss) for consistent comparison."""
    parts = [int(p) for p in ts.split(":")]
    if len(parts) == 2:
        h, m, s = 0, parts[0], parts[1]
    else:
        h, m, s = parts
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def describe_mismatch(expected: list[str], actual: list[str]) -> str:
    lines = [f"expected {len(expected)} timestamps, found {len(actual)}"]
    for i in range(max(len(expected), len(actual))):
        exp = expected[i] if i < len(expected) else "<missing>"
        act = actual[i] if i < len(actual) else "<missing>"
        if exp != act:
            lines.append(f"  chapter {i + 1}: info={exp} content={act}")
    return "; ".join(lines)


def main() -> int:
    args = [int(a) for a in sys.argv[1:]]
    has_error = False
    found_any = False
    for info_path in sorted(INFO_DIR.glob("episode-*.txt")):
        n = int(re.search(r"episode-(\d+)\.txt", info_path.name).group(1))
        if args and n not in args:
            continue
        found_any = True
        content_path = CONTENT_DIR / f"episode-{n}.md"
        if not content_path.exists():
            print(f"[error] {content_path.relative_to(ROOT)}: file missing")
            has_error = True
            continue
        expected = parse_chapters(info_path)
        actual = parse_sections(content_path)
        if expected == actual:
            label = "no chapters" if not expected else f"{len(expected)} chapters"
            print(
                f"[ok] {content_path.relative_to(ROOT)} matches "
                f"{info_path.relative_to(ROOT)} ({label})"
            )
        else:
            print(
                f"[error] {content_path.relative_to(ROOT)} does not match "
                f"{info_path.relative_to(ROOT)}: "
                f"{describe_mismatch(expected, actual)}"
            )
            has_error = True
    if not found_any:
        print("[error] no info/episode-*.txt files found")
        return 1
    return 1 if has_error else 0


if __name__ == "__main__":
    sys.exit(main())

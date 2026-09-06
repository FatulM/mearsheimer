#!/usr/bin/env python3
"""
Minify SRT subtitles into processed/episode-N.md files.

Reads the video title and chapter info from info/episode-N.txt and the
matching transcript/episode-N.srt, then writes processed/episode-N.md
with the video title and each chapter's subtitles concatenated into a
single text block under a `## {mm:ss} - {TITLE}` heading.
Episodes without chapters (e.g. the channel introduction) are written as
a single text block instead.

Usage:
    python3 scripts/process_transcripts.py              # all episodes
    python3 scripts/process_transcripts.py 1 3          # only episodes 1 and 3
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INFO_DIR = ROOT / "info"
TRANSCRIPT_DIR = ROOT / "transcript"
PROCESSED_DIR = ROOT / "processed"

CHAPTER_RE = re.compile(r"^(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+)$")
SEPARATOR_RE = re.compile(r"^—+|-{3,}$")
TS_LINE_RE = re.compile(r"^(\d{1,2}):(\d{2}):(\d{2}),\d{3}\s*-->")


def parse_info(info_path: Path) -> str:
    """Extract the video title from the second non-empty line."""
    lines = [
        ln.strip() for ln in info_path.read_text("utf-8").splitlines() if ln.strip()
    ]
    return lines[1]


def parse_chapters(info_path: Path) -> list:
    """Extract (timestamp, title) chapter pairs below the CHAPTERS marker."""
    chapters = []
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
                chapters.append((m.group(1), m.group(2)))
    return chapters


def parse_srt(srt_path: Path) -> list:
    """Extract (start_seconds, text) cues from an SRT file."""
    cues = []
    for block in re.split(r"\n\s*\n", srt_path.read_text("utf-8")):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        if "-->" in lines[0]:
            ts_line, text_lines = lines[0], lines[1:]
        elif len(lines) >= 2 and "-->" in lines[1]:
            ts_line, text_lines = lines[1], lines[2:]
        else:
            continue
        m = TS_LINE_RE.match(ts_line)
        if not m:
            continue
        start = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
        cues.append((start, " ".join(text_lines)))
    return cues


def to_seconds(ts: str) -> int:
    parts = [int(p) for p in ts.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    h, m, s = parts
    return h * 3600 + m * 60 + s


def normalize_ts(ts: str) -> str:
    """Pad to mm:ss (or h:mm:ss) for consistency with content headings."""
    parts = [int(p) for p in ts.split(":")]
    if len(parts) == 2:
        h, m, s = 0, parts[0], parts[1]
    else:
        h, m, s = parts
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def chapter_index(seconds: int, boundaries: list) -> int:
    for i, boundary in enumerate(boundaries):
        if seconds < boundary:
            return i - 1 if i > 0 else 0
    return len(boundaries) - 1


def minify(title: str, cues: list, chapters: list) -> str:
    head = f"# {title}"
    if not chapters:
        return f"{head}\n\n{' '.join(text for _, text in cues)}"
    boundaries = [to_seconds(ts) for ts, _ in chapters]
    sections = []
    for i, (ts, chap_title) in enumerate(chapters):
        text = " ".join(t for sec, t in cues if chapter_index(sec, boundaries) == i)
        heading = f"## {normalize_ts(ts)} - {chap_title}"
        sections.append(f"{heading}\n\n{text}" if text else heading)
    return f"{head}\n\n{'\n\n'.join(sections)}"


def main() -> None:
    args = [int(a) for a in sys.argv[1:]]
    PROCESSED_DIR.mkdir(exist_ok=True)
    for info_path in sorted(INFO_DIR.glob("episode-*.txt")):
        n = int(re.search(r"episode-(\d+)\.txt", info_path.name).group(1))
        if args and n not in args:
            continue
        srt_path = TRANSCRIPT_DIR / f"episode-{n}.srt"
        if not srt_path.exists():
            print(f"[skip] episode-{n}: transcript missing")
            continue
        chapters = parse_chapters(info_path)
        title = parse_info(info_path)
        cues = parse_srt(srt_path)
        out_path = PROCESSED_DIR / f"episode-{n}.md"
        out_path.write_text(minify(title, cues, chapters) + "\n", "utf-8")
        label = "no chapters" if not chapters else f"{len(chapters)} chapters"
        print(f"[ok] processed/episode-{n}.md ({label})")


if __name__ == "__main__":
    main()

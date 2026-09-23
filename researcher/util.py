#!/usr/bin/env python3
"""Small helpers shared by the researcher CLI scripts."""

from __future__ import annotations

from pathlib import Path
from trace import RunTrace

from config import ROOT


def display_path(path: Path) -> str:
    """Return a repo-root-relative display path (absolute fallback)."""
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def print_usage(trace: RunTrace) -> None:
    """Print the run's total token usage, one line per agent."""
    total = sum(entry["total"] for entry in trace.usage.values())
    print(f"[ok] total tokens: {total}")
    for agent, entry in sorted(trace.usage.items()):
        print(f"      {agent}: {entry['calls']} call(s), {entry['total']} tokens")

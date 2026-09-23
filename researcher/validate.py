#!/usr/bin/env python3
"""Deterministic gates for the generated critique.

Pure-Python, no LLM, mirroring and extending `scripts/check_critiques.py`. The
result is written only when `validate_critique` returns no problems. Checks:
heading parity with the source content, blank lines after headings, a single
horizontal rule before the citations, citation-marker/list self-consistency
with sequential numbering, and citation provenance against the run's source
registry.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sources import SourceRegistry, normalize_url

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
HORIZONTAL_RULE_RE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")
CITE_MARKER_RE = re.compile(r"\[cite:\s*(\d+(?:\s*,\s*\d+)*)\]")
CITE_MERGE_RE = re.compile(
    r"\[cite:\s*(\d+(?:\s*,\s*\d+)*)\]\s*\[cite:\s*(\d+(?:\s*,\s*\d+)*)\]"
)
ANY_BRACKET_RE = re.compile(r"\[[^\]]*\]")
ENTRY_RE = re.compile(r"^(\d+)\.\s+(\S.*)$")
URL_RE = re.compile(r"^https?://\S+$")

EXPECTED_CITE = "[cite: N]"
NO_CLAIMS_RE = re.compile(
    r"(?:هیچ\s+)?ادعا(?:ی|های|یی)\s+قابل(?:ِ)?\s+راستی\u200c?آزمایی\s+"
    r"مستقل(?:ی)?(?:\s+وجود)?\s+ندارد"
)


@dataclass
class Problem:
    """A single deterministic-gate failure."""

    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


def extract_headings(text: str) -> list[tuple[int, str]]:
    """Return (level, raw_line) pairs for every heading in the text."""
    return [
        (len(m.group(1)), m.group(0).strip())
        for m in (HEADING_RE.match(ln) for ln in text.splitlines())
        if m
    ]


def _check_structure(text: str, problems: list[Problem]) -> None:
    lines = text.splitlines()
    if not text.endswith("\n"):
        problems.append(Problem("structure", "file does not end with a newline"))
    if not text.endswith("\n\n") and text.strip():
        problems.append(Problem("structure", "file does not end with a blank line"))

    headings = extract_headings(text)
    if not headings or headings[0][0] != 1:
        problems.append(Problem("structure", "missing the H1 title heading"))
    h1s = [h for h in headings if h[0] == 1]
    if len(h1s) > 1:
        problems.append(Problem("structure", f"multiple H1 headings ({len(h1s)})"))
    others = [h for h in headings if h[0] not in (1, 2)]
    if others:
        levels = sorted({h[0] for h in others})
        problems.append(
            Problem("structure", f"heading levels other than H1/H2 used: {levels}")
        )

    for i, raw in enumerate(lines):
        if not HEADING_RE.match(raw):
            continue
        if i + 1 >= len(lines) or lines[i + 1].strip():
            problems.append(
                Problem(
                    "structure",
                    f"heading at line {i + 1} is not followed by a blank line",
                )
            )


def _check_headings_match(
    critique_text: str, content_text: str, problems: list[Problem]
) -> None:
    content_heads = extract_headings(content_text)
    critique_heads = extract_headings(critique_text)
    c_h1 = [h for h in content_heads if h[0] == 1]
    k_h1 = [h for h in critique_heads if h[0] == 1]
    if k_h1 != c_h1:
        problems.append(
            Problem(
                "heading",
                f"H1 title mismatch: critique={k_h1[0][1] if k_h1 else '<none>'} "
                f"content={c_h1[0][1] if c_h1 else '<none>'}",
            )
        )
    c_h2 = [h[1] for h in content_heads if h[0] == 2]
    k_h2 = [h[1] for h in critique_heads if h[0] == 2]
    if k_h2 == c_h2:
        return
    if len(k_h2) != len(c_h2):
        problems.append(
            Problem(
                "heading",
                f"chapter count mismatch: critique has {len(k_h2)} chapters, content has {len(c_h2)}",
            )
        )
    for i in range(max(len(c_h2), len(k_h2))):
        expected = c_h2[i] if i < len(c_h2) else "<missing>"
        actual = k_h2[i] if i < len(k_h2) else "<extra>"
        if expected != actual:
            problems.append(
                Problem(
                    "heading",
                    f"chapter {i + 1} mismatch: content={expected} critique={actual}",
                )
            )


def _check_rule(text: str, problems: list[Problem]) -> int | None:
    lines = text.splitlines()
    rules = [i for i, ln in enumerate(lines) if HORIZONTAL_RULE_RE.match(ln)]
    if len(rules) != 1:
        problems.append(
            Problem(
                "rule",
                f"expected exactly one horizontal rule before citations, found {len(rules)}",
            )
        )
        return None
    return rules[0]


def _parse_entries(cite_lines: list[str], problems: list[Problem]) -> dict[int, str]:
    entries: dict[int, str] = {}
    for line in cite_lines:
        if not line.strip():
            continue
        match = ENTRY_RE.match(line)
        if not match:
            problems.append(
                Problem("citations", f"malformed citation entry: {line[:80]!r}")
            )
            continue
        number = int(match.group(1))
        parts = match.group(2).split(" — ")
        if len(parts) != 3:
            problems.append(
                Problem(
                    "citations",
                    f"entry {number} must use exactly two em-dashes: {line[:80]!r}",
                )
            )
            continue
        url = parts[2].strip()
        if not URL_RE.match(url):
            problems.append(
                Problem(
                    "citations",
                    f"entry {number} does not end with a valid URL: {url!r}",
                )
            )
            continue
        entries[number] = url
    return entries


def split_body_parts(text: str) -> list[str]:
    """Split a critique body into parts: the overall assessment and chapters.

    The overall assessment is everything before the first `##` heading. Each
    chapter part starts at its own `## {mm:ss} - {TITLE}` heading and runs
    until the next heading.
    """
    parts: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current:
                parts.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        parts.append("\n".join(current))
    return parts


def _check_per_chapter_citations(body: str, problems: list[Problem]) -> None:
    """Require at least one `[cite: N]` marker in every research-bearing chapter.

    A chapter with no verifiable claims passes via the no-claims exemption
    phrase. The overall assessment part (before the first `##` heading) is
    exempt.
    """
    parts = split_body_parts(body)
    for index, part in enumerate(parts[1:], start=1):
        if CITE_MARKER_RE.search(part):
            continue
        if NO_CLAIMS_RE.search(part):
            continue
        problems.append(
            Problem("citations", f"chapter {index} has no {EXPECTED_CITE} marker")
        )


def _check_citations(
    body: str,
    entries: dict[int, str],
    registry: SourceRegistry | None,
    require_alive: bool,
    problems: list[Problem],
) -> None:
    for bracket in ANY_BRACKET_RE.finditer(body):
        token = bracket.group(0)
        if not CITE_MARKER_RE.fullmatch(token):
            problems.append(
                Problem(
                    "body",
                    f"forbidden bracketed marker (only {EXPECTED_CITE} allowed): {token!r}",
                )
            )

    referenced: list[int] = []
    for match in CITE_MARKER_RE.finditer(body):
        for part in match.group(1).split(","):
            referenced.append(int(part.strip()))

    if not referenced:
        problems.append(Problem("citations", "no [cite: N] markers found in the body"))
    _check_per_chapter_citations(body, problems)

    for number in referenced:
        if number not in entries:
            problems.append(
                Problem("citations", f"[cite: {number}] has no matching citation entry")
            )

    referenced_set = set(referenced)
    for number in entries:
        if number not in referenced_set:
            problems.append(
                Problem(
                    "citations",
                    f"citation entry {number} is never referenced in the body",
                )
            )

    expected_numbers = list(range(1, len(entries) + 1))
    if sorted(entries) != expected_numbers:
        problems.append(
            Problem(
                "citations",
                f"citation entries must be numbered 1..{len(entries)}; got {sorted(entries)}",
            )
        )

    first_seen: dict[int, int] = {}
    for position, number in enumerate(referenced):
        first_seen.setdefault(number, position)
    ordered = [first_seen[n] for n in expected_numbers if n in first_seen]
    if ordered != sorted(ordered):
        problems.append(
            Problem("citations", "entries are not numbered in first-reference order")
        )

    if registry is None:
        return
    for number, url in entries.items():
        source = registry.get(url)
        if source is None:
            problems.append(
                Problem(
                    "provenance",
                    f"entry {number} URL was never retrieved during this run: {normalize_url(url)}",
                )
            )
            continue
        if not (source.fetched and source.alive is not False):
            problems.append(
                Problem(
                    "provenance",
                    f"entry {number} URL was not fetched during this run: "
                    f"{normalize_url(url)}",
                )
            )
        if require_alive and source.alive is False:
            problems.append(
                Problem(
                    "provenance",
                    f"entry {number} URL failed the liveness check: {normalize_url(url)}",
                )
            )


def validate_critique(
    text: str,
    content_text: str,
    registry: SourceRegistry | None = None,
    *,
    require_alive: bool = False,
) -> list[Problem]:
    """Run every deterministic gate and return the list of problems (empty = pass)."""
    problems: list[Problem] = []
    _check_structure(text, problems)
    _check_headings_match(text, content_text, problems)

    lines = text.splitlines()
    rule_idx = _check_rule(text, problems)
    if rule_idx is None:
        return problems

    body = "\n".join(lines[:rule_idx])
    entries = _parse_entries(lines[rule_idx + 1 :], problems)
    _check_citations(body, entries, registry, require_alive, problems)
    return problems


def _ensure_heading_blank_lines(text: str) -> str:
    """Insert a blank line after every heading that lacks one."""
    lines = text.split("\n")
    out: list[str] = []
    for i, line in enumerate(lines):
        out.append(line)
        if HEADING_RE.match(line) and i + 1 < len(lines) and lines[i + 1].strip():
            out.append("")
    return "\n".join(out)


def _renumber_citations(text: str) -> str:
    """Renumber citation entries and inline markers to first-reference order.

    Applied only when the transformation is bijective (every cited number maps
    to exactly one entry and every entry is cited), because then it is safe to
    compute mechanically. Otherwise the original text is returned unchanged and
    the reviewer must handle it.
    """
    lines = text.split("\n")
    rules = [i for i, line in enumerate(lines) if HORIZONTAL_RULE_RE.match(line)]
    if len(rules) != 1:
        return text
    rule = rules[0]
    entries = lines[rule + 1 :]

    entry_nums: list[int] = []
    for line in entries:
        if not line.strip():
            continue
        match = ENTRY_RE.match(line)
        if not match:
            return text
        entry_nums.append(int(match.group(1)))

    body_text = "\n".join(lines[:rule])
    referenced: list[int] = []
    for match in CITE_MARKER_RE.finditer(body_text):
        referenced.extend(int(part.strip()) for part in match.group(1).split(","))

    if not referenced or sorted(set(referenced)) != sorted(set(entry_nums)):
        return text

    ordered = dict.fromkeys(referenced)
    mapping = {old: i + 1 for i, old in enumerate(ordered)}
    if all(mapping[n] == n for n in entry_nums):
        return text

    def _remap(match: re.Match) -> str:
        nums = ",".join(
            str(mapping[int(part.strip())]) for part in match.group(1).split(",")
        )
        return f"[cite: {nums}]"

    new_body = CITE_MARKER_RE.sub(_remap, body_text)

    new_entries: list[str] = []
    for line in entries:
        match = ENTRY_RE.match(line)
        if match:
            line = f"{mapping[int(match.group(1))]}{line[match.end(1) :]}"
        new_entries.append(line)
    return "\n".join([new_body, "---", *new_entries])


def _canonical_cite(nums: str) -> str:
    """Return the canonical ascending `[cite: N]` marker for a number list."""
    numbers = sorted({int(part.strip()) for part in nums.split(",")})
    return f"[cite: {','.join(str(n) for n in numbers)}]"


def _normalize_cite_markers(text: str) -> str:
    """Sort the numbers inside each `[cite: N]` marker and merge adjacent markers.

    `[cite: 2,1]` becomes `[cite: 1,2]`, and a run of adjacent markers such as
    `[cite: 1] [cite: 2,3]` becomes `[cite: 1,2,3]`. Only `[cite: N]` markers
    are touched (both markers in a merge must be citation markers), only
    whitespace separates the markers being merged, the set of referenced
    numbers is preserved, and the merged marker keeps the text span that the
    run of markers supported. Idempotent.
    """
    text = CITE_MARKER_RE.sub(lambda m: _canonical_cite(m.group(1)), text)
    while True:
        merged, count = CITE_MERGE_RE.subn(
            lambda m: _canonical_cite(f"{m.group(1)},{m.group(2)}"), text
        )
        if count == 0:
            return merged
        text = merged


def repair_mechanical(text: str, *, renumber: bool = True) -> str:
    """Apply safe, deterministic repairs without an LLM.

    Fixes heading blank lines, citation numbering in first-reference order
    (when bijective), citation-marker normalization (ascending numbers and
    merging of adjacent markers), and the trailing newline/blank line.
    Idempotent; any fix that cannot be guaranteed safe is left for the
    reviewer. Pass `renumber=False` to keep the citations section as written
    (the simplify stage must never rewrite the numbering).
    """
    text = _ensure_heading_blank_lines(text)
    if renumber:
        text = _renumber_citations(text)
    text = _normalize_cite_markers(text)
    stripped = text.rstrip("\n")
    return f"{stripped}\n\n" if stripped else text


def cited_urls(text: str) -> list[str]:
    """Return every URL listed in the citations section, in order."""
    lines = text.splitlines()
    rules = [i for i, ln in enumerate(lines) if HORIZONTAL_RULE_RE.match(ln)]
    if not rules:
        return []
    urls: list[str] = []
    for line in lines[rules[-1] + 1 :]:
        match = ENTRY_RE.match(line)
        if not match:
            continue
        parts = match.group(2).split(" — ")
        if len(parts) == 3 and URL_RE.match(parts[2].strip()):
            urls.append(parts[2].strip())
    return urls


if __name__ == "__main__":
    import sys
    from pathlib import Path

    if len(sys.argv) != 3:
        sys.exit("usage: python3 researcher/validate.py <critique.md> <content.md>")
    critique = Path(sys.argv[1]).read_text("utf-8")
    content = Path(sys.argv[2]).read_text("utf-8")
    found = validate_critique(critique, content)
    for problem in found:
        print(f"[error] {problem}")
    print(f"[ok] {len(found)} problem(s)" if found else "[ok] all gates passed")
    sys.exit(1 if found else 0)

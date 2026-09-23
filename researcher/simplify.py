#!/usr/bin/env python3
"""Agentic Persian language simplification of a finished episode critique.

Reads the cited critique produced by `main.py` from
`researcher/files/result/episode-N.md`, strips and holds aside the citations
section, rewrites the body once with the dedicated Persian-writing model
(`LLM_MODEL_AGENT_LANGUAGE`), then runs a reviewer/fixer loop
(`LLM_MODEL_AGENT_REVIEWER`) that compares the original body with the
simplified body, repairs every fidelity problem it finds, and reports only the
problems that remain after its revision, until none remain. The original
result file is left untouched; the simplified critique is written to
`researcher/files/simplify/episode-N.md`.

Only the single simplification pass uses `LLM_MODEL_AGENT_LANGUAGE`. The
review/fix loop reuses `LLM_MODEL_AGENT_REVIEWER`. Both roles fall back to the
base `LLM_MODEL` when unset, like the other scripts in this repo.

Usage:
    python3 researcher/simplify.py 2
    python3 researcher/simplify.py 2 --verbose --max-rounds 2
    python3 researcher/simplify.py 2 --out /tmp/episode-2.simple.md
    python3 researcher/simplify.py 2 --run-id 20260922-101500-episode-2-language
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from trace import RunTrace

from agent import load_prompt, make_client, run_agent, strip_fences
from config import (
    LANGUAGE,
    PROMPTS_DIR,
    RESULT_DIR,
    REVIEWER,
    RUNS_DIR,
    SIMPLIFY_DIR,
    Settings,
    check_endpoint,
    load_settings,
)
from sources import SourceRegistry
from tools import Toolbox, TranscriptIndex
from util import display_path, print_usage
from validate import (
    CITE_MARKER_RE,
    HORIZONTAL_RULE_RE,
    Problem,
    repair_mechanical,
    split_body_parts,
    validate_critique,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simplify the Persian language of a finished episode critique."
    )
    parser.add_argument("episode", type=int, help="episode number to simplify (>= 1)")
    parser.add_argument(
        "--out",
        type=Path,
        help="output file (default: researcher/files/simplify/episode-N.md)",
    )
    parser.add_argument("--max-rounds", type=int, help="maximum reviewer/fixer passes")
    parser.add_argument(
        "--run-id",
        dest="run_id",
        metavar="RUN_ID",
        help="reuse an existing run directory under files/runs/",
    )
    parser.add_argument("--resume", dest="run_id", help=argparse.SUPPRESS)
    parser.add_argument(
        "--verbose", action="store_true", help="print every trace event"
    )
    return parser.parse_args(argv)


def read_result(n: int) -> str:
    """Read the cited critique from the researcher result directory."""
    path = RESULT_DIR / f"episode-{n}.md"
    if not path.exists():
        sys.exit(f"[error] missing input file: {path}")
    return path.read_text("utf-8")


def new_run_dir(episode: int, run_id: str | None) -> Path:
    """Create (or reuse) the language-run directory for this episode.

    `run_id` names an existing run directory under `files/runs/`; when absent,
    a fresh `<timestamp>-episode-<n>-language` directory is created. The
    timestamp format matches `main.py`; the suffix marks the run as the
    language-simplification stage.
    """
    if run_id:
        run_dir = RUNS_DIR / run_id
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        run_dir = RUNS_DIR / f"{stamp}-episode-{episode}-language"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def split_citations(text: str) -> tuple[str, str]:
    """Split a critique into (body, citations) at the horizontal rule.

    The citations section is returned verbatim so it can be rejoined unchanged.
    When no rule is present, the whole text is the body and citations is empty.
    """
    lines = text.splitlines()
    rules = [i for i, line in enumerate(lines) if HORIZONTAL_RULE_RE.match(line)]
    if not rules:
        return text.strip("\n"), ""
    rule = rules[-1]
    body = "\n".join(lines[:rule]).strip("\n")
    citations = "\n".join(lines[rule + 1 :]).strip("\n")
    return body, citations


def join_citations(body: str, citations: str) -> str:
    """Reassemble the simplified body with the untouched citations section."""
    body = body.strip("\n")
    if not citations.strip():
        return f"{body}\n\n"
    return f"{body}\n\n---\n\n{citations.strip()}\n\n"


def parse_review(raw: str) -> tuple[bool, list[str], str]:
    """Parse the reviewer's JSON verdict into (ok, problems, revised).

    Type-safe: no value from the model is allowed to crash the pipeline or
    corrupt the output. `ok` is read as a boolean only (the string "false"
    counts as `False`), `problems` is read as a list of strings, and `revised`
    is read as a non-empty string.
    """
    text = strip_fences(raw)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end < start:
        return False, ["reviewer response did not contain a JSON object"], ""
    try:
        payload = json.loads(text[start : end + 1], strict=False)
    except json.JSONDecodeError as exc:
        return False, [f"reviewer response was not valid JSON: {exc}"], ""
    if not isinstance(payload, dict):
        return False, ["reviewer response was not a JSON object"], ""

    ok_value = payload.get("ok")
    if isinstance(ok_value, str):
        ok = ok_value.strip().lower() == "true"
    elif isinstance(ok_value, bool):
        ok = ok_value
    else:
        ok = False

    problems_value = payload.get("problems")
    malformed = ["malformed problem list"]
    if problems_value is None:
        problems: list[str] = []
    elif isinstance(problems_value, str):
        problems = list(malformed)
    elif isinstance(problems_value, list):
        problems = [p for p in problems_value if isinstance(p, str) and p.strip()]
    else:
        problems = list(malformed)

    revised_value = payload.get("revised")
    revised = revised_value if isinstance(revised_value, str) else ""
    return ok, problems, revised.strip()


def part_citation_numbers(part: str) -> set[int]:
    """Return the set of unique citation numbers mentioned in a body part."""
    numbers: set[int] = set()
    for match in CITE_MARKER_RE.finditer(part):
        numbers.update(int(token.strip()) for token in match.group(1).split(","))
    return numbers


def _part_label(part: str, index: int) -> str:
    first = part.splitlines()[0] if part.strip() else ""
    if first.startswith("## "):
        return f"chapter {index} ({first})"
    return f"general assessment part {index}"


def citation_fidelity(candidate_body: str, reference_body: str) -> list[Problem]:
    """Mechanically check citation coverage per critique part.

    The simplifier is allowed to merge `[cite: N]` markers or move them
    slightly within a chapter, but must not drop a citation from a chapter or
    move it into another part. For each part (the general assessment and every
    chapter) the set of unique citation numbers must be identical before and
    after the simplification, so `[cite: 1] ... [cite: 4] ... [cite: 1,2,3]`
    matching `... [cite: 1,2,3,4]` is accepted for the same part.
    """
    reference_parts = split_body_parts(reference_body)
    candidate_parts = split_body_parts(candidate_body)
    if len(reference_parts) != len(candidate_parts):
        return [
            Problem(
                "citations",
                f"part count changed during simplification: original has "
                f"{len(reference_parts)} part(s), simplified has "
                f"{len(candidate_parts)}",
            )
        ]

    problems: list[Problem] = []
    for index, (original_part, simplified_part) in enumerate(
        zip(reference_parts, candidate_parts), start=1
    ):
        expected = part_citation_numbers(original_part)
        actual = part_citation_numbers(simplified_part)
        if expected == actual:
            continue
        problems.append(
            Problem(
                "citations",
                f"{_part_label(simplified_part, index)}: unique citation "
                f"coverage changed (missing={sorted(expected - actual) or 'none'}, "
                f"added={sorted(actual - expected) or 'none'})",
            )
        )
    return problems


def deterministic_problems(text: str, reference: str, has_citations: bool) -> list:
    """Run the structural/citation gates, skipping citation gates when absent."""
    problems = validate_critique(text, reference, None)
    if not has_citations:
        return [p for p in problems if p.code != "rule"]
    candidate_body, _ = split_citations(text)
    reference_body, _ = split_citations(reference)
    problems.extend(citation_fidelity(candidate_body, reference_body))
    return problems


def run_simplifier(client, settings: Settings, toolbox: Toolbox, body: str) -> str:
    """Run the single simplification pass on the citation-free body."""
    prompt = load_prompt(PROMPTS_DIR / "simplify.md")
    raw = run_agent(
        client,
        model=settings.model(LANGUAGE),
        agent="simplifier",
        system_prompt=prompt,
        user_message=body,
        toolbox=toolbox,
        tool_names=[],
        max_tool_calls=0,
        trace=toolbox.trace,
    )
    return strip_fences(raw)


def run_language_reviewer(
    client,
    settings: Settings,
    toolbox: Toolbox,
    original_body: str,
    candidate_body: str,
    problems: list,
    previous_problems: list | None = None,
) -> tuple[bool, list[str], str]:
    """Run one reviewer/fixer pass and return (ok, problems, revised body).

    `previous_problems` carries the problems reported by the previous round so
    the reviewer can re-verify only those items against the current candidate
    text instead of re-auditing from scratch. When it is empty, no re-verify
    section is added to the message.
    """
    prompt = load_prompt(PROMPTS_DIR / "simplify-reviewer.md")
    problem_block = "\n".join(f"- {p}" for p in problems) or "(none)"
    user_message = (
        f"# Original critique body\n\n{original_body}\n\n"
        f"# Simplified candidate body\n\n{candidate_body}\n\n"
        f"# Deterministic validation problems\n\n{problem_block}"
    )
    if previous_problems:
        reverify_block = "\n".join(f"- {p}" for p in previous_problems)
        user_message += (
            f"\n\n# Previously reported problems to re-verify\n\n{reverify_block}\n\n"
            "Check the current candidate text for these items. "
            "Report only the items that still appear in the text."
        )
    raw = run_agent(
        client,
        model=settings.model(REVIEWER),
        agent="language-reviewer",
        system_prompt=prompt,
        user_message=user_message,
        toolbox=toolbox,
        tool_names=[],
        max_tool_calls=0,
        trace=toolbox.trace,
    )
    return parse_review(raw)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.episode < 1:
        sys.exit("[error] episode number must be >= 1")

    settings = load_settings(max_language_rounds=args.max_rounds)
    original = read_result(args.episode)
    run_dir = new_run_dir(args.episode, args.run_id)
    trace = RunTrace(run_dir=run_dir, verbose=args.verbose)
    client = make_client(settings)

    print(f"[ok] run directory: {display_path(run_dir)}")
    print(
        f"[ok] models: language={settings.model(LANGUAGE)} "
        f"reviewer={settings.model(REVIEWER)}"
    )
    check_endpoint(settings)

    (run_dir / "original.md").write_text(original, "utf-8")
    body, citations = split_citations(original)
    has_citations = bool(citations.strip())
    if has_citations:
        (run_dir / "citations.md").write_text(f"{citations}\n", "utf-8")

    toolbox = Toolbox(
        settings,
        SourceRegistry(),
        trace,
        "simplifier",
        original,
        TranscriptIndex(""),
        run_dir,
    )

    simplified_body = run_simplifier(client, settings, toolbox, body)
    (run_dir / "simplified-body-0.md").write_text(
        f"{simplified_body.strip()}\n\n", "utf-8"
    )
    print("[ok] simplification pass complete; starting review loop")

    candidate_body = simplified_body
    accepted = False
    last_problems: list = []
    previous_remaining: list = []
    attempt = 0
    for attempt in range(settings.max_language_rounds + 1):
        candidate = repair_mechanical(
            join_citations(candidate_body, citations), renumber=False
        )
        det = deterministic_problems(candidate, original, has_citations)
        gate_text = f"round {attempt}: {len(det)} deterministic problem(s)"
        trace.log("gates", message=gate_text, problems=[str(p) for p in det])
        print(f"[ok] {gate_text}")

        ok, remaining, revised = run_language_reviewer(
            client, settings, toolbox, body, candidate_body, det, previous_remaining
        )
        changed = bool(revised.strip()) and revised.strip() != candidate_body.strip()
        if changed:
            candidate_body = revised
        final = repair_mechanical(
            join_citations(candidate_body, citations), renumber=False
        )
        final_det = deterministic_problems(final, original, has_citations)
        last_problems = [str(p) for p in final_det] + remaining
        previous_remaining = list(remaining)
        trace.log(
            "language_review",
            message=(
                f"round {attempt}: ok={ok}, {len(remaining)} remaining, "
                f"{len(final_det)} deterministic, changed={changed}"
            ),
            problems=last_problems,
        )

        if ok and not final_det:
            accepted = True
            print(f"[ok] review passed on round {attempt}")
            break
        if attempt == settings.max_language_rounds:
            print(f"[error] review still failing after {attempt} fix pass(es)")
            break
        if not changed:
            print(
                "[error] reviewer made no change and problems remain; cannot converge"
            )
            break
        (run_dir / f"review-{attempt + 1}.md").write_text(final, "utf-8")
        print(
            f"[ok] reviewer pass {attempt + 1} ({len(remaining)} remaining problem(s))"
        )

    out_path = args.out or (SIMPLIFY_DIR / f"episode-{args.episode}.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not accepted:
        final = repair_mechanical(
            join_citations(candidate_body, citations), renumber=False
        )
        final_problems = deterministic_problems(final, original, has_citations)
        failed_path = out_path.with_suffix(".failed.md")
        failed_path.write_text(final, "utf-8")
        for problem in final_problems or last_problems:
            print(f"[error] {problem}")
        trace.save()
        print(
            f"[error] result not written; last simplified body saved to "
            f"{display_path(failed_path)}"
        )
        return 1

    candidate = repair_mechanical(join_citations(candidate_body, citations))
    out_path.write_text(candidate, "utf-8")
    trace.save()
    print(f"[ok] wrote {display_path(out_path)}")
    print_usage(trace)
    return 0


if __name__ == "__main__":
    sys.exit(main())

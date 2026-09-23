#!/usr/bin/env python3
"""Agentic episode critique.

Reads `content/episode-N.md` and `processed/episode-N.md`, plans research
topics, runs parallel research subagents with real web tools, writes the cited
Persian critique, then runs a reviewer/fixer loop until the deterministic gates
pass. The result is written to `researcher/files/result/episode-N.md`.

Usage:
    python3 researcher/main.py 2
    python3 researcher/main.py 2 --verbose --max-review-rounds 2
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from trace import RunTrace

from agent import load_prompt, make_client, run_agent, strip_fences
from config import (
    CONTENT_DIR,
    LEAD,
    PLANNER,
    PROCESSED_DIR,
    PROMPTS_DIR,
    RESEARCH,
    RESULT_DIR,
    REVIEWER,
    RUNS_DIR,
    Settings,
    check_endpoint,
    load_settings,
)
from sources import SourceRegistry
from tools import (
    RESEARCH_TOOLS,
    REVIEWER_TOOLS,
    WRITER_TOOLS,
    Toolbox,
    TranscriptIndex,
)
from util import display_path, print_usage
from validate import cited_urls, extract_headings, repair_mechanical, validate_critique


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Agentically critique an episode with citations."
    )
    parser.add_argument("episode", type=int, help="episode number to critique (>= 1)")
    parser.add_argument(
        "--out",
        type=Path,
        help="output file (default: researcher/files/result/episode-N.md)",
    )
    parser.add_argument(
        "--max-topics", type=int, help="maximum number of research topics"
    )
    parser.add_argument(
        "--max-tool-calls", type=int, help="maximum tool calls per agent"
    )
    parser.add_argument(
        "--max-review-rounds", type=int, help="maximum reviewer/fixer passes"
    )
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


def read_episode(n: int) -> tuple[str, str]:
    """Read and return (content_text, transcript_text) for episode N."""
    content_path = CONTENT_DIR / f"episode-{n}.md"
    transcript_path = PROCESSED_DIR / f"episode-{n}.md"
    missing = [p for p in (content_path, transcript_path) if not p.exists()]
    if missing:
        sys.exit("[error] missing input file(s): " + ", ".join(str(p) for p in missing))
    return content_path.read_text("utf-8"), transcript_path.read_text("utf-8")


def new_run_dir(episode: int, run_id: str | None) -> Path:
    """Create (or reuse) the run directory for this episode.

    `run_id` names an existing run directory under `files/runs/`; when absent,
    a fresh `<timestamp>-episode-<n>` directory is created.
    """
    if run_id:
        run_dir = RUNS_DIR / run_id
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        run_dir = RUNS_DIR / f"{stamp}-episode-{episode}"
    (run_dir / "notes").mkdir(parents=True, exist_ok=True)
    return run_dir


def chapter_map(content_text: str, transcript_text: str) -> str:
    """Build the chapter list (timestamp + titles) for planner context."""
    content_heads = [(h[1]) for h in extract_headings(content_text) if h[0] == 2]
    transcript_heads = [(h[1]) for h in extract_headings(transcript_text) if h[0] == 2]
    lines = [f"content: {h}" for h in content_heads]
    lines += [f"transcript: {h}" for h in transcript_heads]
    return "\n".join(lines)


def parse_plan(raw: str, max_topics: int) -> dict:
    """Parse the planner JSON, falling back to a single general topic."""
    text = strip_fences(raw)
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        try:
            plan = json.loads(text[start : end + 1])
            topics = [
                t for t in plan.get("topics", []) if isinstance(t, dict) and t.get("id")
            ]
            if topics:
                plan["topics"] = topics[:max_topics]
                return plan
        except json.JSONDecodeError:
            pass
    return {
        "topics": [
            {
                "id": "general",
                "description": "General fact-check of the post's main claims",
                "chapters": [],
                "queries": [],
            }
        ],
        "coverage": {},
        "_fallback": True,
    }


TOPIC_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
CHAPTER_STAMP_RE = re.compile(r"^##\s+(\d{1,2}:\d{2})\s*-")


def _normalize_stamp(ts: str) -> str:
    """Canonicalize a `m:ss` timestamp for coverage comparison."""
    ts = ts.strip()
    if ":" not in ts:
        return ts
    minute, _, second = ts.partition(":")
    try:
        return f"{int(minute)}:{int(second):02d}"
    except ValueError:
        return ts


def ensure_plan_coverage(plan: dict, content_text: str, trace: RunTrace) -> None:
    """Ensure every content chapter is covered by a topic and ids are safe.

    When a content chapter timestamp appears in no topic's `chapters` list,
    the uncovered timestamps are appended to a `general` topic (created when
    missing). Topic ids that would be unsafe in an agent name or file name are
    renamed to `topic-{i}`. The fallback plan is left untouched. The plan is
    mutated in place.
    """
    if plan.get("_fallback"):
        return
    content_stamps: list[str] = []
    for raw in (h[1] for h in extract_headings(content_text) if h[0] == 2):
        match = CHAPTER_STAMP_RE.match(raw)
        if match:
            content_stamps.append(match.group(1))
    covered: set[str] = set()
    for topic in plan.get("topics", []):
        for chapter in topic.get("chapters", []):
            covered.add(_normalize_stamp(str(chapter)))

    seen: set[str] = set()
    uncovered = [
        stamp
        for stamp in content_stamps
        if _normalize_stamp(stamp) not in covered
        and not (stamp in seen or seen.add(stamp))
    ]
    if uncovered:
        general = next(
            (t for t in plan.get("topics", []) if t.get("id") == "general"), None
        )
        if general is None:
            general = {
                "id": "general",
                "description": "Fact-check the claims in the uncovered chapters",
                "chapters": [],
                "queries": [],
            }
            plan.setdefault("topics", []).append(general)
        for stamp in uncovered:
            if stamp not in general["chapters"]:
                general["chapters"].append(stamp)
        trace.log(
            "plan",
            message="uncovered chapters added to the general topic",
            chapters=uncovered,
        )
        print(f"[warn] chapters without a research topic: {', '.join(uncovered)}")

    for i, topic in enumerate(plan.get("topics", []), start=1):
        if not TOPIC_ID_RE.fullmatch(topic.get("id", "")):
            old = topic["id"]
            topic["id"] = f"topic-{i}"
            trace.log(
                "plan",
                message=f"renamed topic id {old!r} to {topic['id']!r}",
            )


def run_planner(
    client,
    settings: Settings,
    toolbox: Toolbox,
    content_text: str,
    transcript_text: str,
    run_dir: Path,
) -> dict:
    """Run the planner agent and persist its plan."""
    prompt = load_prompt(PROMPTS_DIR / "planner.md").replace(
        "{max_topics}", str(settings.max_topics)
    )
    user_message = f"# Persian blog post\n\n{content_text}\n\n# Chapters\n\n{chapter_map(content_text, transcript_text)}"
    raw = run_agent(
        client,
        model=settings.model(PLANNER),
        agent="planner",
        system_prompt=prompt,
        user_message=user_message,
        toolbox=toolbox,
        tool_names=[],
        max_tool_calls=0,
        trace=toolbox.trace,
    )
    plan = parse_plan(raw, settings.max_topics)
    ensure_plan_coverage(plan, content_text, toolbox.trace)
    (run_dir / "plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )
    return plan


def run_research(
    client,
    settings: Settings,
    topics: list[dict],
    transcript: TranscriptIndex,
    registry,
    trace,
    notes_dir,
    content_text,
) -> list[dict]:
    """Run one research subagent per topic concurrently and collect their notes."""

    def one(topic: dict) -> dict:
        toolbox = Toolbox(
            settings=settings,
            registry=registry,
            trace=trace,
            agent=f"research:{topic['id']}",
            content_text=content_text,
            transcript=transcript,
            notes_dir=notes_dir,
        )
        prompt = (PROMPTS_DIR / "researcher.md").read_text("utf-8").strip()
        chapters = ", ".join(topic.get("chapters", [])) or "(all)"
        queries = (
            "\n".join(f"- {q}" for q in topic.get("queries", [])) or "(derive your own)"
        )
        user_message = (
            f"# Research topic: {topic['id']}\n\n{topic.get('description', '')}\n\n"
            f"Relevant chapter timestamps: {chapters}\n\nSuggested queries:\n{queries}\n\n"
            f"# English transcript chapters\n\n{_topic_transcript(transcript, topic)}"
        )
        try:
            notes = run_agent(
                client,
                model=settings.model(RESEARCH),
                agent=f"research:{topic['id']}",
                system_prompt=prompt,
                user_message=user_message,
                toolbox=toolbox,
                tool_names=RESEARCH_TOOLS,
                max_tool_calls=settings.max_tool_calls,
                trace=trace,
            )
            return {"id": topic["id"], "ok": True, "notes": strip_fences(notes)}
        except Exception as exc:  # noqa: BLE001
            trace.log(
                "research_failed", agent=f"research:{topic['id']}", error=str(exc)
            )
            return {
                "id": topic["id"],
                "ok": False,
                "notes": f"(research failed: {exc})",
            }

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=min(4, max(1, len(topics)))) as pool:
        futures = {pool.submit(one, topic): topic for topic in topics}
        for future in as_completed(futures):
            results.append(future.result())
    order = {topic["id"]: i for i, topic in enumerate(topics)}
    results.sort(key=lambda item: order.get(item["id"], 0))
    for item in results:
        (notes_dir / f"{item['id']}.notes.md").write_text(item["notes"] + "\n", "utf-8")
    return results


def _topic_transcript(transcript: TranscriptIndex, topic: dict) -> str:
    """Return the transcript chapters relevant to a topic.

    The block is capped at `TOPIC_TRANSCRIPT_MAX_CHARS`; truncation always
    happens on a chapter boundary and a closing note marks the cut.
    """
    chapters = []
    for timestamp in topic.get("chapters", []):
        chapters.extend(transcript.find(str(timestamp), limit=1))
    if not chapters:
        chapters = transcript.chapters
    seen: set[str] = set()
    blocks: list[str] = []
    for chapter in chapters:
        if chapter.timestamp in seen:
            continue
        seen.add(chapter.timestamp)
        blocks.append(f"## {chapter.timestamp} - {chapter.title}\n\n{chapter.body}")
    if (
        sum(len(block) for block in blocks) + 2 * (len(blocks) - 1)
        <= TOPIC_TRANSCRIPT_MAX_CHARS
    ):
        return "\n\n".join(blocks)

    kept: list[str] = []
    length = 0
    for block in blocks:
        cost = len(block) + (2 if kept else 0)
        if length and length + cost > TOPIC_TRANSCRIPT_MAX_CHARS:
            break
        kept.append(block)
        length += cost
    kept.append(
        "(transcript excerpt truncated to the research prompt budget; "
        "use read_transcript to fetch a specific chapter)"
    )
    return "\n\n".join(kept)


TOPIC_TRANSCRIPT_MAX_CHARS = 10000


def compile_notes(notes_dir: Path, results: list[dict]) -> str:
    """Combine subagent notes into a single block for the writer.

    For each topic, the notes are taken from the `note_write` scratch file
    (`notes/{topic_id}.md`) when it exists, falling back to the agent's final
    reply (`notes/{topic_id}.notes.md`) and finally to the returned value.
    """
    blocks: list[str] = []
    for item in results:
        if item["ok"]:
            scratch = notes_dir / f"{item['id']}.md"
            if scratch.exists():
                block = scratch.read_text("utf-8").strip()
            else:
                reply = notes_dir / f"{item['id']}.notes.md"
                block = (
                    reply.read_text("utf-8").strip()
                    if reply.exists()
                    else item["notes"]
                )
        else:
            block = f"(topic {item['id']} could not be researched: {item['notes']})"
        blocks.append(f"## Notes for topic: {item['id']}\n\n{block}")
    return "\n\n".join(blocks) if blocks else "(no research notes)"


def run_writer(
    client, settings: Settings, toolbox: Toolbox, content_text, transcript_text, notes
) -> str:
    """Run the lead writer agent and return the draft critique."""
    prompt = load_prompt(PROMPTS_DIR / "writer.md")
    user_message = (
        f"# Persian blog post\n\n{content_text}\n\n"
        f"# English transcript\n\n{transcript_text}\n\n"
        f"# Research notes\n\n{notes}"
    )
    raw = run_agent(
        client,
        model=settings.model(LEAD),
        agent="writer",
        system_prompt=prompt,
        user_message=user_message,
        toolbox=toolbox,
        tool_names=WRITER_TOOLS,
        max_tool_calls=settings.max_tool_calls,
        trace=toolbox.trace,
    )
    return f"{strip_fences(raw)}\n\n"


def run_reviewer(
    client,
    settings: Settings,
    toolbox: Toolbox,
    draft,
    content_text,
    transcript_text,
    notes,
    problems,
) -> str:
    """Run one reviewer/fixer pass and return the corrected critique."""
    prompt = load_prompt(PROMPTS_DIR / "reviewer.md")
    problem_block = "\n".join(f"- {p}" for p in problems) or "(none)"
    user_message = (
        f"# Draft critique\n\n{draft}\n\n"
        f"# Persian blog post\n\n{content_text}\n\n"
        f"# English transcript\n\n{transcript_text}\n\n"
        f"# Research notes\n\n{notes}\n\n"
        f"# Deterministic validation problems\n\n{problem_block}"
    )
    raw = run_agent(
        client,
        model=settings.model(REVIEWER),
        agent="reviewer",
        system_prompt=prompt,
        user_message=user_message,
        toolbox=toolbox,
        tool_names=REVIEWER_TOOLS,
        max_tool_calls=settings.max_tool_calls,
        trace=toolbox.trace,
    )
    return f"{strip_fences(raw)}\n\n"


def check_liveness(toolbox: Toolbox, text: str) -> None:
    """Run an HTTP liveness check on every cited URL, recording results."""
    for url in cited_urls(text):
        toolbox.trace.log(
            "tool_call",
            agent=toolbox.agent,
            message="url_alive",
            arguments={"url": url},
        )
        result = toolbox.url_alive(url)
        toolbox.trace.log(
            "tool_result",
            agent=toolbox.agent,
            message="url_alive",
            chars=len(str(result)),
            ok=result.get("ok"),
            status=result.get("status"),
        )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.episode < 1:
        sys.exit("[error] episode number must be >= 1")

    settings = load_settings(
        max_topics=args.max_topics,
        max_tool_calls=args.max_tool_calls,
        max_review_rounds=args.max_review_rounds,
    )
    content_text, transcript_text = read_episode(args.episode)
    run_dir = new_run_dir(args.episode, args.run_id)
    trace = RunTrace(run_dir=run_dir, verbose=args.verbose)
    registry = SourceRegistry()
    transcript = TranscriptIndex(transcript_text)
    notes_dir = run_dir / "notes"
    client = make_client(settings)

    print(f"[ok] run directory: {display_path(run_dir)}")
    print(
        f"[ok] models: planner={settings.model(PLANNER)} lead={settings.model(LEAD)} "
        f"research={settings.model(RESEARCH)} reviewer={settings.model(REVIEWER)}"
    )
    check_endpoint(settings)

    planner_toolbox = Toolbox(
        settings, registry, trace, "planner", content_text, transcript, notes_dir
    )
    plan = run_planner(
        client, settings, planner_toolbox, content_text, transcript_text, run_dir
    )
    topics = plan["topics"]
    trace.log(
        "plan", message=f"{len(topics)} topic(s)", topics=[t["id"] for t in topics]
    )
    print(f"[ok] planned {len(topics)} research topic(s)")

    results = run_research(
        client, settings, topics, transcript, registry, trace, notes_dir, content_text
    )
    failed = [r["id"] for r in results if not r["ok"]]
    if failed:
        print(f"[warn] topics without notes: {', '.join(failed)}")
    notes = compile_notes(notes_dir, results)
    registry.save(run_dir / "sources.json")

    writer_toolbox = Toolbox(
        settings, registry, trace, "writer", content_text, transcript, notes_dir
    )
    draft = run_writer(
        client, settings, writer_toolbox, content_text, transcript_text, notes
    )
    (run_dir / "draft.md").write_text(draft, "utf-8")
    print("[ok] wrote draft; starting review loop")

    current = draft
    for attempt in range(settings.max_review_rounds + 1):
        current = repair_mechanical(current)
        problems = validate_critique(current, content_text, registry)
        trace.log(
            "gates",
            message=f"round {attempt}: {len(problems)} problem(s)",
            problems=[str(p) for p in problems],
        )
        if not problems:
            print(f"[ok] gates passed on round {attempt}")
            break
        if attempt == settings.max_review_rounds:
            print(f"[error] gates still failing after {attempt} reviewer pass(es)")
            break
        print(f"[ok] reviewer pass {attempt + 1} ({len(problems)} problem(s))")
        reviewer_toolbox = Toolbox(
            settings, registry, trace, "reviewer", content_text, transcript, notes_dir
        )
        current = run_reviewer(
            client,
            settings,
            reviewer_toolbox,
            current,
            content_text,
            transcript_text,
            notes,
            problems,
        )
        (run_dir / f"review-{attempt + 1}.md").write_text(current, "utf-8")

    check_liveness(writer_toolbox, current)
    registry.save(run_dir / "sources.json")
    final_problems = validate_critique(
        current, content_text, registry, require_alive=True
    )
    trace.log(
        "final_gates",
        message=f"{len(final_problems)} problem(s)",
        problems=[str(p) for p in final_problems],
    )

    out_path = args.out or (RESULT_DIR / f"episode-{args.episode}.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if final_problems:
        failed_path = out_path.with_suffix(".failed.md")
        failed_path.write_text(current, "utf-8")
        for problem in final_problems:
            print(f"[error] {problem}")
        trace.save()
        print(
            f"[error] result not written; last draft saved to {display_path(failed_path)}"
        )
        return 1

    out_path.write_text(current, "utf-8")
    trace.save()
    print(f"[ok] wrote {display_path(out_path)}")
    print_usage(trace)
    return 0


if __name__ == "__main__":
    sys.exit(main())

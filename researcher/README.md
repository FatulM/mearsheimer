# researcher

An agentic version of the episode critique pipeline. It reads a Persian episode post and its English transcript, plans research topics, runs parallel research subagents that search and fetch real web sources, writes the cited Persian critique in the `critique/episode-N-cite.md` format, then a reviewer/fixer agent fact-checks and repairs it until deterministic gates pass.

Unlike `scripts/critique_content_cite.py`, which makes a single call and hopes the endpoint runs its hosted `web_search`, this app does its own client-side tool calling and keeps a provenance registry of every URL it actually retrieved. A citation it cannot trace back to that registry is rejected.

See `DESIGN.md` for the full design.

## Requirements

- Python 3.12 virtualenv at the repo root (`.venv`).
- `pip install -r requirements.txt` from the repo root (adds `ddgs`, `beautifulsoup4`, `lxml`, `tenacity`, and optional `trafilatura`, `pypdf`).
- The shared `.env` with `LLM_BASE_URL` and `LLM_API_KEY`.

## Configuration

Model roles come from `.env`, each falling back to the base `LLM_MODEL` when unset:

```
LLM_MODEL_AGENT_PLANNER=deepseek-v4.1-flash
LLM_MODEL_AGENT_LEAD=deepseek-v4.1-flash
LLM_MODEL_AGENT_RESEARCH=deepseek-v4.1-flash
LLM_MODEL_AGENT_REVIEWER=deepseek-v4.1-flash
LLM_MODEL_AGENT_LANGUAGE=gemini-3.8-flash
```

Optional tuning knobs (with defaults):

```
RESEARCHER_MAX_TOPICS=8
RESEARCHER_MAX_TOOL_CALLS=25
RESEARCHER_MAX_REVIEW_ROUNDS=3
RESEARCHER_LANGUAGE_MAX_ROUNDS=3
RESEARCHER_REQUEST_TIMEOUT=120
```

No search API key is needed: `web_search` uses DuckDuckGo via `ddgs` (default metacrawl, retried on transient network errors).

## Usage

```bash
source .venv/bin/activate
python3 researcher/main.py 2
python3 researcher/main.py 2 --verbose --max-review-rounds 2
python3 researcher/main.py 2 --out /tmp/episode-2.md
python3 researcher/main.py 2 --run-id 20260921-101500-episode-2
```

Inputs are `content/episode-N.md` (the Persian post) and `processed/episode-N.md` (the English transcript), both for episode `N >= 1`. The default output is `researcher/files/result/episode-N.md`.

## Pipeline

1. **Intake** — read the post and transcript, parse chapter headings.
2. **Planner** (`LLM_MODEL_AGENT_PLANNER`) — extract thematic research topics and a chapter coverage map, written to `plan.json`.
3. **Research subagents** (`LLM_MODEL_AGENT_RESEARCH`) — one agent per topic, run concurrently, each with `web_search`, `fetch_url`, `url_alive`, `read_transcript`, and `note_write`. Notes are saved under the run directory.
4. **Writer** (`LLM_MODEL_AGENT_LEAD`) — compose the full cited critique from the post, transcript, and notes.
5. **Reviewer/fixer** (`LLM_MODEL_AGENT_REVIEWER`) — fact-check and repair the draft, iterating until the deterministic gates pass.
6. **Mechanical repair + gates** — `repair_mechanical` applies safe deterministic fixes, then pure-Python gates decide whether to write the result.

## Tools

| Tool | Purpose |
|---|---|
| `web_search` | DuckDuckGo metacrawl search (retried on transient network errors); registers every returned URL |
| `fetch_url` | Fetch and extract main text from HTML or PDF; registers provenance |
| `url_alive` | HTTP liveness check (bot-block statuses count as reachable) |
| `read_transcript` | Look up transcript chapters by timestamp or title |
| `note_write` | Persist research notes under a topic id |
| `validate` | Run the deterministic gates on a draft |

## Deterministic gates

The result is written only when every gate passes:

- one H1, byte-identical to the source content;
- every `## {mm:ss} - {TITLE}` heading byte-identical, in order, with none dropped;
- blank line after every heading, exactly one `---` before the citations, file ends with a blank line;
- every `[cite: N]` maps to an entry; every entry is referenced; entries numbered sequentially in first-reference order;
- every chapter that presents research findings carries at least one `[cite: N]` marker; a chapter with no verifiable claims passes only when it uses the no-claims exemption phrase;
- every cited URL was actually fetched with `fetch_url` during the run (so its content was retrieved), was reachable, and passed the liveness check;
- no bracketed markers other than `[cite: N]`.

Before every gate check, `repair_mechanical` applies safe deterministic fixes — blank lines after headings, citation entries renumbered into first-reference order (when the mapping is bijective), and a trailing blank line. Anything that cannot be fixed safely is left for the reviewer.

If the reviewer cannot satisfy the gates within `RESEARCHER_MAX_REVIEW_ROUNDS`, the run exits non-zero and writes the last draft to `files/result/episode-N.failed.md` instead of a false success.

## Outputs

```
researcher/files/
├── result/episode-N.md            # the critique (or episode-N.failed.md)
└── runs/<timestamp>-episode-N/
    ├── trace.json                 # every agent step, tool call, and token usage
    ├── plan.json                  # topics and coverage map
    ├── notes/<topic>.md           # subagent notes
    ├── draft.md                   # writer output before review
    ├── review-<k>.md              # reviewer pass k (draft.md is the pre-review output)
    └── sources.json               # provenance registry
```

## Language simplification (`simplify.py`)

`python3 researcher/simplify.py N [--verbose] [--max-rounds K] [--out PATH] [--run-id RUN_ID]` is a separate, second-stage pass that runs after `main.py`. It makes the finished Persian critique easier to read without changing what it says.

It reads the cited critique from `researcher/files/result/episode-N.md`. The original file is never modified. It splits the critique at the horizontal rule, keeps the citations section aside verbatim, and rewrites only the body once with `LLM_MODEL_AGENT_LANGUAGE` — the Persian-writing model (for example `gemini-3.8-flash`). A reviewer/fixer loop (`LLM_MODEL_AGENT_REVIEWER`) then compares the original body with the simplified body and repairs every fidelity problem it finds: dropped, added, or altered claims, numbers, names, and verdicts; changed headings; and changed `[cite: N]` markers. It reports only the problems that remain after its own revision, and it accepts a faithful wording change without flagging it. Each round after the first carries the previous round's remaining problems back to the reviewer as a re-verify list, so it checks only the items that still appear in the current candidate text instead of re-auditing from scratch. The corrected body is always kept, so a fix is never discarded. The reviewer loop keeps the `ok: true` veto: the result is written only when the reviewer reports `ok: true`, the deterministic gates pass, the reviewer can no longer change the text, or `RESEARCHER_LANGUAGE_MAX_ROUNDS` passes are used.

One simplification pass only. The reviewer fixes the simplified text; it never re-simplifies it. Deterministic gates run before every reviewer pass and before the write: heading parity with the original result, structure, one `---`, citation self-consistency, and per-part citation coverage. Before the gates run, markers are mechanically normalized: numbers inside each `[cite: N]` marker are sorted ascending, and adjacent markers such as `[cite: 1] [cite: 2]` are merged into `[cite: 1,2]`. For each part (the overall assessment and every chapter) the set of unique citation numbers must then match the original, so the simplified text may merge or slightly move markers inside a chapter, but a citation dropped from a chapter or moved into another chapter fails the run. A broken structure is never written as a success.

The simplified critique goes to `researcher/files/simplify/episode-N.md`. If the loop cannot reach a clean state, the run exits non-zero and writes `researcher/files/simplify/episode-N.failed.md` instead.

Per-run artifacts go under `researcher/files/runs/<timestamp>-episode-N-language/`:

```
researcher/files/runs/<timestamp>-episode-N-language/
├── trace.json                 # every agent step and token usage
├── original.md                # the input critique, kept intact
├── citations.md               # the stripped citations section (verbatim)
├── simplified-body-0.md       # the single simplification pass
└── review-<k>.md              # reviewer-corrected body after fix pass k
```

```bash
source .venv/bin/activate
python3 researcher/simplify.py 2
python3 researcher/simplify.py 2 --verbose --max-rounds 2
python3 researcher/simplify.py 2 --out /tmp/episode-2.simple.md
python3 researcher/simplify.py 2 --run-id 20260922-101500-episode-2-language
```

## Validating the deterministic gates standalone

```bash
python3 researcher/validate.py critique/episode-2-cite.md content/episode-2.md
```

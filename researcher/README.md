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
```

Optional tuning knobs (with defaults):

```
RESEARCHER_MAX_TOPICS=8
RESEARCHER_MAX_TOOL_CALLS=25
RESEARCHER_MAX_REVIEW_ROUNDS=3
RESEARCHER_REQUEST_TIMEOUT=120
```

No search API key is needed: `web_search` uses DuckDuckGo via `ddgs`.

## Usage

```bash
source .venv/bin/activate
python3 researcher/main.py 2
python3 researcher/main.py 2 --verbose --max-review-rounds 2
python3 researcher/main.py 2 --out /tmp/episode-2.md
python3 researcher/main.py 2 --resume 20260921-101500-episode-2
```

Inputs are `content/episode-N.md` (the Persian post) and `processed/episode-N.md` (the English transcript), both for episode `N >= 1`. The default output is `researcher/files/result/episode-N.md`.

## Pipeline

1. **Intake** — read the post and transcript, parse chapter headings.
2. **Planner** (`LLM_MODEL_AGENT_PLANNER`) — extract thematic research topics and a chapter coverage map, written to `plan.json`.
3. **Research subagents** (`LLM_MODEL_AGENT_RESEARCH`) — one agent per topic, run concurrently, each with `web_search`, `fetch_url`, `url_alive`, `read_transcript`, and `note_write`. Notes are saved under the run directory.
4. **Writer** (`LLM_MODEL_AGENT_LEAD`) — compose the full cited critique from the post, transcript, and notes.
5. **Reviewer/fixer** (`LLM_MODEL_AGENT_REVIEWER`) — fact-check and repair the draft, iterating until the deterministic gates pass.
6. **Gates** — pure-Python checks decide whether to write the result.

## Tools

| Tool | Purpose |
|---|---|
| `web_search` | DuckDuckGo search; registers every returned URL |
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
- every cited URL was actually retrieved during the run (provenance) and is reachable (liveness);
- no bracketed markers other than `[cite: N]`.

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
    ├── review-<k>.md              # each reviewer pass
    └── sources.json               # provenance registry
```

## Validating the deterministic gates standalone

```bash
python3 researcher/validate.py critique/episode-2-cite.md content/episode-2.md
```

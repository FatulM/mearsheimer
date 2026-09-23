# researcher — Agentic Episode Critique (Design)

A small agentic application that replaces the one-shot `critique_content_cite.py` flow with a real tool-using agents pipeline. It reads an episode's Persian post and English transcript, researches the web with client-side tools, writes the cited Persian critique in the exact `critique/episode-N-cite.md` format, then a reviewer agent fact-checks and repairs that critique before it is written out.

It reuses the existing `.env` (`LLM_BASE_URL`, `LLM_API_KEY`) and the output contract of `prompts/research-critique-full-cite.md` (Persian body, verbatim chapter headings, `[cite: N]` markers, numbered URL list).

## Why this exists

The current scripts call a model once with a hosted `web_search` tool and hope for the best. Probing showed that on `deepseek-v4.1-flash` native function calling works, but the hosted `web_search` tool is silently ignored (`usage.tools: None`, no URL annotations). So the old pipeline is effectively un-grounded. This app does its own search, keeps a provenance registry of every source it actually retrieved, and refuses to emit citations that were not actually visited.

## Decisions (locked)

| Area | Decision |
|---|---|
| Framework | Custom `openai` SDK loop — no orchestration dependency |
| Tools | Client-side function calling (native `tool_calls`) |
| Search backend | DuckDuckGo via `ddgs` (no API key) |
| Topology | Lead ReAct agent + parallel topic-research subagents + reviewer/fixer |
| Scope | Whole document at once; topics are extracted, not one subagent per chapter |
| Input | `content/episode-N.md` + `processed/episode-N.md` (content + transcript) |
| Output | `researcher/files/result/episode-N.md` |
| Validation | Strict + self-repair loop (deterministic gates must pass) |
| Observability | Per-run trace file + verbose logging |

## Pipeline

```
content/episode-N.md ─┐
processed/episode-N.md ┴─> [1] Intake/parse
                              │
                              v
                        [2] Planner agent  -> research plan (topics + target chapters)
                              │
                              v
                        [3] Research subagents (parallel, one per topic)
                              │   tools: web_search, fetch_url, url_alive, read_transcript, notes
                              v
                        [4] Lead ReAct agent (writer, tools optional) -> full draft critique
                              │
                              v
                        [5] Reviewer/fixer agent
                              │   tools: web_search, fetch_url, url_alive, validator, notes
                              v
                        [6] Mechanical repair + deterministic gates -> pass? write result
                                                                    no -> loop 5 (max K) -> fail loudly
```

### [1] Intake / parse

Read content and transcript. Split both into H1 + ordered `## {mm:ss} - {TITLE}` chapters. These chapter headings are the immutable skeleton the final output must reproduce byte-for-byte.

### [2] Planner agent (`LLM_MODEL_AGENT_PLANNER`)

Content-only, no tools. Produces a JSON research plan: a list of topics, each with a stable id, a short English description, the chapter timestamps it bears on, and search seed queries. Topics are thematic (e.g. "2025 Israel–Iran war timeline", "Strait of Hormuz shipping", "US ground-invasion feasibility"), so tiny/transitional chapters do not get a dedicated agent; every chapter is covered by at least one topic, and the planner must emit a coverage map.

### [3] Research subagents (`LLM_MODEL_AGENT_RESEARCH`)

One per topic, run concurrently under a bounded worker pool. Each is a ReAct agent with tools `web_search`, `fetch_url`, `url_alive`, `read_transcript`, and `note_write`. It returns structured notes: claims checked, findings, quotes, and candidate sources (URL + title + outlet). Every returned URL is registered in the run's **source registry** with how it was obtained (`search` vs `fetch`). Notes are persisted under the run directory so the writer can reuse them.

### [4] Lead ReAct agent / writer (`LLM_MODEL_AGENT_LEAD`)

Receives the post, the transcript, the plan, and all subagent notes. May call `web_search`/`fetch_url` itself to fill gaps. Emits the full critique following the exact output contract (adapted from `research-critique-full-cite.md`, kept locally as `researcher/prompts/writer.md`): Persian body, verbatim chapter headings, overall assessment before the first chapter, `[cite: N]` markers, and a single trailing `---` citations list. It may only cite URLs present in the source registry.

### [5] Reviewer / fixer agent (`LLM_MODEL_AGENT_REVIEWER`)

Two jobs in one loop:

1. **Fact-check the critique** against the transcript and fresh web research: verify claims, catch misattributions, fix incorrect Persian text, drop unsupported assertions.
2. **Repair the document** until the deterministic gates pass (see below).

The reviewer is the only agent allowed to rewrite body text after the draft. Each iteration returns the full corrected document (no commentary), which the deterministic gates then re-check.

### [6] Deterministic gates (`researcher/validate.py`)

Pure-Python checks, no LLM, mirroring and extending `scripts/check_critiques.py`:

- one H1, byte-identical to the content's H1;
- `## {mm:ss} - {TITLE}` headings count, order, and text byte-identical to `content/episode-N.md`;
- blank line after every heading; no stray horizontal rules; exactly one `---` immediately before the citations list; file ends with a blank line;
- every `[cite: N]` maps to an entry; every entry is referenced; numbering is sequential in first-reference order;
- every chapter that presents research findings carries at least one `[cite: N]` marker; a chapter with no verifiable claims passes only when it contains the no-claims exemption phrase;
- every cited URL was actually fetched with `fetch_url` during the run (the strict provenance gate requires `fetched` and `alive is not False`), and is not known dead (network failures and bot-block responses are treated as unknown, not dead, so real sources behind bot walls are not rejected);
- body contains only `[cite: N]` brackets (no `[47†L25-L32]`-style artifacts), timestamps use ASCII digits, body uses Persian numerals otherwise.

Gates run deterministically after every reviewer iteration. Before each gate check, `repair_mechanical` (in `validate.py`) applies safe deterministic fixes: blank lines after headings, citation entries renumbered into first-reference order (only when the mapping is bijective, so it can never mislabel a cite), and a trailing blank line. Fixes that can't be guaranteed safe (e.g. em-dash format parsing) are deliberately left to the reviewer, so the repair layer never corrupts an ambiguous document. The result is written only when all gates pass. If the reviewer cannot reach a passing state within `RESEARCHER_MAX_REVIEW_ROUNDS`, the run exits non-zero and writes the last draft to `files/result/episode-N.failed.md` (never a false "success"). The simplify stage calls `repair_mechanical` with `renumber=False`: citations are never renumbered there, because the citations section must return byte-for-byte from the original result.

## Language simplification pass (`researcher/simplify.py`)

A separate, second-stage app for language quality. The critique pipeline's models are good at agentic research, but they are not strong Persian writers. This stage makes the finished critique easier to read for Iranian readers without changing what it says.

It runs `python3 researcher/simplify.py N` on the finished `researcher/files/result/episode-N.md` and does not touch that file. It splits the critique at the horizontal rule and keeps the citations section aside, verbatim. It then rewrites the body once with `LLM_MODEL_AGENT_LANGUAGE`, the dedicated Persian-writing model chosen for native-like phrasing.

The body is the only text sent to the language model. The citations section is removed first to cut cost and to keep URLs, titles, and numbering out of the model's hands; it is joined back byte-for-byte. The simplification prompt keeps the H1 title and every `## {mm:ss} - {TITLE}` heading byte-identical, keeps every citation number inside its chapter (adjacent `[cite: N]` markers may merge into one), and changes only the wording. It is a simplification pass, not a summary: no claim, judgement, number, or name is dropped, added, or altered.

After the single simplification pass, a reviewer/fixer loop runs. The reviewer (`LLM_MODEL_AGENT_REVIEWER`, no web tools) compares the original body with the simplified body and returns a JSON verdict: `{"ok": bool, "problems": [...], "revised": "<body>"}`. It makes minimal edits, never re-simplifies, and treats a faithful wording change as correct. The `problems` list holds only the problems that remain after its revision, so a fully repaired body returns `ok: true` with an empty list. Each round after the first carries the previous round's remaining problems back to the reviewer as a `# Previously reported problems to re-verify` section, so the reviewer checks only the items that still appear in the current candidate text instead of re-auditing the whole body from scratch; this keeps the loop from restating the same wording differences forever. The acceptance rule keeps the `ok: true` veto: the result is written only when `ok` is `true` and the deterministic gates pass. The corrected body is always adopted, so a fix is never discarded. Deterministic gates run before every reviewer pass and before the write, so structure and citation self-consistency are enforced alongside the model verdict. The citations section is never renumbered in simplify mode — it is stripped, held aside byte-for-byte, and joined back unchanged. Before the gates run, markers are mechanically normalized: numbers inside each `[cite: N]` marker are sorted ascending, and adjacent markers such as `[cite: 1] [cite: 2]` are merged into `[cite: 1,2]`. One gate then compares, per body part (the overall assessment and each chapter), the set of unique citation numbers of the simplified body with the original. The simplification may merge or slightly move markers inside a chapter, but a citation dropped from a chapter or moved into another chapter fails the gate even when the citations list stays self-consistent.

One simplification pass only. The output is `researcher/files/simplify/episode-N.md`; on failure it is `episode-N.failed.md` and the run exits non-zero. Per-run artifacts go under `researcher/files/runs/<timestamp>-episode-N-language/` (`trace.json`, `original.md`, `citations.md`, `simplified-body-0.md`, `review-<k>.md`), using the same timestamp format and run layout as `main.py`.

## Tools (`researcher/tools.py`)

| Tool | Backend | Returns |
|---|---|---|
| `web_search(query, max_results)` | `ddgs` default metacrawl, 3 attempts with backoff on transient failures | `[{title, url, snippet}]` |
| `fetch_url(url)` | `requests` + `trafilatura` for HTML, `pypdf` for PDF | cleaned `{url, title, text}` (truncated) |
| `url_alive(url)` | `requests` GET | `{url, status, ok}` (ok `null` = unknown) |
| `read_transcript(chapter_or_query)` | `processed/episode-N.md` | matching chapter text |
| `note_write(topic_id, content)` | run scratchpad | path + ack |
| `validate(markdown)` | `validate.py` | structured problem list |

Every invocation is appended to the trace with arguments, latency, and outcome. `web_search` and `fetch_url` register their URLs in the source registry.

## Configuration (`.env`)

Added (each falls back to `LLM_MODEL` when unset, per AGENTS.md precedent):

```
LLM_MODEL_AGENT_PLANNER=<model>
LLM_MODEL_AGENT_LEAD=<model>       # lead / writer
LLM_MODEL_AGENT_RESEARCH=<model>   # topic subagents
LLM_MODEL_AGENT_REVIEWER=<model>
LLM_MODEL_AGENT_LANGUAGE=<model>   # Persian-writing model for simplify.py
```

Existing `LLM_BASE_URL` and `LLM_API_KEY` are reused. No search API key is needed (DuckDuckGo). Optional tuning knobs (env with sane defaults): `RESEARCHER_MAX_TOPICS`, `RESEARCHER_MAX_TOOL_CALLS`, `RESEARCHER_MAX_REVIEW_ROUNDS`, `RESEARCHER_REQUEST_TIMEOUT`.

## CLI

```
python3 researcher/main.py N [--out PATH] [--max-topics K] [--max-review-rounds K]
                             [--run-id RUN_ID] [--verbose]
```

Default output: `researcher/files/result/episode-N.md`.

## Files & artifacts

```
researcher/
├── DESIGN.md
├── README.md
├── main.py              # CLI, orchestration, run lifecycle
├── agent.py             # generic ReAct tool-call loop
├── tools.py             # tool implementations + registry + dispatch
├── sources.py           # source registry + provenance
├── validate.py          # deterministic gates + mechanical repair (`repair_mechanical`)
├── config.py            # .env loading, model role resolution, limits
├── trace.py             # run trace log + token usage
├── prompts/
│   ├── planner.md
│   ├── researcher.md
│   ├── writer.md
│   ├── reviewer.md
│   ├── simplify.md
│   └── simplify-reviewer.md
├── simplify.py          # second stage: Persian language simplification
└── files/               # all generated artifacts
    ├── result/episode-N.md
    ├── simplify/episode-N.md
    └── runs/<timestamp>-episode-N/
        ├── trace.json
        ├── plan.json
        ├── notes/<topic-id>.md
        ├── draft.md
        ├── sources.json
        └── review-<k>.md
```

`files/` is generated output. `files/runs/` will be gitignored; `files/result/` is the product.

## New dependencies

Add to `requirements.txt`:

- `ddgs` — DuckDuckGo search, no API key
- `tenacity` — retry/backoff for fetch and LLM calls
- `trafilatura` — main-text extraction and page-title metadata for `fetch_url`
- `pypdf` — text extraction for PDF sources (reports, papers) fetched by `fetch_url`
- `fonttools` — required by `pypdf` to extract text from some fonts (Type1/embedded) in PDFs

Already present and reused: `openai`, `python-dotenv`, `requests`, `tiktoken`.

### HTML to text (`fetch_url`)

`fetch_url` does `requests.get` with a browser-like `User-Agent` and the request timeout, then dispatches on the response: PDF goes to the PDF path below, anything HTML goes to main-text extraction. HTML extraction runs `trafilatura.extract` and pulls the page title from `trafilatura.extract_metadata`. The result is whitespace-normalized, boilerplate lines are dropped, and the text is truncated to a token budget (`tiktoken`) so it fits the agent context, returning `{url, title, text, truncated}` or `{error}`.

### PDF to text (`fetch_url`)

A PDF response is detected by content type or `.pdf` URL and passed to `pypdf`: read the bytes from the response, iterate pages, `extract_text()` each, join and whitespace-normalize, then truncate to the same token budget. Page count and a `truncated` flag are returned so the agent knows content was cut. `fonttools` stays installed because `pypdf` uses it to decode text from some embedded/Type1 fonts. Scanned/image-only PDFs yield little or no text; `fetch_url` then returns `{error: "no extractable text (possibly scanned)"}` rather than an empty string, and the source is not citable. OCR (e.g. `ocrmypdf`) is explicitly out of scope.

Failed fetches stay in the provenance registry as failures and are never citable.

## Error handling & budgets

- LLM calls retry with backoff; per-agent max tool-call budget; whole-run wall clock guard.
- Subagent failure is non-fatal: its topic is marked uncovered and surfaced in the run summary; the writer is told which topics lack notes.
- Any deterministic-gate failure is visible in the trace and blocks the result.

## Non-goals

- No fine-grained per-chapter subagents (short chapters are grouped by topic).
- No hosted `web_search` reliance.
- No changes to `content/`, `critique/`, or the site build; this app only produces the `researcher/files/result` artifact, which can later be copied to `critique/episode-N-cite.md`.

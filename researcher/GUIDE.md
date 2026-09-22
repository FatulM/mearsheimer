# GUIDE.md — Studying the Researcher App

A complete, ordered study guide for `researcher/`, the agentic fact-checking
pipeline that turns a Persian blog post into a cited Persian critique. By the
end you should be able to explain, reproduce, debug, and extend the whole app.

---

## 1. What this app is

For a given episode `N`, `python3 researcher/main.py N`:

1. reads the Persian post (`content/episode-N.md`) and the minified English
   transcript (`processed/episode-N.md`);
2. asks a **planner** agent to split the post into research topics;
3. runs one **research subagent** per topic in parallel, each with real web
   tools (`web_search`, `fetch_url`, `url_alive`, `read_transcript`,
   `note_write`) using an OpenAI-compatible endpoint;
4. asks a **writer** agent to compose the full cited critique in Persian;
5. applies deterministic mechanical repairs and **gates**, and runs a
   **reviewer/fixer** agent only while the gates still fail;
6. writes `researcher/files/result/episode-N.md` only when every gate passes
   (otherwise `episode-N.failed.md`).

The pipeline is a replacement for `scripts/critique_content_cite.py`. It
exists because that script forced one model to do research+writing+citation in
a single pass; this app separates concerns and makes sourcing verifiable.

---

## 2. Prerequisites

- Python 3.12 venv at the repo root; activate it:
  `source .venv/bin/activate`
- `.env` configured (copy `.env.example`): `LLM_BASE_URL`, `LLM_API_KEY`,
  `LLM_MODEL` and the optional `LLM_MODEL_AGENT_*` overrides (see §11).
- Installed deps: `pip install -r requirements.txt`
- The episode's `content/episode-N.md` and `processed/episode-N.md` must exist.

Format/lint the package and validate imports anytime you change it:

```bash
ruff check researcher && ruff format --check researcher
python3 -m compileall researcher
```

---

## 3. Architecture in one picture

```
content/episode-N.md ─┐
processed/episode-N.md ┴─> main.read_episode
                           └─> TranscriptIndex (searchable chapters)
                                 │
                                 ▼
                     [planner] run_planner ──► plan.json
                                 │
                                 ▼
       [research subagents] ThreadPoolExecutor(max_workers=4)
            each: run_agent + Toolbox + web tools
            │                          │
            │ notes returned           └─► SourceRegistry (trace+thread-safe)
            ▼                          ~sources.json
       notes/{topic}.notes.md ─► compile_notes
                                 │
                                 ▼
                     [writer] run_writer ──► draft.md
                                 │
                                 ▼
   ┌───────── review loop (max_review_rounds) ─────────┐
   │  current = repair_mechanical(current)             │
   │  problems = validate_critique(current, ...)       │
   │  if not problems: break                           │
   │  else: run_reviewer(...) ──► review-{k}.md        │
   └───────────────────────────────────────────────────┘
                                 │
                                 ▼
              check_liveness(all cited URLs)  ── into registry
              validate_critique(require_alive=True)
                                 │
                         result/episode-N.md  (or .failed.md)
```

Collapse of responsibility:

| Concern | Owner |
|---|---|
| Orchestration / CLI | `main.py` |
| LLM config, roles, limits | `config.py` |
| Generic ReAct agent loop | `agent.py` |
| Web/transcript/notes tools | `tools.py` |
| Provenance + liveness registry | `sources.py` |
| Structured run log + tokens | `trace.py` |
| Deterministic gates + mechanical repair | `validate.py` |
| Agent behaviour specs | `prompts/*.md` |

---

## 4. Suggested reading order

Read in this order; each step builds on the previous. For every module answer
the "focus questions".

### 4.1 `main.py` first — the spine

Read this end to end before anything else. It is the only module that imports
from all others, so it shows how the pieces connect.

- CLI: `parse_args` — note `--resume RUN_ID` reuses an existing run dir.
- `read_episode` — inputs are the Persian post and the processed transcript.
- `new_run_dir` — every run gets `files/runs/<YYMMDD-HHMMSS>-episode-N/`.
- `chapter_map`, `parse_plan` — the planner output is JSON; if parsing fails
  the app falls back to a single `general` topic.
- `run_planner`, `run_research`, `run_writer`, `run_reviewer` — each builds a
  user message from prompt + inputs and calls the shared `run_agent`.
- The review loop (§ main): note `repair_mechanical` runs **before every**
  gate check, and the reviewer only runs while problems remain.
- `check_liveness` — HEAD/GET check on every cited URL, traced immediately.
- The ending: `validate_critique(require_alive=True)` gates the *final* text;
  a passing run writes the result, a failing one writes `*.failed.md`.

Focus questions:
- Where is the writer's output persisted, and where is each reviewer pass?
- What happens when `max_review_rounds` is exhausted?
- How do the `problems` reach the reviewer, and how do they come back?
- Where is the registry saved to disk (twice)?

### 4.2 `config.py` — settings and roles

- `Settings` frozen dataclass; `Settings.model(role)` returns that role's model.
- `ROLE_ENV` maps role → env var (`LLM_MODEL_AGENT_PLANNER/LEAD/RESEARCH/
  REVIEWER`), each falling back to the base `LLM_MODEL` (this mirrors the
  convention of the repo's other scripts).
- `RESEARCHER_MAX_TOPICS/_TOOL_CALLS/_REVIEW_ROUNDS/_REQUEST_TIMEOUT` knobs.
- `check_endpoint` — a soft preflight against `{base}/models` (warn, not fail).

Focus questions:
- What does `load_settings` complain about, and where does the error exit?
- How would you run a planner with a different model but the same research
  model?

### 4.3 `agent.py` — the ReAct loop

One generic loop, used by every agent:

- `make_client` — OpenAI client for the configured endpoint.
- `_create` — the single LLM call, wrapped in `tenacity` (retry on connection /
  rate-limit / API status errors, exponential backoff, reraise).
- `run_agent` — the loop:
  1. send `[system(user=prompt), {user}]`;
  2. if the response has `tool_calls`, append the assistant message, execute
     each tool through `toolbox.dispatch`, append the `tool` results;
  3. when the tool budget is used up, tools are withheld so the model must
     answer;
  4. when the response has no tool calls, return the text.
- `strip_fences` — removes markdown code fences from model answers.
- `record_usage` is called after every LLM call (feeds the trace).

Focus questions:
- How does the model trigger a tool, and what shape is the tool result?
- Why is "withhold tools at budget end" important for termination?
- Which exceptions are retried, and by how much?

### 4.4 `tools.py` — the tool layer

The largest module. Three groups:

**HTTP/text helpers (top of file):**
- `_reachable`/`_liveness` — bot-block statuses `{401,403,405,429}` count as
  *reachable* so a real source behind a bot wall is not treated as dead.
- `_truncate_tokens` — tiktoken `cl100k_base` budget (≈6000), fallback ~4
  chars/token.
- `html_to_text` — prefers `trafilatura`, falls back to BeautifulSoup main-text
  extraction (`article`/`main`/body, block tags dropped, boilerplate cleaned).
- `pdf_to_text` — `pypdf` per page.

**TranscriptIndex:**
- Parses `processed/episode-N.md` into `Chapter(timestamp, title, body)`.
- `find` — timestamp prefix, then case-insensitive title, then body substring.

**Toolbox + dispatch:**
- `dispatch(name, arguments)` — the single entry point agents use. On failure
  it logs a `tool_error` trace event and returns `{"error": ...}`; on success
  it logs a `tool_call` event and returns JSON. **Key detail:** a `tool_call`
  trace event means the call *succeeded*; failures appear as `tool_error`.
- The six tools (`web_search`, `fetch_url`, `url_alive`, `read_transcript`,
  `note_write`, `validate`) and the three tool sets
  (`WRITER_TOOLS`, `RESEARCH_TOOLS`, `REVIEWER_TOOLS`) — note the reviewer has
  no `note_write`.

Focus questions:
- How do `fetch_url` and `web_search` feed the `SourceRegistry`? What is
  `origin` for each?
- Which statuses make `fetch_url` return `{error}` vs extract text vs "blocked"?
- How does `note_write` differ from `main.py`'s `notes/{id}.notes.md` write?
  (The former is **optional**, called by the model; the latter always happens.)

### 4.5 `sources.py` — provenance

The **source registry** is the anti-hallucination backbone:

- `normalize_url` — strips fragments and trailing slashes for lookups.
- `Source` — `alive: bool|None`, `http_status`, `fetched`, `origin`.
  `citable` == `alive is not False` (unknown/never-checked is *not* citable).
  Wait — re-read: `citable` is `alive is not False`; an **unchecked** source
  (`alive is None`) is considered citable in `_check_citations` unless
  `require_alive` is set. Understand both paths.
- `SourceRegistry` is thread-safe (one lock) because research subagents run in
  parallel against the same registry.
- `add`, `mark_fetched`, `mark_alive`, `get`, `has`, `all`, `save`.

Focus questions:
- What gates a URL out on provenance, and what gates it out on liveness?
- Why does the registry need a lock while `RunTrace` also needs one?

### 4.6 `trace.py` — observability

- `log(kind, agent, message, **fields)` — structured event list + optional
  verbose stdout. Each event has `t` (seconds since run start).
- `record_usage` — per-agent token accumulator plus an `llm_usage` event
  carrying the **per-call** total.
- `save` — `trace.json` = header `{started_at, duration_seconds, usage,
  events}`.

Focus questions:
- How would you list every `tool_error` in a run from `trace.json`?
- Which event kinds exist? (`agent_start`, `agent_done`, `tool_call`,
  `tool_error`, `tool_result`, `llm_usage`, `gates`, `final_gates`, `plan`)

### 4.7 `validate.py` — the deterministic contract

This is what defines "done":

- `Problem` — `{code, message}`.
- `extract_headings` — `(level, raw_line)` pairs.
- `_check_structure` — trailing newline **and** blank line, one H1, H1/H2 only,
  blank line after every heading.
- `_check_headings_match` — H1 and the ordered `## {mm:ss} - {TITLE}` list
  byte-identical to the source content, none dropped/added/rewritten.
- `_check_rule` — exactly one horizontal rule (the `---` before citations).
- `_parse_entries` — entry = `{N}. {Persian} — {title (outlet)} — {URL}`:
  exactly two ` — ` separators (three fields), last field a real URL.
- `_check_citations` — body may contain only `[cite: N]` brackets; every
  cited number maps to an entry; every entry is referenced; entries are
  numbered `1..N`; numbering is in **first-reference order**; provenance
  (URL in registry) and (when asked) liveness (`alive is not False`).
- `repair_mechanical` — the deterministic fix layer: heading blank lines,
  citation **renumbering to first-reference order** (only when the mapping is
  bijective — cite set == entry set), and the trailing blank line. Anything
  ambiguous (e.g. wrong em-dash counts) is left for the reviewer.
- `cited_urls` — every URL in the citations section, for liveness checks.
- Standalone CLI: `python3 researcher/validate.py <critique.md> <content.md>`.

Focus questions:
- What exactly is "first-reference order", and why is the renumbering applied
  only when bijective?
- Which repairs does `repair_mechanical` *not* attempt, and why?
- Walk through ep2's final list: entries `1,3,2,4,8,7,9,...` — why does it
  still pass the ordering gate?

### 4.8 `prompts/` — the behaviour specs

- `planner.md` → research topics + `coverage` map, JSON only, 3..max_topics.
- `researcher.md` → subagent method: search→fetch→cross-check transcript,
  save with `note_write`, report verified findings with URLs; reply ≤1200 words.
- `writer.md` → the output contract: byte-identical headings, at least one
  `[cite: N]` per research-bearing chapter, Persian body with Persian numerals,
  exactly two-em-dash citation entries, codes the `---`/blank-line rules.
- `reviewer.md` → minimal, targeted edits only; never add new research/
  sentences/sources/citations; renumber or drop orphaned cites rather than
  invent; preserve structure and citation contract.

Read each prompt **out loud against `validate.py`**: every constraint in the
prompts is enforced (or mirrored) by the deterministic gates. The prompts
have drifted before (writer once emitted three-field-slash entries, and
reviewers once rewrote whole chapters) — the gates + the improved prompts are
what keep the product stable.

---

## 5. Run artifacts — how to read a run

Every run leaves a directory `files/runs/<timestamp>-episode-N/`:

```
├── cli.log            # stdout/stderr if you redirect (verbose trace echoes)
├── plan.json          # planner output: topics + coverage
├── trace.json         # full event log + per-agent token usage
├── sources.json       # the provenance registry (asdict of every Source)
├── draft.md           # writer output before the review loop
├── review-<k>.md      # reviewer pass k (only when a pass actually ran)
└── notes/
    ├── <topic>.notes.md   # ALWAYS written: subagent final reply
    └── <topic>.md         # only when the model called note_write
```

Reading order for a finished run:

1. `cli.log` — the narrative: planned topics, warnings, gate rounds, total
   tokens, result path.
2. `trace.json`
   - `usage` — per-agent call/token counts (spot the reviewer burning tokens);
   - `events` — filter `event=="gates"` to see problem counts per round;
   - `event=="tool_error"` — every tool failure (e.g. web_search flakes);
   - `event=="tool_call"` — successful calls with their arguments.
3. `sources.json` — every `origin` (`search` vs `fetch`) and the liveness
   fields (`alive`, `http_status`) filled in by `check_liveness`.
4. `draft.md` vs `review-<k>.md` — what the reviewer changed.

---

## 6. A worked example: follow episode-2

1. Run: `20260921-063300-episode-2`. `cli.log` shows `gates passed on round 0
   problem(s)` then `round 1: 0` — i.e. the reviewer fixed one problem.
2. Why: `draft.md`'s citations were not in first-reference order (1 gate
   problem). The reviewer renumbered the list and markers consistently;
   `trace.json` records 7 reviewer LLM calls / ~414k tokens (the historical
   scope-drift case — now mitigated by `repair_mechanical` + `reviewer.md`).
3. `trace.json` also shows 32 `tool_error` events (13 `web_search`,
   19 `fetch_url`) — the transient provider failures that motivated the retry
   logic in `tools.py`.
4. `sources.json` shows each cited URL with `origin`; a later standalone
   `validate.py` re-check passes all gates.
5. Contrast with episode-3's run (`20260921-074427-episode-3`): `gates passed
   on round 0` with **zero** reviewer passes — the mechanical repair handled
   the ordering deterministically. But its `trace.json` shows ~161 `tool_error`
   events: `web_search` was returning `No results found.` (see §9), so
   subagents fell back to `fetch_url` best-guess URLs and the critique became
   Wikipedia-heavy. Reproducing that run today (post backend fix) works.

---

## 7. Debugging toolkit

```bash
# Standalone gate check on any critique:
python3 researcher/validate.py researcher/files/result/episode-2.md content/episode-2.md

# Summarise a run's trace:
python3 - <<'EOF'
import json, collections
t = json.load(open("researcher/files/runs/<run>/trace.json"))
print(collections.Counter(e["event"] for e in t["events"]))
for e in t["events"]:
    if e.get("event") in ("gates", "final_gates"):
        print(e.get("message"), e.get("problems"))
EOF

# Token usage per agent:
#   read trace.json["usage"]
```

Common confusions:

- A `tool_call` event + a `tool_result` event = success. A `tool_error`
  event = failure (the tool_call for that call is *not* logged).
- `ok: null` in `url_alive`/registry means *unknown* (network error or bot
  block), not dead; the final gate only fails on `alive is False`.
- Entry numbers in the citations list are ordered by **first reference** in
  the body, not numerically—so `1,3,2,4,8,7,...` is valid.

---

## 8. Known failure modes (learned in production)

1. **`web_search` backend flakiness.** ddgs' default `auto` metacrawl is the
   reliable choice; pinning a single backend (e.g. `duckduckgo`) caused
   `No results found.` for ~161 calls in one run. `web_search` retries 3
   times; transient failures still surface as tool errors.
2. **Reviewer scope-creep.** A single gate problem (numbering) once triggered a
   reviewer that added new citations and rewrote claims (~414k tokens).
   Mitigations: `reviewer.md`'s minimal-edit rules and `repair_mechanical`
   making ordering problems non-events.
3. **`repair_mechanical` is conservative.** It renumbers only when the cite↔
   entry mapping is bijective and never touches em-dash formatting; ambiguous
   drafts still need the reviewer.
4. **`note_write` is optional.** `{topic}.md` files appear only when the model
   calls the tool; `{topic}.notes.md` always appear (written by `main.py`).
   The writer consumes the compiled notes either way.
5. **Provenance is a fetch, not a judgment.** A guessed URL that `fetch_url`
   retrieves becomes "retrieved during the run" (registry `origin="fetch"`).
   Watch for low-authority best-guess Wikipedia fetches when search fails.

---

## 9. Extension points / exercises

- **Add a tool**: extend `TOOL_SPECS`, add a handler in `Toolbox`, register it
  in the appropriate `*_TOOLS` list, and (if agent-visible) describe it in the
  relevant prompt.
- **Tighten a gate**: new check in `validate.py` (e.g. require
  `{title (outlet)}` parenthetical form instead of slash, or reject
  low-authority domains) — remember to also update `writer.md`/`reviewer.md`
  so the model can satisfy it.
- **New environment knob**: add to `Settings` + `load_settings` + CLI arg.
- **Exercises**:
  1. `validate.py researcher/files/result/episode-1.md content/episode-1.md`
     passes today. Break it (reorder a citation, drop a blank line, change one
     chapter heading) and watch the gate names fire.
  2. Re-run the episode-3 trace summariser after the next run and compare
     `tool_error` counts and per-agent token usage against the fixed backend.
  3. `repair_mechanical` on a draft that is not bijective (e.g. ep1's draft)
     returns it unchanged — confirm why.
  4. Read `reviewer.md` and `writer.md` and list every constraint that
     `validate.py` checks — you should find one for (almost) every rule.
  5. Add a `--dry-run` mode to `main.py` that stops after `draft.md` and
     prints the first pass of the gates without spending reviewer tokens.

---

## 10. Glossary

- **Agent**: one LLM role (planner, research:<topic>, writer, reviewer)
  driven by `run_agent`.
- **Registry / provenance**: every URL a run actually saw, from `web_search`
  (`origin="search"`) or `fetch_url` (`origin="fetch"`).
- **Gate**: a pure-Python check in `validate.py`; a result is written only when
  all pass (liveness included at the end).
- **Mechanical repair**: `repair_mechanical` — safe, deterministic, idempotent
  fixes applied before each gate check.
- **First-reference order**: citation numbering where the sequence is the order
  in which numbers first appear in the body.
- **`.failed.md`**: what gets written when the reviewer cannot satisfy the
  gates within the round budget.

---

## 11. Configuration reference

```bash
LLM_BASE_URL=...                                  # required
LLM_API_KEY=...                                   # required
LLM_MODEL=...                                     # required fallback
LLM_MODEL_AGENT_PLANNER=...   # optional, falls back to LLM_MODEL
LLM_MODEL_AGENT_LEAD=...      #  ^ the writer / lead
LLM_MODEL_AGENT_RESEARCH=...  #  ^ topic subagents
LLM_MODEL_AGENT_REVIEWER=...  #  ^ reviewer/fixer
RESEARCHER_MAX_TOPICS=8
RESEARCHER_MAX_TOOL_CALLS=25
RESEARCHER_MAX_REVIEW_ROUNDS=3
RESEARCHER_REQUEST_TIMEOUT=120
```

---

## 12. Where to go next

After this guide: re-read `researcher/DESIGN.md` (design rationale) and
`researcher/README.md` (usage + gates summary), then the sibling pipelines
in `scripts/` (`critique_content_cite.py`, `check_translation.py`) to see the
non-agentic architecture this app replaces. AGENTS.md has the file-format
contracts (`info/`, `transcript/`, `processed/`, `content/`) the app's inputs
depend on.

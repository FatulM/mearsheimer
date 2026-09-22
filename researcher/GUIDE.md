# GUIDE.md — Studying the Researcher App

This guide explains `researcher/`, the agentic fact-checking pipeline. The pipeline turns a Persian blog post into a cited Persian critique. When you finish this guide, you can explain, reproduce, debug, and extend the whole app.

---

## 1. What this app is

For a given episode `N`, `python3 researcher/main.py N` does these steps:

1. It reads the Persian post (`content/episode-N.md`) and the minified English transcript (`processed/episode-N.md`).
2. It asks a planner agent to split the post into research topics.
3. It runs one research subagent per topic in parallel. Each subagent has real web tools (`web_search`, `fetch_url`, `url_alive`, `read_transcript`, `note_write`). The tools use an OpenAI-compatible endpoint.
4. It asks a writer agent to compose the full cited critique in Persian.
5. It applies deterministic mechanical repairs and gates. It runs a reviewer/fixer agent only while the gates still fail.
6. It writes `researcher/files/result/episode-N.md` only when every gate passes. If a gate fails, it writes `episode-N.failed.md`.

The pipeline replaces `scripts/critique_content_cite.py`. That script forced one model to do research, writing, and citation in a single pass. This app separates those concerns and makes sourcing verifiable.

---

## 2. Prerequisites

- Use the Python 3.12 venv at the repo root. Activate it with `source .venv/bin/activate`.
- Configure `.env`. Copy `.env.example`. Set `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, and the optional `LLM_MODEL_AGENT_*` overrides (see §11).
- Install the deps: `pip install -r requirements.txt`
- The files `content/episode-N.md` and `processed/episode-N.md` must exist.

After you change the package, format it, lint it, and validate imports:

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

Responsibility map:

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
| Language simplification stage | `simplify.py` |

---

## 4. Suggested reading order

Read the modules in this order. Each module builds on the module before it. For every module, answer the focus questions.

### 4.1 `main.py` first — the spine

Read `main.py` from start to finish before you read anything else. It is the only module that imports from all the others. It shows how the pieces connect.

- `parse_args` handles the CLI. Note that `--resume RUN_ID` reuses an existing run directory.
- `read_episode` reads the inputs. The inputs are the Persian post and the processed transcript.
- `new_run_dir` creates a directory for each run. The directory is `files/runs/<YYMMDD-HHMMSS>-episode-N/`.
- `chapter_map` and `parse_plan` handle the planner output. The planner output is JSON. If the parsing fails, the app uses a single `general` topic instead.
- `run_planner`, `run_research`, `run_writer`, and `run_reviewer` build a user message. Each function builds the message from a prompt and the inputs. Then each function calls the shared `run_agent`.
- The review loop is in `main()`. `repair_mechanical` runs before every gate check. The reviewer runs only while problems remain.
- `check_liveness` runs a HEAD or GET check on every cited URL. It logs the check result immediately.
- At the end, `validate_critique(require_alive=True)` checks the final text. If the run passes, it writes the result. If the run fails, it writes `*.failed.md`.

Focus questions:

- Where is the writer's output saved? Where is each reviewer pass saved?
- What happens when `max_review_rounds` is exhausted?
- How do the problems reach the reviewer? How do they come back from the reviewer?
- Where does the run save the registry to disk? It saves it two times.

### 4.2 `config.py` — settings and roles

- `Settings` is a frozen dataclass. `Settings.model(role)` returns the model for that role.
- `ROLE_ENV` maps each role to an env var (`LLM_MODEL_AGENT_PLANNER/LEAD/RESEARCH/REVIEWER`). Each env var falls back to the base `LLM_MODEL`. This mirrors the convention of the repo's other scripts.
- The knobs are `RESEARCHER_MAX_TOPICS`, `RESEARCHER_MAX_TOOL_CALLS`, `RESEARCHER_MAX_REVIEW_ROUNDS`, and `RESEARCHER_REQUEST_TIMEOUT`.
- `check_endpoint` runs a soft preflight check against `{base}/models`. It warns, but it does not fail.

Focus questions:

- What problems does `load_settings` report? Where does the error exit?
- How do you run the planner with a different model but keep the same research model?

### 4.3 `agent.py` — the ReAct loop

`agent.py` provides one generic loop. Every agent uses this loop.

- `make_client` creates an OpenAI client for the configured endpoint.
- `_create` is the single LLM call. It uses `tenacity`. It retries on connection, rate-limit, and API status errors. It uses exponential backoff. At the end it re-raises the error.
- `run_agent` runs the loop. The loop does these steps:

  1. It sends `[system(user=prompt), {user}]`.
  2. If the response has `tool_calls`, append the assistant message to the history. Execute each tool through `toolbox.dispatch`. Append the `tool` results to the history.
  3. When the tool budget ends, the agent withholds the tools. Then the model must answer.
  4. When the response has no tool calls, return the text.

- `strip_fences` removes markdown code fences from the model's answers.
- The agent calls `record_usage` after every LLM call. This feeds the trace.

Focus questions:

- How does the model trigger a tool? What is the shape of the tool result?
- Why must the agent withhold the tools at the budget end? This makes the loop stop.
- Which exceptions does the loop retry? How many times does it retry them?

### 4.4 `tools.py` — the tool layer

`tools.py` is the largest module. It has three groups.

**HTTP/text helpers (top of file):**

- `_reachable` and `_liveness` treat the bot-block statuses `{401,403,405,429}` as `reachable`. A real source behind a bot wall is not dead.
- `_truncate_tokens` uses a tiktoken `cl100k_base` budget of about 6000 tokens. The fallback is about 4 characters per token.
- `html_to_text` prefers `trafilatura`. It falls back to BeautifulSoup main-text extraction. The extractor uses `article`/`main`/body. It drops block tags and cleans the boilerplate.
- `pdf_to_text` uses `pypdf` and reads one page at a time.

**TranscriptIndex:**

- It parses `processed/episode-N.md`. It produces `Chapter(timestamp, title, body)` objects.
- `find` matches a timestamp prefix first. Then it matches a case-insensitive title. Finally, it matches a body substring.

**Toolbox + dispatch:**

- `dispatch(name, arguments)` is the single entry point that agents use. On failure, it logs a `tool_error` trace event and returns `{"error": ...}`. On success, it logs a `tool_call` event and returns JSON. **Key detail:** a `tool_call` trace event means the call succeeded. Failures appear as `tool_error`.
- There are six tools (`web_search`, `fetch_url`, `url_alive`, `read_transcript`, `note_write`, `validate`). There are three tool sets (`WRITER_TOOLS`, `RESEARCH_TOOLS`, `REVIEWER_TOOLS`). The reviewer set has no `note_write`.

Focus questions:

- How do `fetch_url` and `web_search` feed the `SourceRegistry`? What is `origin` for each?
- Which statuses make `fetch_url` return `{error}`? Which statuses make it extract text? Which statuses make it return `blocked`?
- How does `note_write` differ from the `notes/{id}.notes.md` write in `main.py`? `note_write` is optional, and the model calls it. The `main.py` write always happens.

### 4.5 `sources.py` — provenance

The **source registry** stops the model from inventing sources.

- `normalize_url` strips fragments and trailing slashes. This makes URL lookups consistent.
- `Source` has the fields `alive: bool|None`, `http_status`, `fetched`, and `origin`. The property `citable` equals `alive is not False`. So an unchecked source (`alive is None`) is still citable in `_check_citations` unless `require_alive` is set. A source with `alive is False` is not citable. Understand both paths.
- `SourceRegistry` is thread-safe. It uses one lock. Research subagents run in parallel against the same registry.
- `SourceRegistry` provides `add`, `mark_fetched`, `mark_alive`, `get`, `has`, `all`, and `save`.

Focus questions:

- What does the provenance check exclude? What does the liveness check exclude?
- Why does the registry need a lock? Why does `RunTrace` also need a lock?

### 4.6 `trace.py` — observability

- `log(kind, agent, message, **fields)` adds to a structured event list. It also sends optional verbose output to stdout. Each event has `t`, the seconds since the run started.
- `record_usage` tracks tokens per agent. It also writes an `llm_usage` event with the per-call total.
- `save` writes `trace.json`. The file has the header `{started_at, duration_seconds, usage, events}`.

Focus questions:

- How do you list every `tool_error` in a run from `trace.json`?
- What are the event kinds? They are `agent_start`, `agent_done`, `tool_call`, `tool_error`, `tool_result`, `llm_usage`, `gates`, `final_gates`, and `plan`.

### 4.7 `validate.py` — the deterministic contract

This module defines when a critique is done.

- `Problem` is `{code, message}`.
- `extract_headings` returns `(level, raw_line)` pairs.
- `_check_structure` requires a trailing newline and a blank line. It requires one H1. It allows H1 and H2 only. It requires a blank line after every heading.
- `_check_headings_match` checks the H1 and the ordered `## {mm:ss} - {TITLE}` list. They must be byte-identical to the source content. None can be dropped, added, or rewritten.
- `_check_rule` requires exactly one horizontal rule. That rule is the `---` before the citations.
- `_parse_entries` parses each entry. An entry is `{N}. {Persian} — {title (outlet)} — {URL}`. It has exactly two ` — ` separators, so three fields. The last field must be a real URL.
- `_check_citations` checks the body. The body can contain only `[cite: N]` brackets. Every cited number maps to an entry. Every entry is referenced. The entries are numbered `1..N`. The numbering follows first-reference order. The URL must be in the registry, which is the provenance check. When asked, `alive is not False` must hold, which is the liveness check.
- `repair_mechanical` applies deterministic fixes. It adds blank lines after headings. It renumbers citations to first-reference order. It does this only when the mapping is bijective, so the cite set equals the entry set. It adds the trailing blank line. Anything ambiguous, such as wrong em-dash counts, is left for the reviewer.
- `cited_urls` returns every URL in the citations section. The liveness check uses these URLs.
- Run a standalone check with `python3 researcher/validate.py <critique.md> <content.md>`.

Focus questions:

- What is first-reference order? Why does `repair_mechanical` renumber only when the mapping is bijective?
- Which fixes does `repair_mechanical` not try? Why not?
- Examine the episode-2 final list. The entries are `1,3,2,4,8,7,9,...`. Why does this list still pass the ordering gate?

### 4.8 `prompts/` — the behaviour specs

- `planner.md` tells the planner to return research topics and a `coverage` map. The reply is JSON only. The reply contains between 3 and `max_topics` topics.
- `researcher.md` defines the subagent method. The subagent searches, fetches, and cross-checks the transcript. It saves the notes with `note_write`. It reports verified findings with URLs. The reply is at most 1200 words.
- `writer.md` defines the output contract. The headings are byte-identical. Each research-bearing chapter has at least one `[cite: N]`. The body is Persian with Persian numerals. Citation entries use exactly the two em-dashes. The writer must follow the `---` and blank-line rules.
- `reviewer.md` limits the reviewer to minimal, targeted edits. The reviewer never adds research, sentences, sources, or citations. It renumbers or drops orphaned cites. It does not invent new cites. It preserves the structure and the citation contract.

Read each prompt against `validate.py`. The deterministic gates enforce or mirror every constraint in the prompts. The prompts drifted before. The writer once emitted three-field-slash entries. Reviewers once rewrote whole chapters. The gates and the improved prompts keep the product stable.

### 4.9 `simplify.py` — the language stage

`simplify.py` is the second stage of the `researcher/` app. It makes a finished critique easier to read. It does not change what the critique says.

Run `python3 researcher/simplify.py N` after `main.py` writes the result. The stage reads `researcher/files/result/episode-N.md`. It writes a new file at `researcher/files/simplify/episode-N.md`. The original result file stays unchanged.

The stage does these steps:

1. Split the critique at the horizontal rule.
2. Keep the citations section aside.
3. Send only the body to `LLM_MODEL_AGENT_LANGUAGE`.
4. Join the citations section back.
5. Run the reviewer/fixer loop.

The language model rewrites the body one time. The prompt tells the model to keep the H1 title and every chapter heading the same. The prompt tells the model to keep every citation number inside its own chapter. A chapter may merge adjacent markers into one. The prompt tells the model to change only the words.

The reviewer uses `LLM_MODEL_AGENT_REVIEWER`. It compares the original body with the new body. It returns one JSON object: `{"ok": bool, "problems": [...], "revised": "..."}`. It repairs each real problem with a small edit. It never simplifies the text again. It reports only the problems that stay after its edit. A faithful wording change is not a problem.

The corrected body always replaces the candidate body. A fix is never lost. The loop stops when the reviewer reports no problem and the gates pass. The loop also stops when the reviewer makes no change, or after `RESEARCHER_LANGUAGE_MAX_ROUNDS` passes.

Deterministic gates run before each reviewer pass and before the write. The gates check the structure and the citation markers. Before the gates run, the stage sorts the numbers inside each `[cite: N]` marker and merges adjacent markers. One gate compares, for each chapter and the overall assessment, the set of unique citation numbers in the new body with the original body. A citation moved to another chapter, or dropped, fails the gate. Merging or slightly moving markers inside one chapter is correct.

If the loop does not stop cleanly, the stage writes `episode-N.failed.md` and exits non-zero. The run directory is `researcher/files/runs/<timestamp>-episode-N-language/`. It holds `trace.json`, `original.md`, `citations.md`, `simplified-body-0.md`, and `review-<k>.md`.

Focus questions:

- Which model rewrites the body? Which model reviews it?
- Why does the stage remove the citations section before the rewrite?
- When does the loop stop?

---

## 5. Run artifacts — how to read a run

Each run creates a directory `files/runs/<timestamp>-episode-N/`:

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

1. Read `cli.log`. It is the narrative. It shows the planned topics, warnings, gate rounds, total tokens, and result path.
2. Read `trace.json`. Use these filters:

   - `usage` shows the per-agent call and token counts. Watch for a reviewer that uses many tokens.
   - Filter `event == "gates"`. This shows the problem counts per round.
   - Filter `event == "tool_error"`. This shows every tool failure, such as temporary `web_search` failures.
   - Filter `event == "tool_call"`. This shows successful calls with their arguments.

3. Read `sources.json`. It shows every `origin` (`search` or `fetch`). `check_liveness` fills in the liveness fields (`alive`, `http_status`).
4. Compare `draft.md` with `review-<k>.md`. This shows what the reviewer changed.

---

## 6. A worked example: follow episode-2

1. Use the run `20260921-063300-episode-2`. The `cli.log` shows the message `[ok] gates passed on round 0` and the echo `round 1: 0 problem(s)`. This means the review loop fixed one problem.
2. Check the cause. The citations in `draft.md` were not in first-reference order. This caused one gate problem. The reviewer renumbered the list and the markers consistently. The `trace.json` records 7 reviewer LLM calls and about 414k tokens. This was the known scope-drift case. Now `repair_mechanical` and `reviewer.md` prevent it.
3. The `trace.json` also shows 32 `tool_error` events. There are 13 `web_search` errors and 19 `fetch_url` errors. These were transient provider failures. They motivated the retry logic in `tools.py`.
4. The `sources.json` shows the `origin` for each cited URL. A later standalone `validate.py` check passes all gates.
5. Compare this with the episode-3 run (`20260921-074427-episode-3`). It reports `gates passed on round 0` with zero reviewer passes. The mechanical repair fixed the ordering deterministically. But its `trace.json` shows about 161 `tool_error` events. The `web_search` tool returned `No results found.` (see section 9). The subagents used best-guess URLs with `fetch_url` instead. The critique became heavy with Wikipedia sources. The run now works again after the backend fix.

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

- A `tool_call` event plus a `tool_result` event means success. A `tool_error` event means failure. The `tool_call` for a failed call is not logged.
- The value `ok: null` in `url_alive` or the registry means `unknown`, not dead. It can be a network error or a bot block. The final gate fails only when `alive is False`.
- The entry numbers follow the first reference in the body, not the numerical order. So `1,3,2,4,8,7,...` is valid.

---

## 8. Known failure modes (learned in production)

1. **`web_search` backend flakiness.** The ddgs default `auto` metacrawl is the reliable choice. When a run pinned one backend, such as `duckduckgo`, `web_search` returned `No results found.` for about 161 calls in one run. `web_search` retries three times. Transient failures still appear as tool errors.
2. **Reviewer scope creep.** One gate problem about numbering once made the reviewer add new citations and rewrite claims. This used about 414k tokens. Two measures prevent this. The `reviewer.md` file limits the reviewer to minimal edits. The `repair_mechanical` function fixes ordering problems before the gates, so they never trigger the reviewer.
3. **`repair_mechanical` is conservative.** It renumbers only when the cite-to-entry mapping is bijective. It never changes em-dash formatting. Ambiguous drafts still need the reviewer.
4. **`note_write` is optional.** The `{topic}.md` files appear only when the model calls the tool. The `{topic}.notes.md` files always appear. `main.py` writes them. The writer uses the compiled notes either way.
5. **Provenance is a fetch, not a judgment.** A guessed URL that `fetch_url` retrieves becomes retrieved during the run. The registry records `origin="fetch"`. Watch for low-authority best-guess Wikipedia fetches when the search fails.

---

## 9. Extension points / exercises

- **Add a tool.** Extend `TOOL_SPECS`. Add a handler in `Toolbox`. Register the tool in the correct `*_TOOLS` list. If the agent can see it, describe the tool in the relevant prompt.
- **Tighten a gate.** Add a new check in `validate.py`. For example, require the `{title (outlet)}` parenthetical form instead of a slash. Or reject low-authority domains. Update `writer.md` and `reviewer.md` as well. The model needs these updates to pass the new gate.
- **Add a new environment knob.** Add it to `Settings`, `load_settings`, and the CLI args.
- **Exercises:**

  1. Run `python3 researcher/validate.py researcher/files/result/episode-1.md content/episode-1.md`. It passes today. Then break the input. Reorder a citation. Drop a blank line. Change one chapter heading. Watch the gate names that appear.
  2. Run the episode-3 trace summariser again after the next run. Compare the `tool_error` counts and the per-agent token usage. Compare them against the fixed backend.
  3. Run `repair_mechanical` on a draft that is not bijective, such as the episode-1 draft. It returns the draft unchanged. Confirm why.
  4. Read `reviewer.md` and `writer.md`. List every constraint that `validate.py` checks. You should find a check for almost every rule.
  5. Add a `--dry-run` mode to `main.py`. The mode stops after `draft.md`. It prints the first pass of the gates. It does not spend reviewer tokens.

---

## 10. Glossary

- **Agent** — one LLM role. The roles are planner, `research:<topic>`, writer, and reviewer. `run_agent` drives each role.
- **Registry / provenance** — every URL that a run actually saw. The URL comes from `web_search` (`origin="search"`) or `fetch_url` (`origin="fetch"`).
- **Gate** — a check in `validate.py`. The check is pure Python. A result writes only when all gates pass. The liveness check is included at the end.
- **Mechanical repair** — `repair_mechanical`. It applies safe, deterministic, idempotent fixes. It runs before each gate check.
- **First-reference order** — citation numbering. The sequence is the order in which the numbers first appear in the body.
- **`.failed.md`** — the file that the app writes when the reviewer cannot satisfy the gates within the round budget.

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
LLM_MODEL_AGENT_LANGUAGE=...  #  ^ Persian-writing model for simplify.py
RESEARCHER_MAX_TOPICS=8
RESEARCHER_MAX_TOOL_CALLS=25
RESEARCHER_MAX_REVIEW_ROUNDS=3
RESEARCHER_LANGUAGE_MAX_ROUNDS=3
RESEARCHER_REQUEST_TIMEOUT=120
```

---

## 12. Where to go next

After you finish this guide, read `researcher/DESIGN.md` for the design rationale. Read `researcher/README.md` for the usage and the gates summary. Then read the sibling pipelines in `scripts/`. Use `critique_content_cite.py` and `check_translation.py`. This shows the non-agentic architecture that this app replaces. `AGENTS.md` has the file-format contracts. The contracts for `info/`, `transcript/`, `processed/`, and `content/` define the app's inputs.

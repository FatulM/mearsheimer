# Agent Instructions

## Project

This is a static Persian (Farsi) website presenting blog-style Persian summaries of the videos from [John Mearsheimer's YouTube channel](https://www.youtube.com/@JohnMearsheimer). Each episode of the channel becomes a Persian blog post on the website, linked to the original YouTube video. The website will be hosted on GitHub Pages.

## Environment & Setup

- Python 3.12 venv at `.venv/`; always activate: `source .venv/bin/activate`; work dir is repo root.
- Env creation is manual: `python3.12 -m venv .venv`, `source .venv/bin/activate`, `pip install -U pip`, `pip install -r requirements.txt`.

## Commands

- Install deps: `pip install -r requirements.txt`
- Format / check: `ruff format scripts` / `ruff format --check scripts`
- Lint: `ruff check scripts` · Validate imports: `python -m compileall scripts`

## Conventions

- Never read `.env` file content directly; use `.env.example` file as the `.env` file template.
- Never commit, stage, reset, or discard changes unless explicitly requested. Preserve unrelated user changes.
- 120-char line length for .py files; Markdown has no line-length limit; Markdown headings followed by a blank line; all textual files end with a newline.
- All website content is Persian (Farsi) for Iranian readers unless explicitly requested otherwise.
- HTML/CSS/JS maintain RTL layout and Vazirmatn font usage.
- Content updates go to source `.md` files first, then reflected in `.html` files.
- `docs/` is the static site root published via GitHub Pages.
- Project-specific skills live in `.agents/skills/`.

## Project Structure

```
mearsheimer/
├── content/                            # Persian blog posts (episode-N.md)
├── critique/                           # Fact-check critiques of the posts (episode-N.md)
├── info/                               # Channel + episode metadata (URL, title, chapters)
├── transcript/                         # Downloaded YouTube subtitles (episode-N.srt)
├── processed/                          # Minified transcripts for model input (episode-N.md)
├── prompts/                            # Reusable system prompts (see "Prompts")
├── scripts/                            # Python tooling (see "Pipelines")
├── researcher/                         # Agentic critique app (see "Researcher Agent")
├── reports/                            # Translation-check fidelity reports (episode-N.md)
├── requirements.txt                    # Python dependencies
├── docs/                               # Static site root (published via GitHub Pages)
│   ├── index.html                      # Homepage: episode-0 intro + episode links
│   ├── episode-N.html                  # One page per episode (N≥1)
│   ├── critique-episode-N.html         # One fact-check page per critiqued episode (N≥1)
│   ├── assets/style.css                # Shared stylesheet (Vazirmatn, RTL)
│   └── robots.txt                      # Crawler rules
├── .gitignore                          # Git ignore rules
├── _config.yml                         # Jekyll/GitHub Pages site config
├── .github/copilot-instructions.md     # Points to AGENTS.md
├── .agents/skills/site-styling/        # LLM skill: themes the generated site
├── .env                                # Gitignored endpoint config (see .env.example)
├── .env.example                        # Committed template for .env
└── AGENTS.md / CLAUDE.md / README.md / COPYRIGHT.md / LICENSE
```

## Episodes

- Episode 0 is the channel introduction video and has no chapters. `info/episode-0.txt` holds only URL, title, description; its post follows the chapter-free list format of `prompts/generate-post-0.md`.

## File Formats

- **info** (`info/episode-N.txt`): video URL (line 1), title, then a multi-line description containing a `Chapters` section of `{m:ss} {TITLE}` lines after a dash separator (timestamps `m:ss`, no leading zero). `info/channel.txt`: channel URL / name / description.
- **transcript** (`transcript/episode-N.srt`): standard SRT — cue number, `HH:MM:SS,mmm --> HH:MM:SS,mmm` timestamp line, then one or more text lines.
- **processed** (`processed/episode-N.md`, built by `process_transcripts.py`): H1 English video title; per chapter an H2 `## {mm:ss} - {TITLE}` with concatenated subtitle text (timestamps normalised to `mm:ss`). Episode 0 has no sections — one text block.
- **content** (`content/episode-N.md`): Persian post; H1 title translated to Persian; per chapter an H2 `## {mm:ss} - {TITLE}` (timestamp becomes a YouTube jump link on the site). Episode 0 uses lists, no sections.

Every section heading must be followed by a blank line.

## Subtitle Extraction

```bash
yt-dlp --cookies-from-browser chrome --write-auto-sub --convert-subs=srt --skip-download {LINK}
```

Rename the resulting `.srt` file to `transcript/episode-N.srt` for episode N.

## LLM Environment

`.env` (gitignored; `.env.example` is the committed template) configures the OpenAI-compatible endpoint used by the scripts:

```
LLM_BASE_URL=https://api.avalai.org/v1
LLM_API_KEY=aa-FILL_ME_IN
LLM_MODEL=deepseek-v4.1-flash
LLM_MODEL_CONTENT=gemini-3.8-flash
LLM_MODEL_REPORT=gemini-3.5-flash-lite
LLM_MODEL_FIX=deepseek-v4.1-flash
LLM_MODEL_SIMPLIFY=gemini-3.5-flash-lite
LLM_MODEL_CRITIQUE=gpt-5.6-terra
LLM_MODEL_CHAT=deepseek-v4.1-flash
LLM_MODEL_AGENT_PLANNER=deepseek-v4.1-flash
LLM_MODEL_AGENT_LEAD=deepseek-v4.1-flash
LLM_MODEL_AGENT_RESEARCH=deepseek-v4.1-flash
LLM_MODEL_AGENT_REVIEWER=deepseek-v4.1-flash
```

Every script prefers a role-specific variable and falls back to the base `LLM_MODEL` when that variable is unset (failing only if both are missing):

- `LLM_MODEL_CHAT` — interactive chat (`chat.py`)
- `LLM_MODEL_CONTENT` — content creation / summarization (`create_content.py`)
- `LLM_MODEL_REPORT` — check/report scripts (`check_translation.py`)
- `LLM_MODEL_FIX` — fix scripts (`fix_translation.py`)
- `LLM_MODEL_SIMPLIFY` — simplification scripts (`simplify_language.py`, `simplify_critique.py`)
- `LLM_MODEL_CRITIQUE` — fact-checking with the `web_search` tool (`critique_content.py`, `critique_content_cited.py`, `check_web_tool.py`)
- `LLM_MODEL_AGENT_PLANNER`, `LLM_MODEL_AGENT_LEAD`, `LLM_MODEL_AGENT_RESEARCH`, `LLM_MODEL_AGENT_REVIEWER` — the agentic critique app (`researcher/`); see "Researcher Agent"

## Prompts (`prompts/`)

- **Post generation** — `generate-post-0.md` (chapter-free intro) and `generate-post-N.md` (transcript-based, N≥1) work with any model; no native YouTube access. `web-generate-posts*.md` are for **Gemini** models (native YouTube access), used manually with **Gemini 3.1 Pro**. For non-Gemini models, pass `transcript/episode-N.srt` alongside the video URL and chapters.
- **Critique** — `research-critique.md` (content only) and `research-critique-full.md` (+ transcript) fact-check each chapter against authoritative English sources, keeping every chapter heading verbatim (timestamp + title) and never dropping one. The `-cite` variants (`research-critique-cite.md`, `research-critique-full-cite.md`) add inline `[cite: N]` markers and a numbered URL list; full rules are in the prompts. `critique_content.py` uses only the non-cite prompts; `critique_content_cited.py` uses only the `-cite` prompts (writes `critique/episode-N-cite.md`).
- **Translation** — `check-translation.md` (input: transcript, blank line, `--`, blank line, post) reports per-problem-chapter headings with corrected Persian text; `fix-translation.md` (input: post, blank line, `---`, blank line, report) applies those corrections, outputting a full post conforming to `generate-post-N.md`'s structure.
- **Simplification** — `simplify-language.md` (input: a Persian post) rewrites it in plainer Persian for Iranian readers. It is a language-simplification pass, not a summary: the structure (H1 title and every chapter heading verbatim) and all content are preserved; only the wording is simplified.
- **Critique simplification** — `simplify-critique.md` (input: a Persian critique) rewrites it in plainer Persian the same way: the structure (H1 title, overall assessment, and every chapter heading byte-identical) and all content — including every judgement and verdict — are preserved; only the wording is simplified.

## Pipelines

### Content Pipeline

1. Extract video metadata (URL, title, description, chapters) into `info/episode-N.txt`.
2. Download subtitles with yt-dlp into `transcript/episode-N.srt` (see Subtitle Extraction).
3. Run `python3 scripts/process_transcripts.py` → `processed/episode-N.md`.
4. Run `python3 scripts/create_content.py N` → `content/episode-N.md` (uses `generate-post-0.md` for episode 0, `generate-post-N.md` for N≥1).

### Critique Pipeline

`python3 scripts/critique_content.py N [--full]` fact-checks the post and writes `critique/episode-N.md`. It calls the endpoint with `LLM_MODEL_CRITIQUE` (base `LLM_MODEL` fallback) plus a `web_search` tool; `--full` additionally passes the transcript from `processed/episode-N.md` for cross-referencing.

`python3 scripts/critique_content_cited.py N [--full]` is the same fact-check but with the `-cite` prompts, adding inline `[cite: N]` markers and a numbered URL list; it writes `critique/episode-N-cite.md` instead.

### Researcher Agent

`python3 researcher/main.py N [--verbose] [--max-topics K] [--max-tool-calls K] [--max-review-rounds K] [--out PATH] [--resume RUN_ID]` is an agentic replacement for the critique scripts. It reads `content/episode-N.md` and `processed/episode-N.md`, plans research topics (`LLM_MODEL_AGENT_PLANNER`), runs one research subagent per topic in parallel with real client-side tools (`web_search` via `ddgs`, `fetch_url` for HTML/PDF, `url_alive`, `read_transcript`, `note_write`) using `LLM_MODEL_AGENT_RESEARCH`, writes the cited critique with `LLM_MODEL_AGENT_LEAD`, then a reviewer/fixer (`LLM_MODEL_AGENT_REVIEWER`) fact-checks and repairs it until the deterministic gates in `researcher/validate.py` pass (heading parity, citation self-consistency, URL provenance and liveness).

Output goes to `researcher/files/result/episode-N.md`; per-run artifacts (trace, plan, notes, draft, reviewer passes, sources) go under `researcher/files/runs/<timestamp>-episode-N/` (gitignored). If the gates cannot be satisfied, it exits non-zero and writes `episode-N.failed.md` instead. See `researcher/DESIGN.md` and `researcher/README.md`.

### Translation Check & Fix Pipeline

- `python3 scripts/check_translation.py N` — compares `processed/episode-N.md` against `content/episode-N.md` via `LLM_MODEL_REPORT` (no web search) and writes a fidelity report (verbatim headings + full corrected Persian text per problem chapter) to `reports/episode-N.md`.
- `python3 scripts/fix_translation.py N` — applies that report to the post via `LLM_MODEL_FIX`, rewriting `content/episode-N.md`; only flagged text changes.

### Language Simplification Pipeline

- `python3 scripts/simplify_language.py N` — a second, post-fix iteration on the content: rewrites `content/episode-N.md` in plainer Persian via `prompts/simplify-language.md` and `LLM_MODEL_SIMPLIFY` (no web search). It is a language-simplification pass, not a summary — the H1 title and every chapter heading are kept verbatim and all content is preserved; only the wording is simplified. Overwrites `content/episode-N.md`.
- `python3 scripts/simplify_critique.py N` — the same pass for the critique: rewrites `critique/episode-N.md` in plainer Persian via `prompts/simplify-critique.md` and `LLM_MODEL_SIMPLIFY` (no web search). The structure (H1 title, overall assessment, and every chapter heading byte-identical — heading parity with the article is preserved) and all content, including every judgement and verdict, are kept; only the wording is simplified. Overwrites `critique/episode-N.md`.

### Website Build

`python3 scripts/build_site.py` deterministically generates the site under `docs/`:

- Parses each post into semantic RTL Persian HTML (Vazirmatn, shared `docs/assets/style.css`). Each `## {mm:ss} - {TITLE}` becomes a chapter section whose title links to the matching video moment (`&t={seconds}` from `info/episode-N.txt`); the timestamp is carried by the link but not displayed.
- Writes `docs/episode-N.html` (N≥1) and `docs/index.html` (embeds the episode-0 intro and links every episode).
- For each `critique/episode-N.md`, writes `docs/critique-episode-N.html` with the same H1 and chapter headings but no video links (heading parity validated by `check_critiques.py`).
- Article↔critique cross-links: magnifier icons (`a.critique-link`) on article headings point to the critique, back arrows on critique headings point to the article; anchors pair `ch-{i}` / `critique-{i}`.
- Consistent chrome: article H1 links to the video, header/footer link to the channel with an AI-generated disclaimer, GitHub ribbon, and a source link on episode pages.

Division of labor: `build_site.py` owns content and structure (deterministic source of truth for the `.html` files); the styling layer lives in `docs/assets/style.css` and the page-shell templates inside the script, so regeneration keeps the design. Do not hand-edit generated bodies — change `content/episode-N.md` (or the templates) and rebuild.

## Skills

Project-specific LLM skills live in `.agents/skills/`, each a `SKILL.md` plus optional helper files, loaded with the `skill` tool when a task matches.

- [`site-styling`](/.agents/skills/site-styling/SKILL.md) — themes the generated site via `docs/assets/style.css` (and, if needed, the page-shell markup in `build_site.py`), preserving content fidelity: never alter article text, headings, or `mm:ss` timestamps, keep the cross-link icons and anchor ids intact, and stay RTL, Persian, Vazirmatn-rendered, and responsive.

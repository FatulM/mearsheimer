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
LLM_MODEL=gemini-3.8-flash
LLM_MODEL_CRITIQUE=gpt-5.6-terra
```

`create_content.py` and the check/fix-translation scripts use `LLM_MODEL`; `critique_content.py` uses `LLM_MODEL_CRITIQUE`.

## Prompts (`prompts/`)

- **Post generation** — `generate-post-0.md` (chapter-free intro) and `generate-post-N.md` (transcript-based, N≥1) work with any model; no native YouTube access. `web-generate-posts*.md` are for **Gemini** models (native YouTube access), used manually with **Gemini 3.1 Pro**. For non-Gemini models, pass `transcript/episode-N.srt` alongside the video URL and chapters.
- **Critique** — `research-critique.md` (content only) and `research-critique-full.md` (+ transcript) fact-check each chapter against authoritative English sources, keeping every chapter heading verbatim (timestamp + title) and never dropping one. The `-cite` variants (`research-critique-cite.md`, `research-critique-full-cite.md`) add inline `[cite: N]` markers and a numbered URL list; full rules are in the prompts. `critique_content.py` uses only the non-cite prompts.
- **Translation** — `check-translation.md` (input: transcript, blank line, `--`, blank line, post) reports per-problem-chapter headings with corrected Persian text; `fix-translation.md` (input: post, blank line, `---`, blank line, report) applies those corrections, outputting a full post conforming to `generate-post-N.md`'s structure.

## Pipelines

### Content Pipeline

1. Extract video metadata (URL, title, description, chapters) into `info/episode-N.txt`.
2. Download subtitles with yt-dlp into `transcript/episode-N.srt` (see Subtitle Extraction).
3. Run `python3 scripts/process_transcripts.py` → `processed/episode-N.md`.
4. Run `python3 scripts/create_content.py N` → `content/episode-N.md` (uses `generate-post-0.md` for episode 0, `generate-post-N.md` for N≥1).

### Critique Pipeline

`python3 scripts/critique_content.py N [--full]` fact-checks the post and writes `critique/episode-N.md`. It calls the endpoint with `LLM_MODEL_CRITIQUE` plus a `web_search` tool; `--full` additionally passes the transcript from `processed/episode-N.md` for cross-referencing.

### Translation Check & Fix Pipeline

- `python3 scripts/check_translation.py N` — compares `processed/episode-N.md` against `content/episode-N.md` via `LLM_MODEL` (no web search) and writes a fidelity report (verbatim headings + full corrected Persian text per problem chapter) to `reports/episode-N.md`.
- `python3 scripts/fix_translation.py N` — applies that report to the post, rewriting `content/episode-N.md`; only flagged text changes.

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

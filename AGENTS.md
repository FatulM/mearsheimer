# Agent Instructions

## Project

This repository builds a static Persian (Farsi) blog about John Mearsheimer's YouTube videos. Each episode becomes a Persian post linked to its original video. GitHub Pages hosts the site.

## Environment and Commands

- Work from the repository root.
- Use the Python 3.12 virtual environment: `source .venv/bin/activate`.
- Create it when needed: `python3.12 -m venv .venv && source .venv/bin/activate && pip install -U pip && pip install -r requirements.txt`.
- Format Python: `ruff format scripts`.
- Check formatting: `ruff format --check scripts`.
- Lint Python: `ruff check scripts`.
- Validate imports: `python -m compileall scripts`.

## Rules

- Never read `.env`. Use `.env.example` as its template.
- Never commit, stage, reset, or discard changes unless the user asks.
- Preserve unrelated user changes.
- Keep Python lines at 120 characters or fewer.
- Keep Markdown headings followed by a blank line.
- Always end textual files (code, docs, etc.) with a blank line.
- Write website content in Persian for Iranian readers unless the user asks otherwise.
- Keep HTML, CSS, and JavaScript RTL and use the Vazirmatn font.
- Edit source Markdown before generated HTML.
- Treat `docs/` as the GitHub Pages root.
- Store project skills in `.agents/skills/`.

## Structure

`content/` contains Persian posts. `critique/` contains fact checks. `info/` contains metadata. `transcript/` and `processed/` contain subtitle inputs. `prompts/` contains reusable prompts. `scripts/` contains tooling. `researcher/` contains the agentic critique app. `reports/` contains translation reports. `docs/` contains the generated site.

## File Formats

- `info/episode-N.txt`: URL, title, and description. The description contains a `Chapters` section with `{m:ss} {TITLE}` lines after a dash. Timestamps have no leading zero. `info/channel.txt` stores channel metadata.
- `transcript/episode-N.srt`: standard SRT cues with `HH:MM:SS,mmm --> HH:MM:SS,mmm` timestamps.
- `processed/episode-N.md`: English H1 title, then `## {mm:ss} - {TITLE}` sections with merged subtitle text. Episode 0 has one text block and no sections.
- `content/episode-N.md`: Persian H1 title and matching chapter headings. Episode 0 uses lists instead of sections. Each heading must have a blank line after it.

Episode 0 is the channel introduction. Its metadata has no chapters, and its post follows `prompts/generate-post-0.md`.

## Subtitle Extraction

```bash
yt-dlp --cookies-from-browser chrome --write-auto-sub --convert-subs=srt --skip-download {LINK}
```

Rename the downloaded subtitle file to `transcript/episode-N.srt`.

## LLM Configuration

`.env` is gitignored and uses an OpenAI-compatible endpoint. The committed template contains these variables:

```text
LLM_BASE_URL
LLM_API_KEY
LLM_MODEL
LLM_MODEL_*
```

Each script uses its role-specific model variable and falls back to `LLM_MODEL`. It fails only when both are missing.

| Variable | Used by |
| --- | --- |
| `LLM_MODEL_CHAT` | `chat.py` |
| `LLM_MODEL_CONTENT` | `create_content.py` |
| `LLM_MODEL_REPORT` | `check_translation.py` |
| `LLM_MODEL_FIX` | `fix_translation.py` |
| `LLM_MODEL_SIMPLIFY` | `simplify_language.py`, `simplify_critique.py` |
| `LLM_MODEL_CRITIQUE` | Critique scripts and `check_web_tool.py` |
| `LLM_MODEL_AGENT_*` | `researcher/` |

## Pipelines

### Content

1. Save metadata in `info/episode-N.txt`.
2. Download subtitles to `transcript/episode-N.srt`.
3. Run `python3 scripts/process_transcripts.py`.
4. Run `python3 scripts/create_content.py N`. This uses `generate-post-0.md` for episode 0 and `generate-post-N.md` otherwise.

`web-generate-posts*.md` is for Gemini with native YouTube access. Other models need the transcript, video URL, and chapters.

### Critique

Run `python3 scripts/critique_content.py N [--full]` for a critique without citations, or `python3 scripts/critique_content_cite.py N [--full]` for inline citations and a URL list. Both use `LLM_MODEL_CRITIQUE` and `web_search`. `--full` also supplies the processed transcript. Preserve every chapter heading. The prompts are `research-critique*.md` and their `-cite` variants.

### Researcher Agent

Run:

```bash
python3 researcher/main.py N [--verbose] [--max-topics K] [--max-tool-calls K] [--max-review-rounds K] [--out PATH] [--run-id RUN_ID]
```

The agent reads the post and processed transcript, plans topics, researches them in parallel, writes a cited critique, and reviews it. It uses `web_search`, `fetch_url`, `url_alive`, `read_transcript`, and `note_write`. Mechanical repairs run before deterministic gates for heading parity, citation consistency and coverage, fetched URL provenance, and URL liveness.

Successful output goes to `researcher/files/result/episode-N.md`. Run artifacts go to `researcher/files/runs/<timestamp>-episode-N/` and are gitignored. A failed run exits non-zero and writes `episode-N.failed.md`. See `researcher/DESIGN.md` and `researcher/README.md`.

### Researcher Language Simplification

Run:

```bash
python3 researcher/simplify.py N [--verbose] [--max-rounds K] [--out PATH] [--run-id RUN_ID]
```

The script preserves the original critique, citations, headings, claims, judgements, and citation placement while simplifying the Persian body. A reviewer/fixer loop checks and repairs the result. Deterministic gates run before each review and before writing. The output goes to `researcher/files/simplify/episode-N.md` or `.failed.md`; artifacts go to `researcher/files/runs/<timestamp>-episode-N-language/`.

### Translation and Simplification

- `python3 scripts/check_translation.py N` compares `processed/episode-N.md` with `content/episode-N.md` and writes `reports/episode-N.md`.
- `python3 scripts/fix_translation.py N` applies the report to `content/episode-N.md` and changes only flagged text.
- `python3 scripts/simplify_language.py N` simplifies a post without changing its title, headings, structure, or content.
- `python3 scripts/simplify_critique.py N` does the same for a critique, including all judgements, verdicts, and heading parity.

## Website Build

Run `python3 scripts/build_site.py` to generate `docs/`.

- The script parses Markdown into semantic RTL HTML and turns each chapter timestamp into a YouTube jump link. The timestamp is not displayed.
- It writes episode pages, the homepage, and critique pages. Critique pages preserve headings and render `[cite: N]` markers as links to their references.
- Article headings link to critiques with magnifier icons. Critique headings link back with arrow icons. Keep `ch-{i}` and `critique-{i}` anchors intact.
- Shared page chrome includes the channel link, AI-generated disclaimer, GitHub ribbon, and episode source link.
- `build_site.py` owns content and structure. `docs/assets/style.css` owns styling. Do not hand-edit generated bodies. Change Markdown or templates, then rebuild.

## Skills

Project skills live in `.agents/skills/` as `SKILL.md` files with optional helpers. Use the `site-styling` skill for CSS or page-shell changes. Preserve article text, headings, timestamps, cross-link icons, anchor IDs, RTL layout, Persian text, Vazirmatn, and responsive behavior.

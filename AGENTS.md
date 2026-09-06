# Agent Instructions

## Project Description

This is a static Persian (Farsi) website that presents blog-style Persian summaries of the videos from [John Mearsheimer's YouTube channel](https://www.youtube.com/@JohnMearsheimer). Each episode of the channel becomes a Persian blog post on the website, linked to the original YouTube video. The website will be hosted on GitHub Pages.

## Environment

- Python 3.12 venv at `.venv/` folder.
- Always activate: `source .venv/bin/activate`
- Work dir is repo root.

## Environment Setup

Creating the environment is done manually by the user.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

## Commands

- Install deps: `pip install -r requirements.txt`
- Format: `ruff format scripts`
- Check formatting: `ruff format --check scripts`
- Lint: `ruff check scripts`
- Validate imports: `python -m compileall scripts`
- Build the website: `python3 scripts/build_site.py`

## Conventions

- Never commit, stage, reset, or discard changes unless explicitly requested. Preserve unrelated user changes.
- 120-char line length for .py files
- Markdown documents have no line-length limit.
- Markdown headings must be followed by a blank line.
- All textual files, including code and documents, must end with a newline.
- Project-specific skills are in the `.agents/skills/` folder.
- All website content will be in Persian (Farsi) language for Iranian Readers unless explicitly requested otherwise.
- HTML/CSS/JS changes should maintain RTL layout and Vazirmatn font usage.
- Content updates should be made first to source `.md` files then reflected in html `.html` files.
- `www/` is the static site root published via GitHub Pages; all HTML, CSS, and crawler files live there.

## Project Structure

```
mearsheimer/
├── content/                    # Persian blog posts for the website
│   └── episode-N.md            # Persian blog post for episode N (generated with prompts/generate-post-0.md or generate-post-N.md)
├── info/                       # Episode and channel metadata
│   ├── channel.txt             # Channel metadata (URL, title, description)
│   └── episode-N.txt           # Video URL + title + description + chapters for episode N (metadata source)
├── transcript/                 # Downloaded YouTube subtitles (reference)
│   └── episode-N.srt           # Subtitles for episode N
├── processed/                  # Minified subtitle files for model input (generated)
│   └── episode-N.md            # Minified transcript for episode N (generated with scripts/process_transcripts.py)
├── prompts/
│   ├── generate-post-0.md      # System prompt for generating the Persian intro post from processed/episode-0.md
│   ├── generate-post-N.md      # System prompt for generating Persian posts from processed/episode-N.md (N≥1)
│   ├── web-generate-posts.md   # System prompt (for models with YouTube/web access) covering both the intro and N≥1 videos
│   └── web-generate-posts-N.md # System prompt (for models with YouTube/web access) for N≥1 videos from link + chapters
├── scripts/
│   ├── process_transcripts.py  # Minifies info + SRT into processed/episode-N.md
│   ├── create_content.py       # Generates content/episode-N.md via the .env-configured LLM endpoint
│   ├── check_timestamps.py     # Validates content/episode-N.md section timestamps against info/episode-N.txt chapters
│   └── build_site.py           # Deterministically converts content/*.md into the static RTL site under www/
├── requirements.txt            # Python dependencies
├── www/                        # Static site root (published via GitHub Pages)
│   ├── index.html              # Homepage: episode-0 intro article + links to episode pages
│   ├── episode-N.html          # One generated page per episode (N≥1)
│   ├── assets/                 # Site assets; assets/style.css is the shared stylesheet
│   └── robots.txt              # Crawler rules
├── .github/
│   └── copilot-instructions.md # Points to AGENTS.md
├── .agents/
│   └── skills/
│       └── site-styling/       # LLM skill: themes the generated site (CSS + page shell)
├── .env.example                # Committed template for the gitignored .env (LLM endpoint config)
├── AGENTS.md                   # Agent instructions (this file)
├── CLAUDE.md                   # Points to AGENTS.md
├── README.md                   # Project overview
├── COPYRIGHT.md                # Copyright and disclaimer notice for extracted YouTube materials
└── LICENSE                     # BSD 3-Clause license for the repository code
```

## Model Requirements for Post Generation

- `prompts/generate-post-0.md` and `prompts/generate-post-N.md` are used when the model is given the video details from `processed/episode-0.md` / `processed/episode-N.md` (the video title and the transcript text or chapters). These work with any model; no native YouTube access is required.
- `prompts/web-generate-posts.md` and `prompts/web-generate-posts-N.md` are written for **Gemini** models, which have native access to YouTube videos (title, description, chapters, and transcripts) from just the video URL. The user provides the video link and the chapters copied from the video description. These prompts are used manually in a chat with the best model for this task as of today, **Gemini 3.1 Pro**; this is separate from the `LLM_MODEL` configured in `.env`, which `scripts/create_content.py` uses for the transcript-based pipeline.
- When using a non-Gemini model (or any model without native YouTube access), the prompt must be slightly adapted: pass the downloaded `transcript/episode-N.srt` subtitles into the prompt alongside the video URL and chapters.

## Episodes

- Episode 0 is the channel introduction video. It has no chapters, so `info/episode-0.txt` holds the URL, title, and description without a chapters section, and its post follows the chapter-free list-based format described in `prompts/generate-post-0.md`.

## Info File Format

Each `info/episode-N.txt` is structured as follows:

1. The video URL (first line).
2. The video title.
3. The video description, which spans multiple lines and contains the chapters info (a `Chapters` section listing `{m:ss} {TITLE}` lines, preceded by a dash separator line). Timestamps here use `m:ss`, i.e. minutes with no leading zero.

`info/channel.txt` is structured as follows:

1. The channel URL (first line).
2. The channel name.
3. The channel description text.

## Transcript Format

`transcript/episode-N.srt` is a standard SRT subtitle file downloaded from YouTube. It is a sequence of cues separated by blank lines, each cue consisting of:

1. The cue number (starting at 1).
2. A timestamp line: `HH:MM:SS,mmm --> HH:MM:SS,mmm`.
3. One or more lines of subtitle text.

## Processed File Format

`processed/episode-N.md` is the minified subtitle content used as model input when generating the Persian post. It is generated from the chapters in `info/episode-N.txt` and the subtitles in `transcript/episode-N.srt` by `scripts/process_transcripts.py`. Its structure is:

1. The first line is the H1 heading `# {VIDEO TITLE}` (the English video title from the info file).
2. For episodes with chapters, each section starts with an H2 heading `## {mm:ss} - {TITLE}`, followed by the concatenated subtitle text of that chapter (cue numbers and per-cue timestamps are stripped). Timestamps here are normalised to `mm:ss` (minutes with a leading zero when needed).
3. For the chapter-free introduction episode (episode 0), there are no sections; the body is the entire transcript's text as a single text block.

Every section heading must be followed by a blank line.

## Content Format

`content/episode-N.md` is a Persian Markdown blog post with the following structure:

1. The first line is the H1 heading `# {VIDEO TITLE}`, with the title translated into Persian rather than the English title. The episode page title is taken from this H1.
2. For episodes with chapters, each section starts with an H2 heading `## {mm:ss} - {TITLE}`. The pipeline converts the timestamp into a link to the matching moment of the YouTube video.
3. For the chapter-free introduction episode (episode 0), there are no sections; the body uses lists instead.

Every section heading must be followed by a blank line.

## Subtitle Extraction

YouTube subtitles are downloaded with yt-dlp for reference into `transcript/episode-N.srt`:

```bash
yt-dlp --cookies-from-browser chrome --write-auto-sub --convert-subs=srt --skip-download {LINK}
```

After downloading, rename the resulting `.srt` file to `transcript/episode-N.srt` for episode N.

## LLM Environment

`.env` configures the OpenAI-compatible endpoint used by `scripts/create_content.py`. It is gitignored; `.env.example` is the committed template.

```
LLM_BASE_URL=https://api.avalai.org/v1
LLM_API_KEY=aa-FILL_ME_IN
LLM_MODEL=gemini-3.8-flash
```

`scripts/create_content.py` reads the minified transcript, sends it to the model as the user content with the matching prompt in `prompts/` as the system prompt, and writes the Model output to `content/episode-N.md`.

## Content Pipeline

1. Extract video metadata (URL, title, description, chapters) into `info/episode-N.txt`.
2. Download subtitles with yt-dlp into `transcript/episode-N.srt` (see Subtitle Extraction).
3. Run `python3 scripts/process_transcripts.py` to generate `processed/episode-N.md`.
4. Run `python3 scripts/create_content.py N` to generate the Persian blog post `content/episode-N.md`, reading `processed/episode-N.md` and the matching system prompt (`prompts/generate-post-0.md` for episode 0, `prompts/generate-post-N.md` for N≥1) and calling the OpenAI-compatible endpoint configured in `.env`.

## Website Build

`scripts/build_site.py` deterministically converts the Persian posts into the static, hostable site under `www/`:

1. It parses each `content/episode-N.md` into semantic HTML (H1 title, H2 chapter sections, `**bold**`, nested `*` bullets, and ordered lists with Persian numerals).
2. For episodes with chapters, each `## {mm:ss} - {TITLE}` heading becomes a chapter section whose heading shows only the (Persian) title, linked to the matching moment of the source YouTube video via `&t={seconds}` read from `info/episode-N.txt`. The `mm:ss` timestamp is carried by the link but not displayed. This mirrors the timestamp logic validated by `check_timestamps.py`.
3. It writes `www/episode-N.html` for every episode **N≥1** and `www/index.html`, the homepage that embeds the episode-0 intro article (episode 0 has no page of its own) and links to every episode sub-page.
4. Every page is fully RTL, `lang="fa"`, uses the Vazirmatn typeface, and shares a single stylesheet at `www/assets/style.css`.
5. Page chrome is consistent across pages: the article's H1 links to the source video, the header subtitle links to the YouTube channel, the footer links to the channel and notes that the content is AI-generated and may contain errors, and a GitHub ribbon (`برو به گیت‌هاب`) in the top-right corner links to the repository. Episode pages end with a `منبع: تماشای ویدیوی اصلی` link; the homepage places the same link just before the episode listing.

Run it with:

```bash
python3 scripts/build_site.py
```

### Division of labor: generator vs styling skill

- `scripts/build_site.py` owns **content and structure** — accurate markdown→HTML, correct chapter jump-links, the page shell (header/nav/footer), and the `index.html` episode cards. Deterministic and reproducible, so it is the source of truth for the generated `.html` files.
- The **styling layer** lives in `www/assets/style.css` and the page-shell templates inside `build_site.py`. Regeneration reuses these, so your design is never lost when new episodes are added. Do not hand-edit generated article bodies; change the content in `content/episode-N.md` (or the templates in the script) and rebuild.

## Skills

Project-specific LLM skills live in `.agents/skills/`. Each skill is a `SKILL.md` plus optional helper files and is loaded with the `skill` tool when a task matches its description.

- [`site-styling`](/.agents/skills/site-styling/SKILL.md) — themes the site generated by `scripts/build_site.py` to its final look. It targets the shared stylesheet `www/assets/style.css` and, when necessary, the page-shell markup inside the script. It must preserve content fidelity: never alter article text, chapter headings, or the `mm:ss` timestamps (which are exact YouTube jump-links). The agent must keep the site RTL, Persian, Vazirmatn-rendered, and responsive.

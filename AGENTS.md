# Agent Instructions

## Project Description

This is a static Persian (Farsi) website that presents blog-style Persian summaries of the videos from John Mearsheimer's YouTube channel (https://www.youtube.com/@JohnMearsheimer). Each episode of the channel becomes a Persian blog post on the website, linked to the original YouTube video. The website will be hosted on GitHub Pages.

## Conventions

- Never commit, stage, reset, or discard changes unless explicitly requested. Preserve unrelated user changes.
- Markdown documents have no line-length limit.
- Markdown headings must be followed by a blank line.
- All textual files, including code and documents, must end with a newline.
- Skills are in the `.agents/skills/` folder.
- All website content will be in Persian (Farsi) language for Iranian Readers unless explicitly requested otherwise.
- HTML/CSS/JS changes should maintain RTL layout and Vazirmatn font usage.
- Content updates should be made first to source `.md` files then reflected in html `.html` files.

## Project Structure

TODO: Add other files and folders.

```
mearsheimer/
├── content/                    # Persian blog posts for the website
│   └── episode-N.md            # Persian blog post for episode N (generated with prompts/generate-post.md)
├── info/                       # Episode and channel metadata
│   ├── channel.txt             # Channel metadata (URL, title, description)
│   └── episode-N.txt           # Video URL + title + description + chapters for episode N (metadata source)
├── transcript/                 # Downloaded YouTube subtitles (reference)
│   └── episode-N.srt           # Subtitles for episode N
├── prompts/
│   └── generate-post.md        # System prompt used to generate Persian posts from videos
├── .github/
│   └── copilot-instructions.md # Points to AGENTS.md
├── robots.txt                  # Crawler rules
├── AGENTS.md                   # Agent instructions (this file)
├── CLAUDE.md                   # Points to AGENTS.md
├── README.md                   # Project overview and workflow docs
└── LICENSE                     # License file
```

## Model Requirements for Post Generation

- `prompts/generate-post.md` is written for **Gemini** models, which have native access to YouTube videos (title, description, chapters, and transcripts) from just the video URL. The best model for this task as of today is **Gemini 3.1 Pro**.
- When using a non-Gemini model (or any model without native YouTube access), the prompt must be slightly adapted: pass the downloaded `transcript/episode-N.srt` subtitles into the prompt alongside the video URL and chapters.

## Episodes

- Episode 0 is the channel introduction video. It has no chapters, so `info/episode-0.txt` contains only the video URL and its post follows the chapter-free list-based format described in `prompts/generate-post.md`.

## Info File Format

Each `info/episode-N.txt` is structured as follows:

1. The video URL (first line).
2. The video title.
3. The video description, which spans multiple lines and contains the chapters info (a `Chapters` section listing `{mm:ss} {TITLE}` lines, preceded by a dash separator line).

`info/channel.txt` is structured as follows:

1. The channel URL (first line).
2. The channel name.
3. The channel description text.

## Transcript Format

`transcript/episode-N.srt` is a standard SRT subtitle file downloaded from YouTube. It is a sequence of cues separated by blank lines, each cue consisting of:

1. The cue number (starting at 1).
2. A timestamp line: `HH:MM:SS,mmm --> HH:MM:SS,mmm`.
3. One or more lines of subtitle text.

Transcripts are reference only; They are passed into the post-generation prompt only when using a model without native YouTube access (see Model Requirements for Post Generation).

## Content Format

`content/episode-N.md` is a Persian Markdown blog post with the following structure:

1. The first line is the H1 heading `# {VIDEO TITLE}`.
2. For episodes with chapters, each section starts with an H2 heading `## {mm:ss} - {TITLE}`. The pipeline converts the timestamp into a link to the matching moment of the YouTube video.
3. For the chapter-free introduction episode (episode 0), there are no sections; the body uses lists instead.

Every section heading must be followed by a blank line.

## Subtitle Extraction

YouTube subtitles are downloaded with yt-dlp for reference into `transcript/episode-N.srt`:

```bash
yt-dlp --cookies-from-browser chrome --write-auto-sub --convert-subs=srt --skip-download {LINK}
```

After downloading, rename the resulting `.srt` file to `transcript/episode-N.srt` for episode N.

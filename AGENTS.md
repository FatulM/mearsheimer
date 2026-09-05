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
├── content/                    # Source content for the website
│   ├── channel.txt             # Channel metadata (URL, title, description)
│   ├── episode-N.txt           # Video URL + title + description + chapters for episode N (metadata source)
│   ├── episode-N.srt           # Downloaded YouTube subtitles for episode N (reference)
│   └── episode-N.md            # Persian blog post for episode N (generated with prompts/PROMPT.md)
├── prompts/
│   └── PROMPT.md               # System prompt used to generate Persian posts from videos
├── .github/
│   └── copilot-instructions.md # Points to AGENTS.md
├── robots.txt                  # Crawler rules
├── AGENTS.md                   # Agent instructions (this file)
├── CLAUDE.md                   # Points to AGENTS.md
├── README.md                   # Project overview and workflow docs
└── LICENSE                     # License file
```

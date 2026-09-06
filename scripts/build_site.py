#!/usr/bin/env python3
"""
Build the static Persian website (docs/) from the generated Markdown posts.

Reads the Persian blog posts in content/episode-N.md and the video metadata in
info/episode-N.txt, then renders a complete RTL site under docs/:

  * index.html                 - homepage: the episode-0 intro article + links to all episode pages
  * episode-N.html             - one page per episode (N≥1), each chapter heading linked to
                                 the matching moment of the source YouTube video
  * assets/style.css           - shared stylesheet (hand-written / LLM-themed)

The markdown source is deliberately small and regular, so this script performs a
deterministic conversion (escaping, `**bold**`, nested `*` bullets, and ordered
lists) rather than relying on an external markdown library. The design layer
(colors, fonts, layout) lives in assets/style.css and is kept separate so that
regenerating the site never overwrites the theming.

Usage:
    python3 scripts/build_site.py
"""

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content"
INFO_DIR = ROOT / "info"
DOCS_DIR = ROOT / "docs"
ASSETS_DIR = DOCS_DIR / "assets"

SITE_TITLE = "جان میرشایمر"
SITE_SUBTITLE = "وب‌لاگ فارسی رویدادها و تحلیل‌های جان میرشایمر"
CHANNEL_URL = "https://www.youtube.com/@JohnMearsheimer"
GITHUB_URL = "https://github.com/FatulM/mearsheimer"

H1_RE = re.compile(r"^#\s+(.+)$")
H2_RE = re.compile(r"^##\s+(\d{1,2}:\d{2}(?::\d{2})?)\s*-\s*(.+)$")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
BULLET_RE = re.compile(r"^\s*\*\s+(.+)$")
ORDERED_RE = re.compile(r"^[۰-۹0-9]+\s*[.)]\s*(.+)$")


def inline(text: str) -> str:
    """Escape raw text then turn `**bold**` spans into <strong>."""
    escaped = html.escape(text)
    # Replace bold in two steps so nesting/overlap never corrupts the output.
    while BOLD_RE.search(escaped):
        escaped = BOLD_RE.sub(r"<strong>\1</strong>", escaped, count=1)
    return escaped


def timestamp_to_seconds(ts: str) -> int:
    """Convert an 'mm:ss' or 'h:mm:ss' timestamp into whole seconds."""
    parts = [int(p) for p in ts.split(":")]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def render_bullets(items: list[tuple[int, str]]) -> str:
    """Render a flat list of (depth, text) bullets as nested <ul>/<li>."""
    if not items:
        return ""
    base = items[0][0]
    out = []
    i = 0
    while i < len(items):
        _, text = items[i]
        out.append(f"<li>{inline(text)}")
        j = i + 1
        if j < len(items) and items[j][0] > base:
            children = []
            while j < len(items) and items[j][0] > base:
                children.append(items[j])
                j += 1
            reduced = [(d - base, t) for d, t in children]
            out.append("<ul>" + render_bullets(reduced) + "</ul>")
        i = j
        out.append("</li>")
    return "".join(out)


def render_ordered(lines: list[str]) -> str:
    """Render consecutive ordered-list lines as an <ol> with Persian numerals kept."""
    items = "\n".join(f"<li>{inline(line)}</li>" for line in lines)
    return f'<ol class="ordered">\n{items}\n</ol>'


def render_body(lines: list[str], video_url: str) -> str:
    """Turn the content lines (below the H1 title) into HTML, block by block."""

    # First pass: split lines into contiguous segments of the same block type.
    segments: list[tuple[str, list[str]]] = []
    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if H2_RE.match(line):
            segments.append(("h2", [line]))
            continue
        if BULLET_RE.match(line):
            indent = len(line) - len(line.lstrip())
            if segments and segments[-1][0] == "bullets":
                segments[-1][1].append((indent, BULLET_RE.match(line).group(1)))
            else:
                segments.append(("bullets", [(indent, BULLET_RE.match(line).group(1))]))
            continue
        if ORDERED_RE.match(stripped):
            if segments and segments[-1][0] == "ordered":
                segments[-1][1].append(stripped)
            else:
                segments.append(("ordered", [stripped]))
            continue
        segments.append(("para", [stripped]))

    # Second pass: turn each segment into HTML.
    blocks: list[str] = []
    for kind, payload in segments:
        if kind == "h2":
            h2 = H2_RE.match(payload[0])
            ts, title = h2.group(1), h2.group(2)
            secs = timestamp_to_seconds(ts)
            link = f"{video_url}&t={secs}s"
            blocks.append(
                f'<h2><a class="chapter" href="{link}">{inline(title)}</a></h2>'
            )
        elif kind == "bullets":
            blocks.append("<ul>\n" + render_bullets(payload) + "\n</ul>")
        elif kind == "ordered":
            blocks.append(render_ordered(payload))
        else:
            blocks.append(f"<p>{inline(payload[0])}</p>")

    return "\n\n".join(blocks)


def video_source_paragraph(video_url: str) -> str:
    return (
        '<p class="video-source">منبع: '
        f'<a href="{video_url}" rel="noopener noreferrer" target="_blank">'
        "تماشای ویدیوی اصلی</a></p>"
    )


def page_template(
    *,
    title: str,
    h1: str,
    h1_url: str | None,
    body: str,
    nav_links: str,
) -> str:
    """Wrap article body into a complete RTL HTML document."""
    if h1_url:
        h1_html = (
            f'<h1><a class="article-title" href="{h1_url}">{html.escape(h1)}</a></h1>'
        )
    else:
        h1_html = f"<h1>{html.escape(h1)}</h1>"
    return (
        "<!doctype html>\n"
        '<html lang="fa" dir="rtl">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"  <title>{html.escape(title)}</title>\n"
        '  <link rel="stylesheet" href="assets/style.css">\n'
        "</head>\n"
        "<body>\n"
        f'<a class="github-ribbon" href="{GITHUB_URL}" '
        'rel="noopener noreferrer" target="_blank">برو به گیت‌هاب</a>\n'
        '<header class="site-header">\n'
        f'  <nav class="site-nav">{nav_links}</nav>\n'
        f'  <p class="site-subtitle">'
        f'<a href="{CHANNEL_URL}" rel="noopener noreferrer" target="_blank">'
        f"{SITE_SUBTITLE}</a></p>\n"
        "</header>\n"
        '<main class="content">\n'
        f"  <article>\n"
        f"{h1_html}\n"
        f"{body}\n"
        "  </article>\n"
        "</main>\n"
        '<footer class="site-footer">'
        "<p>این وب‌سایت یک ابزار آموزشی غیرتجاری است که به کانال یوتیوب "
        f'<a href="{CHANNEL_URL}" rel="noopener noreferrer" target="_blank">'
        "جان میرشایمر</a> اشاره می‌کند. محتوای این وب‌سایت با هوش مصنوعی "
        "تولید شده است و ممکن است خطا یا اشتباه داشته باشد.</p>"
        "</footer>\n"
        "</body>\n"
        "</html>\n"
    )


def nav_link(href: str, text: str) -> str:
    return f'<a href="{href}">{text}</a>'


def read_content_title(path: Path) -> str:
    """Read the Persian H1 title from a content file."""
    for raw in path.read_text("utf-8").splitlines():
        m = H1_RE.match(raw)
        if m:
            return m.group(1).strip()
    raise ValueError(f"no H1 title in {path}")


def read_video_url(path: Path) -> str:
    return path.read_text("utf-8").splitlines()[0].strip()


def ordered_episodes() -> list[int]:
    nums = [
        int(re.search(r"episode-(\d+)\.md", p.name).group(1))
        for p in CONTENT_DIR.glob("episode-*.md")
    ]
    return sorted(nums)


def main() -> int:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    episodes = ordered_episodes()
    if not episodes:
        print("[error] no content/episode-*.md files found")
        return 1

    # List of (persian_title, html_file) for every episode except 0.
    cards = []
    for n in episodes:
        if n == 0:
            continue
        path = CONTENT_DIR / f"episode-{n}.md"
        title = read_content_title(path)
        cards.append((title, f"episode-{n}.html"))

    # Render one page per episode (N≥1). Episode 0 lives on the homepage.
    for n in episodes:
        if n == 0:
            continue
        content_path = CONTENT_DIR / f"episode-{n}.md"
        info_path = INFO_DIR / f"episode-{n}.txt"
        lines = content_path.read_text("utf-8").splitlines()
        title = read_content_title(content_path)
        video_url = read_video_url(info_path)
        body = render_body(lines[1:], video_url)
        body += "\n\n" + video_source_paragraph(video_url)
        nav_links = nav_link("index.html", "خانه")
        page = page_template(
            title=f"{title} | {SITE_TITLE}",
            h1=title,
            h1_url=video_url,
            body=body,
            nav_links=nav_links,
        )
        out = DOCS_DIR / f"episode-{n}.html"
        out.write_text(page, encoding="utf-8")
        print(f"[ok] wrote {out.relative_to(ROOT)}")

    # Homepage: the episode-0 intro as the lead article + links to every episode.
    content0 = CONTENT_DIR / "episode-0.md"
    if content0.exists():
        lines0 = content0.read_text("utf-8").splitlines()
        title0 = read_content_title(content0)
        body0 = render_body(lines0[1:], "")
        video0 = read_video_url(INFO_DIR / "episode-0.txt")
    else:
        title0 = SITE_TITLE
        body0 = ""
        video0 = CHANNEL_URL
    card_html_parts = []
    for ctitle, fname in cards:
        card_html_parts.append(
            f'<li><a class="episode-card" href="{fname}">'
            f'<span class="episode-title">{html.escape(ctitle)}</span>'
            f"</a></li>"
        )
    cards_html = "\n".join(card_html_parts)
    body0 += (
        "\n\n"
        + video_source_paragraph(video0)
        + '\n\n<section id="episodes" class="episodes">\n'
        "<h2>قسمت‌های کانال</h2>\n"
        "<p>برای مطالعه تحلیل کامل هر قسمت، روی عنوان آن کلیک کنید:</p>\n"
        f'<ul class="episode-list">{cards_html}\n</ul>\n'
        "</section>"
    )
    nav0 = nav_link("#episodes", "قسمت‌ها")
    index = page_template(
        title=f"{SITE_TITLE} | {SITE_SUBTITLE}",
        h1=title0,
        h1_url=video0,
        body=body0,
        nav_links=nav0,
    )
    index_out = DOCS_DIR / "index.html"
    index_out.write_text(index, encoding="utf-8")
    print(f"[ok] wrote {index_out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

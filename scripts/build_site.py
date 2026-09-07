#!/usr/bin/env python3
"""
Build the static Persian website (docs/) from the generated Markdown posts.

Reads the Persian blog posts in content/episode-N.md and the video metadata in
info/episode-N.txt, then renders a complete RTL site under docs/:

  * index.html                 - homepage: the episode-0 intro article + links to all episode pages
  * episode-N.html             - one page per episode (N≥1), each chapter heading linked to
                                 the matching moment of the source YouTube video
  * critique-episode-N.html    - one fact-check page per episode that has a critique/episode-N.md;
                                 it keeps the H1 title and the chapter headings of the article but
                                 carries no YouTube links; every heading links back to the matching
                                 chapter of the episode page
  * assets/style.css           - shared stylesheet (hand-written / LLM-themed)

Content pages carry a small critique icon on the left of the H1 title and of
each chapter heading that jumps to the matching part of the critique page.
Critique pages mirror that with a back icon that returns to the article.

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
CRITIQUE_DIR = ROOT / "critique"
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

CRITIQUE_ICON_SVG = (
    '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" '
    'stroke="currentColor" stroke-width="2.2" stroke-linecap="round" '
    'stroke-linejoin="round" aria-hidden="true">'
    '<circle cx="11" cy="11" r="7.5"/><line x1="21" y1="21" x2="16.4" y2="16.4"/>'
    "</svg>"
)

BACK_ICON_SVG = (
    '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" '
    'stroke="currentColor" stroke-width="2.2" stroke-linecap="round" '
    'stroke-linejoin="round" aria-hidden="true">'
    '<line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>'
    "</svg>"
)


def inline(text: str) -> str:
    """Escape raw text then turn `**bold**` spans into <strong>."""
    escaped = html.escape(text)
    # Replace bold in two steps so nesting/overlap never corrupts the output.
    while BOLD_RE.search(escaped):
        escaped = BOLD_RE.sub(r"<strong>\1</strong>", escaped, count=1)
    return escaped


def persian_digits(num: int) -> str:
    """Render an integer with Persian digits (e.g. 3 -> ۳)."""
    return str(num).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def timestamp_to_seconds(ts: str) -> int:
    """Convert an 'mm:ss' or 'h:mm:ss' timestamp into whole seconds."""
    parts = [int(p) for p in ts.split(":")]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def critique_link(href: str, label: str, *, back: bool = False) -> str:
    """An icon link between an article and its critique.

    The magnifier points to the critique of an episode/chapter; with back=True
    an arrow points back to the matching chapter of the episode page.
    """
    svg = BACK_ICON_SVG if back else CRITIQUE_ICON_SVG
    cls = "critique-link back" if back else "critique-link"
    safe_label = html.escape(label)
    safe_href = html.escape(href)
    return (
        f'<a class="{cls}" href="{safe_href}" title="{safe_label}" '
        f'aria-label="{safe_label}">{svg}</a>'
    )


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


def render_body(
    lines: list[str],
    video_url: str = "",
    *,
    link_chapters: bool = True,
    critique_page: str | None = None,
    content_page: str | None = None,
) -> str:
    """Turn the content lines (below the H1 title) into HTML, block by block.

    link_chapters=False renders chapter headings as plain text instead of
    YouTube deep-links (used on critique pages). critique_page makes each
    chapter carry a critique icon pointing to critique_page#critique-{i};
    content_page makes each chapter carry a back icon pointing to
    content_page#ch-{i} and gives the heading id="critique-{i}".
    """
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

    blocks: list[str] = []
    chapter_index = 0
    for kind, payload in segments:
        if kind == "h2":
            h2 = H2_RE.match(payload[0])
            ts, title = h2.group(1), h2.group(2)
            secs = timestamp_to_seconds(ts)
            h2_id = f'id="ch-{chapter_index}"'
            if link_chapters:
                link = f"{video_url}&t={secs}s"
                title_html = f'<a class="chapter" href="{link}">{inline(title)}</a>'
            else:
                title_html = inline(title)
            suffix = ""
            if critique_page:
                suffix += " " + critique_link(
                    f"{critique_page}#critique-{chapter_index}", "نقد این فصل"
                )
            if content_page:
                h2_id = f'id="critique-{chapter_index}"'
                suffix += " " + critique_link(
                    f"{content_page}#ch-{chapter_index}",
                    "بازگشت به تحلیل این فصل",
                    back=True,
                )
            blocks.append(f"<h2 {h2_id}>{title_html}{suffix}</h2>")
            chapter_index += 1
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
    h1_suffix: str = "",
) -> str:
    """Wrap article body into a complete RTL HTML document.

    h1_url makes the H1 link to an external source (the YouTube video) for
    article pages; pass None when the page must not link to the video (critique
    pages). h1_suffix appends an inline icon after the title (RTL: its left side).
    """
    if h1_url:
        h1_html = (
            f'<h1><a class="article-title" href="{h1_url}">{html.escape(h1)}</a>'
            f"{h1_suffix}</h1>"
        )
    else:
        h1_html = f"<h1>{html.escape(h1)}{h1_suffix}</h1>"
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
        "  <article>\n"
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


def has_critique(n: int) -> bool:
    return (CRITIQUE_DIR / f"episode-{n}.md").exists()


def render_critique_page(n: int, title: str) -> Path | None:
    """Build docs/critique-episode-N.html and return its path (or None)."""
    if not has_critique(n):
        return None
    crit_path = CRITIQUE_DIR / f"episode-{n}.md"
    crit_lines = crit_path.read_text("utf-8").splitlines()
    crit_title = read_content_title(crit_path)
    episode_file = f"episode-{n}.html"
    critique_file = f"critique-episode-{n}.html"
    note = (
        '<p class="page-note">این صفحه نقد و ارزیابی مقاله است. هر فصل به '
        f'<a href="{episode_file}">صفحهٔ تحلیل</a> و به فصلِ متناظرِ آن پیوند دارد.</p>'
    )
    body = (
        note
        + "\n\n"
        + render_body(
            crit_lines[1:],
            link_chapters=False,
            content_page=episode_file,
        )
    )
    nav_links = (
        nav_link("index.html", "خانه")
        + " "
        + nav_link(episode_file, "تحلیل قسمت " + persian_digits(n))
    )
    h1_suffix = " " + critique_link(episode_file, "بازگشت به تحلیل این قسمت", back=True)
    page = page_template(
        title=f"نقد {title} | {SITE_TITLE}",
        h1=crit_title,
        h1_url=None,
        body=body,
        nav_links=nav_links,
        h1_suffix=h1_suffix,
    )
    out = DOCS_DIR / critique_file
    out.write_text(page, encoding="utf-8")
    return out


def main() -> int:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    episodes = ordered_episodes()
    if not episodes:
        print("[error] no content/episode-*.md files found")
        return 1

    # List of (persian_title, html_file, critique_file) for every episode except 0.
    cards = []
    for n in episodes:
        if n == 0:
            continue
        path = CONTENT_DIR / f"episode-{n}.md"
        title = read_content_title(path)
        critique_file = f"critique-episode-{n}.html" if has_critique(n) else None
        cards.append((title, f"episode-{n}.html", critique_file))

    # Render one page per episode (N≥1). Episode 0 lives on the homepage.
    for n in episodes:
        if n == 0:
            continue
        content_path = CONTENT_DIR / f"episode-{n}.md"
        info_path = INFO_DIR / f"episode-{n}.txt"
        lines = content_path.read_text("utf-8").splitlines()
        title = read_content_title(content_path)
        video_url = read_video_url(info_path)
        critique_file = f"critique-episode-{n}.html"
        critique_target = critique_file if has_critique(n) else None

        body = render_body(lines[1:], video_url, critique_page=critique_target)
        body += "\n\n" + video_source_paragraph(video_url)
        h1_suffix = (
            " " + critique_link(critique_file, "نقد این قسمت")
            if has_critique(n)
            else ""
        )
        nav_links = nav_link("index.html", "خانه")
        if has_critique(n):
            nav_links += " " + nav_link(critique_file, "نقد این قسمت")
        page = page_template(
            title=f"{title} | {SITE_TITLE}",
            h1=title,
            h1_url=video_url,
            body=body,
            nav_links=nav_links,
            h1_suffix=h1_suffix,
        )
        out = DOCS_DIR / f"episode-{n}.html"
        out.write_text(page, encoding="utf-8")
        print(f"[ok] wrote {out.relative_to(ROOT)}")

        crit_out = render_critique_page(n, title)
        if crit_out:
            print(f"[ok] wrote {crit_out.relative_to(ROOT)}")

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
    for ctitle, fname, critique_file in cards:
        card = '<li class="episode-card-item">'
        card += (
            f'<a class="episode-card" href="{fname}">'
            f'<span class="episode-title">{html.escape(ctitle)}</span></a>'
        )
        if critique_file:
            card += " " + critique_link(critique_file, "نقد این قسمت")
        card += "</li>"
        card_html_parts.append(card)
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

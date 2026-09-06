---
name: site-styling
description: Style and polish the generated Mearsheimer Persian static site. Use when the user wants to restyle, theme, or refine the "final form" of the pages produced by scripts/build_site.py (docs/). Covers CSS theming, the shared page shell (header/nav/footer markup), RTL/layout polish, Vazirmatn typography, and responsive design.
---

# Site styling skill

The static site is generated deterministically by `scripts/build_site.py` from the
Persian posts in `content/episode-N.md` and metadata in `info/episode-N.txt`. The
**content is authoritative and machine-produced**; your job is purely the
**presentation layer**. You theme and polish the pages; you never rewrite the article
content.

## Files you work with

- `docs/assets/style.css` — the single shared stylesheet loaded by every page. This is
  your primary editing target.
- `scripts/build_site.py` — owns the full-page HTML *shell*: `page_template()`,
  `nav_link()`, header/subtitle/footer markup, and the `index.html` episode-card markup.
  If you need to change the shell/info-architecture (nav, footer, layout wrappers),
  edit the template strings in this script and re-run it. Note the AGENTS convention:
  content source files (`.md`) are updated first, then reflected in `.html`.
- `docs/index.html`, `docs/episode-N.html` (N≥1), `docs/robots.txt` — generated outputs.
  There is **no separate episode-0 page**: the homepage `index.html` embeds the
  episode-0 intro article plus the cards linking to each episode page. Do not hand-edit
  the article bodies after the fact; change `build_site.py` and regenerate instead, so
  your styling survives the next build.

## Non-negotiable constraints

- **RTL + Persian.** Keep `dir="rtl"` and the Persian/Farsi copy throughout. Do not
  introduce LTR layout.
- **Vazirmatn typeface.** All UI text renders with Vazirmatn (already imported via
  `@import` at the top of `style.css`).
- **Preserve content fidelity.** Never alter, trim, or reorder the rendered article
  text, the chapter headings, or the `mm:ss` timestamps. Chapter headings display only
  the (Persian) title, but each one is an exact deep-link into the source YouTube video
  whose `&t={seconds}` value comes from the `mm:ss` timestamp (see `check_timestamps.py`);
  a single changed digit breaks the whole mapping. Do not re-add timestamps to these
  headings.
- **Preserve accessibility basics.** Don't remove the `lang="fa"`/`dir="rtl"` attrs,
  the semantic `<article>/<h1>/<h2>/<main>/<nav>` structure, or link `rel="noopener"`.
- **Preserve the cross-page chrome** produced by the build: the centered header/nav,
  the article H1 linking to the source video (`a.article-title`), the header subtitle
  linking to the YouTube channel, the footer channel link + AI-generated disclaimer,
  the `منبع: تماشای ویدیوی اصلی` source link, and the top-right GitHub ribbon
  (`a.github-ribbon`, text "برو به گیت‌هاب"). You may restyle these in `assets/style.css`,
  but keep them present and functionally intact.
- **Responsive.** Support small screens (a `@media (max-width: 600px)` block already
  exists; keep or extend it). Everything must stay readable on mobile.

## Workflow

1. Re-read the current `docs/assets/style.css` and the relevant page shell in
   `scripts/build_site.py` before making changes so you match existing conventions.
2. Theme within `assets/style.css` first. Change design tokens (colors, spacing,
   radii, shadows, typography scale) toward a polished, editorial, easy-to-read look.
   The accent/brand color lives in `:root` custom properties.
3. If structural polish is needed (header, nav, episode cards, footer), edit the
   template strings in `scripts/build_site.py`, then re-run
   `python3 scripts/build_site.py` to regenerate `docs/`.
4. Never edit the generated `.html` article bodies by hand; if content must change,
   update `content/episode-N.md` and regenerate.
5. Open two generated pages (e.g. `docs/index.html` and `docs/episode-1.html`) to confirm
   the styling reads well with real content and the layout is consistent.

## What "final form" means here

A clean, coherent editorial design that a Persian-speaking reader finds inviting:
consistent typography hierarchy, comfortable line-heights and spacing, a clear visual
distinction between the homepage (episode-0 intro + episode cards) and the article
pages, obvious affordances on the clickable chapter headings and episode cards, and a
restrained accent color used for emphasis rather than decoration.

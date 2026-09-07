---
name: site-styling
description: Style and polish the generated Mearsheimer Persian static site. Use when the user wants to restyle, theme, or refine the "final form" of the pages produced by scripts/build_site.py (docs/). Covers CSS theming, the shared page shell (header/nav/footer markup), the critique↔article cross-link icons, RTL/layout polish, Vazirmatn typography, and responsive design.
---

# Site styling skill

The static site is generated deterministically by `scripts/build_site.py` from the
Persian posts in `content/episode-N.md` and metadata in `info/episode-N.txt`. The
**content is authoritative and machine-produced**; your job is purely the
**presentation layer**. You theme and polish the pages; you never rewrite the article
content.

## Files you work with

- `docs/assets/style.css` — the single shared stylesheet loaded by every page. This is
  your primary editing target (it also themes `a.critique-link`, `p.page-note`, and the
  `.episode-card-item` flex rows).
- `scripts/build_site.py` — owns the full-page HTML *shell*: `page_template()`,
  `nav_link()`, header/subtitle/footer markup, the `index.html` episode-card markup, the
  critique pages, and the critique↔article icon links. If you need to change the
  shell/info-architecture (nav, footer, layout wrappers, critique cross-links), edit the
  template strings and icon markup in this script and re-run it. Note the AGENTS
  convention: content source files (`.md`) are updated first, then reflected in `.html`.
- `docs/index.html`, `docs/episode-N.html` (N≥1), `docs/critique-episode-N.html` (N≥1),
  `docs/robots.txt` — generated outputs. There is **no separate episode-0 page**: the
  homepage `index.html` embeds the episode-0 intro article plus the cards linking to each
  episode page. Do not hand-edit the article bodies after the fact; change
  `build_site.py` and regenerate instead, so your styling survives the next build.

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
- **Preserve the critique↔article cross-links.** On article pages each H1 and chapter
  heading carries a `a.critique-link` magnifier icon (left of the title) into matching
  chapter `critique-episode-N.html#critique-{i}`. On critique pages the same headings
  carry a `a.critique-link.back` arrow back into `episode-N.html#ch-{i}`. The anchor ids
  `ch-{i}` (article) and `critique-{i}` (critique) pair up by chapter order — never
  drop, rename, or reorder either. You may restyle the icons, but keep them clickable,
  visually adjacent, and labeled (`title`/`aria-label`).
- **Critique pages must not link to the YouTube video.** They keep the H1 title as plain
  text (no `a.article-title`), chapter headings as plain headings (no `a.chapter`), and
  have no `منبع: تماشای ویدیوی اصلی` source link. The channel link in the header
  subtitle/footer and the GitHub ribbon are site chrome and stay. Keep `p.page-note`
  (the lead-in note linking back to the episode page) as produced by the build.
- **Preserve accessibility basics.** Don't remove the `lang="fa"`/`dir="rtl"` attrs,
  the semantic `<article>/<h1>/<h2>/<main>/<nav>` structure, or link `rel="noopener"`.
- **Preserve the cross-page chrome** produced by the build: the centered header/nav,
  the header subtitle linking to the YouTube channel, the footer channel link +
  AI-generated disclaimer, the `منبع: تماشای ویدیوی اصلی` source link, and the top-right
  GitHub ribbon (`a.github-ribbon`, text "برو به گیت‌هاب"). The video-specific bits — the
  article H1 linking to the source video (`a.article-title`) and the source link — apply
  to article pages (and the homepage) only; critique pages carry neither. You may restyle
  all of these in `assets/style.css`, but keep them present and functionally intact.
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
5. Open generated pages (e.g. `docs/index.html`, `docs/episode-1.html`, and
   `docs/critique-episode-1.html`) to confirm the styling reads well with real content,
   the layout is consistent, and the critique icons read clearly on both sides of the
   article↔critique link pair.

## What "final form" means here

A clean, coherent editorial design that a Persian-speaking reader finds inviting:
consistent typography hierarchy, comfortable line-heights and spacing, a clear visual
distinction between the homepage (episode-0 intro + episode cards), the article
pages, and the critique pages, obvious affordances on the clickable chapter headings,
episode cards, and critique cross-link icons, and a restrained accent color used for
emphasis rather than decoration. Critique pages should feel like a lighter, secondary
reading mode while keeping the same chrome and heading structure.

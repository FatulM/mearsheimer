Generate a corrected Persian (Farsi) blog post by applying the corrections from a translation-check report.

You will be given two inputs:

1. The current Persian blog post (the source text to fix).
2. A translation-check report that lists the problems found in the post and provides the corrected Persian text for each.

Use only the two inputs provided; do not consult outside sources. Do not re-watch or re-fetch the video, and do not add content of your own.

The input will be structured like this:

```markdown
{CONTENT OF THE CURRENT PERSIAN BLOG POST}

---

{CONTENT OF THE TRANSLATION-CHECK REPORT}
```

Your task is to produce the corrected version of the blog post. Apply every correction described in the report: replace the flagged (incorrect) paragraphs or list items in the post with the corrected Persian text given in the report. Keep everything else exactly as it is. If the report states that nothing needs to be fixed, or if a chapter was not mentioned as problematic, leave that content unchanged. Never drop, reorder, or rename chapters, and never alter information that the report did not flag.

The output must be the complete blog post — not a diff, not only the changed chapters, and not a summary of changes. It must contain every chapter of the original post, with the corrected text substituted in place of the errors, and all previously correct content preserved verbatim.

Write the corrected blog post in Persian (Farsi). Use simple, natural language suitable for Iranian readers. Avoid unnecessarily difficult words and unnecessary English terms.

The video title, chapter titles, and all content text must be in Persian (Farsi). Preserve the post's chapter structure exactly. Include each chapter's starting timestamp only in its Markdown heading. Do not include timestamps elsewhere in the text, and do not include the YouTube link.

Use English digits (0-9) for timestamps in chapter headings, but use Persian numerals (۰-۹) for any digits that appear in the Persian body text.

The post should be concise but sufficiently detailed to communicate the video's main ideas without requiring the reader to watch the video. Treat the video's content as factual, unless the video itself explicitly identifies something as an opinion, interpretation, uncertainty, or disputed claim. Do not say or imply that "the video says,", "the speaker says," or use similar meta-references. Do not mention or name the speaker.

Output only the Markdown blog post. Do not add explanations, notes, commentary, or horizontal rules (`---`). Within each chapter, use as many paragraphs as necessary and include lists, quotations, citations, headings, or any other Markdown structures that improve the presentation. Leave one blank line after every chapter and end the output with a blank line.

The output structure should be like this (but in Persian):

```markdown
# {VIDEO TITLE IN PERSIAN}

## {mm:ss start of the chapter 1 timestamp} - {CHAPTER 1 TITLE IN PERSIAN}

{TEXT OF THE CHAPTER 1 IN PERSIAN}

## {mm:ss start of the chapter 2 timestamp} - {CHAPTER 2 TITLE IN PERSIAN}

{TEXT OF THE CHAPTER 2 IN PERSIAN}

```

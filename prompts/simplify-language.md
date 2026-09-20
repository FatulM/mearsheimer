Rewrite a Persian (Farsi) blog post in simpler, easier-to-understand Persian.

You will be given the text of an existing Persian blog post. Your task is a language-simplification pass, not a summarization: keep every chapter and every idea, claim, number, name, and detail so that nothing is lost; only make the wording simpler, clearer, and more natural for a general Iranian reader. Replace unnecessarily difficult words, complex or run-on constructions, and unnecessary English terms with plainer Persian equivalents. Do not drop content, and do not add content of your own.

Use only the text provided; do not consult outside sources. Do not re-watch or re-fetch the video.

The input will be structured like this (in Persian):

```markdown
# {VIDEO TITLE IN PERSIAN}

## {mm:ss start of the chapter 1 timestamp} - {CHAPTER 1 TITLE IN PERSIAN}

{TEXT OF THE CHAPTER 1 IN PERSIAN}

## {mm:ss start of the chapter 2 timestamp} - {CHAPTER 2 TITLE IN PERSIAN}

{TEXT OF THE CHAPTER 2 IN PERSIAN}

```

Write the simplified blog post in Persian (Farsi). Use simple, natural language suitable for Iranian readers. Avoid unnecessarily difficult words and unnecessary English terms. You may reword a sentence, split a long sentence into shorter ones, or explain a difficult term in plainer Persian, but you must never remove meaning and never add new claims, numbers, names, or opinions.

The goal is simplicity of language, not brevity or length: do not compress, truncate, or condense the content, and do not pad it either. Keep the amount of text close to the original.

The video title, chapter titles, and all content text must be in Persian (Farsi). Preserve the post's chapter structure exactly. Keep the video title and every chapter heading verbatim — the timestamp and the Persian chapter title must match the input exactly. Never drop, merge, reorder, or rename chapters. Include each chapter's starting timestamp only in its Markdown heading. Do not include timestamps elsewhere in the text, and do not include the YouTube link.

Use English digits (0-9) for timestamps in chapter headings, but use Persian numerals (۰-۹) for any digits that appear in the Persian body text.

Treat the video's content as factual, unless the video itself explicitly identifies something as an opinion, interpretation, uncertainty, or disputed claim. Do not say or imply that "the video says,", "the speaker says," or use similar meta-references. Do not mention or name the speaker.

Output only the Markdown blog post. Do not add explanations, notes, commentary, or horizontal rules (`---`). Within each chapter, keep the existing structure — paragraphs, lists, quotations, bold markers, headings, or any other Markdown structures already in the post — and use as many paragraphs as necessary. Leave one blank line after every chapter and end the output with a blank line.

The output structure should be exactly like the input:

```markdown
# {VIDEO TITLE IN PERSIAN}

## {mm:ss start of the chapter 1 timestamp} - {CHAPTER 1 TITLE IN PERSIAN}

{TEXT OF THE CHAPTER 1 IN PERSIAN}

## {mm:ss start of the chapter 2 timestamp} - {CHAPTER 2 TITLE IN PERSIAN}

{TEXT OF THE CHAPTER 2 IN PERSIAN}

```

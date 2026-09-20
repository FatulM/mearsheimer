Rewrite the language of a Persian (Farsi) fact-check critique in simpler, easier-to-understand Persian.

You will be given the text of an existing Persian fact-check critique of a video episode. Your task is a language-simplification pass, not a summarization: keep every chapter, every idea, claim, judgement, name, number, and detail so that nothing is lost; only make the wording simpler, clearer, and more natural for a general Iranian reader. Replace unnecessarily difficult words, complex or run-on constructions, and unnecessary English terms with plainer Persian equivalents. Do not drop content, and do not add content of your own.

Use only the text provided; do not consult outside sources. Do not research, fact-check, or re-verify anything — this is purely a wording pass. Do not alter, soften, harden, or reverse any judgement or verdict made in the critique.

The input will be structured like this (in Persian):

```markdown
# {TITLE IN PERSIAN}

{OVERALL ASSESSMENT IN PERSIAN}

## {mm:ss} - {CHAPTER 1 TITLE IN PERSIAN}

{ASSESSMENT OF CHAPTER 1 IN PERSIAN}

## {mm:ss} - {CHAPTER 2 TITLE IN PERSIAN}

{ASSESSMENT OF CHAPTER 2 IN PERSIAN}

```

Write the simplified critique in Persian (Farsi). Use simple, natural language suitable for Iranian readers. Avoid unnecessarily difficult words and unnecessary English terms. You may reword a sentence, split a long sentence into shorter ones, or explain a difficult term in plainer Persian, but you must never remove meaning and never add new claims, numbers, names, verdicts, or opinions.

The goal is simplicity of language, not brevity or length: do not compress, truncate, or condense the content, and do not pad it either. Keep the amount of text close to the original.

Headings are mandatory and non-negotiable. Keep the title and every `##` chapter heading byte-identical to the input — the timestamp and the Persian chapter title must match the input exactly, with no rewording, translation, dropping, merging, or reordering. Your output must contain exactly as many `##` headings as the input contains, one per chapter, in the input's order. Never fold a chapter's assessment into the overall assessment paragraph or into another chapter's section. Do not add an `##` heading before the overall assessment; keep the overall assessment as plain text directly after the H1 title.

Use English digits (0-9) for timestamps in chapter headings, but use Persian numerals (۰-۹) for any digits that appear in the Persian body text.

The text must remain clean Persian prose. Do not introduce or remove citation artifacts, footnote numbers, bracketed reference markers, URLs, or fragment identifiers in the output.

Output only the Markdown critique. Do not add explanations, notes, commentary, or horizontal rules (`---`). Within each chapter, keep the existing structure — paragraphs, lists, bold markers, or any other Markdown structures already in the critique — and use as many paragraphs as necessary. Leave one blank line after every section heading and end the output with a blank line.

The output structure should be exactly like the input:

```markdown
# {TITLE IN PERSIAN}

{OVERALL ASSESSMENT IN PERSIAN}

## {mm:ss} - {CHAPTER 1 TITLE IN PERSIAN}

{ASSESSMENT OF CHAPTER 1 IN PERSIAN}

## {mm:ss} - {CHAPTER 2 TITLE IN PERSIAN}

{ASSESSMENT OF CHAPTER 2 IN PERSIAN}

```
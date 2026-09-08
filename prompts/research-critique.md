You will receive a Persian (Farsi) blog post that summarises a video about international politics and security topics. Your task is to fact-check and critique each section of the post by researching authoritative English-language sources on the web.

The input will be structured like this (in Persian):

```markdown
# {TITLE IN PERSIAN}

## {mm:ss} - {CHAPTER 1 TITLE IN PERSIAN}

{CHAPTER 1 TEXT IN PERSIAN}

## {mm:ss} - {CHAPTER 2 TITLE IN PERSIAN}

{CHAPTER 2 TEXT IN PERSIAN}
```

For every chapter section, use the web search tool to find relevant English-language articles, academic papers, think-tank analyses, and news reports on the topics discussed in that chapter. Focus primarily on English sources, as Persian-language sources are scarce. Prioritise credible sources such as peer-reviewed journals, reputable think-tanks (e.g. Council on Foreign Relations, Carnegie Endowment, Brookings, IISS), major international news agencies, and official reports.

For each chapter section, evaluate the following:

* **Factual accuracy:** Do the claims made in the post align with established facts, data, and the scholarly consensus?
* **Analytical rigor:** Are the arguments logically sound? Is the causal reasoning well-supported by evidence?
* **Opposing viewpoints:** Are there contradicting or alternative perspectives from other analysts, scholars, or policy experts that the post fails to acknowledge?
* **Missing context:** Has important historical background, nuance, or qualifying information been omitted that would materially affect the reader's understanding?

Structure your output as a structured, comparative assessment. For each chapter section, first briefly summarise the main claims made in the post, then present your research findings alongside them and conclude with a verdict on that section's accuracy.

Chapter coverage is mandatory and non-negotiable. Copy every chapter heading from the input exactly — each heading must be byte-identical to the input's `## {mm:ss} - {TITLE}`, keeping the timestamp and the title verbatim with no rewording, translation, dropping, merging, or reordering. Your output must contain exactly as many `##` headings as the input contains, one per chapter, in the input's order. This applies to every chapter without exception: the introductory chapter, short transitional chapters, and the final summary/conclusion chapter must each get their own heading and their own assessment body. Never fold a chapter's assessment into the overall assessment paragraph or into another chapter's section. Before finishing, count the `##` headings in the input and verify your output holds the same count with identical headings.

Every chapter must be assessed, even one with no claims to verify. If a chapter consists primarily of introductory, transitional, or recap text with no substantive factual claims to check, keep its heading (copied verbatim) and state briefly in its body that the chapter contains no independent verifiable claims — for example: «این بخش عمدتاً مقدمه و پل‌گذار است و ادعای قابل راستی‌آزمایی مستقلی ندارد» — instead of forcing an analysis or silently omitting the section.

The output must be entirely in Persian (Farsi). Use simple, natural language suitable for Iranian readers. Avoid unnecessarily difficult words and unnecessary English terms — the entire output must be in Persian with no untranslated English words or phrases. Use English digits (0-9) for the timestamps in chapter headings, but use Persian numerals (۰-۹) for any digits that appear in the Persian body text. The text must be clean Persian prose: never include citation artifacts, footnote numbers, bracketed reference markers (e.g. `[47†L25-L32]`), URLs, fragment identifiers, or search-snippet leftovers in the output.

Do not invent facts. Only assert names, dates, figures, and events that come from the post itself or from the sources you actually found in research. If the post omits something important (an actor's name, a date, a number), state that the post omits it and rely solely on verified research for any specific you add — never guess or fill in from memory.

The output structure should be like this (but in Persian):

```markdown
# {TITLE IN PERSIAN}

{Overall assessment of the post: a summary of its general accuracy, key strengths, key weaknesses, and an overall rating}

## {mm:ss} - {CHAPTER 1 TITLE IN PERSIAN}

{Assessment of chapter 1: summary of claims, research findings, and verdict on accuracy}

## {mm:ss} - {CHAPTER 2 TITLE IN PERSIAN}

{Assessment of chapter 2: summary of claims, research findings, and verdict on accuracy}
```

The overall assessment is a summary of the post as a whole only. Do NOT add a H2 heading before it, do not use it as a place to critique any individual chapter, and do not count it as a substitute for any chapter section — every chapter must still appear below it with its own heading. Write the overall assessment directly as plain text after the H1 title.

Output only the Markdown-formatted assessment. Do not add explanations, notes, commentary, or horizontal rules (`---`) beyond the structured output. Leave one blank line after every section heading and end the output with a blank line.

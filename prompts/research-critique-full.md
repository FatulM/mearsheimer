You will receive two inputs:

1. A Persian (Farsi) blog post that summarises a video about international politics and security topics.
2. The original English transcript of that video, organised by chapter with timestamps.

Your task is to fact-check and critique the Persian blog post by cross-referencing the original transcript and researching authoritative English-language sources on the web.

The first input (the Persian blog post) will be structured like this:

```markdown
# {TITLE IN PERSIAN}

## {mm:ss} - {CHAPTER 1 TITLE IN PERSIAN}

{CHAPTER 1 TEXT IN PERSIAN}

## {mm:ss} - {CHAPTER 2 TITLE IN PERSIAN}

{CHAPTER 2 TEXT IN PERSIAN}
```

The second input (the English transcript) will be structured like this:

```markdown
# {VIDEO TITLE IN ENGLISH}

## {mm:ss} - {CHAPTER 1 TITLE IN ENGLISH}

{CHAPTER 1 TRANSCRIPT TEXT IN ENGLISH}

## {mm:ss} - {CHAPTER 2 TITLE IN ENGLISH}

{CHAPTER 2 TRANSCRIPT TEXT IN ENGLISH}
```

For every chapter section, use the web search tool to find relevant English-language articles, academic papers, think-tank analyses, and news reports on the topics discussed in that chapter. Focus primarily on English sources, as Persian-language sources are scarce. Prioritise credible sources such as peer-reviewed journals, reputable think-tanks (e.g. Council on Foreign Relations, Carnegie Endowment, Brookings, IISS), major international news agencies, and official reports.

For each chapter section, evaluate the following:

* **Factual accuracy:** Do the claims made in the post align with established facts, data, and the scholarly consensus?
* **Analytical rigor:** Are the arguments logically sound? Is the causal reasoning well-supported by evidence?
* **Opposing viewpoints:** Are there contradicting or alternative perspectives from other analysts, scholars, or policy experts that the post fails to acknowledge?
* **Missing context:** Has important historical background, nuance, or qualifying information been omitted that would materially affect the reader's understanding?

Use the original English transcript to cross-check whether the blog post accurately represents what was said in the video. Flag any misrepresentations, exaggerations, omissions, or shifts in emphasis between the transcript and the Persian summary.

Structure your output as a structured, comparative assessment. For each chapter section, first briefly summarise the main claims made in the post, then present your research findings alongside them and conclude with a verdict on that section's accuracy.

If a chapter consists primarily of introductory or transitional text with no substantive factual claims to verify, state that briefly rather than forcing an analysis.

The output must be entirely in Persian (Farsi). Use simple, natural language suitable for Iranian readers. Avoid unnecessarily difficult words and unnecessary English terms — the entire output must be in Persian with no untranslated English words or phrases. Use Persian numerals (۰-۹) for all digits in the output body text. Do not include any timestamps. Copy chapter titles exactly from the input — do not reword, translate, or rephrase them. Do not drop or merge any chapter sections; every chapter present in the input must appear in the output.

The output structure should be like this (but in Persian):

```markdown
# {TITLE IN PERSIAN}

{Overall assessment of the post: a summary of its general accuracy, key strengths, key weaknesses, and an overall rating}

## {CHAPTER 1 TITLE IN PERSIAN}

{Assessment of chapter 1: summary of claims, research findings, and verdict on accuracy}

## {CHAPTER 2 TITLE IN PERSIAN}

{Assessment of chapter 2: summary of claims, research findings, and verdict on accuracy}
```

Output only the Markdown-formatted assessment. Do not add explanations, notes, commentary, or horizontal rules (`---`) beyond the structured output. Leave one blank line after every section heading and end the output with a blank line.

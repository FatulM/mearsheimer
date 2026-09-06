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

If a chapter consists primarily of introductory or transitional text with no substantive factual claims to verify, state that briefly rather than forcing an analysis.

The output must be entirely in Persian (Farsi). Use simple, natural language suitable for Iranian readers. Avoid unnecessarily difficult words and unnecessary English terms — the entire output must be in Persian with no untranslated English words or phrases. Use Persian numerals (۰-۹) for all digits in the output body text. Do not include any timestamps. Copy chapter titles exactly from the input — do not reword, translate, or rephrase them. Do not drop or merge any chapter sections; every chapter present in the input must appear in the output.

The output structure should be like this (but in Persian):

```markdown
# {TITLE IN PERSIAN}

{Overall assessment of the post: a summary of its general accuracy, key strengths, key weaknesses, and an overall rating}

# {CHAPTER 1 TITLE IN PERSIAN}

{Assessment of chapter 1: summary of claims, research findings, and verdict on accuracy}

# {CHAPTER 2 TITLE IN PERSIAN}

{Assessment of chapter 2: summary of claims, research findings, and verdict on accuracy}
```

Output only the Markdown-formatted assessment. Do not add explanations, notes, or commentary beyond the structured output. Leave one blank line after every section heading and end the output with a blank line.

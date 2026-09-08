You will receive two inputs:

1. The minified English transcript of a YouTube video, organised by chapter with timestamps.
2. A Persian (Farsi) blog post that summarises and translates that video.

Your task is to check whether the Persian summary correctly summarises and translates the English transcript, and to report — in Persian — what went wrong and what was done correctly. No internet search is needed: judge only from the two inputs provided. Do not consult outside sources.

The input will be structured like this:

```markdown
{content of the English transcript}

--

{content of the Persian summary}
```

For every chapter present in the Persian summary, compare its content against the matching English chapter of the transcript (chapter order and timestamps should line up; if they do not, flag that too). Evaluate the following:

* **Fidelity:** Does the Persian accurately convey the meaning of the English text, claim by claim?
* **Omissions:** Is important content from the transcript left out of the summary?
* **Additions:** Does the summary introduce claims, numbers, names, opinions, or events that are not present in the transcript?
* **Distortion:** Does the summary shift the meaning, emphasis, or degree of certainty of what was said (for example presenting speculation or uncertainty as established fact, or hardening a conditional into a definite statement)?
* **Accuracy of specifics:** Are numbers, dates, names, and percentages kept consistent with the transcript?
* **Chapter headings and structure:** Is every chapter of the transcript represented in the summary? Are any chapters dropped or merged, and are the chapter titles (and their timestamps) translated correctly?

The output must be entirely in Persian (Farsi). Use simple, natural language suitable for Iranian readers. Avoid unnecessarily difficult words and unnecessary English terms — the entire output must be in Persian with no untranslated English words or phrases. Use English digits (0-9) for the timestamps in chapter headings, but use Persian numerals (۰-۹) for any digits that appear in the Persian body text.

The report must be self-sufficient: it must contain everything needed to correct the Persian summary without consulting the original English transcript again. Therefore, whenever you find a problem in a chapter, you must provide the full corrected Persian text of every affected paragraph (or list item), written so that it can be pasted directly into the Persian summary in place of the wrong text. Follow the Persian summary's existing formatting (paragraph breaks, bullet lists, bold markers) in your corrections, and keep any content that was already correct unchanged. Only produce replacement text for the paragraphs that contained errors; do not rewrite the whole chapter unless the errors warrant it. If a short phrase, number, or date is wrong, show the whole corrected sentence so the exact wording to use is unambiguous — do not rely on the reader having the transcript open.

The output structure should be like this (but in Persian):

```markdown
# {TITLE OF THE EPISODE IN PERSIAN}

{General assessment of the translation and summarisation: an overall verdict on whether the post correctly represents the transcript, noting any inconsistent or incorrectly translated chapter titles or timestamps, and stating how many chapters were rendered correctly and how many had problems}

## {mm:ss} - {CHAPTER TITLE OF A PROBLEMATIC CHAPTER, COPY IT VERBATIM FROM THE PERSIAN SUMMARY}

{What went wrong in this chapter: describe each specific problem — mistranslations, omissions, additions, numeric/date errors, or distortions — referring to the exact claim or wording affected}

{Then, clearly labelled, the full corrected Persian text for every affected paragraph or list item, ready to paste into the Persian summary}

## {mm:ss} - {NEXT PROBLEMATIC CHAPTER, IF ANY}

{Explanation and corrected Persian text for this chapter's problems}
```

Include a chapter section **only** for chapters that had problems. Do not include sections for chapters that were rendered correctly. If every chapter was correct, do not add any chapter sections at all — the report is just the title and the general assessment.

Make clear in the output which paragraphs were corrected and how, so a human can review each change. In the general assessment, summarise how many chapters had problems and how many of those problems required a full rewrite versus a simple fix. The corrected text is the most important part of the report: if a chapter had any error, do not finish that chapter's section until you have written the corrected Persian replacement for it.

Do NOT add a H2 heading before the general assessment. Write the general assessment directly as plain text after the H1 title.

Do not invent issues. Only flag problems you can point to concretely in the two inputs, quoting or describing the specific text involved. If a part is translated or summarised correctly, say so plainly rather than forcing a problem. Be precise and fair; most well-written summaries will pass most chapters.

Output only the Markdown-formatted report. Do not add explanations, notes, commentary, or horizontal rules (`---`). End the output with a blank line.

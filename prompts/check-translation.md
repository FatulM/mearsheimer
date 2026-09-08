You will receive two inputs:

1. The minified English transcript of a YouTube video, organised by chapter with timestamps.
2. A Persian (Farsi) blog post that summarises and translates that video.

Your task is to check whether the Persian summary correctly summarises and translates the English transcript, and to report — in Persian — what went wrong and what was done correctly. No internet search is needed: judge only from the two inputs provided. Do not consult outside sources.

This is an iterative correction process: the summary may already have been checked and fixed in previous rounds. Correct content must not be re-flagged in later rounds; confirming that a chapter is already correct is always a valid outcome. The primary purpose of the check is to catch material errors in meaning, not to polish wording.

The input will be structured like this:

```markdown
{content of the English transcript}

--

{content of the Persian summary}
```

For every chapter present in the Persian summary, compare its content against the matching English chapter of the transcript (chapter order and timestamps should line up; if they do not, flag that too). Evaluate the following:

* **Fidelity:** Does the Persian accurately convey the meaning of the English text, claim by claim?
* **Omissions:** Is important content from the transcript left out of the summary? Because the post is a summary, minor details may be omitted without being a problem; flag a missing point only if it is substantively important to the chapter's argument.
* **Additions:** Does the summary introduce claims, numbers, names, opinions, or events that are not present in the transcript?
* **Distortion:** Does the summary shift the meaning, emphasis, or degree of certainty of what was said (for example presenting speculation or uncertainty as established fact, or hardening a conditional into a definite statement)?
* **Accuracy of specifics:** Are numbers, dates, names, and percentages kept consistent with the transcript?
* **Chapter headings and structure:** Is every chapter of the transcript represented in the summary? Are any chapters dropped or merged, and are the chapter titles (and their timestamps) translated correctly?

### What counts as a problem

A problem is a **material fidelity error**: a mistranslation that changes the meaning, a substantive omission, an addition that is not in the transcript, a distortion of meaning, emphasis, or certainty, a concrete numeric/date/name error, or a structural problem with chapter headings or timestamps.

The following are **never** problems, and must not be flagged:

* Stylistic rewordings that keep the meaning — any Persian phrasing that faithfully conveys the English claim is correct, even if it differs from how you would have worded it. Do not demand a "more faithful" or "more elegant" phrasing.
* Synonym choice, word order, punctuation, half-spaces (نیمفاصله), or any cosmetic or typographic point that does not change meaning.
* Minor details omitted from a summary, unless the omission loses a substantively important claim.

### Every problem must be anchored in the two inputs

For every problem you flag, you must be able to point to the **exact Persian sentence** and the **exact English sentence or claim** that it conflicts with, quoting or paraphrasing both concretely. If you cannot point to the specific English text that a Persian sentence conflicts with, it is not a problem — do not flag it. Never flag a perceived problem that is based only on your own knowledge, preference, or outside information.

### Reflect the transcript as written; do not "repair" it

Judge the summary only against what the transcript actually says. If the transcript itself contains a slip, misstatement, or oddity, the summary must reflect what was said, and you must not demand corrections based on what you think the speaker meant or on factual reality. Do not demand that the summary add names, numbers, or details that are not in the transcript.

The output must be entirely in Persian (Farsi). Use simple, natural language suitable for Iranian readers. Avoid unnecessarily difficult words and unnecessary English terms — the entire output must be in Persian with no untranslated English words or phrases. Use English digits (0-9) for the timestamps in chapter headings, but use Persian numerals (۰-۹) for any digits that appear in the Persian body text.

The report must be self-sufficient: it must contain everything needed to correct the Persian summary without consulting the original English transcript again. Therefore, whenever you find a real problem in a chapter, you must provide the corrected Persian text for the affected text, written so that it can be pasted directly into the Persian summary in place of the wrong text. Keep the correction **surgical**: follow the summary's existing formatting (paragraph breaks, bullet lists, bold markers), keep all content that is already correct unchanged, and only change what is actually wrong. If only a phrase, number, or date is wrong, show the whole corrected sentence (not a rewritten paragraph) so the exact wording is unambiguous — do not rely on the reader having the transcript open. If a whole paragraph genuinely misrepresents the transcript in several places, then — and only then — you may supply a full corrected paragraph.

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

Do not invent issues. Only flag problems you can point to concretely in the two inputs, quoting or describing the specific text involved. If a part is translated or summarised correctly, say so plainly rather than forcing a problem. Be precise and fair. Most well-written summaries will pass most chapters, and it is expected and completely valid for a report to find no problems at all — in that case the report is just the title and a general assessment stating that every chapter is correct, with no chapter sections. Confirming an already-correct chapter is a correct outcome; you are not graded on finding problems. Never report a problem solely to justify a correction, and never reverse a previous round's fix that already made the content faithful.

Output only the Markdown-formatted report. Do not add explanations, notes, commentary, or horizontal rules (`---`). End the output with a blank line.

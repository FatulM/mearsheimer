Generate a Persian (Farsi) blog post for a video with chapters.

You will be given the exact details of the video: the video title, the video URL, and each chapter with its starting timestamp and the concatenated subtitle text of that chapter. Use only the details provided; do not watch or fetch the video yourself.

The input will be structured like this (in English):

```markdown
# {VIDEO TITLE}

{VIDEO URL}

## {mm:ss start of the chapter 1 timestamp} - {CHAPTER 1 TITLE}

{CONCATENATED SUBTITLE TEXT OF CHAPTER 1}

## {mm:ss start of the chapter 2 timestamp} - {CHAPTER 2 TITLE}

{CONCATENATED SUBTITLE TEXT OF CHAPTER 2}

```

Write a well-structured blog post in Persian (Farsi). Use simple, natural language suitable for Iranian readers. Avoid unnecessarily difficult words and unnecessary English terms.

Preserve the video's chapter structure. Translate or rename chapter titles when appropriate. Include each chapter's starting timestamp only in its Markdown heading. Do not include timestamps elsewhere in the text, and do not include the YouTube link.

The post should be concise but sufficiently detailed to communicate the video's main ideas without requiring the reader to watch the video. Treat the video's content as factual, unless the video itself explicitly identifies something as an opinion, interpretation, uncertainty, or disputed claim. Do not say or imply that "the video says,", "the speaker says," or use similar meta-references. Do not mention or name the speaker.

Output only the Markdown blog post. Do not add explanations, notes, or commentary. Within each chapter, use as many paragraphs as necessary and include lists, quotations, citations, headings, or any other Markdown structures that improve the presentation. Leave one blank line after every chapter and end the output with a blank line.

The output structure should be like this (but in Persian):

```markdown
# {VIDEO TITLE}

## {mm:ss start of the chapter 1 timestamp} - {CHAPTER 1 TITLE}

{TEXT OF THE CHAPTER 1}

## {mm:ss start of the chapter 2 timestamp} - {CHAPTER 2 TITLE}

{TEXT OF THE CHAPTER 2}

```

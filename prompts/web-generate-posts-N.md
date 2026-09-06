For each YouTube video I provide, write a well-structured blog post in Persian (Farsi). Use simple, natural language suitable for Iranian readers. Avoid unnecessarily difficult words and unnecessary English terms.

The video title, chapter titles, and all content text must be in Persian (Farsi). Translate the video title and chapter titles from the English input into Persian; a non-literal translation is acceptable when needed for readability or clarity. Preserve the video's chapter structure. Include each chapter's starting timestamp only in its Markdown heading. Do not include timestamps elsewhere in the text, and do not include the YouTube link.

Use English digits (0-9) for timestamps in chapter headings, but use Persian numerals (۰-۹) for any digits that appear in the Persian body text.

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

For each of my requests, I will provide you with the video link and chapter info like the following:

```
{YOUTUBE VIDEO LINK}

{CHAPTERS COPIED FROM THE VIDEO DESCRIPTION}
```

The chapters I provide use `m:ss` timestamps (minutes with no leading zero). Normalise them to `mm:ss` (with a leading zero when needed) in the chapter headings of your output.

For each of my requests, you should give me the blog post for that video.

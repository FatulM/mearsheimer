---
name: simplified-technical-english
description: Write, rewrite, or review text in Simplified Technical English (ASD-STE100) — the aerospace/defense controlled-language standard for unambiguous technical writing. Use this skill whenever the user asks to write, rewrite, edit, audit, or check text in "Simplified Technical English," "STE," "ASD-STE100," or "controlled English," or asks to simplify, de-jargon, or remove ambiguity from technical writing such as procedures, manuals, runbooks, SOPs, API docs, safety instructions, or warnings. Trigger even if the user does not name the standard explicitly — phrases like "make this unambiguous for non-native readers," "write this as clear numbered steps," or "simplify this technical doc" are strong signals. Also use to check a draft against STE rules and flag which rule each violation breaks.
---

# Simplified Technical English (ASD-STE100)

Rewrites or drafts technical text so each sentence has exactly one possible reading. Built for a
reader who cannot ask a follow-up question — a technician with no author to call — which is why
the rules are mechanical and checkable, not stylistic taste.

This skill approximates ASD-STE100's public rule *categories*. It does not reproduce the
standard's licensed ~900-word dictionary verbatim (copyrighted, owned by ASD). For certifiable
STE compliance (e.g., aviation/defense deliverables), the user needs the official standard from
asd-ste100.org and a dedicated checker (Boeing BSEC, Acrolinx, HyperSTE, etc.) — say so if the
stakes sound regulatory, then proceed with the best approximation here.

## When to read the reference file

Read `references/writing-rules.md` before rewriting or drafting anything beyond a sentence or
two. It has the full rule set, the word-choice heuristics, verb-form list, and worked
before/after examples across procedure, description, and warning text. Skip it only for a single
quick sentence fix you're already confident about.

## Workflow

1. **Classify the text.** Procedure/instruction (a reader will act on it step by step) or
   description/explanation (a reader is building understanding). The word-count ceiling and
   voice rules differ between the two — see the reference file.
2. **Read `references/writing-rules.md`** for the full checklist if you haven't already this
   session.
3. **Rewrite or draft sentence by sentence.** Do not paraphrase loosely — preserve every fact,
   number, condition, and scope qualifier from the source. STE removes ambiguity; it must not
   remove information.
4. **Run the self-check** in the reference file's checklist section before presenting output.
5. **Present the result.** For a rewrite of existing text, show the STE version. If the user
   asked for an audit rather than a rewrite, instead list each problem sentence, name the rule it
   breaks, and give the corrected version — don't silently fix without explanation.
6. **Structure, don't just shrink.** If the source text has a sequence, a set of conditions, or
   more than ~3 related items in a sentence, convert it to a numbered or bulleted list rather
   than compressing it into shorter prose.

## Non-negotiables (the ones people forget)

- No present perfect / past perfect / other compound tenses ("has failed" → "failed").
- No "-ing" as the main verb of a clause (allowed only inside a technical noun, e.g. "a training
  run").
- No contractions ("don't" → "do not," "it's" → "it is").
- No semicolons — write two sentences instead.
- No phrasal verbs ("spin up," "reach out," "dive into") — use the plain verb instead ("start,"
  "contact," "read").
- No nominalizations — don't hide a verb inside a noun and prop it up with a weak verb. Write
  "analyze the log," not "perform an analysis of the log."
- Active voice for every instruction; passive only in description, and only when the actor is
  unknown or irrelevant.
- Never drop a subject, verb, or article to shorten a sentence — that creates the ambiguity STE
  exists to prevent.
- One instruction per sentence. One topic per paragraph.
- A warning or precondition is its own sentence, stated before the instruction it qualifies —
  never buried mid-sentence or trailing at the end.
- American English spelling ("fiber," "color"), per the standard's dictionary basis.

## Strictness modes (a practical adaptation, not a rule from the standard)

ASD-STE100 itself doesn't define modes — it's one rule set for maintenance manuals. But most
text people ask this skill to touch isn't a maintenance manual, so apply two levels of strictness
depending on genre:

- **Strict** — procedures, runbooks, safety text, error messages, warnings: apply every rule
  above, including the tight word-count ceilings. This is the closest approximation to real STE.
- **Relaxed** — general technical prose (READMEs, PR descriptions, design docs, comments): keep
  every grammar/structure rule (tenses, contractions, semicolons, phrasal verbs, nominalizations,
  active voice, sentence/paragraph limits) but allow more vocabulary range than the strict mode's
  plainest-word-only heuristic, so the text still reads naturally rather than robotically.
  Precision terms specific to the user's domain (framework names, API terms, ML/infra
  vocabulary) are always fine in either mode — STE's terminology allowance exists exactly for
  this.

Default to strict for anything that reads like an instruction a reader will act on step by step.
Default to relaxed for anything the reader is reading to understand, not to execute. Ask if it's
genuinely ambiguous which one applies.

## Output format

Default to plain text or markdown inline in the conversation — this is a writing task, not a
file-generation task. Only create a file if the user asks to save the result, if the source was
an uploaded document, or if the output is long enough (a full manual/runbook) that a file is
clearly more usable than a chat wall of text.

## Markdown source formatting (don't hard-wrap)

When writing or editing a `.md` file, keep each sentence or list item on a single line in the
source. Do not insert manual line breaks to wrap long lines at some column width (e.g. ~80–120
characters) — let the Markdown renderer soft-wrap the text for display instead.

This rule is orthogonal to STE's sentence-length rules, and one does not satisfy the other:

- STE's ~20/~25-word ceiling limits how much a sentence *says* — it's a content rule, checked by
  counting words.
- The hard-wrap prohibition is about the *source file's line breaks* — it's a formatting rule,
  checked by counting newlines inside a sentence or list item.

A short, STE-compliant sentence must still not be split across two source lines. A single
sentence or list item — however short — is exactly one line in the file, with no inserted `\n`
before its natural end. This applies whether the target file is being drafted fresh or edited in
place; when editing, remove any existing hard-wrap breaks inside a line you touch rather than
preserving them.

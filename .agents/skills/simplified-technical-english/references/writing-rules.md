# ASD-STE100 Writing Rules — Reference

Paraphrased rule categories from the public description of ASD-STE100 (Issue 9, Jan 2025), a
controlled natural language built by ASD (AeroSpace and Defense Industries Association of
Europe) for aircraft maintenance documentation. Sources: asd-ste100.org, ASD Europe, Wikipedia.
This file does not reproduce the standard's text or its licensed dictionary verbatim.

## 1. Classify before you rewrite

**Procedure / instruction text** — the reader acts on it step by step (a runbook, a setup guide,
an incident-response step, a config change). Rules:
- Max ~20 words per sentence.
- Active voice, always.
- One action per sentence, in the order the reader performs it.

**Descriptive / explanatory text** — the reader is building understanding, not acting yet (an
architecture overview, a "why this works" section, a postmortem narrative). Rules:
- Max ~25 words per sentence.
- Active voice preferred; passive allowed only when the actor is genuinely unknown or irrelevant
  ("the request is rate-limited" is fine if which component does the limiting doesn't matter
  here).

Most real documents mix both — classify sentence by sentence, not document by document.

## 2. Word choice

- Use the plainest, most common correct word. Prefer short over formal, familiar over rare.
- Give each term exactly one meaning for the whole piece. Don't drift between synonyms for one
  concept — pick "endpoint" or "route" and keep it.
- Define an acronym or domain term on first use, then reuse that exact term everywhere.
- No idioms, metaphors, or slang ("under the hood," "spin up," "boil the ocean," "low-hanging
  fruit"). State the literal meaning.
- No rhetorical hedging or filler ("it should be noted that," "in a sense," "arguably").

### Common word swaps (heuristic, not the official dictionary)

| Instead of | Use |
|---|---|
| utilize | use |
| commence | start / begin |
| terminate | stop / end |
| prior to | before |
| subsequent to | after |
| in order to | to |
| due to the fact that | because |
| in the event that | if |
| approximately | about |
| sufficient | enough |
| additional | more |
| obtain | get |
| purchase | buy |
| assist | help |
| attempt (verb) | try |
| modify | change |
| verify / check / confirm / ensure | make sure |
| regarding / with respect to | about |
| however | but |
| a number of | some |
| in the vicinity of | near |
| it is possible that | maybe / can |
| facilitate | help |
| regarding / concerning | about |
| demonstrate | show |
| additionally / furthermore / moreover | also |
| acquire | get |

This table is a starting heuristic for plain word choice — it is not the official ~900-word
ASD-STE100 dictionary, which is licensed and not reproduced here.

## 2a. No contractions, no semicolons

Do not use contractions ("don't," "it's," "can't"). Write the full form: "do not," "it is,"
"cannot." Contractions add a reading-speed ambiguity STE is built to remove.

Do not use semicolons to join two independent clauses. Write two sentences instead.

| Not permitted | STE version |
|---|---|
| The build didn't fail; the tests didn't run. | The build did not fail. The tests did not run. |

## 2b. No phrasal verbs

A phrasal verb pairs a verb with a particle (up, out, on, off) to mean something the words don't
literally say — "spin up," "reach out," "dive into," "roll out," "carry out." These aren't in
the approved dictionary because the meaning isn't recoverable from the words themselves, and the
parts can sometimes be separated ("carry it out"), which adds a second ambiguity. Use the plain
verb instead.

| Not permitted | STE version |
|---|---|
| Spin up a new instance. | Start a new instance. |
| Reach out to the on-call engineer. | Contact the on-call engineer. |
| Roll out the update to staging first. | Deploy the update to staging first. |

## 2c. No nominalizations

A nominalization hides a verb inside a noun, then needs a second, weaker verb to carry the
sentence ("perform an analysis of" instead of "analyze"). Use the plain verb directly.

| Not permitted | STE version |
|---|---|
| Perform an analysis of the log file. | Analyze the log file. |
| Make a decision about the config. | Decide on the config. |
| Give a description of the failure. | Describe the failure. |

## 2d. Spelling

Use American English spelling ("fiber" not "fibre," "color" not "colour," "analyze" not
"analyse") — the standard's dictionary is based on American English and Merriam-Webster. Use a
different spelling only if the user's own style guide or existing codebase already establishes
one.

## 3. Verb forms

Permitted: infinitive, imperative, simple present, simple past, simple future, and past
participle used only as an adjective.

Not permitted: present perfect, past perfect, or any other compound/auxiliary construction.

| Not permitted | STE version |
|---|---|
| We have received the report. | We received the report. |
| The build had failed before the fix. | The build failed before the fix. |
| The service will have started by then. | The service starts before then. |

"-ing" forms are allowed only as part of a technical noun ("a training run," "the sampling
rate," "a logging library"), never as the main verb of a clause.

| Not permitted | STE version |
|---|---|
| Restarting the pod fixes the leak. | If you restart the pod, this fixes the leak. |
| The model is training on the new data. | The model trains on the new data. |

## 4. Voice

- Active voice for every instruction: "Run the migration," not "The migration should be run."
- Passive only in description, only when the actor is unknown or irrelevant to the reader.
- If you're unsure whether to use passive, default to active — it's very rarely wrong.

## 5. Sentence structure

- One instruction or one claim per sentence.
- Stay under the word ceiling for the sentence's category (20 for instructions, 25 for
  description).
- Never omit a subject, verb, or article to shorten a sentence. "Install package, restart
  service" is two dropped subjects and an ambiguous sequence — write "Install the package. Then
  restart the service."
- Cap stacked-noun modifiers at 3 words. "The model training data pipeline config" stacks 5 nouns
  — rewrite as "the config for the pipeline that prepares the model's training data."

## 6. Paragraphs and lists

- One topic per paragraph, about 6 sentences or fewer.
- Any sequence, condition set, or set of more than ~3 related items becomes a numbered or
  bulleted list, not a prose sentence.
- Number steps that must happen in order. Use bullets for items with no required order.

## 7. Critical information (warnings, preconditions)

- State a warning or precondition as its own sentence, first, before the instruction it applies
  to.
- Don't attach it as a trailing clause or bury it mid-paragraph — a reader skimming for the next
  step can miss a trailing warning entirely.

| Buried | STE version |
|---|---|
| Run the drop command, but make sure you have a backup first, since this can't be undone. | Back up the database first. This command cannot be undone. Then run the drop command. |

## 8. Worked example (mixed procedure + description)

**Before:**
> Once the model has been trained and validation has completed, you'll want to make sure that the
> checkpointing config, which handles saving intermediate states, is properly set up before
> deploying, since deploying without it configured has caused rollback issues in the past.

**After:**
> Train the model. Complete validation. Before you deploy the model, check the checkpoint config.
> The checkpoint config saves the model's state during training. In the past, a missing checkpoint
> config caused rollback problems after deployment.

Note what changed: present perfect → simple past/present, one instruction per sentence, the
warning moved to its own sentence before the risky step, "properly set up" → "check," no dropped
subjects.

## 9. Self-check before presenting output

Run this checklist against your draft before showing it to the user:

- [ ] Every clause uses only: simple present, simple past, simple future, infinitive, imperative,
      or a participle-as-adjective. No compound tenses.
- [ ] No "-ing" is functioning as a clause's main verb.
- [ ] No contractions.
- [ ] No semicolons.
- [ ] No phrasal verbs (spin up, reach out, dive into, roll out) — plain verb used instead.
- [ ] No nominalizations (perform an analysis, make a decision) — plain verb used instead.
- [ ] American English spelling throughout.
- [ ] Every instruction sentence is active voice.
- [ ] Every instruction sentence has one action and is roughly ≤20 words; every descriptive
      sentence is roughly ≤25 words.
- [ ] No sentence is missing a subject, verb, or article.
- [ ] No noun cluster exceeds 3 stacked words.
- [ ] Each paragraph covers one topic in ~6 sentences or fewer.
- [ ] Sequences and condition sets are lists, not prose.
- [ ] Every warning/precondition is its own sentence, placed before the step it qualifies.
- [ ] Every term is used with one consistent meaning throughout.
- [ ] No fact, number, condition, or scope qualifier from the source was dropped.

If auditing rather than rewriting: for each violation, name the specific rule from sections 1–7
above before giving the fix, so the user learns the pattern instead of just getting a diff.

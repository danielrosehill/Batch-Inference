---
name: batch-research-record
description: Write what a batch/bulk LLM job taught us into the research notebook — the run record with measured tokens and cost, model screening results in the per-task tables, new or changed provider prices with the date checked, a use/avoid/watch verdict, provider gotchas, and a sample of the outputs. Use at the end of every bulk or batch run (pilots included, and failures especially), after checking a provider's prices, or when the user says "save this to the research notebook", "record that", "note that this worked / to avoid".
---

# Record to the research notebook

Path: `scripts/paths.sh notebook`; create it if missing. If it's a git repo, `git pull` before writing.
Schemas: `shared/notebook-schema.md`. Follow them exactly: other agents parse these files.

## After every run (pilots and failures included)

1. **`runs/YYYY-MM-DD_<job>/run.json`** — provider, model, mode, item count,
   succeeded, tokens (in / cached_in / cache_write / out, from the API's usage
   fields), `cost_usd` with `cost_basis` (`measured` from billing or usage cost;
   `estimated` from usage × price), wall clock, settings that mattered (thinking,
   effort, schema, caching), `outcome`, `verdict`, and a one-line `lesson`.
2. **`runs/.../notes.md`** if anything went wrong or surprised you: the exact
   error text, what you tried, and what fixed it. A failure that cost nothing but
   time is still worth a run record.
3. **`runs/.../samples.jsonl`** — up to 50 output rows, or all of them if the
   output is small. **Only non-sensitive output:** labels, ids, scores and public
   text are fine. Never prompt text from private datasets, personal data or
   credentials. Otherwise say where the full output lives.
4. **`verdicts.md`** — add a line at the top only if the run taught something
   reusable: `date · use|avoid|watch · lane · why · → path`. Don't log routine
   successes on an already-`use` lane. Update or strike an old verdict the new
   run contradicts; don't leave both.

## After screening models on a task type

A screen (several models on the same items, to pick one for a task type) gets a run record
under `runs/` as above, **and** a dated entry in **`tasks/<task>.md`**, one file per task
type (kebab-case, e.g. `tasks/term-anchored-generation.md`). Add the screen to the top of the
file's table, newest first, one row per model: date, model id, route (provider and
`batch`/`sync`), items, score per stratum, failures (count and kind), price (per item or per
Mtok, with the price row's date), and pick (`pick`, `runner-up`, or blank). Link the run with
`→ runs/YYYY-MM-DD_<job>/`. Follow the column layout already in the file or in the repo
`README.md`; create the file with that layout if the task type is new. Don't rewrite old
rows: a later screen that changes the pick gets new rows on top. If the pick changed the
general default, add a `verdicts.md` line too.

## After checking a price

Append a row to **`prices.jsonl`**. Never edit or delete old rows: the history is
the point. Record `checked` (today), the source URL, and `how`: `measured` if it
came from our own billed run, else `vendor docs` or `third-party`. Re-checked and
unchanged still gets a row.

## Provider notes

Add durable facts (API shape, limits, failure modes, things the docs get wrong)
to `providers/<provider>.md` under a dated heading. Create the file for a new
provider.

## Run ledger

After a full run, also add the one-row summary with `log-batch-run`.

## Commit

If the notebook is a git repo: one commit per run or finding, message `<provider>: <what was learned>`, and push.

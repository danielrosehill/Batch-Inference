---
name: setup-batch-eval
description: Set up an evaluation for a batch inference job, to choose or check its model before the full run. Installs the companion ai-eval plugin if it's missing, then gives it the job's real rows, prompt, schema, volume and budget. Use for "set up an eval for this batch job", "evaluate models for this batch", "which model should run this job, properly", "install the eval plugin", or when a job is large, recurring or quality-critical enough that a quick screen won't do.
---

# Set up an eval for a batch job

This plugin runs bulk jobs. The companion plugin [ai-eval](https://github.com/danielrosehill/AI-Eval) decides
which model deserves one. Use it when a job is large, will recur, or feeds something that matters. For a small
one-off, the quick screen in `batch-defaults` is enough.

Check the user's `defaults.md` first (`scripts/paths.sh defaults`): it may say how they get plugins.

## 1. Make sure ai-eval is available

```bash
claude plugin list | grep ai-eval
```

If it's missing, ask, then install:

```bash
claude plugin marketplace add danielrosehill/Claude-Code-Plugins
claude plugin install ai-eval@danielrosehill
```

Its skills load in a new session, so tell the user to restart. Don't carry on as if they were loaded.

## 2. Collect the job's facts

The eval is only as good as what it's told about the job. Measure these from the real files, not from a
description:

| ai-eval asks for | Take it from the batch job |
|---|---|
| Real example | Rows of `in.jsonl`, plus any known-good outputs |
| Context load, output length | Tokens per item, measured. `or_models.py spend` has real figures if a pilot ran |
| Reasoning | The production setting, normally off. A model that can't switch it off fails or costs more |
| Structure | The request `schema`, and whether JSON mode is enough |
| Cost | Cost of the **whole job** at its real token mix, not per call |
| Latency and volume | Item count, the 24 h batch window or a sync run, one-off or recurring |
| Constraints | Whether a `:batch` variant is required, pinned hosts, data policy |

## 3. Run ai-eval's model selection, with these changes

Follow `define-objective` → `define-workload-requirements` → `probe-openrouter` → `shortlist-candidates` →
`run-eval`, with the facts above. Bulk work differs from its default in three ways, so say so when handing over:

- **Items, not repeats.** `run-eval` defaults to one or two tasks with two outputs each. A bulk job fails on its
  awkward rows, so use 20-50 items, one output each, stratified to include the hard cases. Stay wide.
- **Check in code first.** Schema, counts, required terms and length are gates the full run will need anyway.
  Write them once and use them in the eval. Passing isn't quality: read a sample too, or judge blind
  (`scripts/blind_items.py` in ai-eval).
- **Match production.** Same system prompt, schema, reasoning setting and max tokens. Run the eval as sync calls,
  but pin the host if the job will be pinned, since hosts differ in price and quantisation.

If the user has local backends (`backends.py list`), include the local model as a candidate: `run-eval` covers
OpenRouter models, so generate its outputs with `local_batch.py` on the same items and score them with the rest.

If the job must run as a batch, make it a hard requirement that the model has a `:batch` variant
(`or_models.py batch`). Otherwise compare both routes for the top two or three.

## 4. Bring the result back

1. Price the top two or three for the full job (`or_models.py batch <ids> --est-in N --est-out N`).
2. Get the user's yes on model, route and estimate.
3. Pilot 10-20 items through the real runner (`sync-bulk-run`, `openrouter-batch` or `anthropic-batch`), since
   the eval didn't exercise that route.
4. Record the screen with `batch-research-record`.

For a recurring job, offer `regression-eval` so a later model or prompt change gets checked against the same items.

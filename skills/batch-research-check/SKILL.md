---
name: batch-research-check
description: Read the research notebook before choosing a provider, model or lane for a bulk/batch LLM job, or before quoting a batch price — per-task screening tables (which model was picked for a task type and why), dated verdicts (use / avoid / watch), the latest price per provider and model, provider gotchas, and records of past runs with their measured cost. Use when planning any batch job, when the user asks "what's the cheapest/best way to batch this", "which batch provider", "what did that cost last time", or before estimating spend for a bulk run.
---

# Check the research notebook

The notebook is a folder of dated findings: `scripts/paths.sh notebook` prints where it is (a `notebook:`
line in the user's `defaults.md`, else inside the plugin's data directory). Layout:
`shared/notebook-schema.md`. If it's a git repo, `git pull` first. If it doesn't exist yet, there's no
history: say so, and `batch-research-record` will create it after the first run.

## Choosing a model for a task type: `tasks/<task>.md` first

When the question is "which model for this kind of task" (term-anchored sentence generation,
labelling, extraction, judging, context writing, ...), read **`tasks/<task>.md`** before
anything else. There is one file per task type, each a dated table of the models screened on
that task: route, items, score per stratum, failures, price, and which one was picked. `ls tasks/`
to find the task; the nearest match counts, and say so if you stretch one. The latest pick there
beats a general verdict or a `pick-batch-model` default for that task, unless a later
`verdicts.md` line or price row undercuts it. No file for the task means it was never screened:
screen wide and small first (`pick-batch-model`), then record it with `batch-research-record`.

## Then read, in this order

1. **`verdicts.md`** — one line per lesson, newest first. An `avoid` line overrides
   the lane `batch-defaults` would otherwise pick, unless its reason no longer holds.
2. **`prices.jsonl`** — the latest row per (provider, model, mode) is current.
   ```bash
   python3 - <<'PY'
   import json
   rows = [json.loads(l) for l in open("prices.jsonl")]
   latest = {}
   for r in sorted(rows, key=lambda r: r["checked"]):
       latest[(r["provider"], r["model"], r["mode"])] = r
   for r in sorted(latest.values(), key=lambda r: r["usd_per_mtok_in"]):
       print(r["checked"], r["provider"], r["model"], r["mode"], r["usd_per_mtok_in"], r["usd_per_mtok_cached_in"], r["usd_per_mtok_out"], r["how"])
   PY
   ```
3. **`runs/*/run.json`** for a similar job: real tokens per item and cost per item
   beat any estimate. Scale those for the new job's item count.
4. **`providers/<provider>.md`** for the lane you're about to use (API shape and
   gotchas).

## Freshness

A price older than **30 days** is a lead, not a fact. Re-check it at the source
(OpenRouter: `scripts/or_prices.py`; others: their pricing page)
before you quote it in an estimate. Then write the new observation back with
`batch-research-record`, even if it didn't change, so the date moves.

## Then

Say in one line which lane and model you picked and why, citing the task table row, verdict,
price row or run it rests on. Estimate the job's cost from them before spending. If the notebook has nothing on the lane, say so: that
is a reason to pilot small and record the result.

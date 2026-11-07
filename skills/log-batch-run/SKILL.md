---
name: log-batch-run
description: Add a finished batch job to the run ledger: data size, model, cost, rating, notes. Use on "log this run", "add a run record".
---

# Log a batch run

One row per finished job in the run ledger, so "what did I use for that, and how did it go?" has an answer.
This is the short record. `batch-research-record` keeps the full detail in the notebook.

Log full runs and any pilot that changed a decision. Skip routine pilots that lead straight to a logged run.

## Steps

1. Collect the facts from the run: date, item count, tokens, model, route, measured cost
   (`or_models.py spend <usage log>`, or the runner's closing line).
2. Rate it 1-5 for how well the model did the task, from outputs you actually read. Leave the rating out if
   nobody checked them, and say so in the notes.
3. Check the text first if the ledger is public (see Notes). Then add the row:

   ```bash
   python3 run_ledger.py add --date 2026-01-31 --job "Tag support tickets by product area" \
     --task-type classification --items 5000 --data-size "ticket subject lines, ~20 words each" \
     --tokens-in 3400000 --tokens-out 40000 --model deepseek/deepseek-v4.1-flash --route openrouter-sync \
     --cost 0.30 --rating 4 --notes "Clean labels; 'other' was overused" --alternatives "qwen/qwen3.7-flash"
   ```

   Use `--cost-basis estimated` when the cost isn't from usage data.
4. If the ledger dir is a git repo, commit `runs.jsonl` and `RUNS.md` and push.

## Data storage

The ledger is `runs.jsonl` plus a generated `RUNS.md` in the dir from `scripts/paths.sh ledger`: the `ledger:`
line of `defaults.md`, else `<data dir>/ledger`. Never edit `RUNS.md` by hand.

## Notes

The ledger may be a public repo. Keep `--job`, `--data-size` and `--notes` general: what kind of data, never
its contents, names, client details or private project names. Prompts and outputs never go in.

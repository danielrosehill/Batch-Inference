---
name: find-batch-run
description: Look up past batch runs: which model, what it cost, how it did. Use on "what did I use for that", "did this work last time".
---

# Find a past batch run

Check the run ledger for similar work before picking a model, or when the user asks how a past job went.

## Steps

1. Search by what the job was, by model, or by task type. Terms are ANDed, so start with one or two:

   ```bash
   python3 run_ledger.py find classification
   python3 run_ledger.py find --model deepseek --min-rating 4
   python3 run_ledger.py find --task-type extraction
   ```

2. Read the matches. `total_runs` tells you whether an empty result means no similar job or an empty ledger.
3. Answer with the model, route, cost per 1,000 items, rating and notes of the closest runs. Scale the cost to
   the new job's item count.
4. Treat old prices as leads. Before quoting an estimate, check today's price as `batch-defaults` describes.
   For why a model was picked over others, read the notebook (`batch-research-check`).

## Data storage

Read-only. Reads `runs.jsonl` in the dir from `scripts/paths.sh ledger`.

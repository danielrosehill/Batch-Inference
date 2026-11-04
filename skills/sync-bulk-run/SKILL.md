---
name: sync-bulk-run
description: Run a bulk LLM job as parallel sync calls instead of a batch, usually on a cheap instruct model such as DeepSeek V4.1 Flash. Finds and probes candidates from OpenRouter's model list, compares cost against batch, pilots, then runs resumably with a hard spend cap and real measured cost. Use when sync is cheaper than batch today, the model has no batch variant, results are wanted in minutes, or the user says "just use sync", "do it with sync calls", "batch it with DeepSeek Flash", "find a cheap instruct model for this".
---

# Bulk run on sync calls

A batch API isn't always the best way to run a batch. Cheap instruct models are often as cheap on sync, and
sync finishes in minutes, shows failures as they happen, and works with models that have no batch variant.

**Default model: `deepseek/deepseek-v4.1-flash`, reasoning off.** On 2026-11-03 it won a 20-model screen for
generating training sentences (natural text, about a quarter of Gemini 3.1 Flash-Lite's cost), and it became
the sync default for that work. Skip to step 4 for a similar job, or when the user names it.

## 1. Find candidates

```bash
python3 or_models.py candidates --limit 25 --items N --in-per-item I --out-per-item O
```

Estimate I and O from a few real items: tokens are about 4 characters of English, and much less efficient
for Hebrew, Arabic and other non-Latin scripts. Keep 8-15 across vendors and price bands (see
`list-openrouter-models` for the columns).

## 2. Probe

```bash
python3 or_models.py probe <id> <id> ...
```

Drop anything that isn't `ok`. A non-zero `reasoning_tokens` means reasoning didn't really switch off.

## 3. Screen, for a new kind of job

Run the same 30-50 items through each survivor with the production prompt, then score them (`batch-defaults`,
"screen wide, small"). Read the outputs: mechanical checks passed 20/20 for most models in the sentence screen,
and quality still ranged from 2 to 5.

## 4. Compare with batch

```bash
python3 or_models.py batch <model> --est-in T --est-out T
```

Sync can lose on output-heavy jobs. On 2026-11-04 DeepSeek Flash output was 0.50 sync and 0.15 batch, so a job
with more output than input was cheaper as a batch. Say which you chose and why: speed can be worth it.

## 5. Pilot, then ask

```bash
head -20 in.jsonl > pilot.jsonl
python3 openrouter_sync.py pilot.jsonl pilot.out.jsonl --model deepseek/deepseek-v4.1-flash --usage-log data/llm-usage.jsonl
python3 or_models.py spend data/llm-usage.jsonl
```

Read the outputs. `spend` gives the measured tokens and cost per request: scale those to the full set, since
they beat the estimate. Get the user's yes on model, route and estimate before the full run.

## 6. Run

```bash
python3 openrouter_sync.py in.jsonl out.jsonl --model deepseek/deepseek-v4.1-flash \
  --workers 8 --max-cost 2.00 --usage-log data/llm-usage.jsonl
```

- Same request file as the batch runners (`batch-defaults`).
- **Resumable.** Finished rows are kept. Rerun the same command after a crash, a `--max-cost` stop, or to
  retry failed rows.
- `--max-cost` stops new calls once measured spend reaches the cap. Calls in flight still finish, so it can
  overrun slightly. Set it about 25% over the estimate.
- Reasoning is off. If a model refuses, the runner moves to effort low and warns, and cost rises.
- `--workers 8` is a safe start. Raise it for speed, and lower it if 429s appear (they're retried with backoff).
- `--provider <slug>` pins one host when the data or the quantisation matters.
- Exit code is 1 if any row failed or didn't run.

Then report ok and failed counts and real cost, and run `batch-research-record`.

`or_models.py account` shows the key's spend today, this week and this month, to confirm a job's total.

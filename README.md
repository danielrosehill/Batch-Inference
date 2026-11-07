# Batch Inference

Agent skills and scripts for bulk LLM work: one call per item over hundreds or thousands of items.

The question is rarely "how do I call the batch API". It's which model, on which route, at what real cost.
Batch isn't always cheaper than sync on OpenRouter, a model's listed abilities aren't always true, and the
cheapest model is often the wrong one. These tools check all of that on the day.

## Skills

| Skill | What it does |
|---|---|
| `onboarding` | Records your backends, including local servers, and your guide to when each is used. Run this first |
| `batch-defaults` | Router: picks the lane for a job |
| `list-openrouter-models` | Reads OpenRouter's live model list: batch models, sync instruct candidates, hosts, live probes |
| `sync-bulk-run` | Runs a bulk job as parallel sync calls: candidates, probe, cost check, pilot, resumable run with a spend cap |
| `local-bulk-run` | Runs a job on Ollama, llama.cpp, vLLM, LM Studio or your own servers, with hours weighed against cloud cost |
| `openrouter-batch` | OpenRouter Batch API, for any non-Anthropic model |
| `anthropic-batch` | Anthropic Message Batches, Claude Haiku 5.5 by default |
| `cheapest-batch` | The lowest-cost route, usually DeepSeek V4.1 Flash |
| `pick-batch-model` | Exact model id by use case, from measured data |
| `check-api-prices` | Today's prices, sync vs batch, what `~*-latest` aliases really serve |
| `setup-batch-eval` | Sets up a proper eval for a job with the companion [ai-eval](https://github.com/danielrosehill/AI-Eval) plugin, installing it if needed |
| `synthetic-data-generation` | Varied synthetic data: seed, rotate writers, dedupe |
| `batch-research-check` / `batch-research-record` | Read and write a dated notebook of prices, screens and runs |
| `log-batch-run` / `find-batch-run` | Keep a one-row-per-job ledger of model, data size, cost and rating, and search it before the next job |

## Scripts

All take one JSONL request format: `{"id", "user", "system"?, "schema"?}`.

| Script | Purpose | Needs |
|---|---|---|
| `scripts/or_models.py` | `batch`, `candidates`, `hosts`, `probe`, `spend`, `account` | stdlib; a key for `probe` and `account` |
| `scripts/openrouter_sync.py` | JSONL through parallel sync calls, resumable, `--max-cost` | stdlib, `OPENROUTER_API_KEY` |
| `scripts/local_batch.py` | JSONL through any local OpenAI-compatible server, resumable | stdlib |
| `scripts/backends.py` | `list`, `check`, `discover` and `speed` for your backends | stdlib |
| `scripts/openrouter_batch.py` | JSONL through the OpenRouter Batch API | stdlib, `OPENROUTER_API_KEY` |
| `scripts/anthropic_batch.py` | JSONL through Anthropic Batches, direct or through a proxy | `anthropic` SDK, `ANTHROPIC_API_KEY` |
| `scripts/or_prices.py` | Sync vs batch prices, alias resolution, price recording | stdlib |
| `scripts/paths.sh` | Finds the user's data directory | bash |

```bash
python3 scripts/or_models.py candidates --limit 20 --items 5000 --in-per-item 300 --out-per-item 120
python3 scripts/or_models.py probe deepseek/deepseek-v4.1-flash google/gemini-3.1-flash-lite
python3 scripts/openrouter_sync.py in.jsonl out.jsonl --model deepseek/deepseek-v4.1-flash --max-cost 1
```

## Your own defaults

Run `onboarding`. It writes two private files to the directory `scripts/paths.sh dir` prints: `backends.json` (your
servers, never keys) and `defaults.md` (when to use each, spend rules, a secrets wrapper and your notebook's
location). Skills read them first, and they override the built-in lanes. Examples are in `shared/`.

Prices and model picks in the skills are dated. Treat them as leads and re-check with `check-api-prices`.

## License

MIT

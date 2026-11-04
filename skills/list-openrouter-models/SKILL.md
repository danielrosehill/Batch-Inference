---
name: list-openrouter-models
description: Read OpenRouter's live model list for a bulk job. Lists every batch-capable model with batch vs sync price and which is cheaper, finds sync instruct models fit for bulk work (reasoning can be off, JSON mode, cheap), shows who hosts a model, and live-probes a shortlist. Use for "which models support batch", "list the batch models", "what cheap instruct models are there", "what's on OpenRouter for this", "is batch cheaper for X", or before shortlisting models for a screen.
---

# List OpenRouter models

`scripts/or_models.py`, reading `GET /api/v1/models` live (public, no key). Prices are US$ per M tokens.

```bash
python3 or_models.py batch                                # all batch models, cheapest first
python3 or_models.py batch deepseek gemini --est-in 2e6 --est-out 5e5   # filtered, with job cost
python3 or_models.py batch --dearer-only                  # where batch costs more than sync
python3 or_models.py candidates --limit 25 --items 5000 --in-per-item 300 --out-per-item 120
python3 or_models.py hosts deepseek/deepseek-v4.1-flash   # who serves it, price, quantisation
python3 or_models.py probe <id> <id> ...                  # live test, needs OPENROUTER_API_KEY
```

Every listing takes `--json`.

## Reading `batch`

A model is batch-capable when `<id>:batch` exists. Submit with the base id: `POST /api/v1/batches` selects
batch pricing. `cheaper` is worked out at the job's token mix if you gave one, else at 1:1, and the answer
can flip with the mix: on 2026-11-04 `deepseek/deepseek-v4.1-flash` was 0.050/0.150 batch and 0.045/0.500
sync, so sync wins only on input-heavy jobs. Always pass the estimate.

## Reading `candidates`

The filter for "an instruct model I can run bulk sync calls on": text output, a paid price, not expiring,
`--max-out` under US$2/M by default, a JSON mode, and reasoning not mandatory.

| Column | Meaning |
|---|---|
| `reasoning` | `none`: plain instruct model. `optional`: thinks by default, can be switched off. `mandatory` (hidden unless `--reasoning-ok`): bills reasoning tokens on every call |
| `json` | `schema`: claims structured outputs. `object`: JSON mode only. A claim: DeepSeek lists `structured_outputs`, but the runners default it to `object` because its first-party API rejects `json_schema` |
| `peak` | Highest time-of-day price, from `pricing.overrides`. Blank means flat. Dated snapshot ids often have it where the base id doesn't |
| `batch` | Has a `:batch` variant too |

The cheapest rows are often old or tiny (8B models, 2024 releases, 8k context). Sort by fit, not price: drop
what's too small, use `--min-context`, and keep several vendors and price bands.

## Trust the probe, not the listing

`probe` sends one tiny JSON request per model with reasoning off and reports status, host, reasoning tokens
and real cost, at a few thousandths of a cent each. On 2026-11-04 `meta-llama/llama-4-scout` was listed but
returned 404 (no endpoints), and models have returned 429 upstream on repeat tries. A 400 "Reasoning is
mandatory" means the model doesn't belong on a reasoning-off shortlist.

## Hosts

The listed price is roughly the cheapest host's. Unpinned sync calls can land on a different host per
request (three rows of one 2026-11-04 test went to three hosts, at fp4 and fp8), so real cost can sit above the listing, and
quality can vary with quantisation. Check `hosts`, and pin with `--provider` when it matters.

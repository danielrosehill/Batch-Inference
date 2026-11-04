---
name: pick-batch-model
description: Name the specific model (exact OpenRouter or Anthropic id) for a bulk/batch job by use case — labelling, extraction, LLM-as-judge, summarising, translation, distillation teacher, synthetic-data seeds, synthetic-data writing, long-form prose — from measured price, a measured diversity probe and EQ-Bench data, dated. Use when choosing which model to run a batch on, when the user asks "which model for X", "best cheap model for", "what should generate the data", or before writing a model id into a batch script.
---

# Pick the batch model by use case

Checked **2026-10-31**; term-anchored generation row revised **2026-11-04**. Prices are batch US$/M tokens in / out. If this table is more than 7 days old,
run `check-api-prices` first and update it here. Evidence lives in the public notebook
[OpenRouter-Batch-Notes](https://github.com/danielrosehill/OpenRouter-Batch-Notes): entry 07 (price tiers), 08 (cost per
workload shape) and 09 (synthetic-data diversity probe + EQ-Bench). Dated verdicts and run costs:
`batch-research-check`.

| Use case | Default | Alternative | Why / evidence |
|---|---|---|---|
| **Term-anchored generation: example sentences for a vocabulary term, one-line contexts or glosses, short gated items** | `deepseek/deepseek-v4.1-flash`, OpenRouter **sync** in parallel (0.045 / 0.50), reasoning off (`sync-bulk-run`) | `anthropic/claude-haiku-5.5` (0.10 / 0.50) when quality matters most; `xiaomi/mimo-v2.6-flash` | 20-model screen, 2026-11-03, 20 sentences each, read by hand: Haiku 5/5, DeepSeek and MiMo 4/5, `google/gemini-3.1-flash-lite` 3/5 at about 4x DeepSeek's cost. |
| Classification, labelling, tagging (short JSON out) | `claude-haiku-5-5`, Anthropic Batches (0.05 / 0.25; cache hit 0.01) | `openai/gpt-5-nano` (0.025 / 0.20), `deepseek/deepseek-v4.1-flash` (0.05 / 0.15) | Haiku: schema-enforced enums, caching, zero failures over 6,046 rows (2026-10-22). nano is cheapest with cache (08). DeepSeek has no json_schema and ~1.7% malformed rows. |
| Structured extraction to JSON | `claude-haiku-5-5` batch | `openai/gpt-oss-20b` (0.024 / 0.112) | Haiku for schema reliability; gpt-oss-20b cheapest per 1k requests (08). gpt-oss needs reasoning (mandatory). |
| LLM-as-judge / grading | `claude-haiku-5-5` batch | `claude-sonnet-5-5` batch (1 / 5) for nuanced rubrics | Judge quality outranks a few cents. |
| Summarising | `claude-haiku-5-5` batch | `deepseek/deepseek-v4.1-flash` | No caching benefit (08). Output price decides. |
| Translation / rewriting | `claude-haiku-5-5` batch | `z-ai/glm-5.3` (0.45 / 2.00) where the prose has to read well | GLM-5.3 has the best prose per $ (EQ-Bench Elo 2076, slop 8.4). |
| Distillation teacher (targets a small model will learn; faithfulness first) | `claude-haiku-5-5` batch | `google/gemini-3.8-flash` (0.375 / 1.875); `claude-sonnet-5-5` batch for hard formats | Faithfulness is not benchmarked here. Pilot about 10 and read them. Haiku costs 7× less on output than Gemini 3.8 Flash. |
| Synthetic data: seeds / scenario lists | `deepseek/deepseek-v4.1-flash` batch | `claude-haiku-5-5` batch | Low clustering in probe (09). Haiku clustered least on topic (0.23). |
| Synthetic data: writing items, quality first | `z-ai/glm-5.3` + `google/gemini-3.8-flash`, rotated | — | Most varied wording (Gemini J3 0.034) and best prose (GLM). See `synthetic-data-generation`. |
| Synthetic data: writing items, volume first | `deepseek/deepseek-v4.1-flash` + `claude-haiku-5-5` + `google/gemini-3.1-flash-lite`, rotated | — | All ≤ 0.75/M out. Rotation offsets DeepSeek's repetition. |
| Long-form prose / creative | `z-ai/glm-5.3` batch | `openai/gpt-5.6-luna` (0.10 / 0.60, Elo 1832) | EQ-Bench CW v3 |

**No row fits, or the job is new and matters:** don't guess from this table. Screen 8-15 models on
30-50 items first (`batch-defaults`, "screen wide, small") and add the winner here as a dated row.

## Avoid

- `claude-sonnet-5-5` and `openai/gpt-5.6-luna` for **unseeded** sampling: they collapsed most in the
  probe. Sonnet's 10 samples were near-identical (09).
- `openai/gpt-oss-120b`, `openai/gpt-5-nano` for anything where prose quality matters (EQ-Bench Elo 956 / 703).
- `~vendor/*-latest` aliases in a batch: they have no `:batch` id. Resolve with `or_prices.py --latest`.

## Endpoint quirks to send correctly

- **Reasoning cannot be disabled** (HTTP 400 "Reasoning is mandatory") on `claude-sonnet-5.5`, `z-ai/glm-5.3`,
  `z-ai/glm-5.3-flash` and `openai/gpt-oss-120b` via OpenRouter (2026-10-31). Send `{"effort": "low"}` and raise
  `max_tokens` by about 2,000.
- Gemini 3.x: most have no off switch. Effort `low`; reasoning tokens count against `max_tokens`.
  Exception: `google/gemini-3.1-flash-lite` accepts `{"enabled": false}` (verified 2026-11-03: ~36 output
  tokens per short JSON reply, no reasoning tokens; also the Recorder's production setting).
- DeepSeek, Haiku, GPT-6 Luna: `{"enabled": false}` works, and you are not billed for reasoning.

## Then

Get the user's yes before the full run: give the pick with its evidence
row, the alternatives with their prices and the estimate, and wait for a yes. Only a pilot goes ahead unasked.
State the pick in one line with its evidence row, estimate cost (`or_prices.py --est-in --est-out`, or
the 08 per-1k-request matrix), pilot 10–20 items, read them, run.

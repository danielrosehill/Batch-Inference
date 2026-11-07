---
name: batch-defaults
description: Pick the model, provider and lane for any bulk or batch LLM job (labelling, classification, extraction, synthetic data, summarising hundreds or thousands of items). Defaults: Claude Haiku 5.5 on the Anthropic Batches API for judgement work, DeepSeek V4.1 Flash for cheap volume (batch or parallel sync, whichever costs less today), OpenRouter Batch API for other named models; the user's own defaults file overrides these. Use first whenever the user says "batch this", "run it as a batch job", "bulk job", "use Haiku", "cheapest batch possible", "do it with DeepSeek", or a task needs one LLM call per item over many items.
---

# Batch defaults

## Read first

1. **The user's defaults:** `scripts/paths.sh defaults` prints their `defaults.md` if they have one. It
   overrides everything below. Its `When to use which backend` guide decides first, in order, first match
   wins. If there's no `defaults.md`, offer `onboarding` once, then carry on with the table below.
2. **The notebook:** run `batch-research-check` before picking a lane or quoting a price. If its price for
   the lane is over 7 days old, run `check-api-prices`. After every run, pilots and failures included,
   run `batch-research-record`, and after a full run `log-batch-run`.

Get the user's yes before every full run, whatever the amount: the lane, the alternatives with prices,
the estimate. Only a 10-20 item pilot goes ahead unasked. Check the current field, not just this
table: `or_models.py candidates` lists every cheap model that fits.

## Which lane

| The user says / the job needs | Lane | Skill |
|---|---|---|
| Example sentences for vocabulary terms, term contexts or glosses, short gated generation | **DeepSeek V4.1 Flash, OpenRouter sync in parallel**, reasoning off | `sync-bulk-run` |
| Cheap volume work where sync beats batch today, or the model has no batch variant | **Parallel sync calls** on a screened instruct model | `sync-bulk-run` |
| Nothing specific; "batch this"; "Haiku"; anything needing general intelligence or judgement | **Claude Haiku 5.5, Anthropic Message Batches API** (the default) | `anthropic-batch` |
| Harder reasoning or writing quality that Haiku visibly fails at | Same lane, `--model claude-sonnet-5-5`. Say you escalated and why | `anthropic-batch` |
| "the cheapest batch possible", "cheap as possible", "do it with DeepSeek" | **DeepSeek V4.1 Flash**, via OpenRouter batch or DeepSeek direct, whichever is cheaper today | `cheapest-batch` |
| A named non-Anthropic model (GPT, Gemini, Qwen, GLM, Mistral…) | **OpenRouter Batch API** | `openrouter-batch` |
| Results needed in minutes | Parallel sync calls | `sync-bulk-run` |
| "Run it locally", "use Ollama", private data, offline, or the user's guide says so | **The user's local backend** | `local-bulk-run` |

Haiku 5.5 batch is US$0.05 in / 0.25 out per M tokens. Small batches finish in a minute or two, and large
ones usually within the hour.

## Best options (checked 2026-10-31; re-check with `check-api-prices`)

For the exact model per use case (labelling, extraction, judge, teacher, synthetic data), use
**`pick-batch-model`**. For generating synthetic data, use **`synthetic-data-generation`**: varied
output comes from seeding, not from the choice of model.

US$ per M tokens, in / out. Read live on 2026-10-31: OpenRouter `/api/v1/models` with aliases
probed, and the Anthropic and DeepSeek pricing pages.

| Need | Pick | Batch | Sync | Note |
|---|---|---|---|---|
| General default, judgement, structured labels | `claude-haiku-5.5`, Anthropic Batches | 0.05 / 0.25 | 0.10 / 0.50 | Prompts over 100k tokens: 0.25 / 1.25 batch. Cache hits 0.01. |
| Better writing or reasoning | `claude-sonnet-5.5`, Anthropic Batches | 1.00 / 5.00 | 2.00 / 10.00 | |
| Google Flash quality, "Gemini flash latest" | `google/gemini-3.8-flash`, OpenRouter batch | 0.375 / 1.875 | 0.75 / 3.75 | What `~google/gemini-flash-latest` served on 2026-10-31. About 7x Haiku batch on output. |
| Cheapest at decent quality | `deepseek/deepseek-v4.1-flash`, OpenRouter batch | 0.05 / 0.15 | 0.045 / 0.50 | The `~deepseek/deepseek-flash-latest` sync alias (v4.1-flash-1017) was 0.014 / 0.144: cheaper than batch. |
| Cheapest at all, simple tasks | `openai/gpt-oss-120b`, OpenRouter batch | 0.03 / 0.136 | 0.15 / 0.60 | gpt-oss-20b is cheaper sync (0.018 / 0.09) than batch. |
| DeepSeek first-party | `deepseek-flash` direct, off-peak | none | 0.15 / 0.60 | Peak doubles it. No batch API. |

The cost order changes week to week. Haiku 5.5 batch is close to DeepSeek on price, so pick it
unless the user names another model.

## Choosing the model for a new kind of job: screen wide, small

This is the quick version. For a large, recurring or quality-critical job, use `setup-batch-eval`.

Do not pick one model and run the full set on it. Spend the pilot money on breadth instead:

1. **Shortlist 8-15 candidates** with `or_models.py candidates`, then `probe` them, across vendors and price bands, including the table default and the
   older and cheaper Flash / Flash-Lite / DeepSeek / Qwen-flash / Luna models. Most cheap models
   are poor at instruction-heavy work, so the point is to find the good one, not to confirm a guess.
2. **Same 30-50 items for every candidate**, sync calls (no batch for a screen), the exact
   production prompt and schema. Stratify the items so the hard cases are in it (rare terms,
   the language or domain that matters most), not just a random draw.
3. **Score blind**: mechanical checks in code (schema, gate, counts) plus an LLM judge that sees
   all candidates per item under shuffled labels (`claude-sonnet-5.5` via OpenRouter, effort low).
   Read a handful of side-by-side items yourself.
4. **Keep the screen under ~US$0.50** (it is a pilot). Report the table: score per stratum,
   failures, price, full-run estimate for the top two or three.
5. **Ask before the full run** with that table.
6. **Record it** in the notebook (`batch-research-record`): the task, date, route, every
   candidate's score and price, and the pick. Next time, check there first.

A cautionary case: a full Haiku run (US$0.45) and a full Sonnet run (US$2.41) went out before any screen. The
same US$3 would have screened about ten models on 50 items each.

## Rules that apply to every lane

1. **Probe small first.** Send 5–20 items, read the outputs yourself, then run the full set.
   Same input file and script; only the line count changes.
2. **Make the deterministic parts in code.** IDs, labels you already know, templating, and
   dedupe all happen in code. The model writes only what needs a model.
3. **Structured output when the result is data.** Put a JSON Schema in each request's `schema`.
   Nullable enums are rejected (400). Use a `"none"` member and map it afterwards.
4. **Results are keyed by id, never by position.** Both batch APIs return out of order.
5. **Keep raw output.** Write the out JSONL next to the job, then post-process from it. Never
   re-run a batch to recover something you could have re-parsed.
6. **Log cost.** Pass `--usage-log <project>/data/llm-usage.jsonl`. Report the cost and token
   totals when the run ends.
7. **Price check on the day for OpenRouter.** `scripts/or_prices.py <terms> --est-in N --est-out N`.
   OpenRouter batch prices move, and batch is sometimes dearer than sync.
8. **Reasoning costs money.** Haiku runs at `--effort low` by default. DeepSeek and other OpenRouter
   models run with reasoning off by default. Turn it up only when quality needs it.

## Request file (shared by all runners)

JSONL, one request per line:

```json
{"id": "row-1", "system": "optional shared instructions", "user": "the item", "schema": {"type": "object", "...": "optional"}}
```

Keep `system` identical across rows. The Anthropic runner caches it, which cuts input cost on
large runs.

## Scripts

The scripts live in this plugin's `scripts/` (`${CLAUDE_PLUGIN_ROOT}/scripts` when installed). They read keys
from the environment; if `defaults.md` names a secrets wrapper, put it in front of each command. Copy a
script into a project's `scripts/` when the project will rerun it, so the project stays self-contained.

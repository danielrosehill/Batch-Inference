---
name: pick-batch-model
description: Name the specific model (exact OpenRouter or Anthropic id) for a bulk/batch job by use case — labelling, extraction, LLM-as-judge, summarising, translation, distillation teacher, synthetic-data seeds, synthetic-data writing, long-form prose — from measured price, a measured diversity probe and EQ-Bench data, dated. Use when choosing which model to run a batch on, when the user asks "which model for X", "best cheap model for", "what should generate the data", or before writing a model id into a batch script.
---

# Pick the batch model by use case

Checked **2026-10-31**; term-anchored generation row revised **2026-11-23**. Prices are batch US$/M tokens in / out. If this table is more than 7 days old,
run `check-api-prices` first and update it here. Evidence lives in the public notebook
[OpenRouter-Batch-Notes](https://github.com/danielrosehill/OpenRouter-Batch-Notes): entry 07 (price tiers), 08 (cost per
workload shape) and 09 (synthetic-data diversity probe + EQ-Bench). Dated verdicts and run costs:
`batch-research-check`.

| Use case | Default | Alternative | Why / evidence |
|---|---|---|---|
| **Term-anchored generation: example sentences for a vocabulary term, one-line contexts or glosses, short gated items** | `tencent/hy4-flash`, OpenRouter **sync** in parallel (0.035 / 0.14), reasoning off (`sync-bulk-run`); no batch variant on 2026-11-23 | `qwen/qwen3.7-flash` (64/64, plainer, asks questions), `nex-agi/nex-n2.5-mini` (cheapest, repetitive); `anthropic/claude-haiku-5.5` was the best reader on 2026-11-03 but passed only 29/64 of this stricter prompt; `deepseek/deepseek-v4.1-flash` reasoning off | 30-model screen, 2026-11-23, 8 terms x 8 sentences in the production prompt: Hy4 Flash 63/64 past the gate at $0.0043 per 1,000 kept sentences, reads close to DeepSeek; DeepSeek with reasoning left on 63/64 at $0.175, reasoning off 56/64 at $0.029. Earlier: 20-model screen, 2026-11-03, 20 sentences each, read by hand: Haiku 5/5, DeepSeek and MiMo 4/5, `google/gemini-3.1-flash-lite` 3/5 at about 4x DeepSeek's cost. |
| Classification, labelling, tagging (short JSON out) | `claude-haiku-5-5`, Anthropic Batches (0.05 / 0.25; cache hit 0.01) | `openai/gpt-5-nano` (0.025 / 0.20), `deepseek/deepseek-v4.1-flash` (0.05 / 0.15) | Haiku: schema-enforced enums, caching, zero failures over 6,046 rows (2026-10-22). nano is cheapest with cache (08). DeepSeek has no json_schema and ~1.7% malformed rows. |
| Structured extraction to JSON | `claude-haiku-5-5` batch | `openai/gpt-oss-20b` (0.024 / 0.112) | Haiku for schema reliability; gpt-oss-20b cheapest per 1k requests (08). gpt-oss needs reasoning (mandatory). |
| LLM-as-judge / grading | `claude-haiku-5-5` batch | `claude-sonnet-5-5` batch (1 / 5) for nuanced rubrics | Judge quality outranks a few cents. |
| Summarising | `claude-haiku-5-5` batch | `deepseek/deepseek-v4.1-flash` | No caching benefit (08). Output price decides. |
| Translation / rewriting | `claude-haiku-5-5` batch | `z-ai/glm-5.3` (0.45 / 2.00) where the prose has to read well | GLM-5.3 has the best prose per $ (EQ-Bench Elo 2076, slop 8.4). |
| Distillation teacher (targets a small model will learn; faithfulness first) | `claude-haiku-5-5` batch | `google/gemini-3.8-flash` (0.375 / 1.875); `claude-sonnet-5-5` batch for hard formats | Faithfulness is not benchmarked here. Pilot about 10 and read them. Haiku costs 7× less on output than Gemini 3.8 Flash. |
| Synthetic data: seeds / scenario lists | `deepseek/deepseek-v4.1-flash` batch | `claude-haiku-5-5` batch | Low clustering in probe (09). Haiku clustered least on topic (0.23). |
| Synthetic data: writing items, quality first | `z-ai/glm-5.3` + `google/gemini-3.8-flash`, rotated | — | Most varied wording (Gemini J3 0.034) and best prose (GLM). See the `synthetic-data` plugin (`generate-text-data`). |
| Synthetic data: writing items, volume first | `deepseek/deepseek-v4.1-flash` + `claude-haiku-5-5` + `google/gemini-3.1-flash-lite`, rotated | — | All ≤ 0.75/M out. Rotation offsets DeepSeek's repetition. |
| Long-form prose / creative | `z-ai/glm-5.3` batch | `openai/gpt-5.6-luna` (0.10 / 0.60, Elo 1832) | EQ-Bench CW v3 |

### Shortlist: multi-label tagging of short texts (short JSON out, 2026-11-25)

Start here for this kind of work; don't rescreen unless this is over a month old. 26 models on 40 private voice-note transcripts, ZDR
routes only, 21 labels, scored against one agent's reading, so a gap of 1-3 notes is noise. Cost is measured.

| Need | Model | Main label found | Acceptable share of its labels | US$ per 1,000 notes |
|---|---|---|---|---|
| **Default: labels plus free text (e.g. "what label is missing")** | `tencent/hy4-flash`, sync, reasoning off | 33/40 | 0.85 | 0.113 in the screen; **0.030** over a 7,426-note run, 1 failure (the gap is probably prompt caching) |
| Fixed label set only, lowest cost | `liquid/d1.2` (decision model) | 36/40 | 0.82 at threshold 0.5 | 0.036 |
| Fixed labels, highest recall | `typesafe/jev-1.14` (decision model) | 37/40 | 0.72 | 0.089 |
| More accurate labels | `z-ai/glm-5.3-flash`, effort low | 35/40 | 0.92 | 0.166 |
| Fallback at Hy4's price | `particle-ai/particle-1` | 34/40 | 0.91 | 0.113 |

Also tried: `minimax/minimax-m3.1-flash` (36/40, 0.83, $0.148, reasons), `deepseek/deepseek-v4.1-flash-1017` (33/40, 0.90, $0.165),
`anthropic/claude-haiku-5.5` sync (32/39, 0.81, $0.322; its batch route was not tried), `perplexity/pplx-decider-flash-v1.2`
(31/40, $0.018). Weak here: gpt-oss-20b/120b, solar-mini-4-5, ling-3.0-flash, nova-micro, nemotron-3.5-lightning, clef-flash.

- Decision models: `POST /api/v1/systemone`, `questions: {id: {type: "noul", instructions, criteria: {"true": ..., "false": ...}}}`;
  the probability is in `answers.<id>.noul`. Discover them with `/models?output_modalities=all`.
- For private data send `provider: {zdr: true, data_collection: "deny"}`. Hy4 Flash then runs on Fireworks or DeepInfra (0.07 in), not
  Tencent (0.035). ZDR endpoints: `/api/v1/endpoints/zdr`.
- Reasoning could not be disabled (HTTP 400) on `thinkingmachines/inkling-2-small` and `meta/muse-ember`.

**No row fits, or the job is new and matters:** don't guess from this table. Screen 8-15 models on
30-50 items first (`batch-defaults`, "screen wide, small") and add the winner here as a dated row.

## Avoid

- `claude-sonnet-5-5` and `openai/gpt-5.6-luna` for **unseeded** sampling: they collapsed most in the
  probe. Sonnet's 10 samples were near-identical (09).
- `openai/gpt-oss-120b`, `openai/gpt-5-nano` for anything where prose quality matters (EQ-Bench Elo 956 / 703).
- `~vendor/*-latest` aliases in a batch: they have no `:batch` id. Resolve with `or_prices.py --latest`.

## Endpoint quirks to send correctly

- **Check `reasoning_tokens` before a bulk run.** `effort: low` is not off: DeepSeek V4.1 Flash spent 16,277 of 18,038 output tokens on
  reasoning that way (2026-11-23), six times its reasoning-off cost. On the Anthropic-shaped `/api/v1/messages` route send
  `"thinking": {"type": "disabled"}` and leave `effort` out.
- Free endpoints (`:free`): 20 requests a minute account-wide, hit at once by parallel runs; they train on the data. Good readers on
  2026-11-23: `nvidia/nemotron-3-ultra-550b-a55b:free` (52/64, the most natural text), `nvidia/nemotron-3.5-lightning:free` (55/64).

- **Reasoning cannot be disabled** (HTTP 400 "Reasoning is mandatory") on `claude-sonnet-5.5`, `z-ai/glm-5.3`,
  `z-ai/glm-5.3-flash` and `openai/gpt-oss-120b` via OpenRouter (2026-10-31). Send `{"effort": "low"}` and raise
  `max_tokens` by about 2,000.
- Gemini 3.x: most have no off switch. Effort `low`; reasoning tokens count against `max_tokens`.
  Exception: `google/gemini-3.1-flash-lite` accepts `{"enabled": false}` (verified 2026-11-03: ~36 output
  tokens per short JSON reply, no reasoning tokens; also the Recorder's production setting).
- DeepSeek, Haiku, GPT-6 Luna, Hy4 Flash, Qwen3.7 Flash, Nex N2.5 Mini, Ling 3.x: `{"enabled": false}` works, and you are not billed for reasoning.

## Then

Get the user's yes before the full run: give the pick with its evidence
row, the alternatives with their prices and the estimate, and wait for a yes. Only a pilot goes ahead unasked.
State the pick in one line with its evidence row, estimate cost (`or_prices.py --est-in --est-out`, or
the 08 per-1k-request matrix), pilot 10–20 items, read them, run.

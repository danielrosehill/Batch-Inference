---
name: synthetic-data-generation
description: Generate varied, non-repetitive synthetic data in bulk (training pairs, test inputs, personas, scenarios, fake dictations/emails/messages) on batch APIs. Covers the seed-then-write recipe, which models to rotate, and the dedupe and diversity checks, based on the user's 11-model diversity probe (2026-10-31). Use when a task generates many synthetic items, when the user says "synthetic data", "generate examples", "make training data", "it's too repetitive", or when a generated set looks samey.
---

# Synthetic data that isn't repetitive

**Measured 2026-10-31** ([OpenRouter-Batch-Notes](https://github.com/danielrosehill/OpenRouter-Batch-Notes), entry 09):
11 models were given the same prompt 10 times each. 91 of the 110 outputs mentioned the dentist and 83
dry cleaning. Every vendor converges on the same "typical" content, and switching model does not fix it.
Mixing models cuts wording overlap about 3× (trigram Jaccard 0.068 within one model vs 0.023 across
models) but not topic overlap. Variety comes from the **seed**.

## Recipe

1. **Axes in code.** List the dimensions that should vary (who, setting, length, tone, mess level,
   domain) and draw combinations in code with a seeded RNG. Don't ask a model for diversity you can
   enumerate.
2. **Seeds from a model, in chunks.** For open-ended variety (situations, personas), ask for 20–25 per
   call. Each call gets a different axis combination, plus "set k of n, avoid the obvious ones". One
   long list repeats itself. Model: `deepseek/deepseek-v4.1-flash` or `claude-haiku-5-5` batch
   (`pick-batch-model`).
3. **One item per seed.** The writing prompt holds the seed and the axis values. Never "write 50
   examples".
4. **Rotate 2–3 writer families** by item index (e.g. `i % 3`): quality-first
   `z-ai/glm-5.3` + `google/gemini-3.8-flash`, volume-first `deepseek/deepseek-v4.1-flash` +
   `claude-haiku-5-5` + `google/gemini-3.1-flash-lite`. Record the writer model on every row.
   Term-anchored items (sentences for a given vocabulary term, term contexts): `deepseek/deepseek-v4.1-flash`
   sync is the default writer (`pick-batch-model`, 2026-11-03).
5. **Dedupe.** Drop items whose content-word Jaccard to an earlier item is ≥ 0.5 (or embedding cosine
   ≥ 0.9). Report how many were dropped.
6. **Check diversity before scaling.** On the pilot, compute the mean pairwise trigram Jaccard (target
   < 0.07 for free text) and the top-3 content-word share (target < 0.4). Then read 10 items.
   `scripts/diversity_probe.py` in the notebook repo has the metric code.

## Don't

- Don't sample many items from one unseeded prompt, especially on `claude-sonnet-5-5` (most collapsed:
  trigram Jaccard 0.162) or `openai/gpt-5.6-luna` (0.085).
- Don't turn temperature up to get variety: it adds noise, not new topics. Change the seed.
- Don't use one model for both the seeds and every item if the set will train a model: its habits become
  the dataset's habits.

## Batch mechanics

Seeds and items are two batches (the second depends on the first). Use `openrouter-batch` /
`anthropic-batch` for multi-vendor rotation: one batch per model, joined on id. Models that refuse
`reasoning: {"enabled": false}`: see `pick-batch-model`.

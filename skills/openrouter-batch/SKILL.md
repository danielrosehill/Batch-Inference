---
name: openrouter-batch
description: Run a bulk job through the OpenRouter Batch API (POST /api/v1/batches) for any non-Anthropic model — DeepSeek, GPT, Gemini, Qwen, GLM, Mistral — from a JSONL file of prompts, after finding which models are batch-capable and checking whether batch is actually cheaper than sync today. Use when the user says "OpenRouter batch", "batch it on OpenRouter", names a non-Claude model for a bulk job, or asks which models support batch.
---

# OpenRouter batch

- Docs: https://openrouter.ai/docs/batch-quickstart
- **Batch-capable models:** `scripts/or_models.py batch` (skill `list-openrouter-models`). A model is
  batch-capable when a `<id>:batch` variant exists in `/api/v1/models`: 73 of 455 on 2026-11-04.

## 1. Check price on the day

```bash
python3 or_prices.py deepseek-v4.1-flash qwen3.8-flash --est-in 2000000 --est-out 500000
```

OpenRouter batch is **not** a flat 50% off. On 2026-10-19 `deepseek-v4.1-flash:batch` was
dearer than sync. On 2026-10-22 it was 0.05/0.15 against 0.30/1.20. `gpt-oss-20b:batch` and
`glm-5.3-flash:batch` were dearer than sync on both days. If sync is cheaper, run sync calls with
`openrouter_sync.py` instead (skill `sync-bulk-run`) and say so.

## 2. Run

```bash
python3 openrouter_batch.py in.jsonl out.jsonl --model deepseek/deepseek-v4.1-flash \
  --usage-log data/llm-usage.jsonl
```

- `--model` is the base id. The `:batch` suffix is stripped if given, because the batch endpoint
  is what selects batch pricing.
- `--json schema|object|none`. The default is `object` for `deepseek/*`, since DeepSeek's API has
  no json_schema. For those models the schema goes into the system prompt and the reply is parsed
  from the first `{`. The default for other models is `schema`.
- `--reasoning off` (default) sends `{"enabled": false}`. `{"effort": "low", "exclude": true}`
  still bills reasoning tokens, because `exclude` only hides them.
- `--provider <slug>` pins one provider (`provider.only`, no fallbacks). **Without it, OpenRouter
  picks the cheapest eligible host.** On 2026-10-22 a DeepSeek batch ran on "Sail Research", not
  DeepSeek. Pin a provider when the data shouldn't go to an arbitrary host, or when outputs must
  come from the first-party model.
- `--resume <batch id>` collects a batch that was already submitted.

## API facts (verified live 2026-10-22 unless marked docs)

- `POST /api/v1/batches` → `{"id": "batch-…", "status": "validating"}`. Body keys
  `endpoint, model, provider, completion_window` must come **before** `requests` or you get a
  400 (docs). `requests` is `[{custom_id, body}]`, where `body` is a normal chat-completions
  body.
- `GET /batches/{id}` **404s ("not found") for a moment right after submit**. The script retries
  through it for 5 minutes.
- Statuses: `validating → in_progress → finalizing → completed | failed | expired | cancelled`.
  Results come inline in `results` on the completed batch, as
  `{custom_id, response: {status_code, body}}` or `{custom_id, error}`, out of order.
  `GET /batches` (the list) returns `results: null`.
- The 2-row test completed in 60 s. The batch's `usage.cost` is the real charge, in US$.
- Limits (docs): 200 MB per batch, 24 h window, text only, and artifacts are deleted after 30 days
  (410 after that). There is no cancel endpoint, and `DELETE` works only on finished batches.
  Submit checks the estimated cost against the credit balance.
- Key: `OPENROUTER_API_KEY` in the environment.

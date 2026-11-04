---
name: anthropic-batch
description: Run a bulk job through the Anthropic Message Batches API — Claude Haiku 5.5 by default, half price, usually done in minutes — from a JSONL file of prompts, with structured JSON output, a cached system prompt, resume-by-batch-id and cost logging. The default lane for batch work. Use when the user says "Anthropic batch", "Haiku batch", "batch this with Haiku", "run it on the Batches API", or batch-defaults routes here.
---

# Anthropic batch (default lane)

Script: `scripts/anthropic_batch.py` (see `batch-defaults` § Scripts for the path when
`${CLAUDE_PLUGIN_ROOT}` is unset). Needs the `anthropic` SDK, so run it with `uv run --with anthropic`.

## Run

```bash
uv run -q --with anthropic python anthropic_batch.py in.jsonl out.jsonl \
  --usage-log data/llm-usage.jsonl

# through an Anthropic-compatible proxy with a per-project key
uv run -q --with anthropic python anthropic_batch.py in.jsonl out.jsonl \
  --base-url https://proxy.example/anthropic --api-key-env MY_PROJECT_KEY
```

Options: `--model claude-sonnet-5-5` (escalate only on visible Haiku failure), `--effort low|medium|high`
(default low), `--max-tokens` (default 4000; thinking tokens count against it),
`--resume msgbatch_…` (collect without resubmitting; the id prints on submit), `--poll` seconds.

Input and output formats are in `batch-defaults`. Rows that fail come back as
`{"id", "error"}`, e.g. `errored`, `expired`, or `stop_reason=max_tokens`. Resubmit only those
rows.

## Which key

`ANTHROPIC_API_KEY` for direct calls. A project that runs repeatedly can use a proxy with its own
budgeted key (`--base-url`, `--api-key-env`) so spend is attributed to it.

## Facts verified

- 2026-10-22, direct route, 2 rows (one schema, one text): ended in ~75 s and both parsed. Cost
  US$0.00002.
- 2026-10-20/21, through a LiteLLM proxy: structured output, system-block caching and results via
  `{proxy}/v1/messages/batches/{id}/results`. The SDK's `batches.results()` follows an absolute
  api.anthropic.com URL and 401s through a proxy, so the script fetches results itself on both routes.
- `cache_control` goes on the **system block**. Top-level automatic caching marks the per-item
  user message, so every request writes a cache entry and none reads one. That mistake cost a
  4.3M-token cache-write run on 2026-10-20.
- Haiku 5.5 thinks by default. Thinking is billed as output and included in `output_tokens`.

## Alternative: Haiku through OpenRouter's batch

`anthropic/claude-haiku-5.5` on the OpenRouter Batch API costs the same (0.05/0.25) and works.
A 5,104-request run on 2026-10-17 cost US$0.50. Prefer the direct API: it supports
`output_config` structured outputs and prompt caching natively, and the bill lands on the
Anthropic account. Use OpenRouter only if the Anthropic key or credit is unavailable.

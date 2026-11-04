---
name: cheapest-batch
description: Run a bulk LLM job as cheaply as possible — DeepSeek V4.1 Flash via the OpenRouter Batch API or DeepSeek's own API off-peak, whichever costs less today, with reasoning off and JSON-mode fallbacks. Use when the user says "cheapest batch possible", "as cheap as possible", "use DeepSeek", "doesn't need to be smart", or for very large, simple jobs (formatting, tagging, short extraction) where Haiku's quality isn't needed.
---

# Cheapest batch: DeepSeek

The rule: "cheapest batch possible" means DeepSeek, unless today's prices show something
cheaper at acceptable quality. If quality matters more than cost, use `anthropic-batch` (Haiku).

## Decide the route (one command)

```bash
python3 or_prices.py deepseek-v4.1-flash qwen3.8-flash gpt-oss-120b --est-in <N> --est-out <N>
```

| Route | Price (US$/M in/out) | Use when |
|---|---|---|
| OpenRouter batch, `deepseek/deepseek-v4.1-flash` | 0.05 / 0.15 on 2026-10-22 (it moves) | Batch is cheapest today and a 24 h window is fine. **Default.** |
| OpenRouter sync, `deepseek/deepseek-v4.1-flash`, parallel (`sync-bulk-run`) | 0.045 / 0.50 on 2026-11-04 | Input-heavy jobs, or results wanted in minutes |
| DeepSeek direct, `deepseek-flash`, `https://api.deepseek.com` | 0.15 / 0.60 off-peak, double at peak | OpenRouter batch is dearer today, the data must stay first-party, or results are wanted now |

DeepSeek's own platform has **no batch API and no batch discount**. "Batch" there means parallel
sync calls run off-peak. Peak hours are 01:00–04:00 and 06:00–10:00 UTC on weekdays.

Measured on one annotation job (~1.8M in / 5.2M out): DeepSeek direct US$3.38 against
`qwen/qwen3.8-flash` via OpenRouter US$2.71. Price the alternatives instead of assuming
DeepSeek wins.

## Run via OpenRouter batch

```bash
python3 openrouter_batch.py in.jsonl out.jsonl --model deepseek/deepseek-v4.1-flash \
  --usage-log data/llm-usage.jsonl          # add --provider deepseek to keep it first-party
```

Details are in `openrouter-batch`. Unpinned, OpenRouter may route the batch to a third-party
host (it did on 2026-10-22).

## DeepSeek traps (all hit in practice)

1. **No json_schema.** Use `json_object` with the schema in the system prompt (the runner's
   default for `deepseek/*`).
2. **Reasoning dominates cost.** Reasoning tokens bill as output and were 95–99% of output on
   short tasks. Keep reasoning **off**. If it is needed, batch several items per request so the
   preamble is paid once.
3. **`json_object` sometimes returns only whitespace** or a truncated object (5 of 150 rows on
   2026-10-19). The runner reports those rows as `error` with `raw`. Resubmit them. If a row
   fails every time, run it without `response_format`.
4. Budget output at about 3x the visible text if reasoning is on.

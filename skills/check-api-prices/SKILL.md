---
name: check-api-prices
description: Check today's LLM API prices across every lane in use: OpenRouter sync vs batch (live API), what each `~vendor/*-latest` alias really serves, Anthropic list and Batch prices, and DeepSeek direct peak and off-peak. Then record them, dated, in the batch notebook. Use when the user asks "what does X cost now", "check the latest prices", "is batch cheaper", "which is cheapest today", before estimating any paid bulk job when the stored price is more than 7 days old, or when a model id or alias may have moved.
---

# Check API prices (live, then record)

Prices and model ids change constantly. A price is a fact only on the day it was checked. This
skill finds today's numbers and writes them to the notebook's `prices.jsonl`,
so the next session starts from a dated record.

Scripts are in this plugin's `scripts/`. Notebook: `scripts/paths.sh notebook`.

## 1. OpenRouter: one command per question

```bash
python3 or_prices.py --latest                         # what every ~*-latest alias serves today + its batch price
python3 or_prices.py --batch-only --cheapest 15 --est-in N --est-out N   # cheapest batch lanes for a job
python3 or_prices.py gemini-3.8-flash deepseek-v4.1 --est-in N --est-out N  # named models, sync vs batch
```

Add `--record "$(scripts/paths.sh notebook)/prices.jsonl"` to
write the rows shown, dated today.

- **Aliases cannot be batched.** `~google/gemini-flash-latest` has no `:batch` id. Put the
  concrete id it resolves to in the batch.
- **Resolve aliases live, never by price.** `--latest` sends one tiny sync call per alias and
  reads the response's `model` field. On 2026-10-31 the gemini-flash alias was listed at
  gemini-3.7-flash's price but served `google/gemini-3.8-flash`.
- **A resolved snapshot id may not have its own batch variant.** `deepseek-v4.1-flash-1017` has
  none, so the script shows `deepseek-v4.1-flash:batch`, which may be an older snapshot.
- **Sync is sometimes cheaper than batch.** On 2026-10-31 `~deepseek/deepseek-flash-latest` cost
  0.014/0.144 sync against 0.050/0.150 batch. Compare both on the day.
- **Batch and sync aliases can route to third-party hosts.** One DeepSeek call went to "Sail
  Research". Pin with `provider.only` when the host matters.

## 2. Direct providers: fetch the pricing page

There is no price API for these. Fetch the page with WebFetch and ask for exact per-MTok numbers:

| Provider | Page | What to read |
|---|---|---|
| Anthropic | https://platform.claude.com/docs/en/about-claude/pricing | Model table (base in, cache hit, out) and the "Batch processing" table. Haiku 5.5 has a price step above 100k-token prompts. |
| DeepSeek direct | https://api-docs.deepseek.com/quick_start/pricing | Peak vs off-peak (off-peak = half). Peak is 01:00–04:00 and 06:00–10:00 UTC on weekdays. No batch API. |

The Anthropic page is long (over 50 KB). Grep the saved result for `Haiku 5|Sonnet 5|Opus 5` and
`Batch` rather than reading it whole.

## 3. Record

Append one `prices.jsonl` row per (provider, model, mode) in the repo's schema
(`checked, provider, model, mode, usd_per_mtok_in, usd_per_mtok_cached_in, usd_per_mtok_out,
turnaround, source, how, note`). Record it even when the price is unchanged, so the date moves.
A change that shifts a lane choice also gets a line in `verdicts.md` (`batch-research-record`).
If the notebook is a git repo, commit and push it.

## 4. Report

One table: lane, model id (concrete), sync in/out, batch in/out, est. job cost if a job is in
view. Then one line naming the pick and why. Mark anything inferred rather than read live.

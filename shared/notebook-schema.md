# Research notebook layout

A folder of dated findings, so the next job starts from measured facts. Every fact carries the date
it was checked and its source. Never store credentials, private prompt text or personal data.

| Path | What | Format |
|---|---|---|
| `tasks/<task>.md` | Per task type, dated screens of models with scores, prices and the pick | Markdown table, newest first |
| `verdicts.md` | One-line calls, newest first: `date · use\|avoid\|watch · lane · why · → path` | Markdown list |
| `prices.jsonl` | Every price observation, append-only. Latest row per (provider, model, mode) is current | JSONL |
| `providers/<provider>.md` | Lanes, API shape, limits, gotchas | Markdown |
| `runs/YYYY-MM-DD_<job>/run.json` | One real run with measured cost | JSON |
| `runs/YYYY-MM-DD_<job>/notes.md` | What happened, especially what failed. Optional | Markdown |
| `runs/YYYY-MM-DD_<job>/samples.jsonl` | Up to 50 non-sensitive output rows | JSONL |

`prices.jsonl` row:

```json
{"checked": "2026-10-22", "provider": "anthropic", "model": "claude-haiku-5-5",
 "mode": "batch", "usd_per_mtok_in": 0.05, "usd_per_mtok_cached_in": 0.005,
 "usd_per_mtok_out": 0.25, "turnaround": "minutes-1h, max 24h",
 "source": "https://...", "how": "vendor docs | measured | third-party", "note": ""}
```

`mode`: `batch` | `async` | `realtime`. `measured` beats `vendor docs` beats `third-party`.

`run.json`:

```json
{"date": "2026-10-22", "job": "subject-taxonomy-pilot", "project": "my-project",
 "provider": "anthropic", "model": "claude-haiku-5-5", "mode": "batch",
 "items": 100, "succeeded": 100, "tokens": {"in": 0, "cached_in": 0, "cache_write": 0, "out": 0},
 "cost_usd": 0.04, "cost_basis": "measured | estimated", "wall_clock": "~3 min",
 "settings": {"thinking": "off", "effort": "low", "structured_output": "json_schema"},
 "outcome": "ok | failed | partial", "verdict": "use | avoid | watch", "lesson": "one line"}
```

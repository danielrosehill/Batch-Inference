# batch-inference defaults (example)

Copy to `<data dir>/defaults.md` (`scripts/paths.sh dir`). Anything here overrides the plugin's skills.

notebook: ~/path/to/my-llm-notebook

## Running scripts

Secrets wrapper, if keys aren't exported: `my-secrets-tool run --`

## When to use which backend

In order, first match wins. Backends are defined in `backends.json`.

| When | Use |
|---|---|
| Customer data or anything marked private | gpu-box, never cloud. Wait if it's off |
| Simple tagging over 50,000 items, not urgent | gpu-box overnight |
| Example sentences | deepseek/deepseek-v4.1-flash, sync |
| Anything else | Claude Haiku 5.5, Anthropic Batches |

## Spend

Ask before any run over US$1.

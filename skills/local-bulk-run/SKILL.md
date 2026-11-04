---
name: local-bulk-run
description: Run a bulk LLM job on local or self-hosted inference (Ollama, llama.cpp, vLLM, LM Studio or the user's own servers), from the same JSONL as the cloud runners. Checks the backend is up, estimates hours against the cloud price, pilots, then runs resumably. Use for "run it locally", "use Ollama", "use my GPU box", "keep this off the cloud", "run it on the local model", or when the user's backend guide routes a job here.
---

# Bulk run on local inference

Backends come from `backends.json`. If there are none, run `onboarding` first, or pass `--base-url` for a one-off.

## 1. Is it up, and does it have the model?

```bash
python3 backends.py check <name>
```

If it's down, say what the backend's `notes` say about waking it, and stop. Don't fall back to a cloud route without
asking: the job may be local for privacy.

Choose the largest instruct model that fits the job and the hardware, and name it.

## 2. Hours against dollars

```bash
python3 backends.py speed <name> --model <model> --items N --out-per-item O
python3 or_models.py batch deepseek/deepseek-v4.1-flash --est-in T --est-out T
```

Local isn't automatically the cheap option. Cloud bulk prices are low enough that a job can cost cents, against
hours of a machine at full power. Local wins on privacy, on working offline, and on very large simple jobs. Show the
user both figures when the guide in `defaults.md` doesn't settle it.

## 3. Pilot, read, then run

```bash
head -20 in.jsonl > pilot.jsonl
python3 local_batch.py pilot.jsonl pilot.out.jsonl --backend <name> --model <model> --usage-log data/llm-usage.jsonl
```

Small models fail more quietly than cloud ones: read the outputs as well as the counts. If quality matters, put the local
model in the screen beside the cloud candidates (`setup-batch-eval`) instead of assuming it's enough.

Run the full set with the same command on `in.jsonl`.

- **Resumable.** Rerun the same command to continue or retry. A run stops after 3 connection failures in a row, so a
  machine going to sleep costs nothing but the wait.
- `--workers` defaults to the backend's `concurrency`, else 1. Extra workers only help if the server runs requests in
  parallel: vLLM does, and Ollama needs `OLLAMA_NUM_PARALLEL`. Otherwise they just queue, and can hit `--timeout`.
- The first call can take minutes while the model loads. That's not a hang.
- `--think off` is the default. It sends `reasoning_effort: none` to Ollama and `enable_thinking: false` to vLLM.
  Older Ollama versions and llama.cpp ignore this: the model still thinks, `<think>` blocks are stripped from the
  reply, and the run is slower, so raise `--max-tokens` if replies come back empty.
- `--json schema` works on current Ollama and vLLM. If a server rejects it, use `--json object`.
- Long prompts can be cut silently by a small context setting (Ollama's `num_ctx`). Check a long row in the pilot.

Then report ok and failed counts, wall time and tokens per second, and run `batch-research-record`.

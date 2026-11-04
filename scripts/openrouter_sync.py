#!/usr/bin/env python3
"""Run a JSONL file of prompts as parallel sync calls on OpenRouter ("batch with a sync model"). Stdlib only.

Use it when sync is cheaper than batch today, the model has no batch variant, or results are wanted
in minutes rather than inside a 24 h window. Same files as openrouter_batch.py:
    in:  {"id": "row-1", "user": "...", "system": "... (optional)", "schema": {... optional}}
    out: {"id", "result"} or {"id", "error"}

Resumable: ids already in the output file with a result are skipped, and rows are appended as they
finish, so an interrupted run loses nothing. Rerun the same command to retry failed rows.
Cost is the real figure from OpenRouter's usage accounting, not an estimate.

Usage:
  python3 scripts/openrouter_sync.py in.jsonl out.jsonl --model deepseek/deepseek-v4.1-flash
  ... --workers 8 --max-cost 1.00     stop submitting once measured spend reaches US$1.00
  ... --provider deepseek             pin one host (provider.only, no fallbacks)
  ... --usage-log data/llm-usage.jsonl
Reasoning is off by default. A model that refuses that ("Reasoning is mandatory") is moved to effort
low with a warning, because it then bills reasoning tokens.
"""
import argparse, json, os, sys, threading, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from openrouter_batch import body_for, parse

URL = "https://openrouter.ai/api/v1/chat/completions"
RETRY = {408, 429, 500, 502, 503, 504}
lock = threading.Lock()
state = {"reasoning": None, "cost": 0.0, "in": 0, "out": 0, "reasoning_tokens": 0, "stop": False}


def one(r, a, key, mode):
    last = None
    for attempt in range(a.retries + 1):
        if state["stop"]:
            return {"id": r["id"], "skipped": True}
        b = body_for(r, mode, state["reasoning"] or a.reasoning, a.max_tokens)
        b.update(model=a.model, usage={"include": True})
        if a.temperature is not None:
            b["temperature"] = a.temperature
        if a.provider:
            b["provider"] = {"only": [a.provider], "allow_fallbacks": False}
        req = urllib.request.Request(URL, data=json.dumps(b).encode(), headers={
            "Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "llm-ops-plugin"})
        try:
            d = json.load(urllib.request.urlopen(req, timeout=a.timeout))
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:500]
            last = f"HTTP {e.code}: {msg}"
            if e.code == 400 and "mandatory" in msg.lower() and (state["reasoning"] or a.reasoning) == "off":
                with lock:
                    if not state["reasoning"]:
                        state["reasoning"] = "low"
                        print(f"warning: {a.model} cannot switch reasoning off; using effort low, which bills reasoning tokens", file=sys.stderr)
                continue
            if e.code not in RETRY:
                return {"id": r["id"], "error": last}
            time.sleep(2 ** attempt + 1)
            continue
        except Exception as e:
            last = str(e)[:300]
            time.sleep(2 ** attempt + 1)
            continue
        if d.get("error"):  # an upstream failure can arrive inside a 200
            last = json.dumps(d["error"])[:300]
            time.sleep(2 ** attempt + 1)
            continue
        u = d.get("usage") or {}
        with lock:
            state["cost"] += u.get("cost") or 0
            state["in"] += u.get("prompt_tokens") or 0
            state["out"] += u.get("completion_tokens") or 0
            state["reasoning_tokens"] += (u.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0
            if a.max_cost and state["cost"] >= a.max_cost:
                state["stop"] = True
        choice = d["choices"][0]
        text = choice["message"].get("content") or ""
        if not r.get("schema") or mode == "none":
            if text.strip():
                return {"id": r["id"], "result": text, "host": d.get("provider")}
            last = f"empty reply (finish_reason={choice.get('finish_reason')})"
            continue
        try:
            return {"id": r["id"], "result": parse(text), "host": d.get("provider")}
        except (ValueError, json.JSONDecodeError):
            # JSON mode sometimes returns whitespace or a truncated object; a resample usually fixes it.
            last = f"unparseable reply (finish_reason={choice.get('finish_reason')})"
    return {"id": r["id"], "error": last}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("requests")
    ap.add_argument("out")
    ap.add_argument("--model", required=True)
    ap.add_argument("--provider")
    ap.add_argument("--json", choices=["schema", "object", "none"])
    ap.add_argument("--reasoning", default="off", help="off | low | medium | high")
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--temperature", type=float)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--max-cost", type=float, help="stop submitting once measured spend reaches this many US$")
    ap.add_argument("--usage-log")
    a = ap.parse_args()

    key = os.environ.get("OPENROUTER_API_KEY") or sys.exit("no $OPENROUTER_API_KEY in the environment")
    a.model = a.model.removesuffix(":batch")
    mode = a.json or ("object" if a.model.startswith("deepseek/") else "schema")
    reqs = [json.loads(l) for l in Path(a.requests).read_text().splitlines() if l.strip()]
    if len({r["id"] for r in reqs}) != len(reqs):
        sys.exit("ids must be unique")

    out = Path(a.out)
    done, kept = set(), []
    if out.exists():
        for l in out.read_text().splitlines():
            row = json.loads(l)
            if "result" in row:
                done.add(row["id"])
                kept.append(l)
        out.write_text("".join(l + "\n" for l in kept))  # failed rows go, so a rerun retries them
    todo = [r for r in reqs if r["id"] not in done]
    print(f"{len(todo)} to run, {len(done)} already done, {a.model} (json={mode}, {a.workers} workers)", file=sys.stderr)

    t0, ok, failed, skipped = time.time(), 0, 0, 0
    with ThreadPoolExecutor(a.workers) as ex, out.open("a") as f:
        for n, fut in enumerate(as_completed([ex.submit(one, r, a, key, mode) for r in todo]), 1):
            row = fut.result()
            if row.pop("skipped", None):
                skipped += 1
                continue
            ok, failed = ok + ("result" in row), failed + ("error" in row)
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            if n % 100 == 0:
                print(f"{n}/{len(todo)}, US${state['cost']:.4f}", file=sys.stderr)

    wall = round(time.time() - t0, 1)
    print(f"{ok} ok, {failed} failed, {skipped} not run, {state['in']} in / {state['out']} out "
          f"({state['reasoning_tokens']} reasoning), US${state['cost']:.6f}, {wall}s", file=sys.stderr)
    if state["stop"]:
        print(f"stopped at --max-cost {a.max_cost}; rerun with a higher cap to finish", file=sys.stderr)
    if a.usage_log:
        Path(a.usage_log).parent.mkdir(parents=True, exist_ok=True)
        with open(a.usage_log, "a") as f:
            f.write(json.dumps({"api": "openrouter-sync", "model": a.model, "prompt_tokens": state["in"],
                                "completion_tokens": state["out"], "reasoning_tokens": state["reasoning_tokens"],
                                "cost": state["cost"], "requests": ok + failed, "failed": failed, "wall_s": wall,
                                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}) + "\n")
    sys.exit(1 if failed or skipped else 0)


if __name__ == "__main__":
    main()

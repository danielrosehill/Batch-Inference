#!/usr/bin/env python3
"""Run a JSONL file of prompts on a local or self-hosted model. Stdlib only.

Works with anything serving the OpenAI chat API: Ollama, llama.cpp's llama-server, vLLM, LM Studio.
Same files as the other runners:
    in:  {"id": "row-1", "user": "...", "system": "... (optional)", "schema": {... optional}}
    out: {"id", "result"} or {"id", "error"}

Resumable: finished rows are kept and failed rows retried when you rerun the same command. If the
server goes away (a machine asleep or off), the run stops after 3 connection failures in a row,
rather than burning through every remaining row.

Usage:
  python3 scripts/local_batch.py in.jsonl out.jsonl --backend my-gpu-box --model qwen3:14b
  python3 scripts/local_batch.py in.jsonl out.jsonl --base-url http://localhost:11434 --model qwen3:14b
  ... --workers 1          parallel requests; defaults to the backend's `concurrency`, else 1
  ... --think on           leave a thinking model's reasoning on (default off)
  ... --json schema|object|none
  ... --usage-log data/llm-usage.jsonl

--backend names an entry in backends.json (see `backends.py`). A key, if the server wants one, comes
from the environment variable in the entry's `api_key_env` or from --api-key-env.
"""
import argparse, json, os, re, sys, threading, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backends import find, chat_url
from openrouter_batch import parse

lock = threading.Lock()
state = {"in": 0, "out": 0, "down": 0, "stop": False}
THINK = re.compile(r"<think>.*?</think>\s*", re.S)


def body_for(r, a, mode, kind):
    system = r.get("system") or ""
    if r.get("schema") and mode == "object":
        system = (system + "\n\nReply with one JSON object that matches this JSON Schema, and nothing else:\n"
                  + json.dumps(r["schema"])).strip()
    b = {"model": a.model, "max_tokens": a.max_tokens, "stream": False,
         "messages": ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": r["user"]}]}
    if a.temperature is not None:
        b["temperature"] = a.temperature
    if r.get("schema") and mode == "schema":
        b["response_format"] = {"type": "json_schema", "json_schema": {"name": "reply", "strict": True, "schema": r["schema"]}}
    elif r.get("schema") and mode == "object":
        b["response_format"] = {"type": "json_object"}
    if a.think == "off":
        if kind == "ollama":
            b["reasoning_effort"] = "none"
        elif kind == "vllm":
            b["chat_template_kwargs"] = {"enable_thinking": False}
    return b


def one(r, a, url, key, mode, kind):
    last = None
    headers = {"Content-Type": "application/json", **({"Authorization": f"Bearer {key}"} if key else {})}
    for attempt in range(a.retries + 1):
        if state["stop"]:
            return {"id": r["id"], "skipped": True}
        req = urllib.request.Request(url, data=json.dumps(body_for(r, a, mode, kind)).encode(), headers=headers)
        try:
            d = json.load(urllib.request.urlopen(req, timeout=a.timeout))
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read().decode()[:400]}"
            if e.code < 500 and e.code != 429:
                return {"id": r["id"], "error": last}
            time.sleep(2 ** attempt)
            continue
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            last = f"connection: {e}"[:300]
            with lock:
                state["down"] += 1
                if state["down"] >= 3:
                    state["stop"] = True
            time.sleep(2 ** attempt)
            continue
        with lock:
            state["down"] = 0
        u = d.get("usage") or {}
        choice = d["choices"][0]
        with lock:
            state["in"] += u.get("prompt_tokens") or 0
            state["out"] += u.get("completion_tokens") or 0
        text = THINK.sub("", choice["message"].get("content") or "").strip()
        if not text:
            last = f"empty reply (finish_reason={choice.get('finish_reason')}): raise --max-tokens if the model is thinking"
            continue
        if not r.get("schema") or mode == "none":
            return {"id": r["id"], "result": text}
        try:
            return {"id": r["id"], "result": parse(text)}
        except (ValueError, json.JSONDecodeError):
            last = f"unparseable reply (finish_reason={choice.get('finish_reason')})"
    return {"id": r["id"], "error": last}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("requests")
    ap.add_argument("out")
    ap.add_argument("--backend", help="name in backends.json")
    ap.add_argument("--base-url", help="server root, e.g. http://localhost:11434")
    ap.add_argument("--type", help="ollama | llama.cpp | vllm | lmstudio | openai-compatible")
    ap.add_argument("--model")
    ap.add_argument("--api-key-env")
    ap.add_argument("--json", choices=["schema", "object", "none"], default="schema")
    ap.add_argument("--think", choices=["off", "on"], default="off")
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--temperature", type=float)
    ap.add_argument("--workers", type=int)
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--timeout", type=int, default=600, help="seconds per request; a cold model load can take minutes")
    ap.add_argument("--usage-log")
    a = ap.parse_args()

    b = find(a.backend) if a.backend else {}
    base = a.base_url or b.get("base_url") or sys.exit("give --backend or --base-url")
    kind = a.type or b.get("type") or "openai-compatible"
    a.model = a.model or b.get("default_model") or sys.exit("give --model")
    workers = a.workers or b.get("concurrency") or 1
    env = a.api_key_env or b.get("api_key_env")
    key = os.environ.get(env) if env else None
    if env and not key:
        sys.exit(f"no ${env} in the environment")

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
        out.write_text("".join(l + "\n" for l in kept))
    todo = [r for r in reqs if r["id"] not in done]
    print(f"{len(todo)} to run, {len(done)} already done, {a.model} on {base} ({workers} workers)", file=sys.stderr)

    t0, ok, failed, skipped = time.time(), 0, 0, 0
    url = chat_url(base)
    with ThreadPoolExecutor(workers) as ex, out.open("a") as f:
        for n, fut in enumerate(as_completed([ex.submit(one, r, a, url, key, a.json, kind) for r in todo]), 1):
            row = fut.result()
            if row.pop("skipped", None):
                skipped += 1
                continue
            ok, failed = ok + ("result" in row), failed + ("error" in row)
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            if n % 50 == 0:
                left = (time.time() - t0) / n * (len(todo) - n)
                print(f"{n}/{len(todo)}, about {left / 60:.0f} min left", file=sys.stderr)

    wall = round(time.time() - t0, 1)
    tps = round(state["out"] / wall, 1) if wall else 0
    print(f"{ok} ok, {failed} failed, {skipped} not run, {state['in']} in / {state['out']} out, {wall}s, {tps} out tok/s", file=sys.stderr)
    if state["stop"]:
        print("stopped: server unreachable. Rerun the same command when it's back", file=sys.stderr)
    if a.usage_log:
        Path(a.usage_log).parent.mkdir(parents=True, exist_ok=True)
        with open(a.usage_log, "a") as f:
            f.write(json.dumps({"api": f"local:{a.backend or kind}", "model": a.model, "prompt_tokens": state["in"],
                                "completion_tokens": state["out"], "cost": 0, "requests": ok + failed, "failed": failed,
                                "wall_s": wall, "out_tok_s": tps,
                                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}) + "\n")
    sys.exit(1 if failed or skipped else 0)


if __name__ == "__main__":
    main()

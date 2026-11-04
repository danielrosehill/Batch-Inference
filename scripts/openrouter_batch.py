#!/usr/bin/env python3
"""Run a JSONL file of prompts through the OpenRouter Batch API (POST /api/v1/batches). Stdlib only.

For any model that is not Claude-on-Anthropic, including DeepSeek, the usual "cheapest batch".
Docs: https://openrouter.ai/docs/batch-quickstart. Batch-capable models:
https://openrouter.ai/models?variant=batch (or `or_models.py batch`).

Input JSONL is the same as anthropic_batch.py:
    {"id": "row-1", "user": "...", "system": "... (optional)", "schema": {... optional}}
Output JSONL: {"id", "result"} or {"id", "error"}, keyed by id (results are not in input order).

JSON modes (--json):
  schema  response_format json_schema. Not every provider honours it (DeepSeek's does not).
  object  response_format json_object, with the schema pasted into the system prompt. Default for
          deepseek/* models. The reply is parsed from the first "{" if the model wraps it.
  none    plain text.

Usage:
  python3 scripts/openrouter_batch.py in.jsonl out.jsonl --model deepseek/deepseek-v4.1-flash
  ... --provider deepseek          pin one provider (provider.only, allow_fallbacks false)
  ... --resume <batch id>          collect a batch already submitted
  ... --usage-log data/llm-usage.jsonl
Reasoning is switched off by default ({"enabled": false}); --reasoning low|medium|high turns it on.
"""
import argparse, json, os, sys, time, urllib.error, urllib.request
from pathlib import Path

API = "https://openrouter.ai/api/v1"
TERMINAL = {"completed", "failed", "expired", "cancelled"}


def call(method, path, key, body=None, missing_ok=False):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(f"{API}{path}", data=data, method=method,
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=300).read())
    except urllib.error.HTTPError as e:
        if missing_ok and e.code == 404:
            return None
        sys.exit(f"{method} {path}: HTTP {e.code} {e.read().decode()[:2000]}")


def body_for(r, mode, reasoning, max_tokens):
    system = r.get("system") or ""
    if r.get("schema") and mode == "object":
        system = (system + "\n\nReply with one JSON object that matches this JSON Schema, and nothing else:\n"
                  + json.dumps(r["schema"])).strip()
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": r["user"]}]
    b = {"messages": msgs, "max_tokens": max_tokens,
         "reasoning": {"enabled": False} if reasoning == "off" else {"effort": reasoning}}
    if r.get("schema") and mode == "schema":
        b["response_format"] = {"type": "json_schema", "json_schema": {"name": "reply", "strict": True, "schema": r["schema"]}}
    elif r.get("schema") and mode == "object":
        b["response_format"] = {"type": "json_object"}
    return b


def parse(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # DeepSeek json_object mode sometimes pads or wraps the object; take the first one.
        return json.JSONDecoder().raw_decode(text[text.index("{"):])[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("requests")
    ap.add_argument("out")
    ap.add_argument("--model", required=True, help="OpenRouter id without the :batch suffix, e.g. deepseek/deepseek-v4.1-flash")
    ap.add_argument("--provider", help="provider slug to pin, e.g. deepseek")
    ap.add_argument("--json", choices=["schema", "object", "none"])
    ap.add_argument("--reasoning", default="off", help="off | low | medium | high")
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--resume")
    ap.add_argument("--poll", type=int, default=30)
    ap.add_argument("--usage-log")
    a = ap.parse_args()

    key = os.environ.get("OPENROUTER_API_KEY") or sys.exit("no $OPENROUTER_API_KEY in the environment")
    model = a.model.removesuffix(":batch")
    mode = a.json or ("object" if model.startswith("deepseek/") else "schema")
    reqs = [json.loads(l) for l in Path(a.requests).read_text().splitlines() if l.strip()]
    schema_ids = {r["id"] for r in reqs if r.get("schema")}
    if len({r["id"] for r in reqs}) != len(reqs):
        sys.exit("ids must be unique")

    if a.resume:
        batch_id = a.resume
    else:
        # Key order matters: endpoint/model/provider/completion_window must precede requests (else 400).
        sub = {"endpoint": "/v1/chat/completions", "model": model}
        if a.provider:
            sub["provider"] = {"only": [a.provider], "allow_fallbacks": False}
        sub["completion_window"] = "24h"
        sub["requests"] = [{"custom_id": r["id"], "body": body_for(r, mode, a.reasoning, a.max_tokens)} for r in reqs]
        batch_id = call("POST", "/batches", key, sub)["id"]
        print(f"batch {batch_id}: {len(reqs)} requests to {model} (json={mode})", file=sys.stderr)

    # A GET straight after submit 404s ("Batch job ... not found") until the batch is visible;
    # seen 2026-10-22. Treat 404 as "not yet" for the first few minutes.
    started = time.time()
    while True:
        b = call("GET", f"/batches/{batch_id}", key, missing_ok=time.time() - started < 300)
        if b is None:
            print(f"{batch_id}: not visible yet", file=sys.stderr)
            time.sleep(a.poll)
            continue
        if b["status"] in TERMINAL:
            break
        c = b.get("request_counts") or {}
        print(f"{batch_id}: {b['status']}, {c.get('completed', 0)}/{c.get('total', '?')} done", file=sys.stderr)
        time.sleep(a.poll)
    if b["status"] != "completed":
        sys.exit(f"{batch_id}: {b['status']} {b.get('error')}")

    rows = []
    for res in b.get("results") or []:
        cid, resp = res["custom_id"], res.get("response")
        if res.get("error") or not resp or resp.get("status_code") != 200:
            rows.append({"id": cid, "error": res.get("error") or resp})
            continue
        choice = resp["body"]["choices"][0]
        text = choice["message"].get("content") or ""
        try:
            rows.append({"id": cid, "result": parse(text) if cid in schema_ids and mode != "none" else text})
        except (ValueError, json.JSONDecodeError):
            rows.append({"id": cid, "error": f"unparseable reply (finish_reason={choice.get('finish_reason')})", "raw": text})
    Path(a.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))

    u = b.get("usage") or {}
    failed = sum("error" in r for r in rows)
    print(f"batch {batch_id}: {len(rows) - failed} ok, {failed} failed, provider {b.get('provider')}, "
          f"{u.get('prompt_tokens')} in / {u.get('completion_tokens')} out, US${u.get('cost')}", file=sys.stderr)
    if a.usage_log:
        Path(a.usage_log).parent.mkdir(parents=True, exist_ok=True)
        with open(a.usage_log, "a") as f:
            f.write(json.dumps({"api": "openrouter-batch", "model": model, "provider": b.get("provider"),
                                "batch_id": batch_id, "prompt_tokens": u.get("prompt_tokens"),
                                "completion_tokens": u.get("completion_tokens"), "cost": u.get("cost"),
                                "requests": len(rows), "failed": failed,
                                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}) + "\n")


if __name__ == "__main__":
    main()

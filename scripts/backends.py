#!/usr/bin/env python3
"""The user's inference backends, from backends.json in the plugin's data directory. Stdlib only.

  list                     every configured backend
  check [NAME]             is it up, and which models does it serve
  discover                 look for local servers on the usual ports
  speed NAME [--model M]   time one real generation, and estimate a job with --items and --out-per-item

Backends hold connection facts only. Keys stay in environment variables (`api_key_env`). The guide to
when each is used lives in defaults.md. Format: shared/backends.example.json.
"""
import argparse, json, os, subprocess, sys, time, urllib.error, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PORTS = [("ollama", 11434), ("llama.cpp", 8080), ("vllm", 8000), ("lmstudio", 1234)]


def path():
    return Path(subprocess.check_output(["bash", str(HERE / "paths.sh"), "dir"], text=True).strip()) / "backends.json"


def load():
    p = path()
    return json.loads(p.read_text()).get("backends", []) if p.exists() else []


def find(name):
    for b in load():
        if b["name"] == name:
            return b
    sys.exit(f"no backend {name!r} in {path()}: run the onboarding skill, or `backends.py list`")


def root(base):
    return base.rstrip("/").removesuffix("/v1")


def chat_url(base):
    return root(base) + "/v1/chat/completions"


def get(url, key=None, timeout=4):
    h = {"Authorization": f"Bearer {key}"} if key else {}
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout))


def models(base, key=None, timeout=4):
    return sorted(m["id"] for m in get(root(base) + "/v1/models", key, timeout).get("data") or [])


def key_of(b):
    return os.environ.get(b["api_key_env"]) if b.get("api_key_env") else None


def cmd_list(a):
    rows = load()
    if a.json:
        return print(json.dumps(rows, indent=1))
    if not rows:
        return print(f"no backends yet ({path()}): run the onboarding skill")
    for b in rows:
        print(f"{b['name']:20s} {b.get('type', '?'):18s} {b.get('base_url', ''):40s} {b.get('default_model', '')}")


def cmd_check(a):
    rows = []
    for b in [find(a.name)] if a.name else load():
        try:
            ms = models(b["base_url"], key_of(b))
            r = {"name": b["name"], "up": True, "models": ms}
        except Exception as e:
            r = {"name": b["name"], "up": False, "error": str(e)[:120]}
        rows.append(r)
    if a.json:
        return print(json.dumps(rows, indent=1))
    for r in rows:
        print(f"{r['name']:20s} " + (f"up, {len(r['models'])} models: {', '.join(r['models'][:12])}" if r["up"] else f"DOWN: {r['error']}"))
    if not rows:
        print("no backends configured")


def cmd_discover(a):
    found = []
    for kind, port in PORTS:
        base = f"http://localhost:{port}"
        try:
            found.append({"type": kind, "base_url": base, "models": models(base, timeout=2)})
        except Exception:
            pass
    print(json.dumps(found, indent=1) if a.json else "\n".join(f"{f['type']:10s} {f['base_url']} {f['models']}" for f in found) or "no local server answering")


def cmd_speed(a):
    b = find(a.name)
    model = a.model or b.get("default_model") or sys.exit("give --model")
    body = {"model": model, "max_tokens": 200, "stream": False,
            "messages": [{"role": "user", "content": "Write about 100 words on how bread rises."}]}
    if b.get("type") == "ollama":
        body["reasoning_effort"] = "none"
    h = {"Content-Type": "application/json", **({"Authorization": f"Bearer {key_of(b)}"} if key_of(b) else {})}

    def run():
        t = time.time()
        req = urllib.request.Request(chat_url(b["base_url"]), data=json.dumps(body).encode(), headers=h)
        d = json.load(urllib.request.urlopen(req, timeout=600))
        return time.time() - t, (d.get("usage") or {}).get("completion_tokens") or 0

    try:
        cold, _ = run()  # the first call may load the model
        secs, toks = run()
    except urllib.error.HTTPError as e:
        sys.exit(f"{b['name']}: HTTP {e.code} {e.read().decode()[:200]}")
    except OSError as e:
        sys.exit(f"{b['name']}: unreachable: {e}")
    tps = toks / secs if secs else 0
    r = {"backend": b["name"], "model": model, "first_call_s": round(cold, 1), "out_tok_s": round(tps, 1)}
    if a.items and tps:
        r["est_hours"] = round(a.items * a.out_per_item / tps / max(b.get("concurrency") or 1, 1) / 3600, 2)
    print(json.dumps(r, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0], epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n in ("list", "discover"):
        sub.add_parser(n).add_argument("--json", action="store_true")
    c = sub.add_parser("check")
    c.add_argument("name", nargs="?")
    c.add_argument("--json", action="store_true")
    s = sub.add_parser("speed")
    s.add_argument("name")
    s.add_argument("--model")
    s.add_argument("--items", type=int, default=0)
    s.add_argument("--out-per-item", type=float, default=0)
    a = ap.parse_args()
    {"list": cmd_list, "check": cmd_check, "discover": cmd_discover, "speed": cmd_speed}[a.cmd](a)


if __name__ == "__main__":
    main()

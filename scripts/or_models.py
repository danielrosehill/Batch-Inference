#!/usr/bin/env python3
"""Live checks and spend for OpenRouter bulk jobs. Stdlib only.

  probe ID..  one tiny live call per model with reasoning off: does it answer, what did it cost
  spend LOG   measured cost per model from a --usage-log file, plus cost per request
  account     this key's spend today / this week / this month, and any limit

probe and account need OPENROUTER_API_KEY; spend reads a local usage log.

Model discovery (batch-capable models, bulk candidates, hosts) moved to `orexplorer` on 2026-11-14,
in the ai-model-research plugin (github.com/danielrosehill/AI-Model-Research-Plugin):

  OX="uvx --from git+https://github.com/danielrosehill/AI-Model-Research-Plugin orexplorer"
  $OX batch --est-in 2e6 --est-out 5e5 --table                           (was: or_models.py batch)
  $OX bulk --items 5000 --in-per-item 300 --out-per-item 120 --table     (was: candidates)
  $OX endpoints <id> --table                                             (was: hosts)

The listing is a claim, not a test: models listed as usable have returned 404 or 429 in practice, so
`probe` a shortlist before trusting it.
"""
import argparse, collections, json, os, sys, time, urllib.error, urllib.request

API = "https://openrouter.ai/api/v1"
UA = {"User-Agent": "batch-inference-plugin"}


def get(path, key=None):
    h = dict(UA, **({"Authorization": f"Bearer {key}"} if key else {}))
    return json.load(urllib.request.urlopen(urllib.request.Request(API + path, headers=h), timeout=60))


def need_key():
    return os.environ.get("OPENROUTER_API_KEY") or sys.exit("no $OPENROUTER_API_KEY in the environment")


def per_m(v):
    return round(float(v or 0) * 1e6, 4)


def prices(m):
    return per_m(m["pricing"].get("prompt")), per_m(m["pricing"].get("completion"))


















def cmd_probe(a):
    key = need_key()
    rows, total = [], 0.0
    for mid in a.ids:
        body = {"model": mid, "max_tokens": 64, "usage": {"include": True}, "reasoning": {"enabled": False},
                "response_format": {"type": "json_object"},
                "messages": [{"role": "user", "content": 'Reply with the JSON object {"ok": true} and nothing else.'}]}
        req = urllib.request.Request(f"{API}/chat/completions", data=json.dumps(body).encode(),
                                     headers=dict(UA, **{"Authorization": f"Bearer {key}", "Content-Type": "application/json"}))
        t = time.time()
        row = {"id": mid}
        try:
            d = json.load(urllib.request.urlopen(req, timeout=90))
            u = d.get("usage") or {}
            text = (d["choices"][0]["message"].get("content") or "").strip()
            try:
                good = json.loads(text[text.index("{"):text.rindex("}") + 1]).get("ok") is True
            except ValueError:
                good = False
            rt = (u.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0
            row.update(status="ok" if good else "bad-json", seconds=round(time.time() - t, 1), host=d.get("provider"),
                       served=d.get("model"), reasoning_tokens=rt, cost=u.get("cost"))
            total += u.get("cost") or 0
        except urllib.error.HTTPError as e:
            row.update(status=f"http {e.code}", error=e.read().decode()[:160])
        except Exception as e:
            row.update(status="error", error=str(e)[:160])
        rows.append(row)
        if not a.json:
            print(f"{mid:46s} {row['status']:9s} " + (f"{row['seconds']:5.1f}s {row['host']} reasoning_tokens={row['reasoning_tokens']} ${row['cost']}"
                                                      if "seconds" in row else row.get("error", "")))
    if a.json:
        print(json.dumps(rows, indent=1))
    else:
        print(f"total ${total:.6f}")


def cmd_spend(a):
    agg = collections.defaultdict(lambda: collections.Counter())
    for line in open(a.log):
        if not line.strip():
            continue
        r = json.loads(line)
        c = agg[(r.get("api", "?"), r.get("model", "?"))]
        c["runs"] += 1
        c["requests"] += r.get("requests") or 1
        c["failed"] += r.get("failed") or 0
        c["in"] += r.get("prompt_tokens") or r.get("input_tokens") or 0
        c["out"] += r.get("completion_tokens") or r.get("output_tokens") or 0
        c["cost"] += r.get("cost") or r.get("est_cost_usd") or 0
    rows = [dict(api=k[0], model=k[1], **v, cost_per_1k=round(v["cost"] / max(v["requests"], 1) * 1000, 4),
                 in_per_req=round(v["in"] / max(v["requests"], 1)), out_per_req=round(v["out"] / max(v["requests"], 1)))
            for k, v in agg.items()]
    rows.sort(key=lambda r: -r["cost"])
    if a.json:
        return print(json.dumps(rows, indent=1))
    print(f"{'api':18s} {'model':40s} {'runs':>4s} {'reqs':>7s} {'fail':>5s} {'in/req':>7s} {'out/req':>7s} {'US$':>9s} {'$/1k req':>9s}")
    for r in rows:
        print(f"{r['api']:18s} {r['model']:40s} {r['runs']:>4d} {r['requests']:>7d} {r['failed']:>5d} {r['in_per_req']:>7d} "
              f"{r['out_per_req']:>7d} {r['cost']:>9.4f} {r['cost_per_1k']:>9.4f}")
    print(f"total US${sum(r['cost'] for r in rows):.4f}")


def cmd_account(a):
    d = get("/key", need_key())
    d = d.get("data", d)
    keep = {k: d.get(k) for k in ("usage_daily", "usage_weekly", "usage_monthly", "usage", "limit", "limit_remaining")}
    print(json.dumps(keep, indent=1) if a.json else "\n".join(f"{k:16s} {v}" for k, v in keep.items()))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0], epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("probe")
    p.add_argument("ids", nargs="+")
    p.add_argument("--json", action="store_true")
    s = sub.add_parser("spend")
    s.add_argument("log")
    s.add_argument("--json", action="store_true")
    k = sub.add_parser("account")
    k.add_argument("--json", action="store_true")
    a = ap.parse_args()
    {"probe": cmd_probe, "spend": cmd_spend, "account": cmd_account}[a.cmd](a)


if __name__ == "__main__":
    main()

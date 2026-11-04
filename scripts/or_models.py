#!/usr/bin/env python3
"""Read OpenRouter's model list and find what a bulk job can run on. Stdlib only.

  batch       every model with a batch variant: batch vs sync price, which is cheaper, reasoning, JSON
  candidates  sync models fit for bulk work ("instruct" models): text out, JSON mode, reasoning can be
              off, not free, not expiring, ranked by estimated job cost
  hosts ID    who actually serves a model, with each host's price and quantisation
  probe ID..  one tiny live call per model with reasoning off: does it answer, what did it cost
  spend LOG   measured cost per model from a --usage-log file, plus cost per request
  account     this key's spend today / this week / this month, and any limit

`batch`, `candidates` and `hosts` read public endpoints and need no key. `probe` and `account` need
OPENROUTER_API_KEY. Both listing commands take --json, and --est-in/--est-out (job tokens), or
--items with --in-per-item/--out-per-item, to add a cost column.

The listing is a claim, not a test. `reasoning.mandatory: false` and `response_format` come from
OpenRouter's metadata, and models listed as usable have still returned 404 or 429 in practice, so
`probe` a shortlist before trusting it. Prices are the listing's, which is roughly the cheapest
host; the host a job really lands on can cost more (see `hosts`).
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


def peak(m):
    """Highest (in, out) across time-of-day overrides, or None if the price never changes."""
    o = m["pricing"].get("overrides") or []
    if not o:
        return None
    top = max(o, key=lambda x: float(x.get("completion") or 0))
    p = per_m(top.get("prompt")), per_m(top.get("completion"))
    return p if p != prices(m) else None


def reasoning(m):
    """none: no reasoning at all. optional: can be switched off. mandatory: cannot."""
    r = m.get("reasoning")
    if r and r.get("mandatory"):
        return "mandatory"
    if r is None and "reasoning" not in (m.get("supported_parameters") or []):
        return "none"
    return "optional"


def json_mode(m):
    p = m.get("supported_parameters") or []
    return "schema" if "structured_outputs" in p else "object" if "response_format" in p else "-"


def text_out(m):
    return (m.get("architecture") or {}).get("output_modalities") == ["text"]


def job_tokens(a):
    if a.items:
        return a.items * a.in_per_item, a.items * a.out_per_item
    return a.est_in, a.est_out


def cost(tin, tout, p):
    return None if p is None else round((tin * p[0] + tout * p[1]) / 1e6, 4)


def fmt(p):
    return f"{p[0]:.3f}/{p[1]:.3f}" if p else "-"


def add_est(ap):
    ap.add_argument("--est-in", type=float, default=0, help="job input tokens")
    ap.add_argument("--est-out", type=float, default=0, help="job output tokens")
    ap.add_argument("--items", type=int, default=0, help="item count, with --in-per-item and --out-per-item")
    ap.add_argument("--in-per-item", type=float, default=0)
    ap.add_argument("--out-per-item", type=float, default=0)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--json", action="store_true")


def cmd_batch(a):
    data = get("/models")["data"]
    ids = {m["id"]: m for m in data}
    tin, tout = job_tokens(a)
    rows = []
    for m in data:
        if not m["id"].endswith(":batch"):
            continue
        base = m["id"].removesuffix(":batch")
        if a.terms and not any(t in base for t in a.terms):
            continue
        s = ids.get(base)
        bp, sp = prices(m), prices(s) if s else None
        # Compare at the job's token mix when there is one, else at 1:1.
        wi, wo = (tin, tout) if tin or tout else (1e6, 1e6)
        cheaper = "?" if sp is None else "batch" if cost(wi, wo, bp) < cost(wi, wo, sp) else \
            "sync" if cost(wi, wo, sp) < cost(wi, wo, bp) else "same"
        rows.append({"id": base, "batch": bp, "sync": sp, "cheaper": cheaper, "reasoning": reasoning(m),
                     "json": json_mode(m), "context": m.get("context_length"),
                     "est_batch": cost(tin, tout, bp), "est_sync": cost(tin, tout, sp)})
    rows.sort(key=lambda r: r["batch"][0] + r["batch"][1])
    if a.dearer_only:
        rows = [r for r in rows if r["cheaper"] == "sync"]
    n = len(rows)
    rows = rows[:a.limit] if a.limit else rows
    if a.json:
        return print(json.dumps(rows, indent=1))
    est = tin or tout
    print(f"{'model':46s} {'batch in/out':>15s} {'sync in/out':>15s} {'cheaper':>7s} {'reasoning':>9s} {'json':>6s}"
          + ("  est batch / sync $" if est else ""))
    for r in rows:
        print(f"{r['id']:46s} {fmt(r['batch']):>15s} {fmt(r['sync']):>15s} {r['cheaper']:>7s} {r['reasoning']:>9s} {r['json']:>6s}"
              + (f"  {r['est_batch']} / {r['est_sync']}" if est else ""))
    print(f"{n} batch models. US$ per M tokens. A batch runs on the base id through POST /api/v1/batches.")


def cmd_candidates(a):
    data = get("/models")["data"]
    ids = {m["id"] for m in data}
    tin, tout = job_tokens(a)
    rows = []
    for m in data:
        mid = m["id"]
        if mid.endswith((":batch", ":free")) or (mid.startswith("~") and not a.aliases):
            continue
        p = prices(m)
        if p[0] <= 0 or p[1] <= 0 or not text_out(m) or m.get("expiration_date"):
            continue
        r, j = reasoning(m), json_mode(m)
        if r == "mandatory" and not a.reasoning_ok:
            continue
        if j == "-" and not a.no_json:
            continue
        if p[1] > a.max_out or (a.max_in and p[0] > a.max_in) or (a.min_context and (m.get("context_length") or 0) < a.min_context):
            continue
        if a.terms and not any(t in mid for t in a.terms):
            continue
        pk = peak(m)
        rows.append({"id": mid, "sync": p, "peak": pk, "reasoning": r, "json": j, "context": m.get("context_length"),
                     "created": time.strftime("%Y-%m-%d", time.gmtime(m.get("created") or 0)),
                     "has_batch": mid + ":batch" in ids, "est_sync": cost(tin, tout, p), "est_peak": cost(tin, tout, pk)})
    w = (tin, tout) if tin or tout else (1, 3)  # bulk jobs are usually output-heavy
    rows.sort(key=lambda r: w[0] * r["sync"][0] + w[1] * r["sync"][1])
    n = len(rows)
    rows = rows[:a.limit] if a.limit else rows
    if a.json:
        return print(json.dumps(rows, indent=1))
    est = tin or tout
    print(f"{'model':46s} {'sync in/out':>15s} {'peak in/out':>15s} {'reasoning':>9s} {'json':>6s} {'ctx':>8s} {'added':>10s} batch"
          + ("  est sync $" if est else ""))
    for r in rows:
        print(f"{r['id']:46s} {fmt(r['sync']):>15s} {fmt(r['peak']):>15s} {r['reasoning']:>9s} {r['json']:>6s} "
              f"{r['context'] or 0:>8d} {r['created']:>10s} {'yes' if r['has_batch'] else 'no ':>5s}"
              + (f"  {r['est_sync']}" if est else ""))
    print(f"{n} candidates. Listing claims only: `probe` a shortlist before use.")


def cmd_hosts(a):
    d = get(f"/models/{a.id}/endpoints")["data"]
    rows = [{"host": e.get("provider_name"), "tag": e.get("tag"), "quant": e.get("quantization"),
             "in": per_m(e["pricing"].get("prompt")), "out": per_m(e["pricing"].get("completion")),
             "status": e.get("status")} for e in d.get("endpoints", [])]
    rows.sort(key=lambda r: r["in"] + r["out"])
    if a.json:
        return print(json.dumps(rows, indent=1))
    for r in rows:
        print(f"{r['host'] or '?':20s} {r['tag'] or '':28s} {r['quant'] or '':8s} {r['in']:7.3f}/{r['out']:<7.3f} status {r['status']}")


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
    b = sub.add_parser("batch")
    b.add_argument("terms", nargs="*", help="substring filters on the id")
    b.add_argument("--dearer-only", action="store_true", help="only models where batch costs more than sync")
    add_est(b)
    c = sub.add_parser("candidates")
    c.add_argument("terms", nargs="*", help="substring filters on the id")
    c.add_argument("--max-out", type=float, default=2.0, help="max output US$/M (default 2)")
    c.add_argument("--max-in", type=float, default=0)
    c.add_argument("--min-context", type=int, default=0)
    c.add_argument("--reasoning-ok", action="store_true", help="keep models whose reasoning cannot be switched off")
    c.add_argument("--no-json", action="store_true", help="keep models with no JSON mode")
    c.add_argument("--aliases", action="store_true", help="keep ~vendor/*-latest aliases (their listed price is unreliable)")
    add_est(c)
    h = sub.add_parser("hosts")
    h.add_argument("id")
    h.add_argument("--json", action="store_true")
    p = sub.add_parser("probe")
    p.add_argument("ids", nargs="+")
    p.add_argument("--json", action="store_true")
    s = sub.add_parser("spend")
    s.add_argument("log")
    s.add_argument("--json", action="store_true")
    k = sub.add_parser("account")
    k.add_argument("--json", action="store_true")
    a = ap.parse_args()
    {"batch": cmd_batch, "candidates": cmd_candidates, "hosts": cmd_hosts, "probe": cmd_probe,
     "spend": cmd_spend, "account": cmd_account}[a.cmd](a)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Compare OpenRouter sync vs :batch prices on the day (public /api/v1/models, no key needed).

Batch is NOT always cheaper on OpenRouter: on 2026-10-19 the deepseek-v4.1-flash :batch id was
dearer than sync; on 2026-10-22 it was 6x cheaper. Check before every large run.

  python3 scripts/or_prices.py deepseek haiku-5.5 gpt-oss    substring match on ids
  python3 scripts/or_prices.py --batch-only --cheapest 15     cheapest batch-capable models
  ... --est-in 2000000 --est-out 500000                       add a job cost estimate column
  python3 scripts/or_prices.py --latest                       what each ~<family>-latest alias points at
  ... --record <research-repo>/prices.jsonl                   append the rows shown, dated today
  ... --json                                                  machine-readable rows instead of the table

`~vendor/<family>-latest` aliases (e.g. ~google/gemini-flash-latest) have NO :batch variant: a batch
needs the concrete id. The /models API does not say what an alias points at, and its listed price is
not a guide: on 2026-10-31 ~google/gemini-flash-latest was listed at gemini-3.7-flash's price but served
google/gemini-3.8-flash. So --latest resolves each alias with one tiny sync call and reads the
response's `model` field (needs OPENROUTER_API_KEY; costs well under a cent for
all aliases). Without a key it falls back to a price-match guess, marked "?".
"""
import argparse, datetime, json, re, sys, urllib.request

ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
ap.add_argument("terms", nargs="*")
ap.add_argument("--batch-only", action="store_true")
ap.add_argument("--cheapest", type=int)
ap.add_argument("--est-in", type=float, default=0, help="estimated input tokens for the job")
ap.add_argument("--est-out", type=float, default=0, help="estimated output tokens (incl. reasoning)")
ap.add_argument("--latest", action="store_true", help="resolve ~*-latest aliases to concrete ids")
ap.add_argument("--record", metavar="PRICES_JSONL", help="append shown rows to the notebook's prices.jsonl")
ap.add_argument("--json", action="store_true")
a = ap.parse_args()

data = json.load(urllib.request.urlopen("https://openrouter.ai/api/v1/models", timeout=60))["data"]
ids = {m["id"]: m for m in data}
today = datetime.date.today().isoformat()


def price(m):
    p = m["pricing"]
    return round(float(p["prompt"]) * 1e6, 4), round(float(p["completion"]) * 1e6, 4)


def probe(alias):
    import os
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return None
    body = json.dumps({"model": alias, "max_tokens": 16, "reasoning": {"effort": "low"},
                       "messages": [{"role": "user", "content": "ok"}]}).encode()
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=60)).get("model")
    except Exception:
        return None


def resolve(alias):
    """Live probe first; else the newest same-vendor concrete id with the family words and the same price, marked '?'."""
    served = probe(alias)
    if served:
        return served
    vendor, fam = re.match(r"~([^/]+)/(.+)-latest$", alias).groups()
    words = [w for w in fam.split("-") if w not in (vendor,)]
    target = price(ids[alias])
    cands = [m for m in data if m["id"].startswith(vendor + "/") and not m["id"].endswith(":batch")
             and all(w in m["id"] for w in words) and price(m) == target]
    return max(cands, key=lambda m: m.get("created", 0))["id"] + "?" if cands else None


rows = []
for m in data:
    mid = m["id"]
    if mid.endswith(":batch") or (a.batch_only and mid + ":batch" not in ids):
        continue
    if a.latest and not mid.startswith("~"):
        continue
    if a.terms and not any(t in mid for t in a.terms):
        continue
    si, so = price(m)
    target = resolve(mid) if mid.startswith("~") else None
    b = ids.get((target or mid).rstrip("?") + ":batch") or ids.get(re.sub(r"-\d{4}$", "", (target or mid).rstrip("?")) + ":batch")
    bi, bo = price(b) if b else (None, None)
    rows.append({"id": mid, "resolves_to": target, "sync_in": si, "sync_out": so, "batch_in": bi, "batch_out": bo})

key = (lambda r: (r["batch_in"] + r["batch_out"]) if r["batch_in"] is not None else (r["sync_in"] + r["sync_out"])) \
    if a.batch_only else (lambda r: r["sync_in"] + r["sync_out"])
rows.sort(key=key)
if a.cheapest:
    rows = rows[:a.cheapest]

if a.record:
    with open(a.record, "a") as f:
        for r in rows:
            for mode in ("sync", "batch"):
                i, o = r[f"{mode}_in"], r[f"{mode}_out"]
                if i is None:
                    continue
                model = (r["resolves_to"] or r["id"]).rstrip("?") + (":batch" if mode == "batch" else "")
                f.write(json.dumps({"checked": today, "provider": "openrouter", "model": model, "mode": mode,
                                    "usd_per_mtok_in": i, "usd_per_mtok_cached_in": None, "usd_per_mtok_out": o,
                                    "turnaround": "24h window" if mode == "batch" else "realtime",
                                    "source": "https://openrouter.ai/api/v1/models", "how": "or_prices.py (live API)",
                                    "note": (f"via alias {r['id']}" + (" (price-match guess)" if r["resolves_to"].endswith("?") else " (live probe)")) if r["resolves_to"] else ""}) + "\n")
    print(f"recorded {len(rows)} models -> {a.record}", file=sys.stderr)

if a.json:
    print(json.dumps(rows, indent=1))
    sys.exit()
est = a.est_in or a.est_out
print(f"{'model':50s} {'sync in/out $/M':>16s} {'batch in/out $/M':>17s}" + ("  est sync / batch $" if est else ""))
for r in rows:
    name = r["id"] + (f" -> {r['resolves_to']}" if r["resolves_to"] else "")
    bs = f"{r['batch_in']:.3f}/{r['batch_out']:.3f}" if r["batch_in"] is not None else "-"
    line = f"{name:50s} {r['sync_in']:7.3f}/{r['sync_out']:<8.3f} {bs:>17s}"
    if est:
        line += f"  {(a.est_in * r['sync_in'] + a.est_out * r['sync_out']) / 1e6:.2f}"
        line += f" / {(a.est_in * r['batch_in'] + a.est_out * r['batch_out']) / 1e6:.2f}" if r["batch_in"] is not None else " / -"
    print(line)

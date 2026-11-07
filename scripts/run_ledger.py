#!/usr/bin/env python3
"""A small ledger of batch runs: what the job was, what ran it, cost, how it went.

  add     append one run to runs.jsonl and re-render RUNS.md
  find    search past runs (JSON out, newest first)
  render  rebuild RUNS.md from runs.jsonl

The ledger dir comes from --ledger, else `paths.sh ledger`. Stdlib only.
"""
import argparse, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def ledger_dir(arg):
    if arg:
        return Path(arg).expanduser()
    return Path(subprocess.check_output(["bash", str(HERE / "paths.sh"), "ledger"], text=True).strip())


def read(d):
    p = d / "runs.jsonl"
    return [json.loads(l) for l in p.open() if l.strip()] if p.exists() else []


def cell(v):
    return "" if v is None else str(v).replace("|", "\\|").replace("\n", " ")


def render(d):
    rows = sorted(read(d), key=lambda r: r["date"], reverse=True)
    out = ["# Batch runs", "", "Generated from `runs.jsonl`. Newest first. Rating is 1-5 for how well the model did the task.", "",
           "| Date | Job | Task | Data | Model | Route | Cost (US$) | Rating | Notes | Also considered |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        tok = f'{r["tokens_in"]:,} in / {r["tokens_out"]:,} out' if r.get("tokens_in") is not None else ""
        data = "; ".join(x for x in [f'{r["items"]:,} items', r.get("data_size"), tok] if x)
        cost = f'{r["cost_usd"]:.4f}' + ("" if r.get("cost_basis") == "measured" else " (est.)")
        out.append("| " + " | ".join(cell(x) for x in [
            r["date"], r["job"], r["task_type"], data, f'`{r["model"]}`', r["route"], cost,
            r.get("rating"), r.get("notes"), ", ".join(r.get("alternatives") or [])]) + " |")
    (d / "RUNS.md").write_text("\n".join(out) + "\n")


def cmd_add(a, d):
    if a.rating is not None and not 1 <= a.rating <= 5:
        sys.exit("rating must be 1-5")
    row = {"date": a.date, "job": a.job, "task_type": a.task_type, "items": a.items, "data_size": a.data_size,
           "tokens_in": a.tokens_in, "tokens_out": a.tokens_out, "model": a.model, "route": a.route,
           "cost_usd": a.cost, "cost_basis": a.cost_basis, "rating": a.rating, "notes": a.notes,
           "alternatives": [x.strip() for x in a.alternatives.split(",") if x.strip()]}
    d.mkdir(parents=True, exist_ok=True)
    with (d / "runs.jsonl").open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    render(d)
    print(json.dumps(row, ensure_ascii=False))


def cmd_find(a, d):
    rows = sorted(read(d), key=lambda r: r["date"], reverse=True)
    terms = [t.lower() for t in a.terms]
    hits = [r for r in rows
            if all(t in json.dumps(r, ensure_ascii=False).lower() for t in terms)
            and (not a.model or a.model.lower() in r["model"].lower())
            and (not a.task_type or a.task_type.lower() == r["task_type"].lower())
            and (a.min_rating is None or (r.get("rating") or 0) >= a.min_rating)]
    print(json.dumps({"total_runs": len(rows), "matches": hits}, indent=1, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ledger")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("add")
    p.add_argument("--date", required=True, help="YYYY-MM-DD")
    p.add_argument("--job", required=True, help="one line, safe to publish")
    p.add_argument("--task-type", required=True, help="classification, extraction, generation, summarising, judging, ...")
    p.add_argument("--items", type=int, required=True)
    p.add_argument("--data-size", help="what the data was, e.g. '5,199 repo descriptions, ~170 words each'")
    p.add_argument("--tokens-in", type=int)
    p.add_argument("--tokens-out", type=int)
    p.add_argument("--model", required=True)
    p.add_argument("--route", required=True, help="e.g. openrouter-sync, openrouter-batch, anthropic-batch, local")
    p.add_argument("--cost", type=float, required=True, help="US$")
    p.add_argument("--cost-basis", choices=["measured", "estimated"], default="measured")
    p.add_argument("--rating", type=int, help="1-5, how well it did the task")
    p.add_argument("--notes", default="")
    p.add_argument("--alternatives", default="", help="comma-separated models considered")
    p.set_defaults(fn=cmd_add)
    q = sub.add_parser("find")
    q.add_argument("terms", nargs="*")
    q.add_argument("--model")
    q.add_argument("--task-type")
    q.add_argument("--min-rating", type=int)
    q.set_defaults(fn=cmd_find)
    r = sub.add_parser("render")
    r.set_defaults(fn=lambda a, d: render(d))
    a = ap.parse_args()
    a.fn(a, ledger_dir(a.ledger))


if __name__ == "__main__":
    main()

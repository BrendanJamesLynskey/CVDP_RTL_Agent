"""M3l descriptive tables from the four scored CSVs (stdlib only). Usage: analyze_tables.py IDS16 FIRES_HELDOUT E_CSVs R_CSVs
(E_CSVs and R_CSVs are comma lists). Prints markdown."""
import csv, statistics, sys, collections

ids16 = [l.strip() for l in open(sys.argv[1]) if l.strip() and not l.startswith("#")]
ho = {l.strip() for l in open(sys.argv[2]) if l.strip()}
def rows(spec):
    out = []
    for f in spec.split(","):
        out += [r for r in csv.DictReader(open(f)) if r["id"] in ids16]
    return out
E, R = rows(sys.argv[3]), rows(sys.argv[4])
def f(x): return float(x) if x not in ("", None) else 0.0

print("### Per problem: passes out of 5 runs, and the example(s) shown\n")
print("| Problem | Set | R | E | E - R | Example(s) shown to E | E llm_error rows |\n|---|---|---|---|---|---|---|")
tot = collections.Counter()
for i in sorted(ids16):
    e = [r for r in E if r["id"] == i]; r = [x for x in R if x["id"] == i]
    pe, pr = sum(x["pass"] == "1" for x in e), sum(x["pass"] == "1" for x in r)
    ex = sorted({x.get("examples_ids", "") for x in e} - {""})
    ne = sum(x["stop_reason"] == "llm_error" for x in e)
    st = "held-out" if i in ho else "dev"
    print(f"| {i} | {st} | {pr}/{len(r)} | {pe}/{len(e)} | {pe-pr:+d} | {'; '.join(ex)} | {ne} |")
    tot[st, "R"] += pr; tot[st, "E"] += pe; tot[st, "n"] += len(r)
print("\n### Dev / held-out split of the 16 (descriptive only)\n")
print("| Set | Problems | Runs per arm | R passes | E passes | R rate | E rate |\n|---|---|---|---|---|---|---|")
for st in ("held-out", "dev"):
    n = tot[st, "n"]
    print(f"| {st} | {n//5} | {n} | {tot[st,'R']} | {tot[st,'E']} | {100*tot[st,'R']/n:.1f}% | {100*tot[st,'E']/n:.1f}% |")
n = tot["held-out","n"] + tot["dev","n"]
print(f"| both | 16 | {n} | {tot['held-out','R']+tot['dev','R']} | {tot['held-out','E']+tot['dev','E']} | "
      f"{100*(tot['held-out','R']+tot['dev','R'])/n:.1f}% | {100*(tot['held-out','E']+tot['dev','E'])/n:.1f}% |")

print("\n### Effort and estimated cost, 16 problems x 5 runs per arm\n")
print("| | R | E |\n|---|---|---|")
def agg(rs, k, fn): return fn([f(x[k]) for x in rs])
for lab, k, fn, fmt in [("Rows", None, None, None),
        ("Prompt tokens, total", "prompt_tokens", sum, "{:,.0f}"), ("Completion tokens, total", "completion_tokens", sum, "{:,.0f}"),
        ("Cache-read tokens, total", "cache_read_tokens", sum, "{:,.0f}"),
        ("Turns, median", "turns", statistics.median, "{:.1f}"), ("Turns, mean", "turns", statistics.mean, "{:.2f}"),
        ("Wall time per run, median (s)", "wall_time_s", statistics.median, "{:.1f}"),
        ("Wall time per run, mean (s)", "wall_time_s", statistics.mean, "{:.1f}"),
        ("Estimated cost, total (USD, `api_cost_estimate_usd`)", "api_cost_estimate_usd", sum, "{:.4f}"),
        ("Estimated cost per run (USD)", "api_cost_estimate_usd", statistics.mean, "{:.5f}")]:
    if k is None: print(f"| {lab} | {len(R)} | {len(E)} |"); continue
    print(f"| {lab} | {fmt.format(agg(R,k,fn))} | {fmt.format(agg(E,k,fn))} |")
print("\nProvider-reported `cost_usd` is 0 on every row (unreported), so the estimate column is the only cost figure.")
print("\nE rows by example size: runs with an example `examples_bytes` median "
      f"{statistics.median([f(x['examples_bytes']) for x in E if x.get('examples_ids')]):.0f} bytes; "
      f"{sum(1 for x in E if x.get('examples_ids'))} of {len(E)} E runs carried examples.")

print("\n### Failure labels (`failure_label`; empty = passed) on the 16\n")
labs = sorted({x["failure_label"] for x in E + R}, key=lambda s: (s != "", s))
print("| Label | R | E |\n|---|---|---|")
for l in labs:
    print(f"| {l or '(passed)'} | {sum(x['failure_label']==l for x in R)} | {sum(x['failure_label']==l for x in E)} |")
print("\n### Stop reasons\n\n| Stop reason | R | E |\n|---|---|---|")
for s in sorted({x["stop_reason"] for x in E + R}):
    print(f"| {s} | {sum(x['stop_reason']==s for x in R)} | {sum(x['stop_reason']==s for x in E)} |")
print("\n### Withheld entries per E run\n")
print(f"`examples_withheld_repo` values: {sorted({x['examples_withheld_repo'] for x in E})}; "
      f"`examples_withheld_overlap` values: {sorted({x['examples_withheld_overlap'] for x in E})}; "
      f"`skill_text_copied` values: {sorted({x['skill_text_copied'] for x in E})}.")

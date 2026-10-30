"""M3g's descriptive tables from collect.py CSVs: which skills the plan loaded and how often, pass rate with and
without each skill loaded (by problem-run; not causal, the plan chooses), unknown names and bytes loaded, prompt
tokens per problem-run by arm (the added tokens), and pass rate by category. No test is run here: the
pre-registered comparisons are ablate.py's.

Usage: python3 tools/m3g_tables.py --arm A=a1.csv,a2.csv --arm K=k1.csv,... [--ids FILE] [--skills-arm K]
"""
import argparse
import collections
import csv
import statistics


def load(spec, ids):
    rows = []
    for f in spec.split(","):
        rows += [r for r in csv.DictReader(open(f)) if ids is None or r["id"] in ids]
    return rows


def pct(n, d):
    return f"{100 * n / d:.1f}%" if d else "–"


def skills_tables(rows):
    n = len(rows)
    loads = collections.Counter(s for r in rows for s in (r.get("skills_loaded") or "").split("+") if s)
    status = collections.Counter(r.get("skills_status") or "(blank)" for r in rows)
    sets = collections.Counter(r.get("skills_loaded") or "(none)" for r in rows)
    unknown = collections.Counter(s for r in rows for s in (r.get("skills_unknown") or "").split("+") if s)
    b = [int(r["skills_bytes"]) for r in rows if (r.get("skills_bytes") or "").strip()]
    out = [f"#### Skills loaded ({n} problem-runs)\n",
           "Status: " + ", ".join(f"{k} {v}" for k, v in sorted(status.items())) + ". "
           f"Bytes loaded: mean {statistics.mean(b):.0f}, min {min(b)}, max {max(b)}." if b else "No bytes recorded.",
           f" Cut by the cap: {sum(1 for r in rows if r.get('skills_truncated') == '1')}. Unknown names: "
           + (", ".join(f"{k} ({v})" for k, v in unknown.most_common()) or "none") + ".\n",
           "| Skill | Loaded in | Share | Pass rate when loaded | Pass rate when not |", "|---|---|---|---|---|"]
    for s, c in loads.most_common():
        w = [r for r in rows if s in (r.get("skills_loaded") or "").split("+")]
        wo = [r for r in rows if s not in (r.get("skills_loaded") or "").split("+")]
        out.append(f"| `{s}` | {c} | {pct(c, n)} | {pct(sum(int(r['pass']) for r in w), len(w))} | "
                   f"{pct(sum(int(r['pass']) for r in wo), len(wo))} |")
    sk = [r for r in rows if "self-check-and-cocotb" in (r.get("skills_loaded") or "").split("+")]
    no = [r for r in rows if r not in sk]
    ran = lambda rs: sum(1 for r in rs if (r.get("selfcheck_runs") or "0") not in ("0", ""))
    out += ["", f"Own testbench run: {ran(sk)} of {len(sk)} rows ({pct(ran(sk), len(sk))}) with "
            f"`self-check-and-cocotb` loaded, {ran(no)} of {len(no)} ({pct(ran(no), len(no))}) without it."]
    out += ["", "| Set of skills loaded | Problem-runs | Pass rate |", "|---|---|---|"]
    for s, c in sets.most_common(10):
        w = [r for r in rows if (r.get("skills_loaded") or "(none)") == s]
        out.append(f"| {s.replace('+', ', ')} | {c} | {pct(sum(int(r['pass']) for r in w), len(w))} |")
    return out


def tokens_table(arms):
    out = ["#### Prompt and completion tokens per problem-run\n",
           "| Arm | Rows | Prompt tokens mean / median | Completion tokens mean | LLM calls mean | Turns mean "
           "| Rows with a self-check run |", "|---|---|---|---|---|---|---|"]
    for name, rows in arms.items():
        pt = [int(r["prompt_tokens"] or 0) for r in rows]
        ct = [int(r["completion_tokens"] or 0) for r in rows]
        lc = [int(r["llm_calls"] or 0) for r in rows]
        tu = [int(r["turns"] or 0) for r in rows]
        sc = sum(1 for r in rows if (r.get("selfcheck_runs") or "0") not in ("0", ""))
        out.append(f"| {name} | {len(rows)} | {statistics.mean(pt):,.0f} / {statistics.median(pt):,.0f} | "
                   f"{statistics.mean(ct):,.0f} | {statistics.mean(lc):.2f} | {statistics.mean(tu):.2f} | "
                   f"{sc} ({pct(sc, len(rows))}) |")
    return out


def category_table(arms):
    cats = sorted({r["cid"] for rows in arms.values() for r in rows})
    out = ["#### Pass rate by category (pooled over runs)\n",
           "| Category | " + " | ".join(arms) + " |", "|---|" + "---|" * len(arms)]
    for c in cats:
        cells = []
        for rows in arms.values():
            w = [r for r in rows if r["cid"] == c]
            cells.append(f"{pct(sum(int(r['pass']) for r in w), len(w))} ({len(w)})")
        out.append(f"| {c} | " + " | ".join(cells) + " |")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", action="append", required=True)
    ap.add_argument("--ids")
    ap.add_argument("--skills-arm", default="K")
    a = ap.parse_args()
    ids = None
    if a.ids:
        ids = {ln.strip() for ln in open(a.ids) if ln.strip() and not ln.startswith("#")}
    arms = {}
    for spec in a.arm:
        name, files = spec.split("=", 1)
        arms[name] = load(files, ids)
    lines = []
    if a.skills_arm in arms:
        lines += skills_tables(arms[a.skills_arm]) + [""]
    lines += tokens_table(arms) + [""] + category_table(arms)
    print("\n".join(lines))


if __name__ == "__main__":
    main()

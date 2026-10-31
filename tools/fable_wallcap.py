"""Brief 21: the Claude Code ladder's Fable 5.1 problems that stopped on the 480 s wall cap, rerun with a longer one.

`ids` lists the problems whose ladder row has `stop_reason=wall_time` (the ids file is committed, so the rerun's
problem list is fixed by the ladder's CSV, not chosen). `analyze` reads the ladder CSV and the rerun CSV, checks the
rerun covers exactly those ids once each, and writes markdown: what happened to each problem, the pass counts, the
wall-time distribution under the new cap, and Fable's 86-problem score with the rerun rows put in place of the
ladder's. It also writes that substituted 86-row CSV, so ablate.py can pair it against the base. The substituted score
is exploratory: one run, a different Claude Code version, and a longer cap than any other ladder arm had.

Usage: python3 tools/fable_wallcap.py ids <ladder.csv> <ids.txt>
       python3 tools/fable_wallcap.py analyze <ladder.csv> <rerun.csv> --ids <ids.txt> [--substituted OUT.csv]
           [--cap 1500] > tables.md
"""
import argparse
import csv
import os
import statistics
import sys

CAP_OLD = 480.0


def read_rows(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def read_ids(path):
    return [ln.strip() for ln in open(path) if ln.strip() and not ln.startswith("#")]


def wall_capped(rows):
    """Ids of the rows the agent's wall cap stopped, sorted."""
    return sorted(r["id"] for r in rows if r.get("stop_reason") == "wall_time")


def write_ids(rows, src, out):
    ids = wall_capped(rows)
    by_id = {r["id"]: r for r in rows}
    passed = sum(by_id[i]["pass"] == "1" for i in ids)
    with open(out, "w") as f:
        f.write("# Claude Code ladder, Fable 5.1: the problems its one run stopped on the 480 s wall cap (brief 21 rerun set)\n")
        f.write(f"# source: {src.replace(os.sep, '/')}\n")
        f.write("# rule: stop_reason == wall_time (tools/fable_wallcap.py ids)\n")
        f.write(f"# count: {len(ids)}: passed under the cap {passed}, failed {len(ids) - passed}\n")
        for i in ids:
            f.write(i + "\n")
    return ids


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def quantiles(xs):
    xs = sorted(xs)
    if not xs:
        return None
    q = statistics.quantiles(xs, n=4) if len(xs) >= 2 else [xs[0]] * 3
    return {"min": xs[0], "q1": q[0], "median": statistics.median(xs), "q3": q[2], "max": xs[-1]}


def analyze(ladder, rerun, ids, cap, substituted_out=None, out=sys.stdout):
    by_id = {r["id"]: r for r in ladder}
    new = {}
    for r in rerun:
        if r["id"] in new:
            raise SystemExit(f"rerun has more than one row for {r['id']}: one run was asked for")
        new[r["id"]] = r
    missing = [i for i in ids if i not in new]
    extra = sorted(set(new) - set(ids))
    if missing or extra:
        raise SystemExit(f"rerun rows do not match the ids file: missing {missing}, extra {extra}")
    bad = [i for i in ids if by_id.get(i, {}).get("stop_reason") != "wall_time"]
    if bad:
        raise SystemExit(f"not wall-capped in the ladder CSV: {bad}")
    w = out.write

    def passed(r):
        return str(r.get("pass", "")).strip() == "1"

    old_pass = sum(passed(by_id[i]) for i in ids)
    new_pass = sum(passed(new[i]) for i in ids)
    cap_hits = [i for i in ids if new[i].get("stop_reason") == "wall_time"]
    invalid = [i for i in ids if new[i].get("stop_reason") in ("error", "llm_error", "rate_limited", "no_task")]
    trans = {"pass→pass": 0, "pass→fail": 0, "fail→pass": 0, "fail→fail": 0}
    for i in ids:
        trans[f"{'pass' if passed(by_id[i]) else 'fail'}→{'pass' if passed(new[i]) else 'fail'}"] += 1
    walls = [_f(new[i].get("wall_time_s")) for i in ids]
    walls = [x for x in walls if x is not None]
    finished = [x for x in walls if x < cap - 0.5]
    q = quantiles(walls)
    qf = quantiles(finished)

    w(f"#### The {len(ids)} wall-capped problems, rerun with a {cap:.0f} s cap\n\n")
    w("| | Ladder (480 s cap) | Rerun |\n|---|---|---|\n")
    w(f"| Passed | {old_pass} / {len(ids)} | {new_pass} / {len(ids)} |\n")
    w(f"| Stopped on the wall cap | {len(ids)} | {len(cap_hits)} |\n")
    w(f"| Invalid rows (error, llm_error, rate limit) | 0 | {len(invalid)} |\n")
    w(f"| Transitions (ladder → rerun) | | pass→pass {trans['pass→pass']}, pass→fail {trans['pass→fail']}, "
      f"fail→pass {trans['fail→pass']}, fail→fail {trans['fail→fail']} |\n\n")
    if q:
        w(f"**Wall time under the {cap:.0f} s cap**, all {len(walls)} rows: min {q['min']:.0f} s, Q1 {q['q1']:.0f} s, "
          f"median {q['median']:.0f} s, Q3 {q['q3']:.0f} s, max {q['max']:.0f} s.")
        if qf:
            w(f" The {len(finished)} that finished before the cap: median {qf['median']:.0f} s, Q3 {qf['q3']:.0f} s, "
              f"max {qf['max']:.0f} s.")
        w("\n\n")
        bins = [(0, 480, "under 480 s (the old cap)"), (480, 900, "480–900 s"), (900, 1200, "900–1,200 s"),
                (1200, cap - 0.5, f"1,200 s to under the cap"), (cap - 0.5, 1e9, f"stopped on the {cap:.0f} s cap")]
        w("| Wall time | Problems | Passed |\n|---|---|---|\n")
        for lo, hi, name in bins:
            sel = [i for i in ids if _f(new[i].get("wall_time_s")) is not None and lo <= _f(new[i]["wall_time_s"]) < hi]
            w(f"| {name} | {len(sel)} | {sum(passed(new[i]) for i in sel)} |\n")
        w("\n")

    w("#### Each problem\n\n")
    w("| Problem | Difficulty | Ladder pass | Rerun pass | Rerun wall s | Rerun stop | Turns | Tool calls |\n"
      "|---|---|---|---|---|---|---|---|\n")
    for i in ids:
        o, n = by_id[i], new[i]
        w(f"| `{i}` | {o.get('difficulty', '')} | {'yes' if passed(o) else 'no'} | {'yes' if passed(n) else 'no'} | "
          f"{n.get('wall_time_s', '')} | {n.get('stop_reason', '')} | {n.get('turns', '')} | {n.get('tool_calls', '')} |\n")
    w("\n")

    total = len(ladder)
    old_total = sum(passed(r) for r in ladder)
    new_total = old_total - old_pass + new_pass
    w(f"#### Fable's {total}-problem score with the {len(ids)} rerun rows substituted (exploratory)\n\n")
    w(f"Ladder, 480 s cap on every problem: **{old_total}/{total} = {100 * old_total / total:.1f}%**. With the rerun rows in "
      f"place of the {len(ids)} wall-capped ones: **{new_total}/{total} = {100 * new_total / total:.1f}%** "
      f"({new_total - old_total:+d} problems). The other {total - len(ids)} rows are the ladder's own, under its 480 s cap.\n")

    if substituted_out:
        fields = list(ladder[0].keys())
        with open(substituted_out, "w", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            wr.writeheader()
            for r in ladder:
                row = new[r["id"]] if r["id"] in new else r
                wr.writerow({k: row.get(k, "") for k in fields})
    return {"old_pass": old_pass, "new_pass": new_pass, "cap_hits": len(cap_hits), "invalid": len(invalid),
            "old_total": old_total, "new_total": new_total, "total": total, "transitions": trans}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("ids")
    a.add_argument("ladder")
    a.add_argument("out")
    b = sub.add_parser("analyze")
    b.add_argument("ladder")
    b.add_argument("rerun")
    b.add_argument("--ids", required=True)
    b.add_argument("--substituted", default=None)
    b.add_argument("--cap", type=float, default=1500.0)
    args = ap.parse_args(argv)
    if args.cmd == "ids":
        ids = write_ids(read_rows(args.ladder), args.ladder, args.out)
        print(f"{len(ids)} ids -> {args.out}")
    else:
        analyze(read_rows(args.ladder), read_rows(args.rerun), read_ids(args.ids), args.cap, args.substituted)


if __name__ == "__main__":
    main()

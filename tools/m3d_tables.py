"""M3d's secondary tables from collect.py CSVs: effort per problem (turns, LLM calls, self-check runs), the verify
step's refusals and let-throughs, and, for arm S, how the blind spec cases on the final design agree with the hidden
tests. Descriptive only: no test is run here (the pre-registered comparisons are ablate.py's).

Usage: python3 tools/m3d_tables.py --arm A=a1.csv,a2.csv --arm V=... --arm S=... [--ids tools/m3b_eval_ids.txt]
"""
import argparse
import collections
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ablate  # noqa: E402


def _n(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def effort(arms):
    out = ["#### Effort per problem-run\n",
           "| Arm | Rows | Turns median / mean | 1-turn rows | LLM calls median / mean | Self-check runs median / mean "
           "| Rows with 0 self-check runs |", "|---|---|---|---|---|---|---|"]
    for name, rows in arms.items():
        def mm(k):
            v = [x for x in (_n(r.get(k)) for r in rows) if x is not None]
            return f"{statistics.median(v):g} / {statistics.mean(v):.2f}" if v else "n/a"
        one = sum(1 for r in rows if _n(r.get("turns")) == 1)
        zero = sum(1 for r in rows if _n(r.get("selfcheck_runs")) == 0)
        out.append(f"| {name} | {len(rows)} | {mm('turns')} | {one} ({100 * one / len(rows):.0f}%) | "
                   f"{mm('llm_calls')} | {mm('selfcheck_runs')} | {zero} ({100 * zero / len(rows):.0f}%) |")
    out.append("\nSelf-check runs are counted from the trace (`taxonomy.py`): the agent's own testbench runs, "
               "verify's reruns included, the spec testbench not.")
    return "\n".join(out) + "\n"


def stops(arms):
    keys = sorted({r.get("stop_reason", "") for rows in arms.values() for r in rows})
    out = ["#### Stop reasons\n", "| Arm | " + " | ".join(keys) + " |", "|---|" + "---|" * len(keys)]
    for name, rows in arms.items():
        c = collections.Counter(r.get("stop_reason", "") for r in rows)
        out.append(f"| {name} | " + " | ".join(str(c[k]) for k in keys) + " |")
    return "\n".join(out) + "\n"


def verify(arms):
    out = ["#### The verify step\n",
           "| Arm | Rows | verify runs | Refusals | Rows with a refusal | Let-throughs | Reruns by verify | "
           "Submits verified | Pass rate, verified submits | Pass rate, let-through submits |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for name, rows in arms.items():
        vr = [r for r in rows if str(r.get("verify_submit")) == "1"]
        if not vr:
            continue
        s = lambda k: int(sum(_n(r.get(k)) or 0 for r in vr))  # noqa: E731
        ref_rows = sum(1 for r in vr if (_n(r.get("verify_refusals")) or 0) > 0)
        ver = [r for r in vr if str(r.get("verified_at_submit")) == "1"]
        lt = [r for r in vr if str(r.get("verified_at_submit")) == "0"]
        rate = lambda rs: f"{sum(r['pass'] == '1' for r in rs)}/{len(rs)}" if rs else "n/a"  # noqa: E731
        out.append(f"| {name} | {len(vr)} | {s('verify_runs')} | {s('verify_refusals')} | {ref_rows} | "
                   f"{s('verify_let_through')} | {s('verify_reruns')} | {len(ver)} | {rate(ver)} | {rate(lt)} |")
    return "\n".join(out) + "\n"


def spec(arms):
    out = []
    for name, rows in arms.items():
        sr = [r for r in rows if str(r.get("spec_vectors")) == "1"]
        if not sr:
            continue
        st = collections.Counter(r.get("spec_status") or "none" for r in sr)
        fs = collections.Counter(r.get("spec_final_status") or "none" for r in sr)
        cases = [_n(r.get("spec_cases")) for r in sr if r.get("spec_status") == "generated"]
        out += [f"#### Spec cases, arm {name}\n",
                f"Spec call outcome over {len(sr)} problem-runs: " + ", ".join(f"{k} {v}" for k, v in st.most_common())
                + f". Cases per generated set: median {statistics.median(cases):g}." if cases else "",
                "\nFinal-design spec result: " + ", ".join(f"{k} {v}" for k, v in fs.most_common()) + ".\n",
                "| All spec cases pass on the final design | Hidden tests pass | Hidden tests fail |", "|---|---|---|"]
        for label, keep in (("yes", lambda r: r.get("spec_final_status") == "pass"),
                            ("no (fail or timeout)", lambda r: r.get("spec_final_status") in ("fail", "timeout")),
                            ("not applied (no cases, unbuildable, error, or not run)",
                             lambda r: r.get("spec_final_status") not in ("pass", "fail", "timeout"))):
            g = [r for r in sr if keep(r)]
            out.append(f"| {label} | {sum(r['pass'] == '1' for r in g)} | {sum(r['pass'] != '1' for r in g)} |")
        out.append("")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", action="append", required=True)
    ap.add_argument("--ids")
    a = ap.parse_args(argv)
    arms = ablate.arms_from(a.arm, [])
    if a.ids:
        keep = {ln.strip() for ln in open(a.ids) if ln.strip() and not ln.startswith("#")}
        arms = {n: [r for r in rows if r["id"] in keep] for n, rows in arms.items()}
    print(effort(arms))
    print(stops(arms))
    print(verify(arms))
    print(spec(arms))


if __name__ == "__main__":
    main()

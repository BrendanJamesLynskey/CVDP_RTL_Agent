"""How much of the hidden testbench's interface does M3c's interface check know from what the agent is given? An
offline check on the dataset, for the report: for each problem, the given interface (cvdp_agent/interface.py, from
the prompt and context only) against the names the hidden testbench reads (tools/reachable.py, from the hidden
files). The agent itself never reads the hidden files; this tool does, offline, as reachable.py does. No LLM.

Per problem: the hidden top module(s), whether the given interface has a module of that name and where it came from
(rtl, header, doc, testbench, prompt), and how many of the `dut.<name>` handles the hidden testbench reads are
ports or parameters of that given module.

Usage: python3 tools/interface_given.py <agentic.jsonl> [--ids tools/m3b_eval_ids.txt] [--md-out FILE]
"""
import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

import reachable  # noqa: E402
from cvdp_agent.interface import given_interface  # noqa: E402


def rows(records):
    out = []
    for r in records:
        given, _ = given_interface(r)
        h = reachable.handles(r)
        tops = sorted(n for n, w in h.items() if "top module" in w)
        top = next((t for t in tops if t in given), tops[0] if tops else "")
        dut = sorted(n for n, w in h.items() if any(x.count(".") == 1 for x in w))
        g = given.get(top)
        known = set(g["ports"]) | set(g["params"]) if g else set()
        out.append({"id": r["id"], "cid": (r.get("categories") or [""])[0], "top": top, "given": bool(g),
                    "source": g["source"] if g else "", "dut": len(dut), "covered": sum(n in known for n in dut)})
    return out


def report(rs):
    by_src = collections.Counter(r["source"] or "not given" for r in rs)
    n_dut = sum(r["dut"] for r in rs)
    n_cov = sum(r["covered"] for r in rs)
    lines = ["# M3c: the given interface against the hidden testbench's names\n",
             f"Made by `tools/interface_given.py` over {len(rs)} problems. The interface check knows the hidden top "
             f"module's name for **{sum(r['given'] for r in rs)} of {len(rs)}**; of the {n_dut} top-level `dut.` "
             f"handles the hidden testbenches read, {n_cov} ({100 * n_cov / max(1, n_dut):.0f}%) are ports or "
             "parameters of that given module (the rest are internal signals, new ports a modification adds, or "
             "names the agent is not given).\n",
             "| Source of the top module's interface | Problems |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in sorted(by_src.items(), key=lambda kv: -kv[1])]
    lines += ["", "| Problem | cid | Hidden top | Given (source) | `dut.` handles given / read |", "|---|---|---|---|---|"]
    for r in rs:
        lines.append(f"| `{r['id'].replace('cvdp_agentic_', '')}` | {r['cid']} | `{r['top']}` | "
                     f"{'yes (' + r['source'] + ')' if r['given'] else 'no'} | {r['covered']} / {r['dut']} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset")
    ap.add_argument("--ids")
    ap.add_argument("--md-out")
    a = ap.parse_args(argv)
    records = [json.loads(ln) for ln in open(a.dataset) if ln.strip()]
    if a.ids:
        keep = {ln.strip() for ln in open(a.ids) if ln.strip() and not ln.startswith("#")}
        records = [r for r in records if r["id"] in keep]
    md = report(rows(records))
    if a.md_out:
        with open(a.md_out, "w") as f:
            f.write(md)
    print(md)


if __name__ == "__main__":
    main()

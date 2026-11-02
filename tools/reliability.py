"""Reliability of a model inside the LangGraph agent, from the traces a sweep uploads (F1B). Pass rate says how often
the agent was right; this says how often the model failed as a component: replies the agent could not use, cut-off
replies, provider errors, loops and stops on a cap. Model-free: every count comes from trace.jsonl and summary.json.

Per problem-run (one agent_out/ directory), counted from the trace:
  unparsable    an edit reply with nothing the agent could read in it (no file, diff, testbench or <checks> block, no
                edit error, and not empty), or a reflect reply whose decision could not be read (`decision: unparseable`)
  invalid_edit  a file or testbench write the agent refused (bad path, a diff that does not apply): tool events
                `file_write` / `tb_write` with a non-zero exit code
  length        an LLM call that ended with finish_reason `length` (cut off at max_tokens)
  empty         an empty reply (the summary's `empty_replies`)
  provider_err  an LLM call that raised (provider error, timeout, abandoned at the deadline): llm events with `error`
                that are not a reasoning-field rejection; plus the run's stop on `llm_error`
  loop          an edit turn (2nd or later) whose reply text is the same as the previous edit turn's, or that changed
                no file when the previous edit turn changed none either
  cap_stop      the run stopped on a cap: stop_reason max_turns, wall_time, budget, cost_unreported or
                run_budget_exhausted
A problem-run is a **reliability failure** if any of these is non-zero. Per arm the table gives each measure as
problem-runs affected and as events, and the failures per 86 problems (mean over the arm's runs).

Usage: python3 tools/reliability.py [--ids FILE] [--csv OUT] NAME=artifact_dir[,artifact_dir...] [...]
  An artifact dir is what `gh run download <run id>` writes (it holds work/seed*/...). Each (dir, seed) is one run.
       python3 tools/reliability.py --from-csv rows.csv [--ids FILE]
  remakes the tables from the per-problem-run rows a --csv run wrote (so they can be checked without the traces).
"""
import argparse
import collections
import csv
import glob
import json
import os
import re
import sys

CAPS = {"max_turns", "wall_time", "budget", "cost_unreported", "run_budget_exhausted"}
MEASURES = ("unparsable", "invalid_edit", "length", "empty", "provider_err", "loop", "cap_stop")


def read_jsonl(path):
    out = []
    with open(path, errors="replace") as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def problem_run(agent_out):
    """{measure: event count} for one agent_out/ directory, plus its stop reason."""
    trace = os.path.join(agent_out, "trace.jsonl")
    events = read_jsonl(trace) if os.path.exists(trace) else []
    try:
        summary = json.load(open(os.path.join(agent_out, "summary.json")))
    except (OSError, ValueError):
        summary = {}
    c = dict.fromkeys(MEASURES, 0)
    prev_edit = None
    for e in events:
        kind = e.get("kind")
        if kind == "tool" and e.get("check") in ("file_write", "tb_write") and e.get("exit_code") not in (0, None):
            c["invalid_edit"] += 1
        if kind != "llm":
            continue
        if e.get("error") and not e.get("reasoning_rejected"):
            c["provider_err"] += 1
            continue
        if e.get("finish_reason") == "length":
            c["length"] += 1
        d = e.get("decision")
        if e.get("node") == "reflect" and d == "unparseable":
            c["unparsable"] += 1
        if e.get("node") == "edit" and isinstance(d, dict):
            changed = d.get("changed") or []
            if (not changed and not (d.get("testbench") or []) and not d.get("errors") and not (d.get("checks") or [])
                    and not e.get("empty")):
                c["unparsable"] += 1
            if prev_edit is not None:
                same_text = (e.get("completion") or "") == (prev_edit.get("completion") or "") and e.get("completion")
                both_idle = not changed and not ((prev_edit.get("decision") or {}).get("changed") or [])
                if same_text or both_idle:
                    c["loop"] += 1
            prev_edit = e
    c["empty"] = int(summary.get("empty_replies") or 0)
    stop = summary.get("stop_reason", "")
    if stop == "llm_error" and not c["provider_err"]:
        c["provider_err"] = 1
    if stop in CAPS:
        c["cap_stop"] = 1
    return c, stop


_DIR = re.compile(r"/seed(\d+)/([^/]+)/harness/(\d+)/rundir/agent_out$")


def runs(artifact_dir):
    """{(artifact_dir, seed): {problem id: counts}}"""
    out = collections.defaultdict(dict)
    for d in glob.glob(os.path.join(artifact_dir, "**", "agent_out"), recursive=True):
        m = _DIR.search(d)
        if not m:
            continue
        seed, name, n = m.groups()
        out[(os.path.basename(os.path.normpath(artifact_dir)), seed)][f"{name}_{int(n):04d}"] = problem_run(d)
    return out


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids")
    ap.add_argument("--csv")
    ap.add_argument("--from-csv")
    ap.add_argument("arms", nargs="*")
    a = ap.parse_args(argv)
    ids = None
    if a.ids:
        ids = {ln.strip() for ln in open(a.ids) if ln.strip() and not ln.startswith("#")}
    specs = []  # (arm name, {(run, seed): {id: (counts, stop)}})
    if a.from_csv:
        by_arm = collections.OrderedDict()
        for r in csv.DictReader(open(a.from_csv)):
            run, seed = r["run"].rsplit("#seed", 1)
            c = {k: int(r[k]) for k in MEASURES}
            by_arm.setdefault(r["arm"], {}).setdefault((run, seed), {})[r["id"]] = (c, r["stop_reason"])
        specs = list(by_arm.items())
    for spec in a.arms:
        name, dirs = spec.split("=", 1)
        arm_runs = {}
        for d in dirs.split(","):
            arm_runs.update(runs(d))
        specs.append((name, arm_runs))
    rows, table = [], []
    for name, arm_runs in specs:
        n_runs = len(arm_runs)
        affected = collections.Counter()
        events = collections.Counter()
        fail_runs, problem_runs, stops = 0, 0, collections.Counter()
        for (d, seed), probs in sorted(arm_runs.items()):
            for pid, (c, stop) in sorted(probs.items()):
                if ids is not None and pid not in ids:
                    continue
                problem_runs += 1
                stops[stop] += 1
                failed = any(c[k] for k in MEASURES)
                fail_runs += failed
                for k in MEASURES:
                    affected[k] += bool(c[k])
                    events[k] += c[k]
                rows.append({"arm": name, "run": f"{d}#seed{seed}", "id": pid, "stop_reason": stop,
                             **c, "reliability_failure": int(failed)})
        per86 = (fail_runs / problem_runs * 86) if problem_runs else 0.0
        table.append((name, n_runs, problem_runs, affected, events, fail_runs, per86, stops))
    print("| Arm | Runs | Problem-runs | " + " | ".join(MEASURES) + " | Reliability failures | Per 86 |")
    print("|---|---|---|" + "---|" * len(MEASURES) + "---|---|")
    for name, n_runs, pr, aff, ev, fr, per86, _ in table:
        cells = " | ".join(f"{aff[k]} ({ev[k]})" for k in MEASURES)
        print(f"| {name} | {n_runs} | {pr} | {cells} | {fr} | {per86:.1f} |")
    print("\nEach measure: problem-runs affected (events). Per 86 = failures / problem-runs x 86.\n")
    print("| Arm | Stop reasons |")
    print("|---|---|")
    for name, *_, stops in table:
        print(f"| {name} | " + ", ".join(f"{k or '(none)'} {v}" for k, v in stops.most_common()) + " |")
    if a.csv:
        with open(a.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["arm", "run", "id", "stop_reason", *MEASURES, "reliability_failure"])
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main(sys.argv[1:])

"""Failure taxonomy: one primary label per failed (problem, run), plus secondary flags, from the harness's per-test
logs, the agent's trace.jsonl and its summary.json. Deterministic rules only: no LLM reads or labels anything.

Primary labels, in the order the rules are tried (the first that holds is the primary; every other one that
holds becomes a flag):

  llm_error                      the problem stopped on a provider error, a missed call deadline or unreported cost
  agent_error                    the agent crashed (stop_reason "error"; finalize still ran)
  killed                         no final summary: the harness killed the agent (or it never ran)
  no_edit                        the agent finished without changing anything under rtl/
  stopped_by_cap                 max_turns, budget or wall_time stopped it
  gave_up                        the agent chose give_up
  sim_incomplete                 the hidden tests' log ends inside a simulation with no pytest summary (hang/kill)
  compile_fail_own               the hidden tests' build failed, and so did the agent's own last compile
  compile_fail_hidden            the hidden tests' build failed although the agent's own compile passed: an
                                 interface or port mismatch with the hidden testbench
  tests_failed_selfcheck_passed  hidden tests failed; the agent's own last testbench passed (self-check too weak)
  tests_failed_selfcheck_failed  hidden tests failed; the agent's own last testbench failed and it submitted anyway
  tests_failed_no_selfcheck      hidden tests failed; the agent never ran a testbench of its own
  harness_error                  the log shows no test result at all (a harness, bundle or Docker fault)
  needs_artifacts                the inputs lack the evidence (a CSV from before M3 has no trace or log columns)

Adjusted from M2: `gave_up` (Haiku gave up 1–4 times per sweep), `agent_error` and `killed` are added, and
`tests_failed_selfcheck_failed` splits the case the brief's two self-check labels leave out.

Secondary flags besides the other labels that hold: partial_pass (some hidden tests passed), single_turn,
self_check_off, lint_off, empty_replies, best_edit_restored.

Inputs: work dirs (`--work NAME=dir`, a sweep's work dir with seed*/ or a single harness prefix with
raw_result.json), or collect.py CSVs (positional, or `--arm NAME=a.csv,b.csv`). CSVs written by collect.py since
M3 carry the evidence columns; older CSVs only allow the labels that follow from stop_reason.

Usage: python3 tools/taxonomy.py [--work NAME=dir ...] [--arm NAME=a.csv ...] [csv ...]
           [--excerpts] [--unsolved a.csv,b.csv,...] [--hand labels.csv] [--sheet out.csv --sample 15]
"""
import argparse
import collections
import csv
import glob
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

import log_check  # noqa: E402

LABELS = ["llm_error", "agent_error", "killed", "no_edit", "stopped_by_cap", "gave_up", "sim_incomplete",
          "compile_fail_own", "compile_fail_hidden", "tests_failed_selfcheck_passed",
          "tests_failed_selfcheck_failed", "tests_failed_no_selfcheck", "harness_error"]
EVIDENCE = ["rtl_changed", "own_compile_last", "selfcheck_runs", "selfcheck_last", "log_class"]
_TB_BAD = re.compile(r"(?i)\b(fail|failed|failure|error|fatal)\b")
_LOG_ORDER = ["sim_incomplete", "build_failed", "tests_failed", "harness_error", "missing", "passed"]


def _redact(text):
    try:
        from cvdp_agent.trace import redact
        return redact(text)
    except ImportError:  # the patterns, if the agent package is not on the path
        return re.sub(r"sk-or-[A-Za-z0-9_\-]*|Bearer\s*\S*", "[REDACTED]", text)


# ---------- evidence from a work dir ----------

def test_logs(work, pid, entry):
    """The per-test log files of the problem's failing tests."""
    repo = "_".join(pid.split("_")[:-1])
    out = []
    for t in entry.get("tests", []):
        if t.get("result") == 0:
            continue
        name = os.path.basename(t.get("log") or "")
        p = os.path.join(work, repo, "reports", name)
        if name and os.path.exists(p):
            out.append(p)
    return out


def log_class(paths):
    if not paths:
        return "missing"
    kinds = {log_check.classify(open(p, errors="replace").read()) for p in paths}
    return next(k for k in _LOG_ORDER if k in kinds or k == "passed")


def read_trace(path):
    events = []
    if os.path.exists(path):
        for ln in open(path, errors="replace"):
            try:
                events.append(json.loads(ln))
            except ValueError:
                continue
    return events


def selfcheck_result(e):
    """pass / fail for one testbench tool event, as the agent judged it (exit code and failure words)."""
    if e.get("check") == "testbench_build":
        return "fail" if e.get("exit_code") not in (0, None) else None
    if e.get("exit_code") is None:
        return None
    if e["exit_code"] != 0:
        return "fail"
    if e.get("check") == "testbench_run" and _TB_BAD.search(e.get("output") or ""):
        return "fail"
    return "pass"


def trace_evidence(events, summary):
    compiles = [e for e in events if e.get("kind") == "tool" and e.get("check") == "compile"
                and e.get("exit_code") is not None]
    own = "pass" if compiles and compiles[-1]["exit_code"] == 0 else ("fail" if compiles else "none")
    if summary.get("final_compiled") is True:
        own = "pass"
    elif summary.get("final_compiled") is False:
        own = "fail"
    tb = [r for r in (selfcheck_result(e) for e in events
                      if e.get("kind") == "tool" and e.get("check") in ("testbench_build", "testbench_run",
                                                                         "testbench_cocotb")) if r]
    files = summary.get("files_changed")
    return {"rtl_changed": "" if files is None else int(any(f.startswith("rtl/") for f in files)),
            "own_compile_last": own, "selfcheck_runs": len(tb), "selfcheck_last": tb[-1] if tb else "none"}


def evidence_from_dir(work, pid, entry, problem_dir):
    """The evidence columns for one problem, plus the paths used (for excerpts)."""
    out_dir = os.path.join(problem_dir, "rundir", "agent_out")
    s_path = os.path.join(out_dir, "summary.json")
    summary = json.load(open(s_path)) if os.path.exists(s_path) else {}
    events = read_trace(os.path.join(out_dir, "trace.jsonl"))
    logs = test_logs(work, pid, entry)
    ev = trace_evidence(events, summary) if summary or events else {k: "" for k in EVIDENCE[:-1]}
    ev["log_class"] = log_class(logs) if any(t.get("result") != 0 for t in entry.get("tests", [])) else "passed"
    return ev, {"logs": logs, "events": events}


# ---------- the rules ----------

def _i(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def label(r):
    """(primary, flags) for a failed row: a collect.py row (dict of strings) with or without evidence columns."""
    stop = r.get("stop_reason") or ""
    has = r.get("log_class") not in (None, "")
    log = r.get("log_class") or ""
    own = r.get("own_compile_last") or ""
    tb_last = r.get("selfcheck_last") or ""
    tb_runs = _i(r.get("selfcheck_runs"))
    rtl = _i(r.get("rtl_changed"))
    holds = {
        "llm_error": stop in ("llm_error", "cost_unreported"),
        "agent_error": stop == "error",
        "killed": stop in ("killed", "no_summary", "not_run"),
        "no_edit": rtl == 0,
        "stopped_by_cap": stop in ("max_turns", "budget", "wall_time"),
        "gave_up": stop == "give_up",
        "sim_incomplete": has and log == "sim_incomplete",
        "compile_fail_own": has and log == "build_failed" and own in ("fail", "none"),
        "compile_fail_hidden": has and log == "build_failed" and own == "pass",
        "tests_failed_selfcheck_passed": has and log == "tests_failed" and tb_last == "pass",
        "tests_failed_selfcheck_failed": has and log == "tests_failed" and tb_last == "fail",
        "tests_failed_no_selfcheck": has and log == "tests_failed" and tb_runs == 0,
        "harness_error": has and log == "harness_error",
    }
    true = [k for k in LABELS if holds[k]]
    primary = true[0] if true else ("needs_artifacts" if not has else "unclassified")
    flags = true[1:]
    tests, passed = _i(r.get("tests")), _i(r.get("tests_passed"))
    if tests and passed and 0 < passed < tests:
        flags.append("partial_pass")
    if _i(r.get("turns")) == 1:
        flags.append("single_turn")
    if str(r.get("self_check")) == "0":
        flags.append("self_check_off")
    if str(r.get("lint")) == "0":
        flags.append("lint_off")
    if (_i(r.get("empty_replies")) or 0) > 0:
        flags.append("empty_replies")
    if str(r.get("kept", "")).startswith("best_compiled"):
        flags.append("best_edit_restored")
    return primary, flags


# ---------- inputs ----------

def rows_from_work(name, work):
    """collect.py rows (with evidence) for every seed dir under `work`, each with its paths for excerpts."""
    import collect

    dirs = sorted((d for d in glob.glob(os.path.join(work, "seed*")) if re.search(r"/seed\d+$", d)),
                  key=lambda d: int(d.rsplit("seed", 1)[1])) or [work]
    out = []
    for d in dirs:
        seed = d.rsplit("seed", 1)[1] if re.search(r"/seed\d+$", d) else ""
        raw = json.load(open(os.path.join(d, "raw_result.json")))
        for r in collect.rows(d, seed=seed):
            r = {k: "" if v is None else str(v) for k, v in r.items()}
            entry = raw.get(r["id"], {})
            _, paths = evidence_from_dir(d, r["id"], entry, collect.problem_dir(d, r["id"], entry))
            r["_paths"], r["_arm"], r["_run"] = paths, name, f"{name}#seed{seed or 1}"
            out.append(r)
    return out


def rows_from_csvs(specs, paths):
    import ablate

    out = []
    for name, rows in ablate.arms_from(specs, paths).items():
        for r in rows:
            r["_arm"] = name
            out.append(r)
    return out


# ---------- report ----------

def excerpt(r, n=10):
    """At most n lines: the failing log's telling lines, then the trace's last checks and the stop. Redacted."""
    lines = []
    for p in (r.get("_paths") or {}).get("logs", [])[:1]:
        text = open(p, errors="replace").read()
        all_ = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
        hits = [ln for ln in all_ if re.search(r"(?i)assert|fail|error|unable|fatal", ln)][:4]
        tail = [ln for ln in all_[-2:] if ln not in hits]  # where the log ends (a hang ends mid-simulation)
        for ln in (hits + tail)[:5]:
            lines.append(f"log: {ln[:160]}")
    for e in [e for e in (r.get("_paths") or {}).get("events", [])
              if e.get("kind") in ("tool", "llm", "summary") and e.get("check") not in ("read_task",)][-6:]:
        if e.get("kind") == "tool":
            lines.append(f"trace: {e.get('check')} exit={e.get('exit_code')} {(e.get('command') or '')[:80]}")
        elif e.get("kind") == "llm":
            lines.append(f"trace: llm {e.get('node')} decision={json.dumps(e.get('decision'))[:80]}"
                         + (f" error={str(e.get('error'))[:60]}" if e.get("error") else ""))
        else:
            lines.append(f"trace: summary stop={e.get('stop_reason')} files={e.get('files_changed')}")
    return _redact("\n".join(lines[-n:]))


def count_table(fails, key, title):
    get = lambda r: r.get(key, "")  # noqa: E731
    cols = sorted({get(r) for r in fails})
    labels = [lb for lb in LABELS + ["needs_artifacts", "unclassified"] if any(r["_label"] == lb for r in fails)]
    out = [f"#### {title}\n", "| Label | " + " | ".join(cols) + " | All |", "|---|" + "---|" * (len(cols) + 1)]
    for lb in labels:
        cells = [sum(1 for r in fails if r["_label"] == lb and get(r) == c) for c in cols]
        out.append(f"| {lb} | " + " | ".join(str(c) for c in cells) + f" | {sum(cells)} |")
    tot = [sum(1 for r in fails if get(r) == c) for c in cols]
    out.append("| **All failures** | " + " | ".join(str(c) for c in tot) + f" | {sum(tot)} |")
    return "\n".join(out) + "\n"


def unsolved(rows, unsolved_csvs):
    """Problems no run in `unsolved_csvs` solved, with their labels across the runs given."""
    import ablate

    ref = [r for p in unsolved_csvs for r in ablate.load(p)]
    passed = {r["id"] for r in ref if r["pass"] == "1"}
    ids = sorted({r["id"] for r in ref} - passed)
    by = collections.defaultdict(list)
    for r in rows:
        if r["id"] in ids and r["pass"] != "1":
            by[r["id"]].append(f"{r['_label']}")
    out = [f"#### The {len(ids)} problems no reference run solved ({len(ref)} rows from {len(unsolved_csvs)} CSVs)\n",
           "| Problem | cid | Labels across the runs here |", "|---|---|---|"]
    cid = {r["id"]: r.get("cid", "") for r in ref}
    for i in ids:
        c = collections.Counter(by.get(i, []))
        out.append(f"| `{i.replace('cvdp_agentic_', '')}` | {cid[i]} | "
                   + (", ".join(f"{k} ×{v}" for k, v in c.most_common()) or "(no failed rows here)") + " |")
    return "\n".join(out) + "\n"


def agreement(rows, hand_csv):
    hand = {(h["id"], h["run"]): h["label"] for h in csv.DictReader(open(hand_csv))}
    got = {(r["id"], r["_run"]): r.get("_label", "passed") for r in rows}
    pairs = [(k, v, got.get(k)) for k, v in hand.items()]
    agree = sum(1 for _, h, g in pairs if h == g)
    out = [f"#### Hand labels against the rules: {agree}/{len(pairs)} agree "
           f"({100 * agree / len(pairs):.0f}%)\n" if pairs else "#### Hand labels: none\n",
           "| Problem | Run | Hand | Rules |", "|---|---|---|---|"]
    for (i, run), h, g in sorted(pairs):
        out.append(f"| `{i}` | {run} | {h} | {g}{'' if h == g else ' ✗'} |")
    return "\n".join(out) + "\n"


def write_sheet(rows, path, n, seed=0):
    fails = [r for r in rows if r["pass"] != "1"]
    pick = random.Random(seed).sample(fails, min(n, len(fails)))
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "run", "rule_label", "label", "note"])
        for r in sorted(pick, key=lambda r: (r["id"], r["_run"])):
            w.writerow([r["id"], r["_run"], r["_label"], "", ""])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="*")
    ap.add_argument("--arm", action="append", help="NAME=a.csv[,b.csv]")
    ap.add_argument("--work", action="append", help="NAME=work_dir")
    ap.add_argument("--excerpts", action="store_true", help="3 evidence excerpts per label (needs --work)")
    ap.add_argument("--unsolved", help="comma-separated CSVs: list the problems none of them solved")
    ap.add_argument("--hand", help="CSV of hand labels (id, run, label): agreement with the rules")
    ap.add_argument("--sheet", help="write a hand-labelling sheet of --sample failures to this CSV")
    ap.add_argument("--sample", type=int, default=15)
    a = ap.parse_args(argv)
    rows = rows_from_csvs(a.arm, a.csv)
    for spec in a.work or []:
        name, _, d = spec.partition("=")
        rows += rows_from_work(name, d)
    for r in rows:
        if r["pass"] != "1":
            r["_label"], r["_flags"] = label(r)
    fails = [r for r in rows if r["pass"] != "1"]
    print(f"{len(fails)} failed (problem, run) rows of {len(rows)}.\n")
    print(count_table(fails, "_arm", "Primary label by arm"))
    print(count_table(fails, "cid", "Primary label by cid"))
    flags = collections.Counter(f for r in fails for f in r["_flags"])
    print("Secondary flags: " + (", ".join(f"{k} {v}" for k, v in flags.most_common()) or "none") + "\n")
    if a.unsolved:
        print(unsolved(rows, a.unsolved.split(",")))
    if a.excerpts:
        print("#### Evidence, up to 3 per label\n")
        for lb in LABELS:
            ex = [r for r in fails if r["_label"] == lb and r.get("_paths")][:3]
            for r in ex:
                print(f"**{lb}**: `{r['id']}` ({r['_run']})\n```\n{excerpt(r) or '(no log or trace)'}\n```\n")
    if a.hand:
        print(agreement(rows, a.hand))
    if a.sheet:
        write_sheet(rows, a.sheet, a.sample)


if __name__ == "__main__":
    main()

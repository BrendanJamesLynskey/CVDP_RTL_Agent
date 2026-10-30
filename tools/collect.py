"""Join the harness's raw_result.json with each problem's agent summary.json: one CSV row per problem.

Pass/fail comes only from raw_result.json (a problem passes when it has tests and every one has result 0, the
harness's own rule). Cost and tokens come only from summary.json, which records provider-reported usage.

Rows are grouped by the requested model (`--model`, what the sweep asked for), so a problem whose agent left no
summary.json still counts in that model's denominator.

`seed` is the sweep's repeat number (`--seed`, else the agent's summary); each seed is its own work dir.

Usage: python3 tools/collect.py <work_dir> [--dataset problems.jsonl] [--runner ubuntu-24.04] [--model ID] [--seed N]
       > results.csv
"""
import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
FIELDS = ["label", "id", "seed", "cid", "difficulty", "pass", "tests", "tests_passed", "amba", "requested_model", "model",
          "provider", "cost_usd",
          "cost_unreported_calls", "prompt_tokens", "completion_tokens", "llm_calls", "tool_calls", "turns",
          "wall_time_s", "harness_agent_s", "stop_reason", "kept", "agent_status", "self_check", "lint",
          "max_turns", "budget_usd", "reasoning", "reasoning_used", "reasoning_tokens", "empty_replies",
          "empty_retries", "reflect_parse_retries", "providers", "runner", "summary_found",
          # M3: the failure taxonomy's evidence (tools/taxonomy.py) and its label for a failed problem
          "rtl_changed", "own_compile_last", "selfcheck_runs", "selfcheck_last", "log_class", "failure_label",
          "failure_flags",
          # M3b: the lessons snapshot's hash, blank with no memory
          "memory",
          # M3c (after memory, so older CSVs still parse): the switches, the mutation gate and the interface check,
          # blank when the switch was off
          "mutation_gate", "interface_check", "gate_runs", "gate_outcomes", "gate_failures", "gate_overridden",
          "mutants_generated", "mutants_compiled", "mutants_killed", "mutants_unfinished", "gate_wall_s",
          "interface_runs", "interface_mismatch_runs", "interface_kinds", "interface_fallbacks",
          "interface_blocks", "interface_unresolved",
          # M3d (after M3c's): verify before submit and the blind spec cases, blank when the switch was off
          "verify_submit", "spec_vectors", "verify_runs", "verify_refusals", "verify_let_through", "verify_outcomes",
          "verify_reruns", "testbench_runs", "verified_at_submit", "spec_status", "spec_failed_open", "spec_cases",
          "spec_steps", "spec_runs", "spec_unbuildable_runs", "spec_final_status", "spec_final_passed",
          "spec_final_total",
          # M3g (after M3d's): the knowledge pack's manifest hash and the skills the plan loaded, blank with no pack
          "skills_pack", "skills_status", "skills_loaded", "skills_requested", "skills_unknown", "skills_bytes",
          "skills_truncated"]
M3C_GATE = ("gate_runs", "gate_failures", "mutants_generated", "mutants_compiled", "mutants_killed",
            "mutants_unfinished", "gate_wall_s")
M3C_IFACE = ("interface_runs", "interface_mismatch_runs", "interface_blocks")
M3D_VERIFY = ("verify_runs", "verify_refusals", "verify_let_through", "verify_reruns", "testbench_runs")
M3D_SPEC = ("spec_cases", "spec_steps", "spec_runs", "spec_unbuildable_runs")


import taxonomy  # noqa: E402  (after the path insert; taxonomy imports collect lazily)


def amba_ids(path=os.path.join(HERE, "amba_ids.txt")):
    return {ln.strip() for ln in open(path) if ln.strip() and not ln.startswith("#")}


def problem_dir(work, pid, entry):
    """work/<cvdp_..._name>/harness/<n>, as the harness lays it out (create_context in dataset_processor.py)."""
    parts = pid.split("_")
    cand = os.path.join(work, "_".join(parts[:-1]), "harness", str(int(parts[-1])))
    if os.path.isdir(cand):
        return cand
    for t in entry.get("tests", []):  # fall back to the log path the harness recorded
        log = t.get("log") or ""
        d = os.path.join(work, os.path.basename(os.path.dirname(os.path.dirname(log))), "harness",
                         os.path.splitext(os.path.basename(log))[0])
        if os.path.isdir(d):
            return d
    return cand


def m3c_columns(s):
    """M3c's columns from a summary; blank for an agent without the switch (or an older one)."""
    sw = s.get("switches", {})
    out = {k: "" for k in FIELDS[FIELDS.index("mutation_gate"):]}
    out["mutation_gate"] = int(bool(sw.get("mutation_gate"))) if s else ""
    out["interface_check"] = int(bool(sw.get("interface_check"))) if s else ""
    if "gate_runs" in s:
        out.update({k: s.get(k, 0) for k in M3C_GATE})
        out["gate_outcomes"] = "+".join(s.get("gate_outcomes") or [])
        out["gate_overridden"] = int(bool(s.get("gate_overridden")))
    if "interface_runs" in s:
        out.update({k: s.get(k, 0) for k in M3C_IFACE})
        out["interface_kinds"] = "+".join(f"{k}:{v}" for k, v in sorted((s.get("interface_kinds") or {}).items()))
        out["interface_fallbacks"] = (s.get("interface_engines") or {}).get("yosys", 0)
        out["interface_unresolved"] = int(bool(s.get("interface_mismatch_unresolved")))
    return out


def m3d_columns(s):
    """M3d's columns from a summary; blank for an agent without the switch (or an older one)."""
    sw = s.get("switches", {})
    out = {k: "" for k in FIELDS[FIELDS.index("verify_submit"):]}
    out["verify_submit"] = int(bool(sw.get("verify_submit"))) if s else ""
    out["spec_vectors"] = int(bool(sw.get("spec_vectors"))) if s else ""
    if "verify_runs" in s:
        out.update({k: s.get(k, 0) for k in M3D_VERIFY})
        out["verify_outcomes"] = "+".join(s.get("verify_outcomes") or [])
        v = s.get("verified_at_submit")
        out["verified_at_submit"] = "" if v is None else int(bool(v))
    if "spec_status" in s:
        out.update({k: s.get(k, 0) for k in M3D_SPEC})
        out["spec_status"] = s.get("spec_status") or ""
        out["spec_failed_open"] = int(bool(s.get("spec_failed_open")))
        out["spec_final_status"] = s.get("spec_final_status") or ""
        for k in ("spec_final_passed", "spec_final_total"):
            out[k] = "" if s.get(k) is None else s[k]
    return out


def m3g_columns(s):
    """M3g's columns from a summary; blank for an agent without a pack (or an older one)."""
    out = {k: "" for k in FIELDS[FIELDS.index("skills_pack"):]}
    if "skills_status" in s:
        out["skills_pack"] = s.get("skills_pack") or ""
        out["skills_status"] = s.get("skills_status") or ""
        for k in ("skills_loaded", "skills_requested", "skills_unknown"):
            out[k] = "+".join(str(x) for x in (s.get(k) or []))
        out["skills_bytes"] = s.get("skills_bytes", 0)
        out["skills_truncated"] = int(bool(s.get("skills_truncated")))
    return out


def rows(work, dataset=None, runner="", model="", seed="", reasoning_hint=""):
    """`reasoning_hint` is the sweep's setting, used for a row whose agent left no summary."""
    raw = json.load(open(os.path.join(work, "raw_result.json")))
    meta = {}
    if dataset:
        for ln in open(dataset):
            if ln.strip():
                r = json.loads(ln)
                meta[r["id"]] = r.get("categories", ["", ""])
    amba = amba_ids()
    out = []
    for pid in sorted(set(raw) | set(meta)):
        e = raw.get(pid, {})
        tests = e.get("tests", [])
        passed = sum(1 for t in tests if t.get("result") == 0)
        cats = meta.get(pid, [e.get("category", ""), e.get("difficulty", "")])
        pdir = problem_dir(work, pid, e)
        s_path = os.path.join(pdir, "rundir", "agent_out", "summary.json")
        s = json.load(open(s_path)) if os.path.exists(s_path) else {}
        sw = s.get("switches", {})
        served = s.get("model") or ""
        requested = model or s.get("requested_model") or served or "unknown"
        reasoning = sw.get("reasoning", s.get("reasoning", "")) or reasoning_hint
        out.append({
            "label": f"{requested} (reasoning {reasoning})" if reasoning else requested,
            "id": pid,
            "seed": seed or s.get("seed") or "",
            "cid": e.get("category") or cats[0],
            "difficulty": e.get("difficulty") or (cats[1] if len(cats) > 1 else ""),
            "pass": int(bool(tests) and passed == len(tests)),
            "tests": len(tests),
            "tests_passed": passed,
            "amba": int(pid in amba),
            "requested_model": requested,
            "model": served if isinstance(served, str) else "+".join(served),
            "provider": s.get("provider", ""),
            "cost_usd": "" if s.get("cost_usd") is None else s["cost_usd"],
            "cost_unreported_calls": s.get("cost_unreported_calls", ""),
            "prompt_tokens": s.get("prompt_tokens", 0),
            "completion_tokens": s.get("completion_tokens", 0),
            "llm_calls": s.get("llm_calls", 0),
            "tool_calls": s.get("tool_calls", 0),
            "turns": s.get("turns", 0),
            "wall_time_s": s.get("wall_time_s", ""),
            "harness_agent_s": round(e["agent_execution"], 2) if "agent_execution" in e else "",
            "stop_reason": s.get("stop_reason") or ("not_run" if pid not in raw else "no_summary"),
            "kept": s.get("kept", ""),
            "agent_status": e.get("agent_status", ""),
            "self_check": int(sw["self_check"]) if "self_check" in sw else "",
            "lint": int(sw["lint"]) if "lint" in sw else "",
            "max_turns": sw.get("max_turns", ""),
            "budget_usd": sw.get("budget_usd", ""),
            "reasoning": reasoning,
            "reasoning_used": s.get("reasoning_used", ""),
            "reasoning_tokens": s.get("reasoning_tokens", ""),
            "empty_replies": s.get("empty_replies", ""),
            "empty_retries": s.get("empty_retries", ""),
            "reflect_parse_retries": s.get("reflect_parse_retries", ""),
            "providers": "+".join(f"{k}:{v}" for k, v in (s.get("providers") or {}).items()),
            "runner": runner,
            "summary_found": int(bool(s)),
        })
        row = out[-1]
        row.update(m3c_columns(s))
        row.update(m3d_columns(s))
        row.update(m3g_columns(s))
        ev, _ = taxonomy.evidence_from_dir(work, pid, e, pdir)
        row.update(ev)
        if row["pass"] != 1:
            primary, flags = taxonomy.label({k: "" if v is None else str(v) for k, v in row.items()})
            row["failure_label"], row["failure_flags"] = primary, "+".join(flags)
        else:
            row["failure_label"] = row["failure_flags"] = ""
        row["memory"] = s.get("memory") or ""
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work")
    ap.add_argument("--dataset")
    ap.add_argument("--runner", default="")
    ap.add_argument("--model", default="", help="the model the sweep requested")
    ap.add_argument("--seed", default="", help="the sweep's repeat number for this work dir")
    ap.add_argument("--reasoning", default="", help="the sweep's reasoning setting (labels rows with no summary)")
    ap.add_argument("--no-header", action="store_true", help="rows only, to append another seed's")
    a = ap.parse_args()
    w = csv.DictWriter(sys.stdout, fieldnames=FIELDS)
    if not a.no_header:
        w.writeheader()
    for r in rows(a.work, a.dataset, a.runner, a.model, a.seed, a.reasoning):
        w.writerow(r)


if __name__ == "__main__":
    main()

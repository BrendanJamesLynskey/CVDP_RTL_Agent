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

HERE = os.path.dirname(os.path.abspath(__file__))
FIELDS = ["id", "seed", "cid", "difficulty", "pass", "tests", "tests_passed", "amba", "requested_model", "model",
          "provider", "cost_usd",
          "cost_unreported_calls", "prompt_tokens", "completion_tokens", "llm_calls", "tool_calls", "turns",
          "wall_time_s", "harness_agent_s", "stop_reason", "kept", "agent_status", "self_check", "lint",
          "max_turns", "budget_usd", "reasoning", "reasoning_used", "reasoning_tokens", "empty_replies",
          "empty_retries", "reflect_parse_retries", "runner", "summary_found"]


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


def rows(work, dataset=None, runner="", model="", seed=""):
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
        s_path = os.path.join(problem_dir(work, pid, e), "rundir", "agent_out", "summary.json")
        s = json.load(open(s_path)) if os.path.exists(s_path) else {}
        sw = s.get("switches", {})
        served = s.get("model") or ""
        requested = model or s.get("requested_model") or served or "unknown"
        out.append({
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
            "reasoning": sw.get("reasoning", s.get("reasoning", "")),
            "reasoning_used": s.get("reasoning_used", ""),
            "reasoning_tokens": s.get("reasoning_tokens", ""),
            "empty_replies": s.get("empty_replies", ""),
            "empty_retries": s.get("empty_retries", ""),
            "reflect_parse_retries": s.get("reflect_parse_retries", ""),
            "runner": runner,
            "summary_found": int(bool(s)),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work")
    ap.add_argument("--dataset")
    ap.add_argument("--runner", default="")
    ap.add_argument("--model", default="", help="the model the sweep requested")
    ap.add_argument("--seed", default="", help="the sweep's repeat number for this work dir")
    ap.add_argument("--no-header", action="store_true", help="rows only, to append another seed's")
    a = ap.parse_args()
    w = csv.DictWriter(sys.stdout, fieldnames=FIELDS)
    if not a.no_header:
        w.writeheader()
    for r in rows(a.work, a.dataset, a.runner, a.model, a.seed):
        w.writerow(r)


if __name__ == "__main__":
    main()

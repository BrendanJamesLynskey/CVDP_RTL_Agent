"""The PR smoke run checks plumbing, not score: every problem ran the agent image, the harness scored it, the agent
wrote its trace and summary into rundir (which the harness keeps), and collect.py joined them.

Usage: python3 tools/smoke_check.py <work_dir> <expected problems>
"""
import csv
import json
import os
import sys


def main(work, expected):
    raw = json.load(open(os.path.join(work, "raw_result.json")))
    rows = list(csv.DictReader(open(os.path.join(work, "results.csv"))))
    problems = []
    if len(raw) != expected:
        problems.append(f"raw_result.json has {len(raw)} problems, expected {expected}")
    for r in rows:
        if r["summary_found"] != "1":
            problems.append(f"{r['id']}: no agent_out/summary.json in the work dir")
        if r["stop_reason"] in ("error", "no_summary", "not_run", "no_task"):
            problems.append(f"{r['id']}: stop_reason {r['stop_reason']}")
        if r["agent_status"] not in ("completed", "completed_no_patch"):
            problems.append(f"{r['id']}: harness agent_status {r['agent_status']}")
        if r["tests"] == "0":
            problems.append(f"{r['id']}: the harness ran no tests")
    for d in os.listdir(work):
        rep = os.path.join(work, d, "reports")
        if os.path.isdir(rep) and not [f for f in os.listdir(rep) if f.endswith(".txt")]:
            problems.append(f"{d}: no per-test logs in reports/")
    print(f"{len(rows)} problems collected; passes {sum(r['pass'] == '1' for r in rows)} (not checked)")
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    print("smoke plumbing OK")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))

"""The PR smoke run checks plumbing, not score: for every seed, every problem ran the agent image, the harness scored
it, the agent wrote its trace and summary into rundir (which the harness keeps), and collect.py joined them, with
the seed in its own column.

Usage: python3 tools/smoke_check.py <work_dir> <expected problems> [<expected seeds>]
"""
import csv
import json
import os
import sys


def main(work, expected, seeds=1):
    rows = list(csv.DictReader(open(os.path.join(work, "results.csv"))))
    problems = []
    for k in range(1, seeds + 1):
        sd = os.path.join(work, f"seed{k}")
        raw_path = os.path.join(sd, "raw_result.json")
        if not os.path.exists(raw_path):
            problems.append(f"seed {k}: no raw_result.json")
            continue
        raw = json.load(open(raw_path))
        if len(raw) != expected:
            problems.append(f"seed {k}: raw_result.json has {len(raw)} problems, expected {expected}")
        for d in os.listdir(sd):
            rep = os.path.join(sd, d, "reports")
            if os.path.isdir(rep) and not [f for f in os.listdir(rep) if f.endswith(".txt")]:
                problems.append(f"seed {k}, {d}: no per-test logs in reports/")
        if sum(r["seed"] == str(k) for r in rows) != expected:
            problems.append(f"seed {k}: results.csv does not have {expected} rows with seed {k}")
    if len(rows) != expected * seeds:
        problems.append(f"results.csv has {len(rows)} rows, expected {expected * seeds}")
    for r in rows:
        tag = f"{r['id']} (seed {r['seed']})"
        if r["summary_found"] != "1":
            problems.append(f"{tag}: no agent_out/summary.json in the work dir")
        if r["stop_reason"] in ("error", "no_summary", "not_run", "no_task"):
            problems.append(f"{tag}: stop_reason {r['stop_reason']}")
        if r["agent_status"] not in ("completed", "completed_no_patch"):
            problems.append(f"{tag}: harness agent_status {r['agent_status']}")
        if r["tests"] == "0":
            problems.append(f"{tag}: the harness ran no tests")
    print(f"{len(rows)} rows collected ({seeds} seed(s)); passes {sum(r['pass'] == '1' for r in rows)} (not checked)")
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    print("smoke plumbing OK")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 1)

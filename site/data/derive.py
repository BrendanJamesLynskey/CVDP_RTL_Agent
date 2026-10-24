#!/usr/bin/env python3
"""Derive every figure the story page draws, from the committed CSVs only (stdlib).

    python3 site/data/derive.py            # writes site/data/story_data.json and checks it
    python3 site/data/derive.py --inject   # also rewrites the DATA block in site/story.html

The checks at the bottom compare what this script computes with the numbers printed in the
milestone reports (docs/reports/*.md). If a report and a CSV ever disagree, the script fails,
so the page cannot quietly drift from the data.
"""
import csv
import glob
import json
import math
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REP = os.path.join(ROOT, "docs", "reports")
OUT = os.path.join(ROOT, "site", "data", "story_data.json")
PAGE = os.path.join(ROOT, "site", "story.html")


def rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def wilson(k, n, z=1.959964):
    """Same formula as tools/table.py."""
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def short(pid):
    return pid.replace("cvdp_agentic_", "")


def run_summary(path, label, runner, run_id):
    r = rows(path)
    k = sum(int(x["pass"]) for x in r)
    n = len(r)
    cost = sum(float(x["cost_usd"] or 0) for x in r)
    lo, hi = wilson(k, n)
    return {
        "label": label, "runner": runner, "run": run_id, "k": k, "n": n,
        "rate": round(100 * k / n, 1), "lo": round(100 * lo, 1), "hi": round(100 * hi, 1),
        "cost": round(cost, 4), "per_solved": round(cost / k, 4) if k else None,
        "pass": {short(x["id"]): int(x["pass"]) for x in r},
        "cid": {short(x["id"]): x["cid"] for x in r},
    }


# ---- M2: three models, two runners (docs/reports/m2/{x86,arm64}/results_*.csv) ----
M2_RUNS = [
    ("Haiku 5.5 (low)", "x86-64", "39967302029", "m2/x86/results_claude-haiku-5.5_low.csv"),
    ("Haiku 5.5 (low)", "Arm64", "39975578761", "m2/arm64/results_claude-haiku-5.5_low.csv"),
    ("gpt-6-luna (default)", "x86-64", "39967317698", "m2/x86/results_gpt-6-luna_default.csv"),
    ("gpt-6-luna (default)", "Arm64", "39981444074", "m2/arm64/results_gpt-6-luna_default.csv"),
    ("DeepSeek V4.1 Flash (off)", "x86-64", "39975562293", "m2/x86/results_deepseek-v4.1-flash-1017_off.csv"),
    ("DeepSeek V4.1 Flash (off)", "Arm64", "39981458867", "m2/arm64/results_deepseek-v4.1-flash-1017_off.csv"),
]
m2 = [run_summary(os.path.join(REP, p), lab, rn, rid) for lab, rn, rid, p in M2_RUNS]
flips = {}
for i in range(0, 6, 2):
    a, b = m2[i], m2[i + 1]
    flips[a["label"]] = sum(1 for p in a["pass"] if a["pass"][p] != b["pass"][p])

# ---- M3: seven arms x two runs (docs/reports/m3/runs/*.csv) ----
ARMS = {
    "A": "base", "B": "self-check off", "C": "lint off", "D": "self-check and lint off",
    "E": "5 turns", "F": "20 turns", "G": "budget $0.02",
}
m3_files = {}
for f in sorted(glob.glob(os.path.join(REP, "m3", "runs", "*.csv"))):
    tag, run_id = os.path.basename(f)[:-4].split("_")
    m3_files[tag] = (run_id, rows(f))
m3_runs = []
for tag, (run_id, r) in m3_files.items():
    k = sum(int(x["pass"]) for x in r)
    m3_runs.append({
        "tag": tag, "run": run_id, "k": k, "n": len(r),
        "cost": round(sum(float(x["cost_usd"] or 0) for x in r), 4),
        "unreported": sum(int(x["cost_unreported_calls"] or 0) for x in r),
        "own_tb": sum(1 for x in r if int(x["selfcheck_runs"] or 0) > 0),
        "pass": {short(x["id"]): int(x["pass"]) for x in r},
    })

# point effects (the intervals come from tools/ablate.py's bootstrap, quoted from arms_paired.md)
def arm_rate(arm):
    a, b = m3_files[arm + "1"][1], m3_files[arm + "2"][1]
    pa = {x["id"]: int(x["pass"]) for x in a}
    pb = {x["id"]: int(x["pass"]) for x in b}
    return {p: (pa[p] + pb[p]) / 2 for p in pa}


base = arm_rate("A")
point = {}
better_worse = {}
for arm in "BCDEFG":
    ar = arm_rate(arm)
    d = [ar[p] - base[p] for p in base]
    point[arm] = round(100 * sum(d) / len(d), 1)
    better_worse[arm] = (sum(1 for x in d if x > 0), sum(1 for x in d if x < 0), sum(1 for x in d if x == 0))
a1 = {x["id"]: int(x["pass"]) for x in m3_files["A1"][1]}
a2 = {x["id"]: int(x["pass"]) for x in m3_files["A2"][1]}
noise_point = round(100 * sum(a2[p] - a1[p] for p in a1) / len(a1), 1)

# Paired effects and intervals exactly as printed in docs/reports/m3/arms_paired.md and
# calibration_same_runner.md (bootstrap seeds live in tools/ablate.py; not re-run here).
def parse_effects(path):
    out = {}
    for line in open(path):
        m = re.match(r"\| (\w+) \| ([^|]+) \| ([-+]?\d+\.\d) \[([-+]?\d+\.\d), ([-+]?\d+\.\d)\] \| (\d+) / (\d+) / (\d+) \| ([\d.]+) \|", line)
        if m:
            out[m.group(1)] = {
                "finding": m.group(2).strip(), "eff": float(m.group(3)), "lo": float(m.group(4)),
                "hi": float(m.group(5)), "better": int(m.group(6)), "worse": int(m.group(7)),
                "same": int(m.group(8)), "p": float(m.group(9)),
            }
    return out


effects = parse_effects(os.path.join(REP, "m3", "arms_paired.md"))
floor = parse_effects(os.path.join(REP, "m3", "calibration_same_runner.md"))["A2"]
pareto = rows(os.path.join(REP, "m3", "pareto.csv"))

# ---- taxonomy (failure_label column, written by tools/collect.py) ----
labels = {}
by_cid = {}
for tag, (run_id, r) in m3_files.items():
    for x in r:
        if int(x["pass"]):
            continue
        lab = x["failure_label"]
        labels[lab] = labels.get(lab, 0) + 1
        by_cid.setdefault(lab, {}).setdefault(x["cid"], 0)
        by_cid[lab][x["cid"]] += 1
fail_total = sum(labels.values())
tb_ran_failed = labels.get("tests_failed_selfcheck_passed", 0) + labels.get("tests_failed_selfcheck_failed", 0)
problems_per_label = {}
for lab in ("compile_fail_hidden", "signal_missing_hidden", "tests_failed_selfcheck_passed"):
    s = set()
    for tag, (run_id, r) in m3_files.items():
        s |= {x["id"] for x in r if not int(x["pass"]) and x["failure_label"] == lab}
    problems_per_label[lab] = len(s)

# ---- the problem x run raster: 6 M2 runs + 13 new M3 runs (A1 is M2's Arm64 Luna run) ----
ids = sorted(m2[0]["pass"])
cols = [{"name": f"{r['label'].split(' ')[0]} {r['runner']}", "pass": r["pass"]} for r in m2]
for tag in ["A2", "B1", "B2", "C1", "C2", "D1", "D2", "E1", "E2", "F1", "F2", "G1", "G2"]:
    cols.append({"name": f"M3 {tag}", "pass": {short(x['id']): int(x['pass']) for x in m3_files[tag][1]}})
assert m3_files["A1"][0] == "39981444074"
never_m2 = [p for p in ids if all(c["pass"][p] == 0 for c in cols[:6])]
always_m2 = [p for p in ids if all(c["pass"][p] == 1 for c in cols[:6])]
never_all = [p for p in ids if all(c["pass"][p] == 0 for c in cols)]
raster = {
    "ids": ids,
    "cid": [m2[0]["cid"][p] for p in ids],
    "cols": [c["name"] for c in cols],
    "bits": ["".join(str(c["pass"][p]) for c in cols) for p in ids],
}

# ---- hero trace: csr_using_apb_interface_0001, run A1 (row in m3/runs/A1_*.csv,
#      log and trace lines in m3/taxonomy_m3.md) ----
hero = next(x for x in m3_files["A1"][1] if x["id"] == "cvdp_agentic_csr_using_apb_interface_0001")
hero_out = {k: hero[k] for k in ("pass", "cost_usd", "llm_calls", "tool_calls", "turns", "wall_time_s",
                                   "harness_agent_s", "stop_reason", "failure_label", "own_compile_last",
                                   "selfcheck_runs", "prompt_tokens", "completion_tokens", "cid", "difficulty")}


# ---- published results (verified by hand against the primary sources on 2026-10-24; see external.json) ----
ext = json.load(open(os.path.join(ROOT, "site", "data", "external.json")))
for r in ext["same_92"]:
    lo, hi = wilson(r["k"], r["n"])
    r["rate"], r["lo"], r["hi"] = round(100 * r["k"] / r["n"], 1), round(100 * lo, 1), round(100 * hi, 1)

m3_cost = round(sum(r["cost"] for r in m3_runs if r["tag"] != "A1"), 4)
m2_cost = 0.0
for p in glob.glob(os.path.join(REP, "m2", "*", "results_*.csv")):
    m2_cost += sum(float(x["cost_usd"] or 0) for x in rows(p))
m2_cost = round(m2_cost, 4)

data = {
    "m2": [{k: v for k, v in r.items() if k not in ("pass", "cid")} for r in m2],
    "m2_flips": flips,
    "m2_never": len(never_m2), "m2_always": len(always_m2), "never_all_20": len(never_all),
    "m3_runs": [{k: v for k, v in r.items() if k != "pass"} for r in m3_runs],
    "m3_effects": effects, "m3_point_check": point, "m3_better_worse_check": better_worse,
    "noise_floor": floor, "noise_point_check": noise_point,
    "pareto": [{"arm": p["arm"], "usd": float(p["usd_per_problem"]), "rate": float(p["pass_rate"]),
                "frontier": int(p["frontier"]), "lb": int(p["cost_lower_bound"])} for p in pareto],
    "taxonomy": dict(sorted(labels.items(), key=lambda kv: -kv[1])), "taxonomy_total": fail_total,
    "taxonomy_by_cid": by_cid, "problems_per_label": problems_per_label,
    "own_tb_ran_failed": tb_ran_failed,
    "raster": raster, "hero": hero_out,
    "cost_m2": m2_cost, "cost_m3": m3_cost,
    "external": ext,
}

# ---- checks against the reports ----
errors = []
def check(cond, msg):
    if not cond:
        errors.append(msg)

check([r["k"] for r in m2] == [52, 56, 52, 53, 43, 41], "M2 pass counts")
check([r["per_solved"] for r in m2] == [0.0214, 0.0184, 0.0105, 0.0109, 0.0240, 0.0238], f"M2 $/solved {[r['per_solved'] for r in m2]}")
check([(r["lo"], r["hi"]) for r in m2] == [(46.3, 66.2), (50.7, 70.2), (46.3, 66.2), (47.4, 67.2), (36.9, 56.9), (34.8, 54.7)], "M2 Wilson")
check(list(flips.values()) == [10, 9, 12], f"M2 flips {flips}")
check(len(never_m2) == 28 and len(always_m2) == 29, f"M2 never/always {len(never_m2)} {len(always_m2)}")
check(len(never_all) == 24, f"never in 20 runs {len(never_all)}")
check(fail_total == 565, f"failures {fail_total}")
check(labels == {"tests_failed_no_selfcheck": 271, "compile_fail_hidden": 74, "signal_missing_hidden": 73,
                 "tests_failed_selfcheck_passed": 61, "stopped_by_cap": 56, "sim_incomplete": 13,
                 "tests_failed_selfcheck_failed": 12, "no_edit": 5}, f"labels {labels}")
check(tb_ran_failed == 73, "73 failed with own testbench")
check(problems_per_label == {"compile_fail_hidden": 8, "signal_missing_hidden": 9, "tests_failed_selfcheck_passed": 26}, f"problems per label {problems_per_label}")
for arm in "BCDEFG":
    e = effects[arm]
    check(abs(e["eff"] - point[arm]) < 0.06, f"effect {arm} {e['eff']} vs {point[arm]}")
    check((e["better"], e["worse"], e["same"]) == better_worse[arm], f"better/worse {arm}")
check(floor["eff"] == noise_point == -2.2, "noise floor")
check(abs(m2_cost - 8.5539) < 0.00005, f"M2 cost {m2_cost}")
check(abs(m3_cost - 8.2537) < 0.00005, f"M3 cost {m3_cost}")
check([r["own_tb"] for r in m3_runs] == [31, 32, 0, 0, 67, 67, 0, 0, 39, 34, 39, 39, 41, 39], "own testbench counts")
check(hero["failure_label"] == "signal_missing_hidden", "hero label")

json.dump(data, open(OUT, "w"), indent=1, sort_keys=False)
if errors:
    print("MISMATCH:\n  " + "\n  ".join(errors))
    sys.exit(1)
print(f"ok: {OUT} ({len(json.dumps(data))} bytes); all report checks pass")

if "--inject" in sys.argv:
    page = open(PAGE).read()
    block = "/*DATA:BEGIN*/" + json.dumps(data, separators=(",", ":")) + "/*DATA:END*/"
    page2 = re.sub(r"/\*DATA:BEGIN\*/.*?/\*DATA:END\*/", lambda m: block, page, flags=re.S)
    if page2 == page and block not in page:
        sys.exit("no DATA block in story.html")
    open(PAGE, "w").write(page2)
    print("injected data block into", PAGE)

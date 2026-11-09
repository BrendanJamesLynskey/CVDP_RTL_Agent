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

# ---- M3b: four arms x three runs on the 86-problem evaluation set (docs/reports/m3b/) ----
M3B = os.path.join(REP, "m3b")
EVAL = [l.strip() for l in open(os.path.join(ROOT, "tools", "m3b_eval_ids.txt")) if l.strip() and not l.startswith("#")]
M3B_ARMS = {"A": ("LangGraph", "none"), "B": ("Deep Agents", "none"), "C": ("LangGraph", "lessons"), "D": ("Deep Agents", "lessons")}
m3b_files = {}
for f in sorted(glob.glob(os.path.join(M3B, "runs", "*.csv"))):
    tag, run_id = os.path.basename(f)[:-4].split("_")
    m3b_files.setdefault(tag[0], []).append((tag, run_id, rows(f)))
m3b_arms = {}
m3b_rate = {}
for arm, runs in m3b_files.items():
    allr = [x for _, _, r in runs for x in r]
    k = sum(int(x["pass"]) for x in allr)
    cost = sum(float(x["cost_usd"] or 0) for x in allr)
    pt = sum(int(x["prompt_tokens"] or 0) for x in allr)
    tok = pt + sum(int(x["completion_tokens"] or 0) for x in allr)
    capr = [x for x in allr if x["stop_reason"] == "max_turns"]
    labs = {}
    for x in allr:
        if not int(x["pass"]):
            labs[x["failure_label"]] = labs.get(x["failure_label"], 0) + 1
    wall = sorted(float(x["wall_time_s"]) for x in allr)
    m3b_arms[arm] = {
        "harness": M3B_ARMS[arm][0], "memory": M3B_ARMS[arm][1],
        "runs": [{"tag": t, "run": rid, "k": sum(int(x["pass"]) for x in r), "n": len(r)} for t, rid, r in runs],
        "k": k, "n": len(allr), "rate": round(100 * k / len(allr), 1),
        "cost": round(cost, 4), "usd_problem": round(cost / len(allr), 4), "usd_solved": round(cost / k, 4),
        "prompt_tokens": pt, "tokens": tok, "usd_per_mprompt": round(1e6 * cost / pt, 3),
        "cap_stops": len(capr), "cap_stops_passed": sum(int(x["pass"]) for x in capr),
        "unreported": sum(int(x["cost_unreported_calls"] or 0) for x in allr),
        "labels": labs, "fails": sum(labs.values()),
        "memory_col": sorted({x["memory"] for x in allr}),
        "ids": sorted({x["id"] for x in allr}),
    }
    per = {}
    for _, _, r in runs:
        for x in r:
            per.setdefault(x["id"], []).append(int(x["pass"]))
    m3b_rate[arm] = {p: sum(v) / len(v) for p, v in per.items()}


def paired(a, base):
    d = [m3b_rate[a][p] - m3b_rate[base][p] for p in EVAL]
    return (round(100 * sum(d) / len(d), 1), sum(1 for x in d if x > 0), sum(1 for x in d if x < 0), sum(1 for x in d if x == 0))


def sign_p(b, w):
    """Exact two-sided sign test, as tools/ablate.py describes it."""
    n, k = b + w, min(b, w)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def parse_sections(path):
    """Effects table per base (`X`) section of an ablate.py report."""
    out, base = {}, None
    for line in open(path):
        m = re.match(r"#### Paired effect against the base \(`(\w+)`\)", line)
        if m:
            base = m.group(1)
            continue
        m = re.match(r"\| (\w+) \| ([^|]+) \| ([-+]?\d+\.\d) \[([-+]?\d+\.\d), ([-+]?\d+\.\d)\] \| (\d+) / (\d+) / (\d+) \| ([\d.]+) \|", line)
        if m and base:
            out[m.group(1) + "-" + base] = {
                "finding": m.group(2).strip(), "eff": float(m.group(3)), "lo": float(m.group(4)),
                "hi": float(m.group(5)), "better": int(m.group(6)), "worse": int(m.group(7)),
                "same": int(m.group(8)), "p": float(m.group(9)),
            }
    return out


m3b_eff = parse_sections(os.path.join(M3B, "arms_paired_eval86.md"))
m3b_eff.update(parse_sections(os.path.join(M3B, "arms_paired_secondary_eval86.md")))
M3B_ROLE = {"C-A": "primary", "D-B": "secondary", "B-A": "primary", "D-C": "secondary", "D-A": "exploratory"}
m3b_check = {}
for key, role in M3B_ROLE.items():
    a, base = key.split("-")
    m3b_eff[key]["role"] = role
    m3b_check[key] = paired(a, base) + (sign_p(*paired(a, base)[1:3]),)
BONF = 0.05 / 4
m3b_bonf_pass = [k for k, r in M3B_ROLE.items() if r != "exploratory" and m3b_eff[k]["p"] < BONF]

# noise floor and M3's largest effect, restricted to the 86 (intervals quoted from M3b_report.md "In short")
rep3b = open(os.path.join(REP, "M3b_report.md")).read()
def m3_on_eval(arm):
    a, b = ({x["id"]: int(x["pass"]) for x in m3_files[arm + s][1]} for s in "12")
    return {p: (a[p] + b[p]) / 2 for p in EVAL}
fa1 = {x["id"]: int(x["pass"]) for x in m3_files["A1"][1]}
fa2 = {x["id"]: int(x["pass"]) for x in m3_files["A2"][1]}
dn = [fa2[p] - fa1[p] for p in EVAL]
mf = re.search(r"differ by \*\*([−-][\d.]+)\s+points\s+\[([−-][\d.]+),\s+\+([\d.]+)\]\*\*\s+\((\d+) better, (\d+) worse, (\d+) the same\)", rep3b)
m3b_floor = {"eff": round(100 * sum(dn) / len(dn), 1), "lo": -float(mf.group(2)[1:]), "hi": float(mf.group(3)),
             "better": sum(1 for x in dn if x > 0), "worse": sum(1 for x in dn if x < 0), "same": sum(1 for x in dn if x == 0),
             "report": (-float(mf.group(1)[1:]), int(mf.group(4)), int(mf.group(5)), int(mf.group(6)))}
fF, fA = m3_on_eval("F"), m3_on_eval("A")
mF = re.search(r"20 turns, is\s+\*\*\+([\d.]+) \[([−-][\d.]+), \+([\d.]+)\]\*\*", rep3b)
m3b_f20 = {"eff": round(100 * sum(fF[p] - fA[p] for p in EVAL) / len(EVAL), 1), "lo": -float(mF.group(2)[1:]),
           "hi": float(mF.group(3)), "report": float(mF.group(1))}

# the lessons snapshot and how often each lesson is retrieved for the 86 (retrieval_eval86.md)
snap_path = glob.glob(os.path.join(M3B, "lessons", "lessons_*.json"))
assert len(snap_path) == 1, snap_path
snap = json.load(open(snap_path[0]))
retr = {}
for line in open(os.path.join(M3B, "retrieval_eval86.md")):
    m = re.match(r"\| (L\d\d) \| (\d+) \| (.*) \|$", line.rstrip())
    if m:
        retr[m.group(1)] = (int(m.group(2)), m.group(3))
lesson_text = {l["id"]: l["text"] for l in snap["lessons"]}
top = sorted(retr, key=lambda k: (-retr[k][0], k))[:4]
learn = []
for f in sorted(glob.glob(os.path.join(M3B, "learning", "learn_*.csv"))):
    r = rows(f)
    learn.append({"run": os.path.basename(f)[6:-4], "k": sum(int(x["pass"]) for x in r), "n": len(r),
                  "cost": round(sum(float(x["cost_usd"] or 0) for x in r), 4),
                  "unreported": sum(int(x["cost_unreported_calls"] or 0) for x in r)})
smoke = float(re.search(r"Total \*\*\$([\d.]+)\*\* of the", rep3b).group(1))
m3b_scored = round(sum(a["cost"] for a in m3b_arms.values()), 4)
m3b_learn = round(sum(x["cost"] for x in learn), 4)
m3b_total = round(m3b_scored + m3b_learn + snap["provenance"]["cost_usd"] + smoke, 4)
spend_all = round(0.75 + m2_cost + m3_cost + m3b_total, 2)  # M1 "about $0.75" (M3_report.md, cost bookkeeping)
mA, mB = m3b_arms["A"], m3b_arms["B"]

m3b = {
    "arms": {k: {kk: vv for kk, vv in v.items() if kk not in ("ids", "memory_col")} for k, v in sorted(m3b_arms.items())},
    "effects": m3b_eff, "bonferroni": BONF, "bonf_pass": m3b_bonf_pass,
    "floor": {k: v for k, v in m3b_floor.items() if k != "report"}, "f20": {k: v for k, v in m3b_f20.items() if k != "report"},
    "lessons": {"hash": snap["hash"], "n": len(snap["lessons"]), "attempts": snap["provenance"]["attempts"],
                "passed": snap["provenance"]["passed"], "problems": snap["provenance"]["problems"],
                "cost": snap["provenance"]["cost_usd"], "never": sorted(k for k in retr if retr[k][0] == 0),
                "top": [{"id": k, "count": retr[k][0], "text": lesson_text[k]} for k in top]},
    "learning": learn, "cost_scored": m3b_scored, "cost_learning": m3b_learn, "cost_smoke": smoke, "cost_total": m3b_total,
    "n_eval": len(EVAL),
}

# ---- shared pooling for the 86-problem sets below (confirming run, M3c, Claude Code ladder) ----
import statistics
def load_runs(pattern):
    out = {}
    for f in sorted(glob.glob(pattern)):
        tag, run_id = os.path.basename(f)[:-4].split("_")
        out.setdefault(tag[0], []).append((tag, run_id, rows(f)))
    return out


def pool(runs):
    allr = [x for _, _, r in runs for x in r]
    k = sum(int(x["pass"]) for x in allr)
    cost = sum(float(x["cost_usd"] or 0) for x in allr)
    labs = {}
    for x in allr:
        if not int(x["pass"]):
            labs[x["failure_label"]] = labs.get(x["failure_label"], 0) + 1
    per = {}
    for _, _, r in runs:
        for x in r:
            per.setdefault(x["id"], []).append(int(x["pass"]))
    tok = sum(int(x["prompt_tokens"] or 0) + int(x["completion_tokens"] or 0) for x in allr)
    wc = [x for x in allr if x["stop_reason"] == "wall_time"]
    return {
        "runs": [{"tag": t, "run": rid, "k": sum(int(x["pass"]) for x in r), "n": len(r)} for t, rid, r in runs],
        "k": k, "n": len(allr), "rate": round(100 * k / len(allr), 1),
        "cost": round(cost, 4), "usd_problem": round(cost / len(allr), 4), "usd_solved": round(cost / k, 4) if k else None,
        "unreported": sum(int(x["cost_unreported_calls"] or 0) for x in allr),
        "labels": labs, "fails": sum(labs.values()), "tokens": tok,
        "turn_cap": sum(1 for x in allr if x["stop_reason"] == "max_turns"),
        "wall_cap": len(wc), "wall_cap_failed": sum(1 for x in wc if not int(x["pass"])),
        "wall_med": round(statistics.median(float(x["wall_time_s"]) for x in allr)),
        "ids": sorted(per), "_rate": {p: sum(v) / len(v) for p, v in per.items()},
    }


def paired_on(arm, base):
    d = [arm["_rate"][p] - base["_rate"][p] for p in EVAL]
    b, w = sum(1 for x in d if x > 0), sum(1 for x in d if x < 0)
    return (round(100 * sum(d) / len(d), 1), b, w, len(d) - b - w, sign_p(b, w))


def public(arm):
    return {k: v for k, v in arm.items() if not k.startswith("_") and k != "ids"}


# ---- M3b confirming run: B - A on 6 new runs an arm (docs/reports/m3b/confirm_*.md, confirm_runs/) ----
conf_runs = load_runs(os.path.join(M3B, "confirm_runs", "*.csv"))
conf = {a: pool(r) for a, r in sorted(conf_runs.items())}
conf_eff = parse_sections(os.path.join(M3B, "confirm_paired_eval86.md"))["B-A"]
conf_chk = paired_on(conf["B"], conf["A"])
conf_seeds = sorted({int(x["seed"]) for _, _, r in conf_runs["A"] + conf_runs["B"] for x in r})
conf_verdict = "confirmed" if conf_eff["lo"] > 0 and conf_eff["eff"] > 0 else "reversed" if conf_eff["hi"] < 0 else "not confirmed"
conf_rep = open(os.path.join(M3B, "confirm_result.md")).read()
conf_rep_verdict = re.search(r"## Verdict: (.+)", conf_rep).group(1).strip()
conf_rep_total = float(re.search(r"Total spend \$(\d+\.\d+)", conf_rep).group(1))
conf_cost = round(sum(a["cost"] for a in conf.values()), 4)
m3b_conf = {"arms": {a: public(v) for a, v in conf.items()}, "effect": conf_eff, "verdict": conf_verdict,
            "seeds": conf_seeds, "cost": conf_cost}

# ---- M3c: arms A, M (mutation gate), I (interface check), 3 runs each (docs/reports/M3c_report.md, m3c/) ----
M3C = os.path.join(REP, "m3c")
c_runs = load_runs(os.path.join(M3C, "runs", "*.csv"))
m3c_arms = {a: pool(c_runs[a]) for a in "AMI"}
m3c_eff = parse_sections(os.path.join(M3C, "arms_paired_eval86.md"))
m3c_chk = {k: paired_on(m3c_arms[k[0]], m3c_arms["A"]) for k in ("M-A", "I-A")}
Mrows = [x for _, _, r in c_runs["M"] for x in r]
Irows = [x for _, _, r in c_runs["I"] for x in r]
gate_out = {}
for x in Mrows:
    for o in x["gate_outcomes"].split("+"):
        if o:
            gate_out[o] = gate_out.get(o, 0) + 1
gsum = lambda col: sum(int(x[col] or 0) for x in Mrows)
gate = {
    "runs": gsum("gate_runs"), "outcomes": gate_out, "problem_runs": sum(1 for x in Mrows if int(x["gate_runs"] or 0) > 0),
    "generated": gsum("mutants_generated"), "compiled": gsum("mutants_compiled"), "killed": gsum("mutants_killed"),
    "unfinished": gsum("mutants_unfinished"),
    "skipped_problems": len({x["id"] for x in Mrows if "skipped" in x["gate_outcomes"].split("+")}),
}
gate["kill_rate"] = round(100 * gate["killed"] / gate["compiled"], 1)
mm = [x for x in Irows if int(x["interface_mismatch_runs"] or 0) > 0]
iface = {"checks": sum(int(x["interface_runs"] or 0) for x in Irows),
         "mismatch_checks": sum(int(x["interface_mismatch_runs"] or 0) for x in Irows),
         "mismatch_pr": len(mm), "mismatch_pr_passed": sum(int(x["pass"]) for x in mm),
         "blocks": sum(int(x["interface_blocks"] or 0) for x in Irows)}
rep3c = open(os.path.join(REP, "M3c_report.md")).read()
m3c_smoke = float(re.search(r"Total \*\*\$([\d.]+)\*\* of the", rep3c).group(1))
m3c_scored = round(sum(a["cost"] for a in m3c_arms.values()), 4)
m3c = {"arms": {a: public(v) for a, v in m3c_arms.items()}, "effects": m3c_eff, "gate": gate, "iface": iface,
       "cost_scored": m3c_scored, "cost_smoke": m3c_smoke,
       "solved_x": round(m3c_arms["M"]["usd_solved"] / m3c_arms["A"]["usd_solved"], 1)}

# ---- Claude Code ladder: one run per model against M3c's arm A (docs/reports/claude_code_ladder.md) ----
LADDER = [("haiku", "Haiku 5.5", "claude-haiku-5-5"), ("sonnet", "Sonnet 5.5", "claude-sonnet-5-5"),
          ("opus", "Opus 5.5", "claude-opus-5-5"), ("fable", "Fable 5.1", "claude-fable-5-1")]
lad_eff = parse_sections(os.path.join(REP, "claude_code", "ladder_paired_eval86.md"))
ladder = {}
lad_chk = {}
for key, name, stem in LADDER:
    r = rows(os.path.join(REP, "claude_code", "runs", stem + ".csv"))
    z = pool([("1", stem, r)])
    lad_chk[key] = paired_on(z, m3c_arms["A"])
    z["name"], z["providers"] = name, sorted({x["provider"] for x in r})
    z["effect"] = lad_eff[key + "-luna"]
    ladder[key] = z
lad_union = sum(1 for p in EVAL if any(ladder[k]["_rate"][p] for k in ladder))
lad_all = sum(1 for p in EVAL if all(ladder[k]["_rate"][p] for k in ladder))
claude_ladder = {"arms": {k: public(v) for k, v in ladder.items()}, "order": [k for k, _, _ in LADDER],
                 "union": lad_union, "all": lad_all}

# ---- the unsolved-problems analysis: 12 problems no Claude model solved (docs/reports/unsolved_analysis.md) ----
BLIM = [l.strip() for l in open(os.path.join(ROOT, "tools", "benchmark_limited_ids.txt")) if l.strip() and not l.startswith("#")]
EVAL79 = [p for p in EVAL if p not in BLIM]
uns = sorted(p for p in EVAL if not any(ladder[k]["_rate"][p] for k in ladder))
uns_A0 = [p for p in uns if m3c_arms["A"]["_rate"][p] == 0]
def on79(arm, runs):
    return sum(round(arm["_rate"][p] * runs) for p in EVAL79), runs * len(EVAL79)
u79 = {"A": on79(m3c_arms["A"], len(c_runs["A"]))}
for k in ladder:
    u79[k] = on79(ladder[k], 1)
unsolved = {"n": len(uns), "never_A": len(uns_A0), "blim": len(BLIM), "n79": len(EVAL79),
            "blim_in_uns": all(p in uns for p in BLIM),
            "r79": {k: round(100 * a / b, 1) for k, (a, b) in u79.items()}, "k79": {k: list(v) for k, v in u79.items()}}
rep_un = open(os.path.join(REP, "unsolved_analysis.md")).read()
mc = re.search(r"Class counts: \*\*benchmark-limited (\d+) \((\d+) strong, (\d+) borderline\), environment (\d+), agent-limited (\d+)", rep_un)
unsolved.update({"border": int(mc.group(3)), "env": int(mc.group(4)), "agent": int(mc.group(5))})
mt = re.search(r"In (\d+) of arm A's (\d+) valid attempts on them", rep_un)
unsolved.update({"p2_untested": int(mt.group(1)), "p2_valid": int(mt.group(2))})
mdf = re.search(r"the defaults alone were set to (\d+) and (\d+)", rep_un)
unsolved["tl_defaults"] = [int(mdf.group(1)), int(mdf.group(2))]
# part two: solved by at least 2 Claude models, never by M3c's arm A
P2 = sorted(p for p in EVAL if sum(ladder[k]["_rate"][p] for k in ladder) >= 2 and m3c_arms["A"]["_rate"][p] == 0)
unsolved["p2"] = len(P2)

# ---- M3d: arms A, V (verify before submit), S (V + blind spec cases), 3 runs each (docs/reports/M3d_report.md, m3d/) ----
M3D = os.path.join(REP, "m3d")
d_runs = load_runs(os.path.join(M3D, "runs", "*.csv"))
m3d_arms = {a: pool(d_runs[a]) for a in "AVS"}
m3d_eff = parse_sections(os.path.join(M3D, "arms_paired_eval86.md"))
m3d_eff79 = parse_sections(os.path.join(M3D, "arms_paired_eval79.md"))
m3d_chk = {k: paired_on(m3d_arms[k[0]], m3d_arms["A"]) for k in ("V-A", "S-A")}
d_rows = {a: [x for _, _, r in d_runs[a] for x in r] for a in "AVS"}
def rate79(a):
    r = [x for x in d_rows[a] if x["id"] in EVAL79]
    return round(100 * sum(int(x["pass"]) for x in r) / len(r), 1), len(r)
m3d_extra = {}
for a, rs in d_rows.items():
    m3d_extra[a] = {
        "no_sc": sum(1 for x in rs if int(x["selfcheck_runs"] or 0) == 0),
        "one_turn": sum(1 for x in rs if int(x["turns"] or 0) == 1),
        "turns_med": statistics.median(int(x["turns"] or 0) for x in rs),
        "llm_error_stop": sum(1 for x in rs if x["stop_reason"] == "llm_error"),
        "guard": sum(1 for x in rs if x["stop_reason"] == "run_budget_exhausted"),
        "rate79": rate79(a)[0], "n79": rate79(a)[1],
    }
    if a != "A":
        m3d_extra[a].update({"verify_runs": sum(int(x["verify_runs"] or 0) for x in rs),
                             "refusals": sum(int(x["verify_refusals"] or 0) for x in rs),
                             "refused_rows": sum(1 for x in rs if int(x["verify_refusals"] or 0) > 0)})
Srows = d_rows["S"]
spec_tab = {}
for x in Srows:
    st = x["spec_final_status"]
    key = "pass" if st == "pass" else "fail" if st == "fail" else "na"
    spec_tab.setdefault(key, [0, 0])[0 if int(x["pass"]) else 1] += 1
spec_gen = sum(1 for x in Srows if x["spec_status"] == "generated")
p2_pass = {a: sum(int(x["pass"]) for x in d_rows[a] if x["id"] in P2) for a in "AVS"}
guard_adj = round(100 * m3d_extra["S"]["guard"] * (m3d_arms["A"]["k"] / m3d_arms["A"]["n"]) / m3d_arms["A"]["n"], 1)
rep3d = open(os.path.join(REP, "M3d_report.md")).read()
m3d_smoke = float(re.search(r"\*\*Smoke runs\.\*\* \$([\d.]+) reported", rep3d).group(1))
m3d_scored = round(sum(a["cost"] for a in m3d_arms.values()), 4)
m3d = {"arms": {a: public(v) for a, v in m3d_arms.items()}, "effects": m3d_eff, "effects79": m3d_eff79, "extra": m3d_extra,
       "spec": spec_tab, "spec_generated": spec_gen, "guard_adj": guard_adj, "cost_scored": m3d_scored, "cost_smoke": m3d_smoke,
       "solved_x": {a: round(m3d_arms[a]["usd_solved"] / m3d_arms["A"]["usd_solved"], 1) for a in "VS"}}

# ---- M3e: LangGraph + Opus 5.5, one run, exploratory; 67 attempted problems (docs/reports/M3e_report.md, m3e/) ----
M3E = os.path.join(REP, "m3e")
def ids_file(path):
    return [l.strip() for l in open(path) if l.strip() and not l.startswith("#")]
E_ATT = ids_file(os.path.join(M3E, "attempted_ids.txt"))
E_REF = ids_file(os.path.join(M3E, "guard_refused_ids.txt"))
E_ATT63 = [p for p in E_ATT if p not in BLIM]
e_all = rows(os.path.join(M3E, "runs", "LG_opus_41040802008.csv"))
def restrict(runs, ids):
    keep = set(ids)
    return [(t, rid, [x for x in r if x["id"] in keep]) for t, rid, r in runs]
e_arms = {
    "luna": pool(restrict(d_runs["A"], E_ATT)),
    "opus": pool(restrict([("LG", "41040802008", e_all)], E_ATT)),
    "cc": pool(restrict([("1", "claude-opus-5-5", rows(os.path.join(REP, "claude_code", "runs", "claude-opus-5-5.csv")))], E_ATT)),
}
def parse_plus(path):
    """ablate.py effect rows whose arm names carry a '+' (LG+Opus, CC+Opus)."""
    out, base = {}, None
    for line in open(path):
        m = re.match(r"#### Paired effect against the base \(`([\w+]+)`\)", line)
        if m:
            base = m.group(1); continue
        m = re.match(r"\| ([\w+]+) \| ([^|]+) \| ([-+]?\d+\.\d) \[([-+]?\d+\.\d), ([-+]?\d+\.\d)\] \| (\d+) / (\d+) / (\d+) \| ([\d.]+) \| (\d+) \|", line)
        if m and base:
            out[m.group(1) + "-" + base] = {"finding": m.group(2).strip(), "eff": float(m.group(3)), "lo": float(m.group(4)),
                "hi": float(m.group(5)), "better": int(m.group(6)), "worse": int(m.group(7)), "same": int(m.group(8)),
                "p": float(m.group(9)), "n": int(m.group(10))}
    return out
e_eff = {**parse_plus(os.path.join(M3E, "vs_luna_attempted67.md")), **parse_plus(os.path.join(M3E, "harness_opus_attempted67.md"))}
e_eff63 = {**parse_plus(os.path.join(M3E, "vs_luna_attempted63.md")), **parse_plus(os.path.join(M3E, "harness_opus_attempted63.md"))}
E_KEYS = {"model": "LG+Opus-LG+luna", "harness": "CC+Opus-LG+Opus", "total": "CC+Opus-LG+luna"}
def paired_ids(arm, base, ids):
    d = [arm["_rate"][p] - base["_rate"][p] for p in ids]
    b, w = sum(1 for x in d if x > 0), sum(1 for x in d if x < 0)
    return (round(100 * sum(d) / len(d), 1), b, w, len(d) - b - w)
e_chk = {"model": paired_ids(e_arms["opus"], e_arms["luna"], E_ATT), "harness": paired_ids(e_arms["cc"], e_arms["opus"], E_ATT),
         "total": paired_ids(e_arms["cc"], e_arms["luna"], E_ATT)}
e_chk63 = {"model": paired_ids(e_arms["opus"], e_arms["luna"], E_ATT63), "harness": paired_ids(e_arms["cc"], e_arms["opus"], E_ATT63)}
e_opus_rows = [x for x in e_all if x["id"] in set(E_ATT)]
e_luna_rows = [x for _, _, r in restrict(d_runs["A"], E_ATT) for x in r]
e_nosc = {"opus": round(100 * sum(1 for x in e_opus_rows if int(x["selfcheck_runs"] or 0) == 0) / len(e_opus_rows)),
          "luna": round(100 * sum(1 for x in e_luna_rows if int(x["selfcheck_runs"] or 0) == 0) / len(e_luna_rows))}
e_smoke = round(sum(float(x["cost_usd"] or 0) for f in sorted(glob.glob(os.path.join(M3E, "smoke", "*.csv"))) for x in rows(f)), 4)
e_scored = round(sum(float(x["cost_usd"] or 0) for x in e_all), 4)
e_refused = sum(1 for x in e_all if x["stop_reason"] == "run_budget_exhausted")
rep3e = open(os.path.join(REP, "M3e_report.md")).read()
m3e = {"arms": {a: public(v) for a, v in e_arms.items()}, "effects": {k: e_eff[v] for k, v in E_KEYS.items()},
       "effects63": {k: e_eff63[E_KEYS[k]] for k in ("model", "harness")}, "n": len(E_ATT), "n63": len(E_ATT63),
       "refused": e_refused, "nosc": e_nosc, "cost_scored": e_scored, "cost_smoke": e_smoke,
       "solved_x": round(e_arms["opus"]["usd_solved"] / e_arms["luna"]["usd_solved"])}
# brief 14b: the full 86-problem LG+Opus arm, merged from three dispatches (m3e/full86/; raw finishing runs in m3e/finish/)
E_RUNS86 = ["41040802008", "41095517652", "41097171384"]
e86_all = rows(os.path.join(M3E, "full86", "LG_opus_" + "+".join(E_RUNS86) + ".csv"))
e_fin = {os.path.basename(f)[8:-4]: rows(f) for f in sorted(glob.glob(os.path.join(M3E, "finish", "LG_opus_*.csv")))}
e_finish = round(sum(float(x["cost_usd"] or 0) for r in e_fin.values() for x in r), 4)
e86_arms = {
    "luna": pool(restrict(d_runs["A"], EVAL)),
    "opus": pool([("LG", "+".join(E_RUNS86), e86_all)]),
    "cc": pool(restrict([("1", "claude-opus-5-5", rows(os.path.join(REP, "claude_code", "runs", "claude-opus-5-5.csv")))], EVAL)),
}
e86_eff = {**parse_plus(os.path.join(M3E, "vs_luna_eval86.md")), **parse_plus(os.path.join(M3E, "harness_opus_eval86.md"))}
e79_eff = {**parse_plus(os.path.join(M3E, "vs_luna_eval79.md")), **parse_plus(os.path.join(M3E, "harness_opus_eval79.md"))}
e86_chk = {"model": paired_ids(e86_arms["opus"], e86_arms["luna"], EVAL), "harness": paired_ids(e86_arms["cc"], e86_arms["opus"], EVAL),
           "total": paired_ids(e86_arms["cc"], e86_arms["luna"], EVAL)}
e79_chk = {k: paired_ids(*{"model": (e86_arms["opus"], e86_arms["luna"]), "harness": (e86_arms["cc"], e86_arms["opus"]),
                           "total": (e86_arms["cc"], e86_arms["luna"])}[k], EVAL79) for k in E_KEYS}
e_tail = {a: sum(int(e86_arms[a]["_rate"][p]) for p in E_REF) for a in ("opus", "cc")}
e86_nosc = round(100 * sum(1 for x in e86_all if int(x["selfcheck_runs"] or 0) == 0) / len(e86_all))
m3e["full"] = {"arms": {a: public(v) for a, v in e86_arms.items()}, "effects": {k: e86_eff[v] for k, v in E_KEYS.items()},
               "effects79": {k: e79_eff[v] for k, v in E_KEYS.items()}, "n": len(EVAL), "n79": len(EVAL79), "runs": E_RUNS86,
               "cost_finish": e_finish, "tail": e_tail, "nosc": e86_nosc,
               "solved_x": round(e86_arms["opus"]["usd_solved"] / e86_arms["luna"]["usd_solved"])}

# ---- M3g: a frozen knowledge pack loaded as skills, K against A (docs/reports/M3g_report.md, m3g/) ----
# Only aggregates leave this block: no held-out problem id, text or test reaches the page or the data block.
M3G = os.path.join(REP, "m3g")
G_HO = ids_file(os.path.join(ROOT, "tools", "m3g_heldout_ids.txt"))
g_hdr = [l[1:].strip() for l in open(os.path.join(ROOT, "tools", "m3g_heldout_ids.txt")) if l.startswith("#")]
g_hdrs = "\n".join(g_hdr)
g_set = {
    "file": re.search(r"source: [^,]+, (\S+\.jsonl)", g_hdrs).group(1),
    "rev": re.search(r"revision: ([0-9a-f]{7})", g_hdrs).group(1),
    "seed": re.search(r"random\.Random\((\d+)\)", g_hdrs).group(1),
    "eligible": int(re.search(r"eligible: (\d+)", g_hdrs).group(1)),
    "of": int(re.search(r"excluded from (\d+)", g_hdrs).group(1)),
    "cid": {c: int(n) for c, n in re.findall(r"(cid00\d) \([^)]*\) (\d+)", g_hdrs)},
}
def g_load(stem):
    out = []
    for f in sorted(glob.glob(os.path.join(M3G, "runs", stem + "*.csv"))):
        tag, run_id = os.path.basename(f)[:-4].rsplit("_", 1)
        out.append((tag.split("_")[1], run_id, rows(f)))
    return out
g_runs = {"hA": g_load("heldout_A"), "hK": g_load("heldout_K"), "dK": g_load("dev_K"), "dA": d_runs["A"]}
g_arms = {k: pool(v) for k, v in g_runs.items()}
g_rows = {k: [x for _, _, r in v for x in r] for k, v in g_runs.items()}
g_eff = {"ho": parse_sections(os.path.join(M3G, "heldout_paired.md"))["K-A"],
         "d86": parse_sections(os.path.join(M3G, "dev_paired_eval86.md"))["K-A"],
         "d79": parse_sections(os.path.join(M3G, "dev_paired_eval79.md"))["K-A"]}
g_chk = {"ho": paired_ids(g_arms["hK"], g_arms["hA"], G_HO), "d86": paired_ids(g_arms["dK"], g_arms["dA"], EVAL),
         "d79": paired_ids(g_arms["dK"], g_arms["dA"], EVAL79)}
def g_r79(k):
    r = [x for x in g_rows[k] if x["id"] in EVAL79]
    return round(100 * sum(int(x["pass"]) for x in r) / len(r), 1)
Krows = g_rows["hK"] + g_rows["dK"]
g_sk = {}
for k in ("hK", "dK"):
    for x in g_rows[k]:
        for s in x["skills_loaded"].split("+"):
            if s:
                g_sk.setdefault(s, {"hK": 0, "dK": 0})[k] += 1
g_cfg = open(os.path.join(ROOT, "agent", "cvdp_agent", "config.py")).read()
g_pack = os.path.join(ROOT, "agent", "cvdp_agent", "skills", "rtl_pack")
def g_mean(k, col):
    return sum(int(x[col] or 0) for x in g_rows[k]) / len(g_rows[k])
def g_sc(k):
    return round(100 * sum(1 for x in g_rows[k] if int(x["selfcheck_runs"] or 0) > 0) / len(g_rows[k]), 1)
def g_iface(k):
    return g_arms[k]["labels"].get("compile_fail_hidden", 0) + g_arms[k]["labels"].get("signal_missing_hidden", 0)
g_smoke = round(sum(float(x["cost_usd"] or 0) for f in sorted(glob.glob(os.path.join(M3G, "smoke", "*.csv"))) for x in rows(f)), 4)
g_scored = round(sum(a["cost"] for k, a in g_arms.items() if k != "dA"), 4)
m3g = {
    "arms": {k: public(v) for k, v in g_arms.items()}, "effects": g_eff, "set": g_set, "n_ho": len(G_HO), "n": len(EVAL), "n79": len(EVAL79),
    "r79": {k: g_r79(k) for k in ("dA", "dK")},
    "loaded": sum(1 for x in Krows if x["skills_status"] == "loaded"), "k_rows": len(Krows),
    "skills": dict(sorted(g_sk.items(), key=lambda kv: -(kv[1]["hK"] + kv[1]["dK"]))),
    "unknown": sum(len([u for u in x["skills_unknown"].split("+") if u]) for x in Krows),
    "truncated": sum(1 for x in Krows if int(x["skills_truncated"] or 0) > 0),
    "bytes_mean": {k: round(g_mean(k, "skills_bytes")) for k in ("hK", "dK")}, "bytes_max": max(int(x["skills_bytes"] or 0) for x in Krows),
    "ptok": {k: round(g_mean(k, "prompt_tokens")) for k in g_rows}, "sc": {k: g_sc(k) for k in g_rows},
    "iface": {k: g_iface(k) for k in g_rows},
    "max_skills": int(re.search(r"skills_max: int = (\d+)", g_cfg).group(1)),
    "cap_bytes": int(re.search(r"skills_cap_bytes: int = ([\d_]+)", g_cfg).group(1).replace("_", "")),
    "pack_n": len([f for f in os.listdir(g_pack) if f.endswith(".md") and f not in ("INDEX.md", "PROVENANCE.md")]),
    "pack_sha": sorted({x["skills_pack"] for x in Krows}),
    "cost_scored": g_scored, "cost_smoke": g_smoke,
}
m3g["ptok_x"] = {s: round(100 * (m3g["ptok"][s + "K"] / m3g["ptok"][s + "A"] - 1)) for s in "hd"}
m3g["money_x"] = round(100 * (g_arms["hK"]["cost"] / g_arms["hA"]["cost"] - 1))

# ---- M3h (the pack as Claude Code's own skills) and M3i (Claude Code stripped to our prompt and four tools) ----
# docs/reports/M3h_report.md, m3h/ and M3i_report.md, m3i/. Prefixes h_ and i_. Names and counts only: no skill text, and
# no held-out id, text or test, reaches the page or the data block. Both ran on the Max plan: nothing is billed per call.
M3H = os.path.join(REP, "m3h")
M3I = os.path.join(REP, "m3i")
def hi_load(base, stem):
    out = []
    for f in sorted(glob.glob(os.path.join(base, "runs", stem + "*.csv"))):
        tag, run_id = os.path.basename(f)[:-4].rsplit("_", 1)
        out.append((tag.split("_")[1], run_id, rows(f)))
    return out
H_RUNS = {"hA": hi_load(M3H, "heldout_A"), "hS1": hi_load(M3H, "heldout_S1c"), "hS2": hi_load(M3H, "heldout_S2c"),
          "hS2n": hi_load(M3H, "heldout_S2_"), "hP": hi_load(M3I, "heldout_P"),
          "dA": restrict(hi_load(M3H, "dev86_A_"), EVAL), "dS1": restrict(hi_load(M3H, "dev86_S1c_"), EVAL),
          "dS2": restrict(hi_load(M3H, "dev86_S2c_"), EVAL), "dP": restrict(hi_load(M3I, "dev86_P_"), EVAL)}
h_arms = {k: pool(v) for k, v in H_RUNS.items()}
h_rows = {k: [x for _, _, r in v for x in r] for k, v in H_RUNS.items()}
def h_eff(path, key):
    return parse_sections(path)[key]
h_effects = {
    "ho": h_eff(os.path.join(M3H, "heldout_paired.md"), "S2c-A"), "ho_s1": h_eff(os.path.join(M3H, "heldout_paired.md"), "S1c-A"),
    "ho_s2s1": h_eff(os.path.join(M3H, "heldout_paired_S2c_S1c.md"), "S2c-S1c"),
    "d86": h_eff(os.path.join(M3H, "dev86_paired.md"), "S2c-A"), "d86_s1": h_eff(os.path.join(M3H, "dev86_paired.md"), "S1c-A"),
    "d86_s2s1": h_eff(os.path.join(M3H, "dev86_paired_S2c_S1c.md"), "S2c-S1c"),
    "d79": h_eff(os.path.join(M3H, "dev79_paired.md"), "S2c-A"), "d79_s1": h_eff(os.path.join(M3H, "dev79_paired.md"), "S1c-A"),
}
h_chk = {"ho": paired_ids(h_arms["hS2"], h_arms["hA"], G_HO), "ho_s1": paired_ids(h_arms["hS1"], h_arms["hA"], G_HO),
         "ho_s2s1": paired_ids(h_arms["hS2"], h_arms["hS1"], G_HO),
         "d86": paired_ids(h_arms["dS2"], h_arms["dA"], EVAL), "d86_s1": paired_ids(h_arms["dS1"], h_arms["dA"], EVAL),
         "d86_s2s1": paired_ids(h_arms["dS2"], h_arms["dS1"], EVAL),
         "d79": paired_ids(h_arms["dS2"], h_arms["dA"], EVAL79), "d79_s1": paired_ids(h_arms["dS1"], h_arms["dA"], EVAL79)}
i_effects = {"ho": h_eff(os.path.join(M3I, "heldout_paired.md"), "P-D"), "d86": h_eff(os.path.join(M3I, "dev86_paired.md"), "P-D"),
             "d79": h_eff(os.path.join(M3I, "dev79_paired.md"), "P-D")}
i_chk = {"ho": paired_ids(h_arms["hP"], h_arms["hA"], G_HO), "d86": paired_ids(h_arms["dP"], h_arms["dA"], EVAL),
         "d79": paired_ids(h_arms["dP"], h_arms["dA"], EVAL79)}
def h_med(k, col):
    return statistics.median(float(x[col]) for x in h_rows[k])
def h_mean(k, col):
    return sum(float(x[col] or 0) for x in h_rows[k]) / len(h_rows[k])
def h_ptok(k):
    return h_mean(k, "prompt_tokens")
def h_loaded(k):
    return sum(1 for x in h_rows[k] if int(x.get("skills_n") or 0) > 0)
m3h = {
    "effects": h_effects, "n_ho": len(G_HO), "n": len(EVAL), "n79": len(EVAL79),
    "arms": {k: {"k": v["k"], "n": v["n"], "rate": v["rate"]} for k, v in h_arms.items()},
    "loaded": {k: h_loaded(k) for k in ("hS1", "hS2", "hS2n", "dS1", "dS2")},
    "turns_med": {k: h_med(k, "turns") for k in ("hA", "hS1", "hS2", "dA", "dS1", "dS2")},
    "ptok": {k: round(h_ptok(k)) for k in ("hA", "hS1", "hS2", "dA", "dS1", "dS2")},
    "pack_s2": 25, "pack_s1": 15,
}
m3i = {
    "effects": i_effects, "n_ho": len(G_HO), "n": len(EVAL), "n79": len(EVAL79),
    "arms": {k: {"k": h_arms[k]["k"], "n": h_arms[k]["n"], "rate": h_arms[k]["rate"]} for k in ("hA", "hP", "dA", "dP")},
    "turns_med": {k: h_med(k, "turns") for k in ("hA", "hP", "dA", "dP")},
    "ptok": {k: round(h_ptok(k)) for k in ("hA", "hP", "dA", "dP")},
    "wall_med": {k: round(h_med(k, "wall_time_s")) for k in ("hA", "hP", "dA", "dP")},
    "tools": sorted({x["cc_tools"] for k in ("hP", "dP") for x in h_rows[k]}),
    "skills_mcp": sorted({(x["cc_skills_n"], x["cc_mcp_n"]) for k in ("hP", "dP") for x in h_rows[k]}),
}

# ---- M3j (lean Claude Code against a plain API loop, billed to the API key) ----
# docs/reports/M3j_report.md and m3j/. Prefix j_. PA, B and R from M3j; P and D from M3i/M3h above (hP, hA, dP, dA).
# Held-out seeds 1-2 and 3 are separate dispatches; R's 86 run is m3h_merge.py's merge of its first run and the rerun.
M3J = os.path.join(REP, "m3j")
J_RUNS = {"hPA": hi_load(M3J, "heldout_PA"), "hB": hi_load(M3J, "heldout_B"), "hR": hi_load(M3J, "heldout_R"),
          "dPA": restrict(hi_load(M3J, "dev86_PA_"), EVAL), "dB": restrict(hi_load(M3J, "dev86_B_"), EVAL),
          "dR": restrict(hi_load(M3J, "dev86_R_merged"), EVAL)}
j_arms = {k: pool(v) for k, v in J_RUNS.items()}
j_rows = {k: [x for _, _, r in v for x in r] for k, v in J_RUNS.items()}
# cost covers every row the sweeps ran: the 86-problem dispatches ran all 92 agentic problems
j_rows.update({"cdPA": [x for _, _, r in hi_load(M3J, "dev86_PA_") for x in r], "cdB": [x for _, _, r in hi_load(M3J, "dev86_B_") for x in r],
               "cdR": [x for _, _, r in hi_load(M3J, "dev86_R_merged") for x in r]})
j_ho = parse_sections(os.path.join(M3J, "heldout_paired.md"))
j_effects = {"ho": j_ho["R-PA"], "ho_b": j_ho["B-PA"],
             "ho_pap": parse_sections(os.path.join(M3J, "heldout_PA_vs_P.md"))["PA-P"],
             "ho_rd": parse_sections(os.path.join(M3J, "heldout_R_vs_D.md"))["R-D"],
             "d86": parse_sections(os.path.join(M3J, "dev86_paired.md"))["R-PA"],
             "d86_b": parse_sections(os.path.join(M3J, "dev86_paired.md"))["B-PA"]}
j_chk = {"ho": paired_ids(j_arms["hR"], j_arms["hPA"], G_HO), "ho_b": paired_ids(j_arms["hB"], j_arms["hPA"], G_HO),
         "ho_pap": paired_ids(j_arms["hPA"], h_arms["hP"], G_HO), "ho_rd": paired_ids(j_arms["hR"], h_arms["hA"], G_HO),
         "d86": paired_ids(j_arms["dR"], j_arms["dPA"], EVAL), "d86_b": paired_ids(j_arms["dB"], j_arms["dPA"], EVAL)}
def j_mean(k, col):
    return sum(float(x[col] or 0) for x in j_rows[k]) / len(j_rows[k])
def j_sum(k, col):
    return sum(float(x[col] or 0) for x in j_rows[k])
def j_list_usd(k):
    """R's cost from its tokens at Claude Haiku 5.5's list rates under 100K tokens per request: fresh input $0.10/M,
    cache read $0.01/M, cache write $0.125/M, output $0.50/M (the report's Cost section)."""
    cr, cw, pt = j_sum(k, "cache_read_tokens"), j_sum(k, "cache_write_tokens"), j_sum(k, "prompt_tokens")
    return ((pt - cr - cw) * 0.10 + cr * 0.01 + cw * 0.125 + j_sum(k, "completion_tokens") * 0.50) / 1e6
m3j = {
    "effects": j_effects, "n_ho": len(G_HO), "n": len(EVAL),
    "arms": {k: {"k": v["k"], "n": v["n"], "rate": v["rate"]} for k, v in j_arms.items()},
    "turns_med": {k: statistics.median(float(x["turns"]) for x in j_rows[k]) for k in ("hPA", "hB", "hR")},
    "ptok": {k: round(j_mean(k, "prompt_tokens")) for k in ("hPA", "hB", "hR")},
    "usd": {"hPA": round(j_sum("hPA", "plan_cost_estimate_usd"), 2), "hB": round(j_sum("hB", "plan_cost_estimate_usd"), 2),
            "hR": round(j_list_usd("hR"), 2), "dPA": round(j_sum("cdPA", "plan_cost_estimate_usd"), 2),
            "dB": round(j_sum("cdB", "plan_cost_estimate_usd"), 2), "dR": round(j_list_usd("cdR"), 2)},
    "key_source": sorted({x["cc_api_key_source"] for k in ("hPA", "hB", "dPA", "dB") for x in j_rows[k]}),
    "tools_b": sorted({x["cc_tools"] for k in ("hB", "dB") for x in j_rows[k]}),
    "console_usd": 7.83, "console_before_usd": 0.57,
}

# ---- M3k (a timing-claims turn T and an exploratory pre-submit check K on the plain API loop; R reused from M3j) ----
# docs/reports/M3k_report.md and m3k/. Prefix k_. R is M3j's arm R (J_RUNS hR, dR). The 86's llm_error rows are not run.
M3K = os.path.join(REP, "m3k")
K_RUNS = {"hR": J_RUNS["hR"], "hT": hi_load(M3K, "heldout_T"), "hK": hi_load(M3K, "heldout_K"),
          "dR": J_RUNS["dR"], "dT": restrict(hi_load(M3K, "dev86_T_"), EVAL), "dK": restrict(hi_load(M3K, "dev86_K_"), EVAL)}
k_arms = {k: pool(v) for k, v in K_RUNS.items()}
k_rows = {k: [x for _, _, r in v for x in r] for k, v in K_RUNS.items()}
k_rows.update({"cdT": [x for _, _, r in hi_load(M3K, "dev86_T_") for x in r], "cdK": [x for _, _, r in hi_load(M3K, "dev86_K_") for x in r]})
k_ho = parse_sections(os.path.join(M3K, "heldout_paired.md"))
k_d86 = parse_sections(os.path.join(M3K, "dev86_paired.md"))
k_effects = {"ho_t": k_ho["T-R"], "ho_k": k_ho["K-R"], "d86_t": k_d86["T-R"], "d86_k": k_d86["K-R"]}
k_chk = {"ho_t": paired_ids(k_arms["hT"], k_arms["hR"], G_HO), "ho_k": paired_ids(k_arms["hK"], k_arms["hR"], G_HO),
         "d86_t": paired_ids(k_arms["dT"], k_arms["dR"], EVAL), "d86_k": paired_ids(k_arms["dK"], k_arms["dR"], EVAL)}
def k_mean(k, col):
    return sum(float(x[col] or 0) for x in k_rows[k]) / len(k_rows[k])
k_fired = [x for x in k_rows["hK"] if x["presubmit_rounds"] not in ("", "0")]
k_fired_ids = {x["id"] for x in k_fired}
# the problems where K and R differ, and how many of them are ones where K's check fired
k_diff = [i for i in G_HO if k_arms["hK"]["_rate"][i] != k_arms["hR"]["_rate"][i]]
m3k = {
    "effects": k_effects, "n_ho": len(G_HO), "n": len(EVAL),
    "arms": {k: {"k": v["k"], "n": v["n"], "rate": v["rate"]} for k, v in k_arms.items()},
    "turns_med": {k: statistics.median(float(x["turns"]) for x in k_rows[k]) for k in ("hR", "hT", "hK")},
    "ptok": {k: round(k_mean(k, "prompt_tokens")) for k in ("hR", "hT", "hK")},
    "wall_med": {k: round(statistics.median(float(x["wall_time_s"]) for x in k_rows[k])) for k in ("hR", "hT", "hK")},
    "fired_n": len(k_fired), "fired_problems": len(k_fired_ids), "fired_pass": sum(int(x["pass"]) for x in k_fired),
    "fired_cleared": sum(1 for x in k_fired if x["presubmit_final_findings_n"] == "0"),
    "fired_net": sum(k_arms["hK"]["_rate"][i] - k_arms["hR"]["_rate"][i] for i in k_fired_ids),
    "diff_n": len(k_diff), "diff_fired": sum(1 for i in k_diff if i in k_fired_ids),
    "usd": {"hT": round(sum(float(x["api_cost_estimate_usd"] or 0) for x in k_rows["hT"]), 2),
            "hK": round(sum(float(x["api_cost_estimate_usd"] or 0) for x in k_rows["hK"]), 2),
            "dT": round(sum(float(x["api_cost_estimate_usd"] or 0) for x in k_rows["cdT"]), 2),
            "dK": round(sum(float(x["api_cost_estimate_usd"] or 0) for x in k_rows["cdK"]), 2)},
    "llm_error": sum(1 for k in ("cdT", "cdK") for x in k_rows[k] if x["stop_reason"] == "llm_error"),
    "claims_med": statistics.median(float(x["timing_claims_n"]) for x in k_rows["hT"]),
}

# ---- M3l (retrieved real-RTL examples E against a fresh R, on the 16 problems that get an example) ----
# docs/reports/M3l_report.md and m3l/. Prefix l_. The one pre-registered comparison (2026-11-09 amendment) is E - R over the 16.
M3L = os.path.join(REP, "m3l")
L_IDS16 = ids_file(os.path.join(M3L, "ids16.txt"))
L_HO_IDS = ids_file(os.path.join(ROOT, "tools", "m3l_fires_heldout_ids.txt"))
def l_load(stem):
    return [x for f in sorted(glob.glob(os.path.join(M3L, "runs", stem + "_*.csv"))) for x in rows(f) if x["id"] in set(L_IDS16)]
l_rows = {"E": l_load("dev_E") + l_load("heldout_E"), "R": l_load("dev_R") + l_load("heldout_R")}
l_rate = {a: {i: sum(int(x["pass"]) for x in v if x["id"] == i) / sum(1 for x in v if x["id"] == i) for i in L_IDS16} for a, v in l_rows.items()}
l_eff = parse_sections(os.path.join(M3L, "paired16.md"))["E-R"]
l_eff15 = parse_sections(os.path.join(M3L, "paired15.md"))["E-R"]
l_d = [l_rate["E"][i] - l_rate["R"][i] for i in L_IDS16]
l_chk = (round(100 * sum(l_d) / len(l_d), 1), sum(1 for d in l_d if d > 0), sum(1 for d in l_d if d < 0), sum(1 for d in l_d if d == 0))
l_pp = [{"id": i, "set": "held-out" if i in set(L_HO_IDS) else "dev",
         "R": sum(int(x["pass"]) for x in l_rows["R"] if x["id"] == i), "E": sum(int(x["pass"]) for x in l_rows["E"] if x["id"] == i),
         "n": sum(1 for x in l_rows["E"] if x["id"] == i),
         "ex": sorted({e for x in l_rows["E"] if x["id"] == i for e in x["examples_ids"].split(";") if e})} for i in sorted(L_IDS16)]
l_ret = list(csv.DictReader(open(os.path.join(M3L, "retrieval.csv"))))
l_cov = {s: [sum(1 for r in l_ret if r["set"] == s and int(r["n"]) > 0), sum(1 for r in l_ret if r["set"] == s)] for s in ("heldout100", "dev86")}
m3l = {
    "effect": l_eff, "effect15": l_eff15, "n": len(L_IDS16),
    "arms": {a: {"k": sum(int(x["pass"]) for x in v), "n": len(v), "rate": round(100 * sum(int(x["pass"]) for x in v) / len(v), 1)} for a, v in l_rows.items()},
    "per_problem": l_pp, "cov": l_cov, "pool_kept": 37, "pool": 86,
    "ptok_M": {a: round(sum(float(x["prompt_tokens"] or 0) for x in v) / 1e6, 2) for a, v in l_rows.items()},
    "usd": {a: round(sum(float(x["api_cost_estimate_usd"] or 0) for x in v), 2) for a, v in l_rows.items()},
    "llm_error": sum(1 for x in l_rows["E"] if x["stop_reason"] == "llm_error"),
    "overlap_withheld": sum(int(x["examples_withheld_overlap"] or 0) for x in l_rows["E"]),
    "same_5_5": sum(1 for q in l_pp if q["R"] == q["n"] and q["E"] == q["n"]),
    "split": {st: {"R": sum(q["R"] for q in l_pp if q["set"] == st), "E": sum(q["E"] for q in l_pp if q["set"] == st),
                   "n": sum(q["n"] for q in l_pp if q["set"] == st)} for st in ("held-out", "dev")},
}

spend_all = round(spend_all + conf_cost + m3c_scored + m3c_smoke + m3d_scored + m3d_smoke + e_scored + e_smoke + e_finish + g_scored + g_smoke, 2)  # + confirming run, M3c, M3d, M3e (with brief 14b's two) and M3g scored sweeps and smoke runs

# Prose numbers in story.html: <span data-d="key">value</span>; --inject rewrites the value from here.
MINUS = "−"
def sg(x, d=1):
    return ("+" if x > 0 else MINUS if x < 0 else "+") + f"{abs(x):.{d}f}"
def p2(p):
    """Two significant figures, half up, as the report prints them (0.815 -> 0.82)."""
    from decimal import Decimal, ROUND_HALF_UP
    q = Decimal(str(p))
    return str(q.quantize(Decimal("0.01") if p >= 0.1 else Decimal("0.001"), rounding=ROUND_HALF_UP))
def ci(e):
    return f"[{sg(e['lo'])}, {sg(e['hi'])}]"
prose = {
    "spend_all": f"{spend_all:,.2f}",
    "m3b_n": str(len(EVAL)), "m3b_runs_arm": str(len(m3b_files["A"])),
    "m3b_pr_arm": str(mA["n"]), "m3b_pr_all": f"{sum(a['n'] for a in m3b_arms.values()):,}",
    "m3b_scored": f"{m3b_scored:.2f}", "m3b_learn": f"{m3b_learn:.2f}", "m3b_total": f"{m3b_total:.2f}",
    "bonf": f"{BONF:.4f}",
    "floor_eff": sg(m3b_floor["eff"]), "floor_ci": ci(m3b_floor),
    "f20_eff": sg(m3b_f20["eff"]), "f20_ci": ci(m3b_f20),
    "les_n": str(len(snap["lessons"])), "les_att": str(snap["provenance"]["attempts"]),
    "les_pass": str(snap["provenance"]["passed"]), "les_never": str(sum(1 for k in retr if retr[k][0] == 0)),
    "les_never_ids": ", ".join(sorted(k for k in retr if retr[k][0] == 0)),
    "les_cost": f"{snap['provenance']['cost_usd']:.4f}", "les_problems": str(snap["provenance"]["problems"]),
    "les_hash": snap["hash"],
    "tok_A": f"{mA['tokens'] / 1e6:.1f}", "tok_B": f"{mB['tokens'] / 1e6:.1f}",
    "ptok_A": f"{mA['prompt_tokens'] / 1e6:.1f}", "ptok_B": f"{mB['prompt_tokens'] / 1e6:.1f}",
    "tok_x": f"{mB['tokens'] / mA['tokens']:.0f}", "ptok_x": f"{mB['prompt_tokens'] / mA['prompt_tokens']:.0f}",
    "mp_A": f"{mA['usd_per_mprompt']:.3f}", "mp_B": f"{mB['usd_per_mprompt']:.3f}",
    "upp_lo": f"{min(a['usd_problem'] for a in m3b_arms.values()):.4f}",
    "upp_hi": f"{max(a['usd_problem'] for a in m3b_arms.values()):.4f}",
}
for key, e in m3b_eff.items():
    if key in M3B_ROLE:
        k = key.replace("-", "")
        prose[f"e_{k}"] = sg(e["eff"]); prose[f"ci_{k}"] = ci(e); prose[f"p_{k}"] = p2(e["p"])
        prose[f"bws_{k}"] = f"{e['better']} / {e['worse']} / {e['same']}"
for a, v in m3b_arms.items():
    prose[f"rate_{a}"] = f"{v['rate']:.1f}"; prose[f"k_{a}"] = str(v["k"]); prose[f"us_{a}"] = f"{v['usd_solved']:.4f}"
    prose[f"cap_{a}"] = str(v["labels"].get("stopped_by_cap", 0)); prose[f"nst_{a}"] = str(v["labels"].get("tests_failed_no_selfcheck", 0))
    prose[f"stp_{a}"] = str(v["labels"].get("tests_failed_selfcheck_passed", 0))
    prose[f"capall_{a}"] = str(v["cap_stops"]); prose[f"cappass_{a}"] = str(v["cap_stops_passed"])
    prose[f"runs_{a}"] = ", ".join(str(r["k"]) for r in v["runs"])
def rng(lab):
    v = sorted(a["labels"].get(lab, 0) for a in m3b_arms.values())
    return f"{v[0]}\u2013{v[-1]}" if v[0] != v[-1] else str(v[0])
prose["cfh_range"], prose["smh_range"] = rng("compile_fail_hidden"), rng("signal_missing_hidden")
for t in m3b["lessons"]["top"]:
    prose[f"top_{t['id']}"] = str(t["count"])
# confirming run, M3c and the Claude Code ladder
def put_eff(pre, e):
    prose[f"{pre}e"] = sg(e["eff"]); prose[f"{pre}ci"] = ci(e); prose[f"{pre}p"] = p2(e["p"])
    prose[f"{pre}bws"] = f"{e['better']} / {e['worse']} / {e['same']}"
put_eff("cf_", conf_eff)
prose["cf_runs"] = str(len(conf_runs["A"])); prose["cf_n"] = str(conf["A"]["n"])
prose["cf_seeds"] = f"{conf_seeds[0]} to {conf_seeds[-1]}"; prose["cf_cost"] = f"{conf_cost:.2f}"
prose["cf_verdict"] = conf_verdict.upper(); prose["cf_unrep"] = str(sum(a["unreported"] for a in conf.values()))
for a, v in conf.items():
    prose[f"cf_rate_{a}"] = f"{v['rate']:.1f}"; prose[f"cf_k_{a}"] = str(v["k"]); prose[f"cf_us_{a}"] = f"{v['usd_solved']:.4f}"
    prose[f"cf_nst_{a}"] = str(v["labels"].get("tests_failed_no_selfcheck", 0)); prose[f"cf_cap_{a}"] = str(v["turn_cap"])
    prose[f"cf_wall_{a}"] = str(v["wall_med"])
for key in ("M-A", "I-A"):
    put_eff("c_" + key.replace("-", "") + "_", m3c_eff[key])
prose["c_runs_arm"] = str(len(c_runs["A"])); prose["c_pr_arm"] = str(m3c_arms["A"]["n"])
for a, v in m3c_arms.items():
    prose[f"c_rate_{a}"] = f"{v['rate']:.1f}"; prose[f"c_k_{a}"] = str(v["k"]); prose[f"c_us_{a}"] = f"{v['usd_solved']:.4f}"
    prose[f"c_wall_{a}"] = str(v["wall_med"]); prose[f"c_fails_{a}"] = str(v["fails"])
    for lab, short_ in (("tests_failed_no_selfcheck", "nst"), ("tests_failed_selfcheck_passed", "stp"), ("stopped_by_cap", "cap")):
        prose[f"c_{short_}_{a}"] = str(v["labels"].get(lab, 0))
    prose[f"c_iface_{a}"] = str(v["labels"].get("compile_fail_hidden", 0) + v["labels"].get("signal_missing_hidden", 0))
prose["c_solved_x"] = f"{m3c['solved_x']:.1f}"; prose["c_scored"] = f"{m3c_scored:.2f}"
prose["c_unrep"] = str(sum(a["unreported"] for a in m3c_arms.values()))
prose["g_runs"] = str(gate["runs"]); prose["g_pr"] = str(gate["problem_runs"])
prose["g_skip"] = str(gate["outcomes"].get("skipped", 0)); prose["g_skip_pct"] = f"{100 * gate['outcomes'].get('skipped', 0) / gate['runs']:.0f}"
prose["g_skip_probs"] = str(gate["skipped_problems"]); prose["g_notb"] = str(gate["outcomes"].get("no_tb", 0))
prose["g_kill"] = f"{gate['kill_rate']:.0f}"; prose["g_killed"] = f"{gate['killed']:,}"; prose["g_compiled"] = f"{gate['compiled']:,}"
prose["i_checks"] = str(iface["checks"]); prose["i_mm"] = str(iface["mismatch_checks"]); prose["i_pr"] = str(iface["mismatch_pr"])
prose["i_pr_pass"] = str(iface["mismatch_pr_passed"]); prose["i_blocks"] = str(iface["blocks"])
for k, z in ladder.items():
    put_eff(f"l_{k}_", z["effect"])
    prose[f"l_rate_{k}"] = f"{z['rate']:.1f}"; prose[f"l_k_{k}"] = str(z["k"]); prose[f"l_wall_{k}"] = str(z["wall_med"])
prose["l_wcap_fable"] = str(ladder["fable"]["wall_cap"]); prose["l_wcapf_fable"] = str(ladder["fable"]["wall_cap_failed"])
prose["l_union"] = str(lad_union); prose["l_all"] = str(lad_all)
# the unsolved-problems analysis
prose["u_n"] = str(unsolved["n"]); prose["u_neverA"] = str(unsolved["never_A"]); prose["u_blim"] = str(unsolved["blim"])
prose["u_n79"] = str(unsolved["n79"])
prose["u_border"] = str(unsolved["border"]); prose["u_env"] = str(unsolved["env"]); prose["u_agent"] = str(unsolved["agent"])
prose["u_p2"] = str(unsolved["p2"]); prose["u_p2_unt"] = str(unsolved["p2_untested"]); prose["u_p2_valid"] = str(unsolved["p2_valid"])
prose["u_tl_def"] = f"{unsolved['tl_defaults'][0]} and {unsolved['tl_defaults'][1]}"
prose["d_p2_A"], prose["d_p2_V"], prose["d_p2_S"] = (str(p2_pass[a]) for a in "AVS")
prose["d_p2_n"] = str(len(P2) * len(d_runs["A"]))
for k, (a, b) in u79.items():
    prose[f"u_k79_{k}"] = str(a); prose[f"u_n79_{k}"] = str(b); prose[f"u_r79_{k}"] = f"{unsolved['r79'][k]:.1f}"
# M3d
for key in ("V-A", "S-A"):
    put_eff("d_" + key.replace("-", "") + "_", m3d_eff[key])
    prose["d_" + key.replace("-", "") + "_e79"] = sg(m3d_eff79[key]["eff"]); prose["d_" + key.replace("-", "") + "_ci79"] = ci(m3d_eff79[key])
prose["d_runs_arm"] = str(len(d_runs["A"])); prose["d_pr_arm"] = str(m3d_arms["A"]["n"])
for a, v in m3d_arms.items():
    x = m3d_extra[a]
    prose[f"d_rate_{a}"] = f"{v['rate']:.1f}"; prose[f"d_k_{a}"] = str(v["k"]); prose[f"d_us_{a}"] = f"{v['usd_solved']:.4f}"
    prose[f"d_wall_{a}"] = str(v["wall_med"]); prose[f"d_fails_{a}"] = str(v["fails"])
    for lab, short_ in (("tests_failed_no_selfcheck", "nst"), ("tests_failed_selfcheck_passed", "stp"), ("stopped_by_cap", "cap"), ("llm_error", "lle")):
        prose[f"d_{short_}_{a}"] = str(v["labels"].get(lab, 0))
    prose[f"d_nosc_{a}"] = f"{100 * x['no_sc'] / v['n']:.0f}"; prose[f"d_1t_{a}"] = f"{100 * x['one_turn'] / v['n']:.0f}"
    prose[f"d_tmed_{a}"] = f"{x['turns_med']:.0f}"; prose[f"d_r79_{a}"] = f"{x['rate79']:.1f}"
for a in "VS":
    prose[f"d_sx_{a}"] = f"{m3d['solved_x'][a]:.1f}"; prose[f"d_ref_{a}"] = str(m3d_extra[a]["refused_rows"])
prose["d_sp_pass_k"] = str(spec_tab["pass"][0]); prose["d_sp_pass_n"] = str(sum(spec_tab["pass"]))
prose["d_sp_fail_k"] = str(spec_tab["fail"][0]); prose["d_sp_fail_n"] = str(sum(spec_tab["fail"]))
prose["d_sp_pass_pct"] = f"{100 * spec_tab['pass'][0] / sum(spec_tab['pass']):.0f}"
prose["d_sp_fail_pct"] = f"{100 * spec_tab['fail'][0] / sum(spec_tab['fail']):.0f}"
prose["d_sp_gen"] = str(spec_gen)
prose["d_guard"] = str(m3d_extra["S"]["guard"]); prose["d_guard_adj"] = sg(guard_adj)
prose["d_scored"] = f"{m3d_scored:.2f}"; prose["d_unrep"] = str(sum(a["unreported"] for a in m3d_arms.values()))
# M3e
for k, e in m3e["effects"].items():
    put_eff(f"e3_{k}_", e)
for k, e in m3e["effects63"].items():
    prose[f"e3_{k}_e63"] = sg(e["eff"]); prose[f"e3_{k}_ci63"] = ci(e)
for a, v in e_arms.items():
    prose[f"e3_rate_{a}"] = f"{v['rate']:.1f}"; prose[f"e3_k_{a}"] = str(v["k"]); prose[f"e3_n_{a}"] = str(v["n"])
prose["e3_n"] = str(m3e["n"]); prose["e3_n63"] = str(m3e["n63"]); prose["e3_refused"] = str(e_refused)
prose["e3_nosc_opus"] = str(e_nosc["opus"]); prose["e3_nosc_luna"] = str(e_nosc["luna"])
prose["e3_cost"] = f"{e_arms['opus']['cost']:.2f}"; prose["e3_upp"] = f"{e_arms['opus']['cost'] / e_arms['opus']['n']:.3f}"
prose["e3_ups"] = f"{e_arms['opus']['cost'] / e_arms['opus']['k']:.3f}"; prose["e3_us_luna"] = f"{e_arms['luna']['usd_solved']:.4f}"
prose["e3_sx"] = str(m3e["solved_x"]); prose["e3_smoke"] = f"{e_smoke:.2f}"; prose["e3_spend"] = f"{e_scored + e_smoke + e_finish:.2f}"
prose["e3_wall_opus"] = str(e_arms["opus"]["wall_med"]); prose["e3_wall_luna"] = str(e_arms["luna"]["wall_med"])
# M3e, all 86 problems (brief 14b's merged arm)
F3 = m3e["full"]
for k, e in F3["effects"].items():
    put_eff(f"e3f_{k}_", e)
for k, e in F3["effects79"].items():
    prose[f"e3f_{k}_e79"] = sg(e["eff"]); prose[f"e3f_{k}_ci79"] = ci(e)
for a, v in e86_arms.items():
    prose[f"e3f_rate_{a}"] = f"{v['rate']:.1f}"; prose[f"e3f_k_{a}"] = str(v["k"]); prose[f"e3f_n_{a}"] = str(v["n"])
prose["e3f_cost"] = f"{e86_arms['opus']['cost']:.2f}"; prose["e3f_upp"] = f"{e86_arms['opus']['cost'] / e86_arms['opus']['n']:.3f}"
prose["e3f_ups"] = f"{e86_arms['opus']['cost'] / e86_arms['opus']['k']:.3f}"; prose["e3f_us_luna"] = f"{e86_arms['luna']['usd_solved']:.4f}"
prose["e3f_sx"] = str(F3["solved_x"]); prose["e3f_finish"] = f"{e_finish:.2f}"; prose["e3f_nosc"] = str(e86_nosc)
prose["e3f_nosc_luna"] = str(round(100 * sum(1 for _, _, r in d_runs["A"] for x in r if int(x["selfcheck_runs"] or 0) == 0) / e86_arms["luna"]["n"]))
prose["e3f_tail_opus"] = str(e_tail["opus"]); prose["e3f_tail_cc"] = str(e_tail["cc"]); prose["e3f_tail_n"] = str(len(E_REF))
for k in E_KEYS:
    prose[f"e3f_{k}_p"] = f"{F3['effects'][k]['p']:.2g}"  # 0.0014, 1, 0.0046, as the report prints them
prose["e3f_wall_opus"] = str(e86_arms["opus"]["wall_med"]); prose["e3f_wall_luna"] = str(e86_arms["luna"]["wall_med"])
# the front page: process changes on gpt-6-luna with no detectable effect (M3's six ablations, M3b's memory, M3c's two checks, M3d's two steps)
proc = [effects[a] for a in "BCDEFG"] + [m3b_eff["C-A"]] + [m3c_eff[k] for k in ("M-A", "I-A")] + [m3d_eff[k] for k in ("V-A", "S-A")]
prose["proc_n"] = str(len(proc)); prose["proc_null"] = str(sum(1 for e in proc if e["lo"] <= 0 <= e["hi"]))
prose["proc_det"] = str(sum(1 for e in proc if e["lo"] > 0 or e["hi"] < 0))
prose["e3_model_p"] = f"{m3e['effects']['model']['p']:.1g}"  # 0.0009, as the report prints it
# M3g (prefix g_; the M3c gate's g_runs, g_skip, ... keep their names, and no key may be written twice)
G = m3g
g_before = set(prose)
g_new = {}
for k, e in G["effects"].items():
    g_new[f"g_{k}_e"] = sg(e["eff"]); g_new[f"g_{k}_ci"] = ci(e); g_new[f"g_{k}_p"] = f"{e['p']:.2g}"
    g_new[f"g_{k}_bws"] = f"{e['better']} / {e['worse']} / {e['same']}"
for k, v in g_arms.items():
    g_new[f"g_rate_{k}"] = f"{v['rate']:.1f}"; g_new[f"g_k_{k}"] = str(v["k"]); g_new[f"g_n_{k}"] = str(v["n"])
    g_new[f"g_us_{k}"] = f"{v['usd_solved']:.4f}"; g_new[f"g_ptok_{k}"] = f"{G['ptok'][k]:,}"; g_new[f"g_sc_{k}"] = f"{G['sc'][k]:.1f}"
    g_new[f"g_iface_{k}"] = str(G["iface"][k]); g_new[f"g_stp_{k}"] = str(v["labels"].get("tests_failed_selfcheck_passed", 0))
    g_new[f"g_nst_{k}"] = str(v["labels"].get("tests_failed_no_selfcheck", 0))
    g_new[f"g_ge_{k}"] = "≥ " if v["unreported"] else ""
for k in ("dA", "dK"):
    g_new[f"g_r79_{k}"] = f"{G['r79'][k]:.1f}"
g_new["g_ho_n"] = str(G["n_ho"]); g_new["g_runs_arm"] = str(len(g_runs["hA"]))
g_new["g_set_file"] = G["set"]["file"]; g_new["g_set_rev"] = G["set"]["rev"]; g_new["g_set_seed"] = G["set"]["seed"]
g_new["g_set_elig"] = str(G["set"]["eligible"]); g_new["g_set_of"] = str(G["set"]["of"])
for c, n in G["set"]["cid"].items():
    g_new[f"g_set_{c}"] = str(n)
g_new["g_loaded"] = str(G["loaded"]); g_new["g_krows"] = str(G["k_rows"])
sr = G["skills"]["spec-reading"]; sc_ = G["skills"]["self-check-and-cocotb"]
g_new["g_spec_pct"] = f"{100 * (sr['hK'] + sr['dK']) / G['k_rows']:.0f}"
g_new["g_selfsk_lo"] = f"{100 * min(sc_['hK'] / g_arms['hK']['n'], sc_['dK'] / g_arms['dK']['n']):.0f}"
g_new["g_selfsk_hi"] = f"{100 * max(sc_['hK'] / g_arms['hK']['n'], sc_['dK'] / g_arms['dK']['n']):.0f}"
g_new["g_unknown"] = str(G["unknown"]); g_new["g_trunc"] = str(G["truncated"])
g_new["g_bytes_h"] = f"{G['bytes_mean']['hK']:,}"; g_new["g_bytes_max"] = f"{G['bytes_max']:,}"
g_new["g_max"] = str(G["max_skills"]); g_new["g_cap"] = f"{G['cap_bytes']:,}"; g_new["g_pack_n"] = str(G["pack_n"])
g_new["g_pack_sha"] = G["pack_sha"][0][:8]
g_new["g_ptok_hx"] = f"+{G['ptok_x']['h']}"; g_new["g_ptok_dx"] = f"+{G['ptok_x']['d']}"; g_new["g_money_x"] = f"+{G['money_x']}"
g_new["g_scored"] = f"{G['cost_scored']:.2f}"; g_new["g_smoke"] = f"{G['cost_smoke']:.2f}"; g_new["g_spend"] = f"{G['cost_scored'] + G['cost_smoke']:.2f}"
g_new["g_ho_hi"] = sg(G["effects"]["ho"]["hi"]); g_new["g_unrep"] = str(sum(g_arms[k]["unreported"] for k in ("hA", "hK", "dK")))
g_new["g_wall_hA"] = str(g_arms["hA"]["wall_med"]); g_new["g_wall_hK"] = str(g_arms["hK"]["wall_med"])
g_clash = sorted(set(g_new) & g_before)
prose.update(g_new)

# M3h and M3i (prefixes h_ and i_)
hi_before = set(prose)
hi_new = {}
for k, e in m3h["effects"].items():
    hi_new[f"h_{k}_e"] = sg(e["eff"]); hi_new[f"h_{k}_ci"] = ci(e); hi_new[f"h_{k}_p"] = p2(e["p"])
    hi_new[f"h_{k}_bws"] = f"{e['better']} / {e['worse']} / {e['same']}"
for k, e in m3i["effects"].items():
    hi_new[f"i_{k}_e"] = sg(e["eff"]); hi_new[f"i_{k}_ci"] = ci(e); hi_new[f"i_{k}_p"] = p2(e["p"])
    hi_new[f"i_{k}_bws"] = f"{e['better']} / {e['worse']} / {e['same']}"
for k, v in h_arms.items():
    hi_new[f"h_rate_{k}"] = f"{v['rate']:.1f}"; hi_new[f"h_k_{k}"] = str(v["k"]); hi_new[f"h_n_{k}"] = str(v["n"])
hi_new["h_ho_n"] = str(m3h["n_ho"]); hi_new["h_d86_n"] = str(m3h["n"]); hi_new["h_d79_n"] = str(m3h["n79"])
hi_new["h_hi_up"] = sg(m3h["effects"]["ho"]["hi"])
for k in ("hS1", "hS2", "hS2n", "dS1", "dS2"):
    hi_new[f"h_load_{k}"] = str(m3h["loaded"][k])
for k in ("hA", "hS1", "hS2", "dA", "dS1", "dS2"):
    hi_new[f"h_turns_{k}"] = f"{m3h['turns_med'][k]:g}"; hi_new[f"h_ptok_{k}"] = f"{m3h['ptok'][k]:,}"
hi_new["h_ptok_s1x"] = f"+{round(100 * (m3h['ptok']['hS1'] / m3h['ptok']['hA'] - 1))}"
hi_new["h_ptok_s2x"] = f"+{round(100 * (m3h['ptok']['hS2'] / m3h['ptok']['hA'] - 1))}"
hi_new["h_pack_v2"] = str(m3h["pack_s2"]); hi_new["h_pack_v1"] = str(m3h["pack_s1"])
hi_new["h_copied_hS2"] = str(sum(1 for x in h_rows["hS2"] if x.get("skill_text_copied") == "1"))
hi_new["h_runs_ho"] = str(len(H_RUNS["hA"])); hi_new["h_runs_d86"] = str(len(H_RUNS["dA"]))
for k in ("hA", "hP", "dA", "dP"):
    hi_new[f"i_rate_{k}"] = f"{m3i['arms'][k]['rate']:.1f}"; hi_new[f"i_k_{k}"] = str(m3i["arms"][k]["k"]); hi_new[f"i_n_{k}"] = str(m3i["arms"][k]["n"])
    hi_new[f"i_turns_{k}"] = f"{m3i['turns_med'][k]:g}"; hi_new[f"i_ptok_{k}"] = f"{m3i['ptok'][k]:,}"; hi_new[f"i_wall_{k}"] = str(m3i["wall_med"][k])
hi_new["i_ptok_hx"] = f"{round(100 * m3i['ptok']['hP'] / m3i['ptok']['hA'])}"
hi_new["i_ptok_save"] = str(100 - int(hi_new["i_ptok_hx"]))  # input-token saving of P against D, held-out, %
hi_new["i_ptok_dx"] = f"{round(100 * m3i['ptok']['dP'] / m3i['ptok']['dA'])}"
hi_new["i_tools_n"] = str(len(m3i["tools"][0].split(";")))
hi_clash = sorted(set(hi_new) & hi_before)
prose.update(hi_new)

# M3j (prefix j_)
j_before = set(prose)
j_new = {}
for k, e in m3j["effects"].items():
    j_new[f"j_{k}_e"] = sg(e["eff"]); j_new[f"j_{k}_ci"] = ci(e); j_new[f"j_{k}_p"] = p2(e["p"])
    j_new[f"j_{k}_bws"] = f"{e['better']} / {e['worse']} / {e['same']}"
for k, v in m3j["arms"].items():
    j_new[f"j_rate_{k}"] = f"{v['rate']:.1f}"; j_new[f"j_k_{k}"] = str(v["k"]); j_new[f"j_n_{k}"] = str(v["n"])
for k in ("hPA", "hB", "hR"):
    j_new[f"j_turns_{k}"] = f"{m3j['turns_med'][k]:g}"; j_new[f"j_ptok_{k}"] = f"{m3j['ptok'][k]:,}"
j_new["j_ptok_rpa"] = str(round(100 * m3j["ptok"]["hR"] / m3j["ptok"]["hPA"]))
j_new["j_ptok_rd"] = str(round(100 * m3j["ptok"]["hR"] / m3i["ptok"]["hA"]))
for k, v in m3j["usd"].items():
    j_new[f"j_usd_{k}"] = f"{v:.2f}"
j_new["j_usd_scored"] = f"{sum(m3j['usd'].values()):.1f}"
j_new["j_console"] = f"{m3j['console_usd']:.2f}"
j_clash = sorted(set(j_new) & j_before)
prose.update(j_new)

# M3k (prefix k_)
k_before = set(prose)
k_new = {}
for k, e in m3k["effects"].items():
    k_new[f"k_{k}_e"] = sg(e["eff"]); k_new[f"k_{k}_ci"] = ci(e); k_new[f"k_{k}_p"] = p2(e["p"])
    k_new[f"k_{k}_bws"] = f"{e['better']} / {e['worse']} / {e['same']}"
for k, v in m3k["arms"].items():
    k_new[f"k_rate_{k}"] = f"{v['rate']:.1f}"; k_new[f"k_k_{k}"] = str(v["k"]); k_new[f"k_n_{k}"] = str(v["n"])
for k in ("hR", "hT", "hK"):
    k_new[f"k_turns_{k}"] = f"{m3k['turns_med'][k]:g}"; k_new[f"k_ptok_{k}"] = f"{m3k['ptok'][k]:,}"; k_new[f"k_wall_{k}"] = str(m3k["wall_med"][k])
k_new["k_ptok_tx"] = str(round(100 * (m3k["ptok"]["hT"] / m3k["ptok"]["hR"] - 1)))
k_new["k_ptok_kx"] = str(round(100 * (m3k["ptok"]["hK"] / m3k["ptok"]["hR"] - 1)))
k_new["k_fired_n"] = str(m3k["fired_n"]); k_new["k_fired_problems"] = str(m3k["fired_problems"])
k_new["k_fired_cleared"] = str(m3k["fired_cleared"]); k_new["k_diff_n"] = str(m3k["diff_n"])
for k, v in m3k["usd"].items():
    k_new[f"k_usd_{k}"] = f"{v:.2f}"
k_new["k_usd_scored"] = f"{sum(m3k['usd'].values()):.2f}"
k_new["k_usd_r"] = f"{m3j['usd']['hR']:.2f}"
k_clash = sorted(set(k_new) & k_before)
prose.update(k_new)
# M3l (prefix l_)
l_before = set(prose)
l_new = {}
l_new["l_e"] = sg(l_eff["eff"]); l_new["l_ci"] = ci(l_eff); l_new["l_p"] = f"{l_eff['p']:.3f}"
l_new["l_bws"] = f"{l_eff['better']} / {l_eff['worse']} / {l_eff['same']}"
l_new["l_e15"] = sg(l_eff15["eff"]); l_new["l_ci15"] = ci(l_eff15)
for a, v in m3l["arms"].items():
    l_new[f"l_k_{a}"] = str(v["k"]); l_new[f"l_n_{a}"] = str(v["n"]); l_new[f"l_rate_{a}"] = f"{v['rate']:.1f}"
l_new["l_cov_ho"] = str(l_cov["heldout100"][0]); l_new["l_cov_dev"] = str(l_cov["dev86"][0])
l_new["l_cov_ho_pct"] = str(round(100 * l_cov["heldout100"][0] / l_cov["heldout100"][1])); l_new["l_cov_dev_pct"] = str(round(100 * l_cov["dev86"][0] / l_cov["dev86"][1]))
l_new["l_kept"] = str(m3l["pool_kept"]); l_new["l_pool"] = str(m3l["pool"]); l_new["l_removed"] = str(m3l["pool"] - m3l["pool_kept"])
l_new["l_ptok_E"] = f"{m3l['ptok_M']['E']:.2f}"; l_new["l_ptok_R"] = f"{m3l['ptok_M']['R']:.2f}"
l_new["l_usd_E"] = f"{m3l['usd']['E']:.2f}"; l_new["l_usd_R"] = f"{m3l['usd']['R']:.2f}"
l_new["l_usd_scored"] = f"{sum(m3l['usd'].values()):.2f}"
l_new["l_same"] = str(m3l["same_5_5"]); l_new["l_llm_error"] = str(m3l["llm_error"])
l_clash = sorted(set(l_new) & l_before)
prose.update(l_new)

m3b["prose"] = prose

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
    "m3b": m3b,
    "m3b_confirm": m3b_conf, "m3c": m3c, "ladder": claude_ladder,
    "unsolved": unsolved, "m3d": m3d, "m3e": m3e, "m3g": m3g, "m3h": m3h, "m3i": m3i, "m3j": m3j, "m3k": m3k, "m3l": m3l,
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

# M3b (docs/reports/M3b_report.md, m3b/arms_paired*_eval86.md, taxonomy_by_arm.md, pareto.csv, retrieval_eval86.md)
check(len(EVAL) == 86, f"eval set {len(EVAL)}")
for a, v in m3b_arms.items():
    check(v["ids"] == sorted(EVAL) and v["n"] == 258 and len(v["runs"]) == 3, f"M3b arm {a} rows")
    check(v["memory_col"] == ([""] if a in "AB" else [snap["hash"]]), f"M3b arm {a} memory column {v['memory_col']}")
    check(v["unreported"] == 0, f"M3b arm {a} unreported")
check({a: v["k"] for a, v in m3b_arms.items()} == {"A": 149, "B": 160, "C": 153, "D": 168}, "M3b pooled passes")
check({a: [r["k"] for r in v["runs"]] for a, v in m3b_arms.items()} == {"A": [48, 51, 50], "B": [54, 51, 55], "C": [51, 51, 51], "D": [52, 59, 57]}, "M3b runs")
check({a: v["usd_solved"] for a, v in m3b_arms.items()} == {"A": 0.0124, "B": 0.0119, "C": 0.0113, "D": 0.0106}, "M3b $/solved")
check({a: v["usd_problem"] for a, v in m3b_arms.items()} == {"A": 0.0072, "B": 0.0074, "C": 0.0067, "D": 0.0069}, "M3b $/problem")
check({a: v["cost"] for a, v in m3b_arms.items()} == {"A": 1.8484, "B": 1.9081, "C": 1.7268, "D": 1.7841}, "M3b arm cost")
check({a: v["tokens"] for a, v in m3b_arms.items()} == {"A": 8878176, "B": 45667940, "C": 8159082, "D": 43215570}, "M3b tokens")
check((mA["usd_per_mprompt"], mB["usd_per_mprompt"]) == (0.268, 0.044), "M3b $ per M prompt tokens")
check((round(mB["tokens"] / 1e6, 1), round(mA["tokens"] / 1e6, 1)) == (45.7, 8.9), "M3b 45.7M against 8.9M")
for row in rows(os.path.join(M3B, "pareto.csv")):
    v = m3b_arms[row["arm"]]
    check(abs(float(row["pass_rate"]) - v["k"] / v["n"]) < 0.0006 and round(float(row["usd_per_problem"]), 4) == v["usd_problem"], f"M3b pareto {row['arm']}")
tax = {}
for line in open(os.path.join(M3B, "taxonomy_by_arm.md")):
    m = re.match(r"\| (\w+) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \| \d+ \|", line)
    if m and not tax.get("_done"):
        tax[m.group(1)] = dict(zip("ABCD", map(int, m.group(2, 3, 4, 5))))
    if line.startswith("#### Primary label by cid"):
        tax["_done"] = True
tax.pop("_done", None)
for lab, by in tax.items():
    for a in "ABCD":
        check(m3b_arms[a]["labels"].get(lab, 0) == by[a], f"M3b taxonomy {lab} {a}")
check({a: v["fails"] for a, v in m3b_arms.items()} == {"A": 109, "B": 98, "C": 105, "D": 90}, "M3b failures")
check({a: (v["cap_stops"], v["cap_stops_passed"]) for a, v in m3b_arms.items() if a != "C"} == {"A": (18, 7), "B": (49, 20), "D": (44, 11)}, "M3b cap stops")
for key, (eff, b, w, same, p) in m3b_check.items():
    e = m3b_eff[key]
    check(abs(e["eff"] - eff) < 0.06 and (e["better"], e["worse"], e["same"]) == (b, w, same), f"M3b effect {key} {e} vs {eff, b, w, same}")
    check(abs(e["p"] - p) < 0.0006 * max(1, p * 10), f"M3b sign test {key} {e['p']} vs {p:.4f}")
check({k: (m3b_eff[k]["eff"], m3b_eff[k]["lo"], m3b_eff[k]["hi"]) for k in M3B_ROLE} ==
      {"C-A": (1.6, -3.1, 6.6), "D-B": (3.1, -0.4, 7.0), "B-A": (4.3, 0.0, 8.5), "D-C": (5.8, 1.9, 10.1), "D-A": (7.4, 2.3, 12.8)}, "M3b intervals")
check(m3b_bonf_pass == [], f"Bonferroni {m3b_bonf_pass}")
check((m3b_floor["eff"], m3b_floor["better"], m3b_floor["worse"], m3b_floor["same"]) == m3b_floor["report"] == (-2.3, 3, 5, 78), f"M3b noise floor {m3b_floor}")
check(m3b_f20["eff"] == m3b_f20["report"] == 4.1, f"M3 F on the 86 {m3b_f20}")
check(len(snap["lessons"]) == 40 and snap["provenance"]["attempts"] == 87 and snap["provenance"]["passed"] == 19, "snapshot size")
check(snap["hash"] == "b783931cbf160595" and snap["provenance"]["cost_unreported_calls"] == 0, "snapshot hash")
check(sorted(retr) == sorted(lesson_text) and all(retr[k][1] == lesson_text[k] for k in retr), "retrieval table = snapshot text")
check(m3b["lessons"]["never"] == ["L07", "L08", "L17", "L28", "L30", "L38"], f"never retrieved {m3b['lessons']['never']}")
check([(t["id"], t["count"]) for t in m3b["lessons"]["top"]] == [("L03", 50), ("L02", 40), ("L37", 36), ("L06", 33)], "top lessons")
check([(x["k"], x["n"]) for x in learn] == [(6, 29), (7, 29), (6, 29)] and sum(x["unreported"] for x in learn) == 3, f"learning runs {learn}")
check(round(m3b_scored, 2) == 7.27 and round(m3b_learn, 2) == 3.41 and smoke == 0.1855, f"M3b costs {m3b_scored} {m3b_learn}")

# M3b confirming run (docs/reports/m3b/confirm_preregistration.md, confirm_result.md, confirm_paired_eval86.md)
for a in "AB":
    check(conf[a]["ids"] == sorted(EVAL) and conf[a]["n"] == 516 and len(conf_runs[a]) == 6, f"confirm arm {a} rows")
check(conf_seeds == [4, 5, 6, 7, 8, 9], f"confirm seeds {conf_seeds}")
check((conf["A"]["k"], conf["B"]["k"], conf["A"]["rate"], conf["B"]["rate"]) == (299, 323, 57.9, 62.6), "confirm pooled pass@1")
check((conf_eff["eff"], conf_eff["lo"], conf_eff["hi"], conf_eff["better"], conf_eff["worse"], conf_eff["same"]) == (4.7, 1.0, 8.5, 16, 7, 63), f"confirm effect {conf_eff}")
check(abs(conf_eff["eff"] - conf_chk[0]) < 0.06 and conf_chk[1:4] == (16, 7, 63) and abs(conf_chk[4] - conf_eff["p"]) < 0.0006, f"confirm recomputed {conf_chk}")
check(conf_verdict == conf_rep_verdict == "confirmed", f"confirm verdict {conf_verdict} / {conf_rep_verdict}")
check((conf["A"]["labels"].get("tests_failed_no_selfcheck"), conf["B"]["labels"].get("tests_failed_no_selfcheck")) == (121, 79), "confirm untested failures")
check((conf["A"]["turn_cap"], conf["B"]["turn_cap"]) == (28, 101), "confirm turn-cap stops")
check((conf["A"]["usd_solved"], conf["B"]["usd_solved"]) == (0.0126, 0.0119) and (conf["A"]["unreported"], conf["B"]["unreported"]) == (1, 1), "confirm $/solved")
check((conf["A"]["wall_med"], conf["B"]["wall_med"]) == (51, 72), "confirm median wall")
check(round(conf_cost, 1) == conf_rep_total, f"confirm spend {conf_cost} vs {conf_rep_total}")
# M3c (docs/reports/M3c_report.md, m3c/arms_paired_eval86.md, taxonomy_by_arm.md, pareto.csv)
for a in "AMI":
    check(m3c_arms[a]["ids"] == sorted(EVAL) and m3c_arms[a]["n"] == 258 and len(c_runs[a]) == 3, f"M3c arm {a} rows")
check({a: v["k"] for a, v in m3c_arms.items()} == {"A": 159, "M": 161, "I": 155}, "M3c pooled passes")
check({a: [r["k"] for r in v["runs"]] for a, v in m3c_arms.items()} == {"A": [56, 51, 52], "M": [51, 55, 55], "I": [51, 56, 48]}, "M3c runs")
check({k: (m3c_eff[k]["eff"], m3c_eff[k]["lo"], m3c_eff[k]["hi"], m3c_eff[k]["better"], m3c_eff[k]["worse"], m3c_eff[k]["same"]) for k in ("M-A", "I-A")}
      == {"M-A": (0.8, -3.9, 5.8, 13, 10, 63), "I-A": (-1.6, -6.2, 3.1, 10, 13, 63)}, "M3c effects")
for k, (eff, b, w, same, p) in m3c_chk.items():
    e = m3c_eff[k]
    check(abs(e["eff"] - eff) < 0.06 and (e["better"], e["worse"], e["same"]) == (b, w, same) and abs(e["p"] - p) < 0.0006, f"M3c recomputed {k} {eff, b, w, same, p}")
tax3c, cols3c = {}, None
for line in open(os.path.join(M3C, "taxonomy_by_arm.md")):
    if line.startswith("#### Primary label by cid"):
        break
    m = re.match(r"\| Label \| (.*) \| All \|", line)
    if m:
        cols3c = [c.strip() for c in m.group(1).split("|")]
    m = re.match(r"\| (\w+) \| ([\d |]+) \|$", line.rstrip())
    if m and cols3c:
        tax3c[m.group(1)] = dict(zip(cols3c, map(int, m.group(2).split("|"))))
check(len(tax3c) == 8, f"M3c taxonomy rows {len(tax3c)}")
for lab, by in tax3c.items():
    for a in "AMI":
        check(m3c_arms[a]["labels"].get(lab, 0) == by[a], f"M3c taxonomy {lab} {a}")
check({a: (v["labels"].get("tests_failed_no_selfcheck"), v["labels"].get("tests_failed_selfcheck_passed"), v["labels"].get("stopped_by_cap")) for a, v in m3c_arms.items()}
      == {"A": (56, 14, 4), "M": (None, 50, 19), "I": (45, 18, 12)}, "M3c key labels")
check({a: v["fails"] for a, v in m3c_arms.items()} == {"A": 99, "M": 97, "I": 103}, "M3c failures")
check({a: v["usd_solved"] for a, v in m3c_arms.items()} == {"A": 0.0099, "M": 0.0190, "I": 0.0113}, "M3c $/solved")
check({a: v["unreported"] for a, v in m3c_arms.items()} == {"A": 1, "M": 3, "I": 0}, "M3c unreported")
check({a: v["wall_med"] for a, v in m3c_arms.items()} == {"A": 51, "M": 135, "I": 59}, "M3c median wall")
for row in rows(os.path.join(M3C, "pareto.csv")):
    v = m3c_arms[row["arm"]]
    check(abs(float(row["pass_rate"]) - v["k"] / v["n"]) < 0.0006 and round(float(row["usd_per_problem"]), 4) == v["usd_problem"], f"M3c pareto {row['arm']}")
check(gate["runs"] == 390 and gate["outcomes"] == {"no_tb": 141, "pass": 103, "fail": 85, "skipped": 61} and gate["problem_runs"] == 242, f"gate runs {gate}")
check((gate["generated"], gate["compiled"], gate["killed"], gate["unfinished"], gate["kill_rate"]) == (2904, 1872, 1051, 0, 56.1), f"mutants {gate}")
check(gate["skipped_problems"] == 38, "gate skipped problems")
check(iface == {"checks": 672, "mismatch_checks": 99, "mismatch_pr": 38, "mismatch_pr_passed": 21, "blocks": 3}, f"interface {iface}")
check(m3c["solved_x"] == 1.9, f"M3c $/solved ratio {m3c['solved_x']}")
# Claude Code ladder (docs/reports/claude_code_ladder.md, claude_code/ladder_paired_eval86.md)
for k, z in ladder.items():
    check(z["ids"] == sorted(EVAL) and z["n"] == 86, f"ladder {k} rows")
    check(z["providers"] == ["claude_plan"] and z["cost"] == 0, f"ladder {k} is on the plan, not provider-billed")
    eff, b, w, same, p = lad_chk[k]
    e = z["effect"]
    check(abs(e["eff"] - eff) < 0.06 and (e["better"], e["worse"], e["same"]) == (b, w, same) and abs(e["p"] - p) < 0.0006 * max(1, p * 10), f"ladder recomputed {k} {lad_chk[k]} vs {e}")
check({k: (z["k"], z["effect"]["eff"], z["effect"]["lo"], z["effect"]["hi"]) for k, z in ladder.items()} ==
      {"haiku": (57, 4.7, -2.3, 11.2), "sonnet": (60, 8.1, -0.4, 17.4), "opus": (63, 11.6, 1.9, 21.3), "fable": (58, 5.8, -1.2, 12.8)}, "ladder effects")
check({k: z["wall_med"] for k, z in ladder.items()} == {"haiku": 83, "sonnet": 24, "opus": 50, "fable": 265}, "ladder median wall")
check((ladder["fable"]["wall_cap"], ladder["fable"]["wall_cap_failed"], ladder["sonnet"]["wall_cap"], ladder["opus"]["wall_cap"], ladder["haiku"]["wall_cap"]) == (17, 10, 1, 0, 0), "ladder wall-cap stops")
check((lad_union, lad_all) == (74, 45), f"ladder union/all {lad_union} {lad_all}")

# the unsolved-problems analysis (docs/reports/unsolved_analysis.md, tools/benchmark_limited_ids.txt)
check(unsolved["n"] == 12 and unsolved["never_A"] == 10 and unsolved["blim"] == 7 and unsolved["blim_in_uns"], f"unsolved {unsolved}")
check(re.search(r"the 12 of M3b's 86 evaluation problems", rep_un) and re.search(r"10 of them were also never solved", rep_un), "unsolved report counts")
m = re.search(r"arm A scores (\d+)/(\d+) = ([\d.]+)% \(([\d.]+)% on 86\)\.\s+Opus scores (\d+)/(\d+) = ([\d.]+)% \(([\d.]+)%\), Sonnet ([\d.]+)%, Fable ([\d.]+)% and Haiku ([\d.]+)%", rep_un)
check(m is not None, "unsolved report: reduced scores sentence")
if m:
    check(tuple(u79["A"]) == (int(m.group(1)), int(m.group(2))) and unsolved["r79"]["A"] == float(m.group(3)) and m3c_arms["A"]["rate"] == float(m.group(4)), f"unsolved arm A on 79 {u79['A']}")
    check(tuple(u79["opus"]) == (int(m.group(5)), int(m.group(6))) and unsolved["r79"]["opus"] == float(m.group(7)) and ladder["opus"]["rate"] == float(m.group(8)), f"unsolved Opus on 79 {u79['opus']}")
    check((unsolved["r79"]["sonnet"], unsolved["r79"]["fable"], unsolved["r79"]["haiku"]) == tuple(float(m.group(i)) for i in (9, 10, 11)), f"unsolved others on 79 {unsolved['r79']}")
check((unsolved["border"], unsolved["env"], unsolved["agent"]) == (2, 0, 3) and unsolved["blim"] + unsolved["border"] + unsolved["agent"] == unsolved["n"], f"unsolved classes {unsolved}")
check(unsolved["p2"] == 7 and "7 problems were solved by at least 2 Claude models" in rep_un and (unsolved["p2_untested"], unsolved["p2_valid"]) == (14, 20), f"unsolved part two {unsolved['p2']}")
check(re.search(r"traffic_light_controller_0001\b", "\n".join(BLIM)) and re.search(r"sync_serial_communication_0001\b", "\n".join(BLIM)) and unsolved["tl_defaults"] == [10, 20], "unsolved examples in the IDs file")
# M3d (docs/reports/M3d_report.md, m3d/arms_paired_eval86.md, arms_paired_eval79.md, taxonomy_by_arm.md, secondary_tables.md, pareto.csv)
for a in "AVS":
    check(m3d_arms[a]["ids"] == sorted(EVAL) and m3d_arms[a]["n"] == 258 and len(d_runs[a]) == 3, f"M3d arm {a} rows")
check({a: v["k"] for a, v in m3d_arms.items()} == {"A": 157, "V": 152, "S": 145}, "M3d pooled passes")
check({a: v["rate"] for a, v in m3d_arms.items()} == {"A": 60.9, "V": 58.9, "S": 56.2}, "M3d pooled rates")
check({k: (m3d_eff[k]["eff"], m3d_eff[k]["lo"], m3d_eff[k]["hi"], m3d_eff[k]["better"], m3d_eff[k]["worse"], m3d_eff[k]["same"]) for k in ("V-A", "S-A")}
      == {"V-A": (-1.9, -6.6, 2.3, 7, 9, 70), "S-A": (-4.7, -11.2, 1.6, 12, 19, 55)}, "M3d effects")
check(all(m3d_eff[k]["finding"] == "no detectable effect" and m3d_eff[k]["lo"] < 0 < m3d_eff[k]["hi"] for k in ("V-A", "S-A")), "M3d verdicts null")
check("97.5% interval" in open(os.path.join(M3D, "arms_paired_eval86.md")).read(), "M3d intervals are 97.5%")
for k, (eff, b, w, same, p) in m3d_chk.items():
    e = m3d_eff[k]
    check(abs(e["eff"] - eff) < 0.06 and (e["better"], e["worse"], e["same"]) == (b, w, same) and abs(e["p"] - p) < 0.0006, f"M3d recomputed {k} {eff, b, w, same, p}")
check({k: (m3d_eff79[k]["eff"], m3d_eff79[k]["lo"], m3d_eff79[k]["hi"]) for k in ("V-A", "S-A")} == {"V-A": (-2.1, -7.2, 2.5), "S-A": (-5.1, -12.7, 1.7)}, "M3d effects on 79")
check({a: (x["rate79"], x["n79"]) for a, x in m3d_extra.items()} == {"A": (66.2, 237), "V": (64.1, 237), "S": (61.2, 237)}, f"M3d rates on 79 {m3d_extra}")
taxd, colsd = {}, None
for line in open(os.path.join(M3D, "taxonomy_by_arm.md")):
    if line.startswith("#### Primary label by cid"):
        break
    m = re.match(r"\| Label \| (.*) \| All \|", line)
    if m:
        colsd = [c.strip() for c in m.group(1).split("|")]
    m = re.match(r"\| (\w+) \| ([\d |]+) \|$", line.rstrip())
    if m and colsd:
        taxd[m.group(1)] = dict(zip(colsd, map(int, m.group(2).split("|"))))
check(len(taxd) == 8, f"M3d taxonomy rows {len(taxd)}")
for lab, by in taxd.items():
    for a in "AVS":
        check(m3d_arms[a]["labels"].get(lab, 0) == by[a], f"M3d taxonomy {lab} {a}")
check({a: v["fails"] for a, v in m3d_arms.items()} == {"A": 101, "V": 106, "S": 113}, "M3d failures")
check({a: (v["labels"].get("tests_failed_no_selfcheck", 0), v["labels"].get("tests_failed_selfcheck_passed", 0), v["labels"].get("stopped_by_cap", 0), v["labels"].get("llm_error", 0)) for a, v in m3d_arms.items()}
      == {"A": (55, 16, 7, 2), "V": (0, 48, 27, 14), "S": (2, 44, 43, 9)}, "M3d key labels")
check({a: v["usd_solved"] for a, v in m3d_arms.items()} == {"A": 0.0112, "V": 0.0181, "S": 0.0234}, "M3d $/solved")
check({a: v["unreported"] for a, v in m3d_arms.items()} == {"A": 4, "V": 15, "S": 18}, "M3d unreported")
check({a: v["wall_med"] for a, v in m3d_arms.items()} == {"A": 74, "V": 135, "S": 247}, "M3d median wall")
check(m3d["solved_x"] == {"V": 1.6, "S": 2.1} and "V costs 1.6× as much per solved" in rep3d and "S costs 2.1× as much per solved" in rep3d, f"M3d $/solved ratios {m3d['solved_x']}")
for row in rows(os.path.join(M3D, "pareto.csv")):
    v = m3d_arms[row["arm"]]
    check(abs(float(row["pass_rate"]) - v["k"] / v["n"]) < 0.0006 and round(float(row["usd_per_problem"]), 4) == v["usd_problem"], f"M3d pareto {row['arm']}")
sec = open(os.path.join(M3D, "secondary_tables.md")).read()
for a in "AVS":
    x = m3d_extra[a]
    m = re.search(rf"\| {a} \| 258 \| (\d+) / [\d.]+ \| (\d+) \((\d+)%\) \| [\d.]+ / [\d.]+ \| [\d.]+ / [\d.]+ \| (\d+) \((\d+)%\) \|", sec)
    check(m is not None and (x["turns_med"], x["one_turn"], x["no_sc"]) == (int(m.group(1)), int(m.group(2)), int(m.group(4))), f"M3d effort {a} {x}")
check("from 55% to 1%" in rep3d, "M3d 55% to 1%")
m = re.search(r"\| V \| 258 \| (\d+) \| (\d+) \| (\d+) \|", sec); check(m and (m3d_extra["V"]["verify_runs"], m3d_extra["V"]["refusals"], m3d_extra["V"]["refused_rows"]) == tuple(map(int, m.groups())), "M3d verify V")
m = re.search(r"\| S \| 258 \| (\d+) \| (\d+) \| (\d+) \|", sec); check(m and (m3d_extra["S"]["verify_runs"], m3d_extra["S"]["refusals"], m3d_extra["S"]["refused_rows"]) == tuple(map(int, m.groups())), "M3d verify S")
m = re.search(r"\| yes \| (\d+) \| (\d+) \|\n\| no \(fail or timeout\) \| (\d+) \| (\d+) \|\n\| not applied [^|]*\| (\d+) \| (\d+) \|", sec)
check(m is not None and (spec_tab["pass"], spec_tab["fail"], spec_tab["na"]) == ([int(m.group(1)), int(m.group(2))], [int(m.group(3)), int(m.group(4))], [int(m.group(5)), int(m.group(6))]), f"M3d spec table {spec_tab}")
check("a 61% hidden pass rate when they all pass, 57% when" in rep3d and round(100 * spec_tab["pass"][0] / sum(spec_tab["pass"])) == 61 and round(100 * spec_tab["fail"][0] / sum(spec_tab["fail"])) == 57, "M3d spec agreement 61/57")
check(spec_gen == 239 and "generated 239" in sec, "M3d spec generated")
m = re.search(r"The (\d+) refused problem-runs \(`run_budget_exhausted`\).*?about \+([\d.]+) points", rep3d, re.S)
check(m is not None and int(m.group(1)) == m3d_extra["S"]["guard"] == 8 and float(m.group(2)) == guard_adj and m3d_extra["V"]["guard"] == m3d_extra["A"]["guard"] == 0, f"M3d guard {m3d_extra['S']['guard']} {guard_adj}")
check(p2_pass["V"] <= p2_pass["A"] and p2_pass["S"] <= p2_pass["A"] and "None of the 7 problems from brief 09's part two is won" in rep3d, f"M3d part-two problems {p2_pass}")
check(round(m3d_scored, 4) == 7.899 and "provider-reported cost is $7.8990" in rep3d and m3d_smoke == 0.26, f"M3d spend {m3d_scored} {m3d_smoke}")

# M3e (docs/reports/M3e_report.md and the ablate.py outputs in m3e/)
check(len(E_ATT) == 67 and len(E_REF) == 19 and sorted(E_ATT + E_REF) == sorted(EVAL) and e_refused == 19, f"M3e ids {len(E_ATT)} {len(E_REF)} {e_refused}")
check(sum(int(x["pass"]) + int(x["llm_calls"] or 0) for x in e_all if x["id"] in set(E_REF)) == 0, "M3e refused rows made no LLM call")
for k, key in E_KEYS.items():
    e = e_eff[key]
    check((e["eff"], e["better"], e["worse"], e["same"]) == e_chk[k] and e["n"] == 67, f"M3e {k} effect {e} vs {e_chk[k]}")
for k in ("model", "harness"):
    e = e_eff63[E_KEYS[k]]
    check((e["eff"], e["better"], e["worse"], e["same"]) == e_chk63[k] and e["n"] == 63 == len(E_ATT63), f"M3e {k} effect on 63 {e} vs {e_chk63[k]}")
check(f"**+13.4 points [+4.0, +22.4]** (19 better, 3 worse, 45 same; sign test p = {prose['e3_model_p']})" in rep3e and m3e["effects"]["model"]["eff"] == 13.4, "M3e model effect in report")
check("**CC+Opus − LG+Opus = −4.5 points [−13.4, +4.5]** (3 better, 6 worse, 58 same, p = 0.51)" in rep3e, "M3e harness effect in report")
check("**+9.0 [−1.0, +18.9]**" in rep3e and m3e["effects"]["total"]["eff"] == 9.0, "M3e total in report")
check("model +14.3 [+4.2, +23.8], harness\n  −4.8 [−14.3, +4.8]" in rep3e, "M3e 63-problem view in report")
check((e_arms["opus"]["k"], e_arms["opus"]["n"], e_arms["luna"]["k"], e_arms["luna"]["n"], e_arms["cc"]["k"], e_arms["cc"]["n"]) == (52, 67, 129, 201, 49, 67)
      and "**52/67 = 77.6% [67.2, 86.6]**" in rep3e and "129/201 = 64.2%" in rep3e and "49/67 = 73.1%" in rep3e, "M3e pooled rates")
check(f"$17.11 on 67 problems: **${prose['e3_upp']} per problem, ${prose['e3_ups']} per solved problem**" in rep3e
      and round(e_arms["opus"]["cost"], 2) == 17.11 and f"({m3e['solved_x']}× as much)" in rep3e, f"M3e cost {prose['e3_upp']} {prose['e3_ups']} {m3e['solved_x']}")
check(f"smoke runs ${e_smoke:.2f}" in rep3e and f"Spend for this brief: ${e_scored + e_smoke:.2f}" in rep3e, f"M3e spend {e_scored} {e_smoke}")
check(e_nosc == {"opus": 0, "luna": 49} and "| LG+Opus | 67 | 1 / 2.15 | 34 (51%) | 3 / 5.30 | 1 / 1.99 | 0 (0%) |" in open(os.path.join(M3E, "secondary_tables_attempted67.md")).read(), f"M3e no-self-check {e_nosc}")
check((e_arms["opus"]["wall_med"], e_arms["luna"]["wall_med"]) == (44, 84), f"M3e median wall {e_arms['opus']['wall_med']} {e_arms['luna']['wall_med']}")
# M3e full 86 (brief 14b): the merged arm, its effects against the ablate.py outputs, and the report
check(len(e86_all) == 86 and sorted(x["id"] for x in e86_all) == sorted(EVAL) and not any(x["stop_reason"] == "run_budget_exhausted" for x in e86_all), "M3e merged arm: 86 problems, none refused")
e_src = {x["id"]: x for x in e_all if x["id"] in set(E_ATT)}
for r in e_fin.values():
    e_src.update({x["id"]: x for x in r if x["stop_reason"] != "run_budget_exhausted"})
check(sorted(e_src) == sorted(EVAL) and all(e_src[x["id"]] == x for x in e86_all) and sorted(e_fin) == E_RUNS86[1:], "M3e merged arm = first dispatch's 67 + the finishing runs' attempted rows")
for k, key in E_KEYS.items():
    e, e7 = e86_eff[key], e79_eff[key]
    check((e["eff"], e["better"], e["worse"], e["same"]) == e86_chk[k] and e["n"] == 86, f"M3e full {k} effect {e} vs {e86_chk[k]}")
    check((e7["eff"], e7["better"], e7["worse"], e7["same"]) == e79_chk[k] and e7["n"] == 79, f"M3e 79 {k} effect {e7} vs {e79_chk[k]}")
check("**LG+Opus − LG+luna = +11.2 points [+2.7, +20.2]** (24 better, 6 worse, 56 same" in rep3e and F3["effects"]["model"]["eff"] == 11.2, "M3e full model effect in report")
check("**CC+Opus − LG+Opus = +1.2 points\n  [−7.0, +9.3]** (7 better, 6 worse, 73 same, p = 1)" in rep3e and F3["effects"]["harness"]["eff"] == 1.2, "M3e full harness effect in report")
check("**+12.4 [+3.1, +21.7]**" in rep3e and F3["effects"]["total"]["eff"] == 12.4, "M3e full total in report")
check("model +12.2 [+3.4, +21.5], harness\n  +1.3 [−7.6, +10.1], total +13.5 [+3.4, +23.2]" in rep3e, "M3e 79-problem view in report")
check((e86_arms["opus"]["k"], e86_arms["luna"]["k"], e86_arms["luna"]["n"], e86_arms["cc"]["k"]) == (62, 157, 258, 63)
      and "**62/86 = 72.1% [62.8, 81.4]**" in rep3e and "157/258 = 60.9%" in rep3e and "63/86 = 73.3%" in rep3e, "M3e full pooled rates")
check(f"$22.25 on 86 problems: **${prose['e3f_upp']} per problem, ${prose['e3f_ups']} per solved problem**" in rep3e
      and round(e86_arms["opus"]["cost"], 2) == 22.25 and f"({F3['solved_x']}× as much)" in rep3e, f"M3e full cost {prose['e3f_upp']} {prose['e3f_ups']} {F3['solved_x']}")
check(f"**Spend for brief 14b: ${e_finish:.2f}**" in rep3e and f"**M3e in all: ${e_scored + e_smoke + e_finish:.2f}**" in rep3e, f"M3e finish spend {e_finish}")
check(e_tail == {"opus": 10, "cc": 14} and "LG+Opus solved 10 of them, Claude Code + Opus 14" in rep3e, f"M3e tail {e_tail}")
check(e86_nosc == 0 and "| LG+Opus | 86 | 2 / 2.30 | 40 (47%) | 5 / 5.60 | 1 / 2.06 | 0 (0%) |" in open(os.path.join(M3E, "secondary_tables_eval86.md")).read(), f"M3e full no-self-check {e86_nosc}")
# M3g (docs/reports/M3g_report.md and the ablate.py / taxonomy.py / m3g_tables.py outputs in m3g/)
rep3g = open(os.path.join(REP, "M3g_report.md")).read()
g_tab = {s: open(os.path.join(M3G, f"tables_{s}.md")).read() for s in ("heldout", "dev")}
check(not g_clash, f"M3g prose keys clash with existing ones: {g_clash}")
check(len(G_HO) == 100 == len(set(G_HO)) and not set(G_HO) & set(EVAL), f"M3g held-out ids {len(G_HO)}")
check(all(sorted(x["id"] for x in r) == sorted(G_HO) for k in ("hA", "hK") for _, _, r in g_runs[k]), "M3g held-out runs cover the 100 ids")
check(all(sorted(x["id"] for x in r) == sorted(EVAL) for _, _, r in g_runs["dK"]) and len(g_runs["dK"]) == 3, "M3g dev K runs cover the 86")
g_cid_of = {}
for x in g_rows["hA"] + g_rows["hK"]:
    g_cid_of.setdefault(x["id"], set()).add(x["cid"])
check(all(len(c_) == 1 for c_ in g_cid_of.values()), "M3g one cid per held-out id")
g_cids = {}
for c_ in g_cid_of.values():
    g_cids[min(c_)] = g_cids.get(min(c_), 0) + 1
check(g_cids == G["set"]["cid"] == {"cid002": 42, "cid003": 41, "cid004": 17}, f"M3g cid counts {g_cids} {G['set']['cid']}")
check((G["set"]["eligible"], G["set"]["seed"], G["set"]["rev"]) == (193, "20261030", "5b807d9") and "from the 193 eligible cid002/003/004 problems" in rep3g
      and "sampled (seed 20261030)" in rep3g and G["set"]["file"] in rep3g, f"M3g held-out set {G['set']}")
for k, e in g_eff.items():
    check((e["eff"], e["better"], e["worse"], e["same"]) == g_chk[k], f"M3g {k} effect {e} vs recomputed {g_chk[k]}")
check(f"**K − A = +1.0 points [−2.7, +4.7]** (9 better," in rep3g and (g_eff["ho"]["eff"], g_eff["ho"]["lo"], g_eff["ho"]["hi"]) == (1.0, -2.7, 4.7), "M3g held-out effect in report")
check("| 86 problems | 60.9% | 58.5% | **−2.3 [−7.4, +2.3]** | 11 / 12 / 63 | 1 |" in rep3g and g_eff["d86"]["eff"] == -2.3
      and (prose["g_rate_dA"], prose["g_rate_dK"]) == ("60.9", "58.5"), "M3g 86 effect in report")
check("| 79 problems (7 benchmark-limited left out) | 66.2% | 63.7% | **−2.5 [−8.4, +2.5]** | 11 / 12 / 56 | 1 |" in rep3g
      and (G["r79"]["dA"], G["r79"]["dK"]) == (66.2, 63.7) and g_eff["d79"]["eff"] == -2.5, "M3g 79 view in report")
check("| pass@1, 100 problems × 3 runs | 153/300 = 51.0% | 156/300 = 52.0% |" in rep3g and (g_arms["hA"]["k"], g_arms["hK"]["k"]) == (153, 156), "M3g pooled held-out rates")
check(f"loaded skills in {G['loaded']} of {G['k_rows']} problem-runs" in rep3g and (G["loaded"], G["k_rows"]) == (552, 558), f"M3g loaded {G['loaded']}")
check(f"`self-check-and-cocotb` in {prose['g_selfsk_lo']}–{prose['g_selfsk_hi']}%" in rep3g and prose["g_spec_pct"] == "99"
      and (G["skills"]["spec-reading"]["hK"], G["skills"]["spec-reading"]["dK"]) == (299, 253), "M3g skill shares")
check(f"{G['unknown']} names asked for in 558 problem-runs were near misses" in rep3g and G["truncated"] == 0 and "Cut by the cap: 0." in g_tab["heldout"]
      and "Cut by the cap: 0." in g_tab["dev"], f"M3g unknown {G['unknown']} truncated {G['truncated']}")
check(f"Bytes loaded: mean {G['bytes_mean']['hK']}" in g_tab["heldout"] and f"Bytes loaded: mean {G['bytes_mean']['dK']}" in g_tab["dev"]
      and f"at most {G['bytes_max']:,}" in rep3g, f"M3g bytes {G['bytes_mean']} {G['bytes_max']}")
check((G["max_skills"], G["cap_bytes"], G["pack_n"]) == (3, 13000, 15) and "names up to 3 skills; their text (≤ 13,000 bytes)" in rep3g
      and "15 skills written from outside sources" in rep3g and f"manifest SHA-256 `{prose['g_pack_sha']}…`" in rep3g and len(G["pack_sha"]) == 1, "M3g pack settings")
for s, k in (("heldout", "hA"), ("heldout", "hK"), ("dev", "dA"), ("dev", "dK")):
    check(f"| {k[1]} | {g_arms[k]['n']} | {G['ptok'][k]:,} /" in g_tab[s] and f"({G['sc'][k]:.1f}%) |" in g_tab[s], f"M3g tokens / self-check {k}")
check(f"| K, held-out | $0.0033 | ${prose['g_us_hK']} | {prose['g_wall_hK']} s | {prose['g_ptok_hK']} | +4,693 ({prose['g_ptok_hx']}%) |" in rep3g
      and f"| {prose['g_ptok_dK']} | +8,487 ({prose['g_ptok_dx']}%) |" in rep3g and f"{G['money_x']}% more money" in rep3g
      and f"≥${prose['g_us_hA']} per solved problem" in rep3g, "M3g cost lines in report")
g_tax = [("tests failed, own testbench passed", "stp"), ("tests failed, no own testbench", "nst")]
for lab, sh in g_tax:
    check(f"| {lab} | {prose['g_' + sh + '_hA']} | {prose['g_' + sh + '_hK']} | {prose['g_' + sh + '_dA']} | {prose['g_' + sh + '_dK']} |" in rep3g, f"M3g taxonomy {lab}")
check(f"| interface mismatch (`compile_fail_hidden` + `signal_missing_hidden`) | {G['iface']['hA']} | {G['iface']['hK']} | {G['iface']['dA']} | {G['iface']['dK']} |" in rep3g, "M3g interface mismatches")
check(abs(g_scored - 3.8428) < 0.0002 and g_smoke == 0.0437 and "smoke $0.0437, scored $3.8428, **M3g total $3.8865**" in rep3g
      and f"M3g cost **${prose['g_scored']}** for the 9 scored sweeps, **${prose['g_spend']}** with the smoke" in rep3g, f"M3g spend {g_scored} {g_smoke}")
check(prose["g_unrep"] == "6" and "so the 6 unreported calls cost about nothing" in rep3g, f"M3g unreported {prose['g_unrep']}")
# M3h and M3i (docs/reports/M3h_report.md, M3i_report.md and the ablate.py / m3h_tables.py outputs beside them)
rep3h = open(os.path.join(REP, "M3h_report.md")).read()
rep3i = open(os.path.join(REP, "M3i_report.md")).read()
check(not hi_clash, f"M3h/M3i prose keys clash with existing ones: {hi_clash}")
check(all(sorted(x["id"] for x in r) == sorted(G_HO) for k in ("hA", "hS1", "hS2", "hP") for _, _, r in H_RUNS[k])
      and [len(H_RUNS[k]) for k in ("hA", "hS1", "hS2", "hS2n", "hP")] == [3, 3, 3, 1, 3], "M3h/M3i held-out runs cover the 100 ids")
check(all(sorted(x["id"] for x in r) == sorted(EVAL) for k in ("dA", "dS1", "dS2", "dP") for _, _, r in H_RUNS[k])
      and [len(H_RUNS[k]) for k in ("dA", "dS1", "dS2", "dP")] == [1, 1, 1, 1], "M3h/M3i 86 runs cover the 86 ids, one run each")
check(all(x["stop_reason"] != "rate_limited" for k in h_rows for x in h_rows[k]), "M3h/M3i: no rate-limited rows")
for k, e in h_effects.items():
    check((e["eff"], e["better"], e["worse"], e["same"]) == h_chk[k], f"M3h {k} effect {e} vs recomputed {h_chk[k]}")
for k, e in i_effects.items():
    check((e["eff"], e["better"], e["worse"], e["same"]) == i_chk[k], f"M3i {k} effect {e} vs recomputed {i_chk[k]}")
check("- **Primary: S2c − A = −2.0 points [−6.3, +1.7]** (9 better, 12 worse, 79 same; sign test p = 0.66)" in rep3h
      and (prose["h_ho_e"], prose["h_ho_ci"], prose["h_ho_bws"], prose["h_ho_p"]) == ("−2.0", "[−6.3, +1.7]", "9 / 12 / 79", "0.66"), "M3h held-out primary in report")
check("- **S1c − A = +1.3 [−2.7, +5.7]** (13 / 9 / 78, p = 0.52)" in rep3h and "**S2c − S1c = −3.3 [−7.0, −0.0]** (3 / 11 / 86, p = 0.057)" in rep3h
      and (prose["h_ho_s1_e"], prose["h_ho_s2s1_e"]) == ("+1.3", "−3.3"), "M3h held-out secondaries in report")
check("**S2c − A = +3.5 [−2.3, +9.3]** (5 / 2 / 79); **S1c − A = −1.2 [−7.0, +4.7]** (3 / 4 / 79)" in rep3h
      and "S2c − S1c = +4.7 [−2.3, +11.6] (7 / 3 / 76)" in rep3h and (prose["h_d86_e"], prose["h_d86_s1_e"], prose["h_d86_s2s1_e"]) == ("+3.5", "−1.2", "+4.7"), "M3h 86 effects in report")
check("(S2c − A +3.8 [−2.5, +10.1]; S1c − A −1.3 [−7.6, +5.1])" in rep3h and (prose["h_d79_e"], prose["h_d79_s1_e"]) == ("+3.8", "−1.3"), "M3h 79 view in report")
check("S2c (`v2.0` plus the one-line hint) passed 56.3% and A 58.3%" in rep3h
      and (prose["h_rate_hS2"], prose["h_rate_hA"]) == ("56.3", "58.3"), "M3h held-out pass rates in report")
check("Pass counts: A 58/86 (67.4%), S1c 57/86 (66.3%), S2c 61/86 (70.9%)" in rep3h
      and [prose[f"h_k_{k}"] for k in ("dA", "dS1", "dS2")] == ["58", "57", "61"], "M3h 86 pass counts in report")
check("S1c loaded a pack skill in 300 of 300 problem-runs, and S2c in 299 of 300" in rep3h and "the single S2 run loaded one in 3 of 100" in rep3h
      and (m3h["loaded"]["hS1"], m3h["loaded"]["hS2"], m3h["loaded"]["hS2n"]) == (300, 299, 3)
      and (m3h["loaded"]["dS1"], m3h["loaded"]["dS2"]) == (86, 86) and "| S1c | 86 of 86 |" in rep3h, "M3h skill load counts in report")
check("Median turns went from 6 (A) to 12 (S1c) and 11 (S2c)" in rep3h and [m3h["turns_med"][k] for k in ("hA", "hS1", "hS2")] == [6, 12, 11]
      and "| A | – | – | 11 (12.5) | 89 | 2 | 431,567 |" in rep3h and "| S2c | 86 of 86 | 2.72 | 18 (19.1) | 109 | 1 | 487,439 |" in rep3h
      and [m3h["turns_med"][k] for k in ("dA", "dS1", "dS2")] == [11, 17.5, 18], "M3h turns in report")
check("prompt tokens rose by about 46–51% per problem-run" in rep3h and (prose["h_ptok_s2x"], prose["h_ptok_s1x"]) == ("+46", "+51")
      and "| A | 6 (6.9) | 32 | 0 | 167,423 |" in rep3h, "M3h prompt-token rise in report")
check("One S2c problem-run out of 300 held 80 bytes" in rep3h and prose["h_copied_hS2"] == "1", "M3h copied-text count in report")
check("**Status: DONE (2026-11-02). Decision: null.**" in rep3h and "cut to **1 run per arm**" in rep3h, "M3h status and deviation in report")
check("**Primary: P − D = −0.3 points [−4.0, +3.3]** (9 better, 11 worse, 80 same; sign test p = 0.82)" in rep3i
      and (prose["i_ho_e"], prose["i_ho_ci"], prose["i_ho_bws"], prose["i_ho_p"]) == ("−0.3", "[−4.0, +3.3]", "9 / 11 / 80", "0.82"), "M3i held-out primary in report")
check("**P − D = +3.5 [−3.5, +10.5]** (7 better, 4 worse, 75 same; sign test p = 0.55" in rep3i.replace("Development set (86), descriptive: ", "")
      or "P − D = +3.5 [−3.5, +10.5]** (7 better, 4 worse, 75 same; sign test p = 0.55" in rep3i, "M3i 86 effect in report")
check("+2.5 [−5.1, +10.1], 6 / 4 / 69" in rep3i and (prose["i_d79_e"], prose["i_d79_ci"]) == ("+2.5", "[−5.1, +10.1]"), "M3i 79 view in report")
check("| pass@1, 100 problems × 3 runs | 175/300 = 58.3% | 174/300 = 58.0% |" in rep3i and (prose["i_k_hA"], prose["i_k_hP"]) == ("175", "174")
      and "| 86 problems | 58/86 = 67.4% | 61/86 = 70.9% |" in rep3i and (prose["i_k_dA"], prose["i_k_dP"]) == ("58", "61"), "M3i pass counts in report")
check("P uses 37% of D's prompt tokens" in rep3i and "mean prompt tokens per problem-run D 167,423, P 61,805" in rep3i
      and (prose["i_ptok_hA"], prose["i_ptok_hP"], prose["i_ptok_hx"]) == ("167,423", "61,805", "37")
      and "431,567 and 157,887 (P uses 37% of D's again)" in rep3i and prose["i_ptok_dx"] == "37", "M3i prompt tokens in report")
check("median turns D 6, P 5; median wall time D 32 s, P 25 s" in rep3i and (prose["i_turns_hA"], prose["i_turns_hP"], prose["i_wall_hA"], prose["i_wall_hP"]) == ("6", "5", "32", "25")
      and "median turns D 11, P 8; median wall time 89 s and 44 s" in rep3i and (prose["i_turns_dA"], prose["i_turns_dP"]) == ("11", "8"), "M3i effort in report")
check(m3i["tools"] == ["Bash;Edit;Read;Write"] and m3i["skills_mcp"] == [("0", "0")] and "`cc_tools` = `Bash;Edit;Read;Write`" in rep3i, f"M3i profile took effect {m3i['tools']} {m3i['skills_mcp']}")
check("**Status: DONE (2026-11-02). Decision: null.**" in rep3i, "M3i status in report")
# M3j (docs/reports/M3j_report.md and the ablate.py outputs beside it)
rep3j = open(os.path.join(REP, "M3j_report.md")).read()
check(not j_clash, f"M3j prose keys clash with existing ones: {j_clash}")
check([len(J_RUNS[k]) for k in ("hPA", "hB", "hR")] == [2, 2, 2] and all(j_arms[k]["n"] == 300 for k in ("hPA", "hB", "hR")),
      "M3j held-out: two dispatches per arm, 300 problem-runs each")
check(all(j_arms[k]["n"] == len(EVAL) for k in ("dPA", "dB", "dR")), "M3j 86: one run per arm over the 86")
check(all(x["stop_reason"] not in ("rate_limited", "profile_error", "run_budget_exhausted") for k in J_RUNS for x in j_rows[k]),
      "M3j: no not-run rows left")
check(m3j["key_source"] == ["ANTHROPIC_API_KEY"] and m3j["tools_b"] == ["Bash;Edit;Read"], f"M3j profiles {m3j['key_source']} {m3j['tools_b']}")
for k, e in j_effects.items():
    check((e["eff"], e["better"], e["worse"], e["same"]) == j_chk[k], f"M3j {k} effect {e} vs recomputed {j_chk[k]}")
check("- **Primary: R − PA = +0.0 points [−4.3, +4.3]** (7 better, 7 worse, 86 same; sign test p = 1)" in rep3j
      and (prose["j_ho_e"], prose["j_ho_ci"], prose["j_ho_bws"]) == ("+0.0", "[−4.3, +4.3]", "7 / 7 / 86"), "M3j primary in report")
check("**B − PA = +3.7 [+0.0, +7.7]** (13 / 5 / 82; p = 0.096)" in rep3j and j_effects["ho_b"]["finding"] == "no detectable effect"
      and "**PA − P = −3.3 [−7.3, +0.7]** (6 / 12 / 82; p = 0.24)" in rep3j and "**R − D = −3.7 [−8.3, +0.3]** (10 / 15 / 75; p = 0.42)" in rep3j,
      "M3j secondaries in report")
check(f"| PA | 5 (5.8) | 23 | 3 | {prose['j_ptok_hPA']} |" in rep3j and f"| R | 5 (5.4) | 22 | 0 | {prose['j_ptok_hR']} |" in rep3j
      and f"That is {prose['j_ptok_rpa']}% of PA's" in rep3j and f"{prose['j_ptok_rd']}% of D's" in rep3j, "M3j tokens in report")
check(f"| Held-out (300 problem-runs) | ${prose['j_usd_hPA']} (Claude Code's figure) | ${prose['j_usd_hB']} (Claude Code's figure) | ${prose['j_usd_hR']} (from tokens at list rates) |" in rep3j
      and f"| The 86 (92 problems run) | ${prose['j_usd_dPA']} | ${prose['j_usd_dB']} | ${prose['j_usd_dR']} |" in rep3j
      and f"about **${prose['j_usd_scored']} of API credit**" in rep3j and f"${prose['j_console']} for the month" in rep3j, "M3j cost in report")
check("**Status: DONE (2026-11-03). Decision: null.**" in rep3j, "M3j status in report")
# M3k (docs/reports/M3k_report.md and the ablate.py outputs beside it)
rep3k = open(os.path.join(REP, "M3k_report.md")).read()
check(not k_clash, f"M3k prose keys clash with existing ones: {k_clash}")
check([len(K_RUNS[k]) for k in ("hT", "hK")] == [3, 3] and all(k_arms[k]["n"] == 300 for k in ("hR", "hT", "hK")),
      "M3k held-out: three dispatches per arm, 300 problem-runs each")
check(all(k_arms[k]["n"] == len(EVAL) for k in ("dR", "dT", "dK")), "M3k 86: one run per arm over the 86")
check(all(x["stop_reason"] == "submit" for k in ("hT", "hK") for x in k_rows[k]), "M3k: every held-out row ended in submit")
check(m3k["llm_error"] == 3 and "**3 `llm_error` rows**" in rep3k, "M3k: three llm_error rows on the 86, not held-out")
for k, e in k_effects.items():
    check((e["eff"], e["better"], e["worse"], e["same"]) == k_chk[k], f"M3k {k} effect {e} vs recomputed {k_chk[k]}")
check("- **Primary: T − R on the held-out set = +0.3 points [−4.7, +5.3]** (9 better, 9 worse, 82 same; sign test p = 1)" in rep3k
      and (prose["k_ho_t_e"], prose["k_ho_t_ci"], prose["k_ho_t_bws"]) == ("+0.3", "[−4.7, +5.3]", "9 / 9 / 82"), "M3k primary in report")
check("- **Exploratory: K − R = +1.3 [−0.7, +3.7]** (7 / 3 / 90; p = 0.344)" in rep3k
      and (prose["k_ho_k_e"], prose["k_ho_k_ci"], prose["k_ho_k_bws"]) == ("+1.3", "[−0.7, +3.7]", "7 / 3 / 90"), "M3k exploratory in report")
check(f"T passed {prose['k_k_hT']}/300" not in rep3k and f"passed {prose['k_k_hT']}/300 ({prose['k_rate_hT']}%) against R's {prose['k_k_hR']}/300 ({prose['k_rate_hR']}%)" in rep3k
      and f"K passed {prose['k_k_hK']}/300 ({prose['k_rate_hK']}%)" in rep3k, "M3k pooled pass@1 in report")
check(f"| R | 5 (5.4) | 22 | {prose['k_ptok_hR']} |" in rep3k and f"| T | 6 (6.4) | 36 | {prose['k_ptok_hT']} (+{prose['k_ptok_tx']}%) |" in rep3k
      and f"| K | 5 (5.6) | 22 | {prose['k_ptok_hK']} (+{prose['k_ptok_kx']}%) |" in rep3k, "M3k tokens in report")
rep3k_1 = " ".join(rep3k.split())
check(f"It sent a message in {prose['k_fired_n']} of 300 held-out problem-runs ({prose['k_fired_problems']} problems). The model cleared all the findings in {prose['k_fired_cleared']} of them" in rep3k_1
      and f"| Runs where the check sent a message | {prose['k_fired_n']} ({m3k['fired_pass']} passed) in {prose['k_fired_problems']} problems |" in rep3k_1, "M3k firing counts")
check(m3k["fired_net"] == 0 and m3k["diff_fired"] == 0 and m3k["diff_n"] == 10, f"M3k: K and R differ on {m3k['diff_n']} problems, {m3k['diff_fired']} where K fired; net on fired {m3k['fired_net']}")
check(f"| Held-out (300 problem-runs) | $1.44 | ${prose['k_usd_hT']} | ${prose['k_usd_hK']} |" in rep3k
      and f"| The 86 (92 problems run) | $0.81 | ${prose['k_usd_dT']} | ${prose['k_usd_dK']} |" in rep3k
      and f"about **${float(prose['k_usd_scored']):.2f} of API credit**" in rep3k, "M3k cost in report")
check("**Status: DONE (2026-11-04). Decision: null.**" in rep3k, "M3k status in report")
# M3l (docs/reports/M3l_report.md and the ablate.py outputs beside it)
rep3l = open(os.path.join(REP, "M3l_report.md")).read()
rep3l_1 = " ".join(rep3l.split())
check(not l_clash, f"M3l prose keys clash with existing ones: {l_clash}")
check(len(L_IDS16) == 16 and len(L_HO_IDS) == 3 and all(len(l_rows[a]) == 80 for a in l_rows), "M3l: 16 problems, 5 runs per arm each")
check((l_eff["eff"], l_eff["better"], l_eff["worse"], l_eff["same"]) == l_chk, f"M3l effect {l_eff} vs recomputed {l_chk}")
check(f"**Primary: E − R over the 16 problems that receive an example = {prose['l_e']} points {prose['l_ci']}**" in rep3l_1
      and f"({l_eff['better']} problems better, {l_eff['worse']} worse, {l_eff['same']} the same; sign test p = {prose['l_p']})" in rep3l_1, "M3l primary in report")
check(f"R passed {prose['l_k_R']}/80 ({prose['l_rate_R']}%) and E {prose['l_k_E']}/80 ({prose['l_rate_E']}%)" in rep3l_1, "M3l pooled pass@1 in report")
check(f"**{prose['l_kept']} of the pack's {prose['l_pool']} reference entries** remain" in rep3l_1
      and f"**{prose['l_cov_ho']} of 100 held-out problems ({prose['l_cov_ho_pct']}%) and {prose['l_cov_dev']} of the 86 development problems ({prose['l_cov_dev_pct']}%)**" in rep3l_1, "M3l coverage in report")
check(f"estimated **${prose['l_usd_E']} for E and ${prose['l_usd_R']} for R**" in rep3l_1 and f"${prose['l_usd_scored']} for the four dispatches" in rep3l_1, "M3l cost in report")
check(f"{prose['l_ptok_E']} M against {prose['l_ptok_R']} M" in rep3l_1 and m3l["llm_error"] == 2 and m3l["overlap_withheld"] == 0, "M3l tokens, llm_error and overlap in report")
check(f"+6.7 [−4.0, +18.7] (4 / 1 / 10" in rep3l_1 and (prose["l_e15"], prose["l_ci15"]) == ("+6.7", "[−4.0, +18.7]"), "M3l 15-problem sensitivity in report")
check("**Status: DONE (2026-11-09). Decision: no detectable effect" in rep3l, "M3l status in report")
check(78.5 < spend_all < 79.5, f"spend M1 to M3g {spend_all}")
check(prose["proc_null"] == prose["proc_n"] == "11" and prose["proc_det"] == "0", f"process changes null {prose['proc_null']} of {prose['proc_n']}")

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
    unknown = []
    def put(m):
        if m.group(1) not in prose:
            unknown.append(m.group(1))
            return m.group(0)
        return f'<span data-d="{m.group(1)}">{prose[m.group(1)]}</span>'
    page2 = re.sub(r'<span data-d="([\w]+)">[^<]*</span>', put, page2)
    if unknown:
        sys.exit(f"unknown data-d keys in story.html: {unknown}")
    open(PAGE, "w").write(page2)
    print("injected data block into", PAGE)

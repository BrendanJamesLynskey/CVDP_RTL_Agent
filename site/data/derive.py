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

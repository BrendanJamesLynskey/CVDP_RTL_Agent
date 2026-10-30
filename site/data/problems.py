#!/usr/bin/env python3
"""Build the problem browser's data file, docs/problems.json (served next to docs/problems.html), from the committed CSVs and reports (stdlib).

    python3 site/data/problems.py --dataset <cvdp_v1.1.0_agentic_code_generation_no_commercial.jsonl>
    python3 site/data/problems.py            # no dataset: keep the task text already in docs/problems.json
    python3 site/data/problems.py --check    # recompute and fail if docs/problems.json differs (tests/test_site.py)

The task text (prompt and docs/ specifications) comes from the CVDP dataset record at the revision pinned in
.github/workflows/sweep.yml. It is CC BY 4.0 ("Dataset Non-Code", the dataset's LICENSE), so it is republished with
attribution. Given RTL and testbench files are code (Apache-2.0, or the upstream licence in the dataset's NOTICE):
only their names and sizes are listed. The hidden harness (`harness` in the record) and the `patch` field (its
keys name the files the reference solution writes, which the agent is never told) are never read into the output.

Every number in the output is computed here from the committed CSVs. The checks at the bottom compare the totals
with the milestone reports (docs/reports/*.md) and with tools/*_ids.txt, as site/data/derive.py does for the story
page. A mismatch fails the script.

The pass grid's arms are listed in GRID. An arm whose CSVs are not on disk yet (M3e) is left out, so adding it is a
data change: commit its CSVs and rerun this script.
"""
import collections
import csv
import glob
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REP = os.path.join(ROOT, "docs", "reports")
OUT = os.path.join(ROOT, "docs", "problems.json")
NOTES = os.path.join(ROOT, "site", "data", "problem_notes.json")
STORY = os.path.join(ROOT, "site", "data", "story_data.json")
PFX = "cvdp_agentic_"
HF = "https://huggingface.co/datasets/nvidia/cvdp-benchmark-dataset"
SPLIT = "cvdp_v1.1.0_agentic_code_generation_no_commercial.jsonl"
CONFIG = "cvdp_agentic_code_generation_no_commercial"

CID = {
    "cid003": "Spec to RTL",
    "cid004": "RTL modification",
    "cid005": "Spec to RTL, reusing given modules",
    "cid016": "Bug fixing",
}
CID_LONG = {
    "cid003": "Write a new design from a natural-language specification.",
    "cid004": "Change an existing, given design to add or alter behaviour.",
    "cid005": "Write a new design that instantiates and connects modules the task gives.",
    "cid016": "Find and fix the bugs in a given design.",
}
LABEL_WORDS = {
    "llm_error": "provider error or missed call deadline: no valid attempt",
    "agent_error": "the agent crashed",
    "killed": "the harness killed the agent",
    "no_edit": "finished without changing the RTL",
    "stopped_by_cap": "stopped by a turn, budget or wall-time cap",
    "gave_up": "the agent gave up",
    "sim_incomplete": "the hidden simulation did not finish",
    "compile_fail_own": "did not compile, in its own check either",
    "compile_fail_hidden": "compiled in its own check, not in the hidden build (interface or file mismatch)",
    "signal_missing_hidden": "the hidden test reads a name the design does not have",
    "tests_failed_selfcheck_passed": "hidden tests failed; its own testbench passed",
    "tests_failed_selfcheck_failed": "hidden tests failed; its own testbench failed too",
    "tests_failed_no_selfcheck": "hidden tests failed; it never ran a testbench of its own",
    "harness_error": "no test result in the harness log",
}


def rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def ids_file(name):
    return [l.strip() for l in open(os.path.join(ROOT, "tools", name)) if l.strip() and not l.startswith("#")]


def short(pid):
    return pid[len(PFX):] if pid.startswith(PFX) else pid


def run_files(pattern):
    """[(tag, run_id, rows)] for files named <tag>_<run>.csv, sorted by tag."""
    out = []
    for f in sorted(glob.glob(os.path.join(REP, pattern))):
        tag, run_id = os.path.basename(f)[:-4].split("_", 1)
        out.append((tag, run_id, rows(f)))
    return out


EVAL = ids_file("m3b_eval_ids.txt")
EXCL = ids_file("m3b_excluded_ids.txt")
BLIM = ids_file("benchmark_limited_ids.txt")


# ---- the pass grid: arms in display order. Each arm is one or more runs (columns). ----
def luna_arm(key, label, sub, pattern, desc):
    runs = run_files(pattern)
    return {"key": key, "label": label, "group": sub, "desc": desc,
            "cols": [{"tag": t, "run": rid, "rows": r} for t, rid, r in runs]}


def ladder_arm(key, label, stem):
    p = os.path.join(REP, "claude_code", "runs", stem + ".csv")
    return {"key": key, "label": label, "group": "Claude Code", "desc": f"Claude Code with {label}, 1 run (the ladder)",
            "cols": [{"tag": "1", "run": stem, "rows": rows(p)}] if os.path.exists(p) else []}


def refused_note(cols):
    n = sum(1 for c in cols for x in c["rows"] if x["stop_reason"] == "run_budget_exhausted")
    return f"; {n} problems refused by the whole-run cost guard before any LLM call, shown as failures" if n else ""


def m3e_arms():
    """M3e (brief 14): our LangGraph agent with Claude models through OpenRouter. One arm per model in the CSVs'
    `model` column, whatever the run tags are. Empty until its CSVs are committed."""
    by = collections.OrderedDict()
    for t, rid, r in run_files(os.path.join("m3e", "runs", "*.csv")):
        model = (r[0].get("requested_model") or r[0].get("model") or "").split("/")[-1]
        by.setdefault(model, []).append({"tag": t, "run": rid, "rows": r})
    out = []
    for model, cols in by.items():
        name = " ".join(w.capitalize() for w in model.replace("claude-", "").split("-"))
        name = re.sub(r"(\d) (\d)", r"\1.\2", name)
        out.append({"key": "m3e_" + re.sub(r"\W", "", model.replace("claude-", "").split("-")[0]),
                    "label": f"LG + {name}", "group": "M3e", "desc": f"our LangGraph agent with {model}, {len(cols)} run(s)" + refused_note(cols),
                    "cols": cols})
    return out


GRID = [
    luna_arm("m3c_A", "M3c A", "M3c", "m3c/runs/A*.csv", "our agent (LangGraph + gpt-6-luna), M3c's base arm, 3 runs"),
    luna_arm("m3d_A", "M3d A", "M3d", "m3d/runs/A*.csv", "our agent, M3d's base arm, 3 runs"),
    luna_arm("m3d_V", "M3d V", "M3d", "m3d/runs/V*.csv", "verify before submit, 3 runs"),
    luna_arm("m3d_S", "M3d S", "M3d", "m3d/runs/S*.csv", "verify before submit plus blind spec cases, 3 runs"),
    ladder_arm("cc_haiku", "Haiku 5.5", "claude-haiku-5-5"),
    ladder_arm("cc_sonnet", "Sonnet 5.5", "claude-sonnet-5-5"),
    ladder_arm("cc_opus", "Opus 5.5", "claude-opus-5-5"),
    ladder_arm("cc_fable", "Fable 5.1", "claude-fable-5-1"),
] + m3e_arms()
GRID = [a for a in GRID if a["cols"]]
CLAUDE = [a["key"] for a in GRID if a["group"] == "Claude Code"]

# ---- our agent: every arm-A run of LangGraph + gpt-6-luna on the evaluation problems ----
OURS = [("M3", "m3/runs/A*.csv"), ("M3b", "m3b/runs/A*.csv"), ("M3b confirm", "m3b/confirm_runs/A*.csv"),
        ("M3c", "m3c/runs/A*.csv"), ("M3d", "m3d/runs/A*.csv")]
ours_runs = []
for exp, pat in OURS:
    for t, rid, r in run_files(pat):
        ours_runs.append({"exp": exp, "tag": t, "run": rid, "rows": {x["id"]: x for x in r}})

# ---- dataset text ----
args = sys.argv[1:]
dataset = args[args.index("--dataset") + 1] if "--dataset" in args else None
old = json.load(open(OUT)) if os.path.exists(OUT) else None
records = {}
row_idx = {}
if dataset:
    import hashlib
    want = re.search(r"\| `agentic_code_generation_no_commercial` \| `([0-9a-f]+)` \|", open(os.path.join(ROOT, "README.md")).read()).group(1)
    got = hashlib.sha256(open(dataset, "rb").read()).hexdigest()
    if not got.startswith(want):
        sys.exit(f"{dataset}: sha256 {got[:16]} is not the pinned split ({want}, README.md)")
    with open(dataset) as f:
        for i, line in enumerate(f):
            r = json.loads(line)
            records[r["id"]] = r
            row_idx[r["id"]] = i  # the row in the Hugging Face viewer (the file's order; main is the pinned revision)
elif old is None:
    sys.exit("no problems.json yet: pass --dataset <agentic jsonl> (the revision pinned in sweep.yml)")
old_task = {p["id"]: p["task"] for p in old["problems"]} if old else {}
if not records:
    row_idx = {PFX + p["id"]: p["row"] for p in old["problems"]}
rev = re.search(r"DATASET_REV:\s*([0-9a-f]{40})", open(os.path.join(ROOT, ".github", "workflows", "sweep.yml")).read()).group(1)


def task_of(pid):
    """Prompt, docs/ specifications (CC BY 4.0) and the names and sizes of the given code files. Never harness."""
    if not records:
        return old_task[short(pid)]
    r = records[pid]
    docs, given = [], []
    for path, text in sorted(r["context"].items()):
        if path.startswith("docs/"):
            docs.append({"path": path, "md": text})
        else:
            given.append({"path": path, "lines": text.count("\n") + (0 if text.endswith("\n") or not text else 1)})
    return {"prompt": r["prompt"], "docs": docs, "given": given}


def cats_of(pid):
    if records:
        c = records[pid]["categories"]
        return c[0], c[1]
    p = next(p for p in old["problems"] if p["id"] == short(pid))
    return p["cid"], p["difficulty"]


ACRONYM = {"aes": "AES", "des": "DES", "apb": "APB", "axi": "AXI", "axis": "AXIS", "csr": "CSR", "fifo": "FIFO",
           "lfsr": "LFSR", "mii": "MII", "nmea": "NMEA", "gps": "GPS", "rc5": "RC5", "spi": "SPI", "uart": "UART",
           "crc": "CRC", "ttc": "TTC", "hdbn": "HDBn", "cic": "CIC", "fsm": "FSM", "ram": "RAM", "rom": "ROM",
           "alu": "ALU", "i2c": "I2C", "pwm": "PWM", "cdc": "CDC", "64b66b": "64b/66b", "dma": "DMA",
           "mac": "MAC", "ahb": "AHB", "gcd": "GCD", "lms": "LMS", "fir": "FIR", "iir": "IIR", "nco": "NCO",
           "bcd": "BCD", "sha": "SHA", "ecc": "ECC", "vga": "VGA", "usb": "USB", "jtag": "JTAG", "ldpc": "LDPC"}


def readable(pid):
    s = short(pid)
    m = re.match(r"(.*)_(\d{4})$", s)
    base, num = (m.group(1), m.group(2)) if m else (s, "")
    words = [ACRONYM.get(w.lower(), w) for w in base.split("_")]
    if words and words[0] == words[0].lower():
        words[0] = words[0].capitalize()
    return " ".join(words) + (f" #{num}" if num else "")


# ---- flags from the reports ----
rep_un = open(os.path.join(REP, "unsolved_analysis.md")).read()
summary = rep_un.split("## Summary", 1)[1]
un_class = {}
for m in re.finditer(r"^\| `([\w]+)` \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|$", summary, re.M):
    un_class[PFX + m.group(1)] = {"class": m.group(2).strip(), "evidence": m.group(3).strip().replace("`", ""),
                                  "counterfactual": m.group(4).strip().replace("`", ""), "own_tb": m.group(5).strip()}
part2_rows = {}
p2sec = rep_un.split("## Part two", 1)[1].split("## Summary", 1)[0]
for m in re.finditer(r"^\| `([\w]+)` \| (\d)/4 \|", p2sec, re.M):
    part2_rows[PFX + m.group(1)] = int(m.group(2))

rp = open(os.path.join(REP, "reachable_paths.md")).read()
paths = {}
for m in re.finditer(r"^\| `([\w]+)` \| (yes|no) \| `([^`]+)` \| `(\w+)` \| (\d+)/(\d+) \| (yes|no) \|$", rp, re.M):
    paths[PFX + m.group(1)] = {"path": m.group(3), "reason": m.group(4), "m3_iface": [int(m.group(5)), int(m.group(6))],
                               "would_exclude": m.group(7) == "yes"}
given_nc = {}
for m in re.finditer(r"^\| `([\w]+)` \| (yes|no) \| ((?:`[^`]+`(?:, )?)+) \|$", rp.split("## Note: given RTL", 1)[1], re.M):
    given_nc[PFX + m.group(1)] = re.findall(r"`([^`]+)`", m.group(3))

un_rep = open(os.path.join(REP, "m3b", "unreachable.md")).read()
excl_reason = {}
for m in re.finditer(r"^\| `([\w]+)` \| (cid\d+) \| (\d+)/(\d+) \| (.+) \|$", un_rep, re.M):
    excl_reason[PFX + m.group(1)] = {"m3_iface": [int(m.group(3)), int(m.group(4))], "names": m.group(5).strip()}
gi = {}
for m in re.finditer(r"^\| `([\w]+)` \| cid\d+ \| `[^`]*` \| (yes \((\w+)\)|no) \| (\d+) / (\d+) \|$",
                     open(os.path.join(REP, "m3c", "given_interface_eval86.md")).read(), re.M):
    gi[PFX + m.group(1)] = {"src": m.group(3) or "not given", "given": int(m.group(4)), "read": int(m.group(5))}
excl_runs = {}
for f in sorted(glob.glob(os.path.join(REP, "m3b", "runs_excluded", "*.csv"))):
    for x in rows(f):
        excl_runs.setdefault(x["id"], []).append(int(x["pass"]))

# ---- per-problem results ----
def cell(x):
    if x is None:
        return "-"
    if int(x["pass"]):
        return "1"
    return "e" if x["failure_label"] == "llm_error" else "0"


grid_rows = {a["key"]: [{x["id"]: x for x in c["rows"]} for c in a["cols"]] for a in GRID}
problems = []
for pid in EVAL + EXCL:
    cid, diff = cats_of(pid)
    p = {"id": short(pid), "name": readable(pid), "cid": cid, "difficulty": diff, "eval": pid in EVAL, "row": row_idx[pid]}
    if pid in EVAL:
        grid = {}
        labels = collections.Counter()
        solved_arms = 0
        for a in GRID:
            cells = "".join(cell(rr.get(pid)) for rr in grid_rows[a["key"]])
            grid[a["key"]] = cells
            solved_arms += "1" in cells
            for rr in grid_rows[a["key"]]:
                x = rr.get(pid)
                if x is not None and not int(x["pass"]):
                    labels[x["failure_label"]] += 1
        ok = [int(r["rows"][pid]["pass"]) for r in ours_runs if pid in r["rows"]]
        p.update({
            "grid": grid, "ours": [sum(ok), len(ok)], "solved_by": solved_arms,
            "labels": labels.most_common(3),
            "claude_pass": sum("1" in grid[k] for k in CLAUDE),
            "a_pass": grid["m3c_A"].count("1"),
            "iface": gi.get(pid),
        })
        flags = []
        if pid in BLIM:
            flags.append({"k": "blim", "t": "benchmark-limited (strong)", "why": un_class[pid]["evidence"],
                          "cf": un_class[pid]["counterfactual"]})
        elif pid in un_class and "borderline" in un_class[pid]["class"] and un_class[pid]["class"].startswith("benchmark"):
            flags.append({"k": "border", "t": "benchmark-limited (borderline)", "why": un_class[pid]["evidence"],
                          "cf": un_class[pid]["counterfactual"]})
        elif pid in un_class:
            flags.append({"k": "agentlim", "t": un_class[pid]["class"], "why": un_class[pid]["evidence"]})
        if pid in paths:
            q = paths[pid]
            flags.append({"k": "path", "t": "unreachable compiled path", "why": f"the hidden build compiles {q['path']} ({q['reason'].replace('_', ' ')})",
                          "excl": q["would_exclude"], "m3": q["m3_iface"]})
        if pid in given_nc:
            flags.append({"k": "given_nc", "t": "given RTL not compiled", "why": "the hidden build does not compile " + ", ".join(given_nc[pid])})
        p["flags"] = flags
        p["unsolved_claude"] = p["claude_pass"] == 0
        p["unsolved_all"] = solved_arms == 0
        p["claude_only"] = p["claude_pass"] >= 2 and p["a_pass"] == 0
        if pid in part2_rows:
            p["part2_claude"] = part2_rows[pid]
    else:
        r = excl_reason[pid]
        p.update({"excluded": {"names": r["names"].replace("`", ""), "m3_iface": r["m3_iface"],
                               "m3b": [sum(excl_runs.get(pid, [])), len(excl_runs.get(pid, []))]}})
    p["task"] = task_of(pid)
    problems.append(p)

# ---- notes: hand-written for the notable problems (problem_notes.json), data-driven for the rest ----
hand = json.load(open(NOTES)) if os.path.exists(NOTES) else {}
hand = {k: v for k, v in hand.items() if not k.startswith("_")}


def data_note(p):
    """A short note from the data alone, for the problems without a hand-written one."""
    t = p["task"]
    kind = {"cid003": "a spec-to-RTL task", "cid004": "a change to a given design",
            "cid005": "a new design that reuses given modules", "cid016": "a bug fix in a given design"}[p["cid"]]
    big = sum(len(d["md"]) for d in t["docs"]) + len(t["prompt"])
    size = "short" if big < 6000 else "long" if big > 20000 else "medium-length"
    k, n = p["ours"]
    claude = p["claude_pass"]
    if p["solved_by"] == len(GRID):
        lead = "Solved by every arm, though not in every run"
    elif k == 0:
        lead = "Never solved by our agent; some Claude Code runs solve it"
    elif k / n >= 2 / 3 and claude == len(CLAUDE):
        lead = "Easy for every agent here"
    elif k / n >= 2 / 3:
        lead = "Easy for our agent; not every Claude model solves it"
    elif k / n < 1 / 3:
        lead = "Hard for our agent, which passes it only now and then"
    else:
        lead = "Passed in some runs and not others: a coin flip for our agent"
    bits = [f"{kind}, with a {size} prompt and spec"]
    if any(g["path"].startswith("verif/") for g in t["given"]):
        bits.append("a testbench is given")
    gi = p.get("iface")
    if gi:
        if gi["src"] == "not given":
            bits.append("the top module's interface is not given")
        elif gi["given"] < gi["read"]:
            bits.append(f"the hidden test also reads names beyond the given interface ({gi['src']})")
        else:
            bits.append(f"the interface the hidden test reads is given (in the {gi['src']})")
    top = p["labels"][0][0] if p["labels"] else None
    tail = f" Most common failure: {LABEL_WORDS.get(top, top)}." if top else ""
    return f"{lead}. It is " + "; ".join(bits) + "." + tail


for p in problems:
    if not p["eval"]:
        p["note"] = {"by": "data", "text": "Not in the evaluation set: the hidden test reads names the task never gives "
                     "(tools/reachable.py), so no agent can be expected to match them."}
    elif p["id"] in hand:
        p["note"] = {"by": "hand", "text": hand[p["id"]]["note"]}
    else:
        p["note"] = {"by": "data", "text": data_note(p)}

data = {
    "source": {"dataset": "nvidia/cvdp-benchmark-dataset", "hf": HF, "split": SPLIT, "config": CONFIG, "revision": rev,
               "licence": "CC BY 4.0 (dataset non-code); code under Apache-2.0 or its upstream licence (dataset NOTICE)"},
    "cid": CID, "cid_long": CID_LONG, "label_words": LABEL_WORDS,
    "arms": [{"key": a["key"], "label": a["label"], "group": a["group"], "desc": a["desc"],
              "runs": [c["run"] for c in a["cols"]],
              "k": sum(int(x["pass"]) for c in a["cols"] for x in c["rows"] if x["id"] in EVAL),
              "n": sum(1 for c in a["cols"] for x in c["rows"] if x["id"] in EVAL)} for a in GRID],
    "ours": {"desc": "every arm-A run of our LangGraph agent with gpt-6-luna on the evaluation problems",
             "runs": [{"exp": r["exp"], "tag": r["tag"], "run": r["run"]} for r in ours_runs]},
    "problems": problems,
}

# ---- checks against the reports ----
errors = []


def check(cond, msg):
    if not cond:
        errors.append(msg)


ev = [p for p in problems if p["eval"]]
check(len(ev) == 86 and len(problems) == 92, f"problem counts {len(ev)} {len(problems)}")
check(all(len(p["task"]["prompt"]) > 0 for p in problems), "every problem has its prompt")
check(all(set(p["task"]) == {"prompt", "docs", "given"} for p in problems), "task holds only prompt, docs, given names")
# arm pass counts against each experiment's pooled table (| <arm> ... | k/n = r% |)
REPORT_TABLE = {"m3c_A": ("m3c/arms_paired_eval86.md", "A (base)"), "m3d_A": ("m3d/arms_paired_eval86.md", "A (base)"),
                "m3d_V": ("m3d/arms_paired_eval86.md", "V"), "m3d_S": ("m3d/arms_paired_eval86.md", "S"),
                "cc_haiku": ("claude_code/ladder_paired_eval86.md", "haiku"), "cc_sonnet": ("claude_code/ladder_paired_eval86.md", "sonnet"),
                "cc_opus": ("claude_code/ladder_paired_eval86.md", "opus"), "cc_fable": ("claude_code/ladder_paired_eval86.md", "fable")}
for a in data["arms"]:
    if a["key"] in REPORT_TABLE:
        f, lab = REPORT_TABLE[a["key"]]
        m = re.search(rf"^\| {re.escape(lab)} \| \d+: [^|]+ \| (\d+)/(\d+) = ", open(os.path.join(REP, f)).read(), re.M)
        check(m is not None and (a["k"], a["n"]) == (int(m.group(1)), int(m.group(2))), f"arm {a['key']} {a['k']}/{a['n']} vs {f}")
    elif a["group"] == "M3e":
        # M3e's full-86 view (the guard-refused problems counted as failures), as ablate.py printed it
        rep = glob.glob(os.path.join(REP, "m3e", "vs_luna_full86*.md"))
        lab = "LG+" + a["label"].split("+ ")[-1].split()[0]
        m = re.search(rf"^\| {re.escape(lab)} \| \d+: [^|]+ \| (\d+)/(\d+) = ", open(rep[0]).read(), re.M) if rep else None
        check(m is not None and (a["k"], a["n"]) == (int(m.group(1)), int(m.group(2))), f"M3e arm {a['key']} {a['k']}/{a['n']} vs {rep}")
    check(a["n"] == 86 * len(a["runs"]), f"arm {a['key']} rows {a['n']}")
    check(sum(p["grid"][a["key"]].count("1") for p in ev) == a["k"], f"arm {a['key']} grid sum")
story = json.load(open(STORY))
check({a["key"]: a["k"] for a in data["arms"] if a["key"] in REPORT_TABLE} ==
      {"m3c_A": story["m3c"]["arms"]["A"]["k"], "m3d_A": story["m3d"]["arms"]["A"]["k"], "m3d_V": story["m3d"]["arms"]["V"]["k"],
       "m3d_S": story["m3d"]["arms"]["S"]["k"], **{f"cc_{k}": v["k"] for k, v in story["ladder"]["arms"].items()}},
      "arm pass counts match story_data.json")
# our agent: the pooled arm-A counts each report prints
ours_k = collections.Counter()
for r in ours_runs:
    ours_k[r["exp"]] += sum(int(r["rows"][p]["pass"]) for p in EVAL)
    check(all(r["rows"][p]["model"] == "openai/gpt-6-luna" for p in EVAL), f"our run {r['run']} is luna")
check(len(ours_runs) == 17, f"our runs {len(ours_runs)}")
for exp, f in (("M3b", "m3b/arms_paired_eval86.md"), ("M3b confirm", "m3b/confirm_paired_eval86.md"),
               ("M3c", "m3c/arms_paired_eval86.md"), ("M3d", "m3d/arms_paired_eval86.md")):
    m = re.search(r"^\| A \(base\) \| \d+: [^|]+ \| (\d+)/(\d+) = ", open(os.path.join(REP, f)).read(), re.M)
    check(m is not None and ours_k[exp] == int(m.group(1)), f"our agent {exp} {ours_k[exp]} vs {f}")
check(sum(p["ours"][1] for p in ev) == 86 * 17, "our agent rows")
# the 12 unsolved, the 7 benchmark-limited, the 2 borderline, brief 09's part two
uns = sorted(p["id"] for p in ev if p["unsolved_claude"])
check(len(uns) == story["unsolved"]["n"] == 12, f"unsolved {len(uns)}")
check(sorted(PFX + u for u in uns) == sorted(un_class), f"unsolved = the report's twelve {set(uns) ^ {short(x) for x in un_class}}")
check(sum(1 for p in ev if p["unsolved_claude"] and p["a_pass"] == 0) == story["unsolved"]["never_A"] == 10, "unsolved never by arm A")
bl = sorted(p["id"] for p in ev if any(f["k"] == "blim" for f in p["flags"]))
check(len(bl) == story["unsolved"]["blim"] == 7 and bl == sorted(short(x) for x in BLIM), f"benchmark-limited {bl}")
check(sum(1 for p in ev if any(f["k"] == "border" for f in p["flags"])) == story["unsolved"]["border"] == 2, "borderline")
check(all(un_class[b]["class"] == "benchmark-limited (strong)" for b in BLIM), "IDs file = strong rows of the summary")
co = sorted(p["id"] for p in ev if p["claude_only"])
check(len(co) == story["unsolved"]["p2"] == 7 and sorted(PFX + c for c in co) == sorted(part2_rows), f"part two {co}")
check(all(p["claude_pass"] == p.get("part2_claude") for p in ev if p["claude_only"]), "part two Claude passes")
check(sum(1 for p in ev if all(p["grid"][k] == "1" for k in CLAUDE)) == story["ladder"]["all"], "ladder: all four solved")
check(sum(1 for p in ev if p["claude_pass"] > 0) == story["ladder"]["union"], "ladder: at least one solved")
check(sorted(PFX + p["id"] for p in ev if any(f["k"] == "path" for f in p["flags"])) == sorted(paths) and len(paths) == 4, "path flags")
check(sorted(PFX + p["id"] for p in problems if not p["eval"]) == sorted(EXCL) == sorted(excl_reason), "excluded six")
check(all(p["excluded"]["m3b"][0] == 0 and p["excluded"]["m3b"][1] == 12 for p in problems if not p["eval"]), "excluded sweeps 0/12 each")
check(len(gi) == 86 and sorted(gi) == sorted(EVAL), f"given-interface rows {len(gi)}")
check(collections.Counter(v["src"] for v in gi.values()) == {"rtl": 29, "doc": 25, "header": 15, "testbench": 9, "prompt": 5, "not given": 3}, "given-interface sources")
missing = sorted(set(hand) - {p["id"] for p in problems})
check(not missing, f"notes for unknown ids {missing}")

if errors:
    print("MISMATCH:\n  " + "\n  ".join(errors))
    sys.exit(1)
txt = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
if "--check" in args:
    if open(OUT, encoding="utf-8").read() != txt:
        sys.exit(f"{OUT} is stale: run python3 site/data/problems.py")
    print(f"ok: {OUT} matches the CSVs and reports")
    sys.exit(0)
open(OUT, "w", encoding="utf-8").write(txt)
nh = sum(1 for p in problems if p["note"]["by"] == "hand")
print(f"ok: {OUT} ({len(txt.encode()):,} bytes); {len(GRID)} arms; notes {nh} by hand, {len(problems) - nh} data-driven; all checks pass")

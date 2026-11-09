#!/usr/bin/env python3
"""M4: which CVDP 1.1.0 problems were attempted, which were left out, and why. Stdlib only.

Run from the repo root:

  python3 -I docs/reports/m4/coverage.py                        # check coverage.json against the repo's ids files and run CSVs
  python3 -I docs/reports/m4/coverage.py --dataset-dir DIR      # recompute every count from the dataset files in DIR and
                                                                #   compare with coverage.json (add --write to rewrite it)
  python3 -I docs/reports/m4/coverage.py --dataset-dir DIR --write --md   # also rewrite docs/reports/m4/coverage.md

DIR holds the CVDP 1.1.0 .jsonl files at the pinned revision (the SHA-256 sums are in coverage.json). The script reads
only `id`, `categories`, and the fields tools/m3g_heldout.py's eligible() reads (output and given file names, the
docker-compose and Dockerfile text). It never reads a prompt, a hidden test, a patch or a reference solution.

Counts and ids only are committed. The held-out 100 are counted, never listed here: their ids stay in
tools/m3g_heldout_ids.txt, and the site never names them.
"""
import argparse
import collections
import csv
import glob
import hashlib
import importlib.util
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT_JSON = os.path.join(ROOT, "docs", "reports", "m4", "coverage.json")
OUT_MD = os.path.join(ROOT, "docs", "reports", "m4", "coverage.md")
REVISION = "5b807d945f6a99aa645f7e43a64a2115e281b4bf"

# the seven problem files of CVDP 1.1.0: (key, file name, free = open tools only)
FILES = [
    ("agentic", "cvdp_v1.1.0_agentic_code_generation_no_commercial.jsonl", True),
    ("heavy", "cvdp_v1.1.0_agentic_heavy_code_generation_no_commercial.jsonl", True),
    ("copilot", "cvdp_v1.1.0_nonagentic_code_generation_no_commercial.jsonl", True),
    ("comprehension", "cvdp_v1.1.0_nonagentic_code_comprehension.jsonl", True),
    ("agentic_commercial", "cvdp_v1.1.0_agentic_code_generation_commercial.jsonl", False),
    ("heavy_commercial", "cvdp_v1.1.0_agentic_heavy_code_generation_commercial.jsonl", False),
    ("copilot_commercial", "cvdp_v1.1.0_nonagentic_code_generation_commercial.jsonl", False),
]
CATS = {"cid002": "RTL completion", "cid003": "spec to RTL", "cid004": "RTL modification",
        "cid005": "spec to RTL, module reuse", "cid006": "correspondence or question answering",
        "cid007": "code improvement", "cid008": "correspondence or question answering",
        "cid009": "correspondence or question answering", "cid010": "correspondence or question answering",
        "cid012": "testbench stimulus", "cid013": "testbench checker", "cid014": "assertion generation",
        "cid016": "bug fixing"}
# older release files in the same dataset repository; not used (the study is pinned to 1.1.0)
OLDER = "v1.0.2, v1.0.3 and v1.0.4 (not used: the study is pinned to 1.1.0)"
HEAVY_DIR = "cvdp_v1.1.0_agentic_heavy_code_generation_public: a README and 41 git bundles, not a problem file"


def read_ids(path):
    return [ln.strip() for ln in open(os.path.join(ROOT, path)) if ln.strip() and not ln.startswith("#")]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def m3g():
    spec = importlib.util.spec_from_file_location("m3g_heldout", os.path.join(ROOT, "tools", "m3g_heldout.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def by_cat(ids, cat_of):
    c = collections.Counter(cat_of[i] for i in ids)
    return {k: c[k] for k in sorted(c)}


def open_tools(g, row):
    """eligible()'s own test (open simulation image named, no commercial tool named), for either harness layout:
    the non-agentic rows keep their files under harness.files, the agentic rows directly under harness."""
    h = row["harness"]
    files = h.get("files", h)
    text = files.get("docker-compose.yml", "") + "".join(v for k, v in files.items() if k.startswith("Dockerfile"))
    return "__OSS_SIM_IMAGE__" in text and not any(c.lower() in text.lower() for c in g.COMMERCIAL)


def compute(dsdir):
    """Every count, recomputed from the dataset files."""
    g = m3g()
    rows, files, cat_of = {}, [], {}
    for key, name, free in FILES:
        path = os.path.join(dsdir, name)
        rs = g.load(path)
        rows[key] = rs
        ids = [r["id"] for r in rs]
        assert len(ids) == len(set(ids)), f"duplicate ids in {name}"
        for r in rs:
            cat_of[r["id"]] = r["categories"][0]
        files.append({"key": key, "file": name, "sha256_16": sha256_file(path)[:16], "free": free, "problems": len(rs),
                      "by_category": by_cat(ids, cat_of)})
    allids = [r["id"] for k in rows for r in rows[k]]
    assert len(allids) == len(set(allids)), "an id appears in two files"
    # commercial files: does any problem's harness text name only open tools? (eligible()'s own test)
    com = {}
    for key in ("agentic_commercial", "heavy_commercial", "copilot_commercial"):
        n_open = sum(1 for r in rows[key] if open_tools(g, r))
        com[key] = {"problems": len(rows[key]), "open_tools": n_open}
    # the held-out rule and its pool
    pool, excl = g.eligible(rows["copilot"], rows["agentic"])
    held = read_ids("tools/m3g_heldout_ids.txt")
    smoke = read_ids("tools/m3g_smoke_ids.txt")
    in_rule = [r["id"] for r in rows["copilot"] if r["categories"][0] in g.CATEGORIES]
    assert set(held) <= set(pool) and set(smoke) <= set(pool) and not set(held) & set(smoke)
    unsampled = sorted(set(pool) - set(held) - set(smoke))
    shared = sorted(i for i, why in excl.items() if why == "design name shared with an agentic problem")
    other_excl = sorted(set(excl) - set(shared))
    assert len(in_rule) == len(pool) + len(excl)
    # the other non-agentic categories, under the same rule with its category list widened
    saved = dict(g.CATEGORIES)
    g.CATEGORIES.update({"cid007": "code improvement", "cid016": "bug fixing"})
    pool2, excl2 = g.eligible(rows["copilot"], rows["agentic"])
    g.CATEGORIES.clear()
    g.CATEGORIES.update(saved)
    outside = sorted(r["id"] for r in rows["copilot"] if r["categories"][0] in ("cid007", "cid016"))
    would = sorted(set(pool2) & set(outside))
    would_shared = sorted(i for i in outside if excl2.get(i) == "design name shared with an agentic problem")
    would_other = sorted(i for i in outside if i in excl2 and i not in would_shared)
    assert set(held) | set(smoke) | set(unsampled) | set(shared) | set(other_excl) | set(outside) == {r["id"] for r in rows["copilot"]}
    dev = read_ids("tools/m3b_eval_ids.txt")
    excl6 = read_ids("tools/m3b_excluded_ids.txt")
    assert sorted(dev + excl6) == sorted(r["id"] for r in rows["agentic"])
    heavy_ids = sorted(r["id"] for r in rows["heavy"])
    comp_ids = sorted(r["id"] for r in rows["comprehension"])
    return {
        "files": files, "commercial_check": com, "cat_of": cat_of,
        "parts": {
            "agentic_dev86": {"ids": sorted(dev), "by_category": by_cat(dev, cat_of)},
            "agentic_excluded6": {"ids": sorted(excl6), "by_category": by_cat(excl6, cat_of)},
            "heavy_all": {"ids": heavy_ids, "by_category": by_cat(heavy_ids, cat_of)},
            "copilot_heldout100": {"n": len(held), "by_category": by_cat(held, cat_of)},
            "copilot_smoke3": {"ids": sorted(smoke), "by_category": by_cat(smoke, cat_of)},
            "copilot_unsampled": {"ids": unsampled, "by_category": by_cat(unsampled, cat_of)},
            "copilot_name_shared": {"ids": shared, "by_category": by_cat(shared, cat_of)},
            "copilot_other_excluded": {"ids": other_excl, "by_category": by_cat(other_excl, cat_of)},
            "copilot_cid007_cid016": {"ids": outside, "by_category": by_cat(outside, cat_of),
                                      "eligible_under_other_rules": len(would), "eligible_by_category": by_cat(would, cat_of),
                                      "name_shared": len(would_shared), "name_shared_by_category": by_cat(would_shared, cat_of),
                                      "other_exclusion": len(would_other)},
            "comprehension_all": {"ids": comp_ids, "by_category": by_cat(comp_ids, cat_of)},
        },
        "pool": len(pool), "in_rule": len(in_rule),
    }


# ---- the committed record -------------------------------------------------------------------------------------------

def table_rows(c):
    """The one table: a row per (file, part). status is one of attempted, smoke only, left out by rule, never run, cannot be run."""
    p = c["parts"]
    n = lambda k: len(p[k]["ids"]) if "ids" in p[k] else p[k]["n"]
    f = {x["key"]: x for x in c["files"]}
    return [
        {"file": "agentic_code_generation_no_commercial", "part": "the 86 development problems", "n": n("agentic_dev86"),
         "by_category": p["agentic_dev86"]["by_category"], "status": "attempted",
         "where": "M2, M3, M3b to M3l, the Claude Code ladder (tools/m3b_eval_ids.txt)",
         "reason": ""},
        {"file": "agentic_code_generation_no_commercial", "part": "the 6 problems excluded from the development set", "n": n("agentic_excluded6"),
         "by_category": p["agentic_excluded6"]["by_category"], "status": "attempted",
         "where": "M2 and M3 (all 92 problems); left out of the 86 from M3b on, run only in M3b's own excluded-problem sweeps (tools/m3b_excluded_ids.txt)",
         "reason": "the hidden testbench reads signal or parameter names the task never gives (tools/reachable.py, docs/reports/m3b/unreachable.md)"},
        {"file": "agentic_heavy_code_generation_no_commercial", "part": "all", "n": n("heavy_all"),
         "by_category": p["heavy_all"]["by_category"], "status": "never run",
         "where": "M0 and M1 null agent only (no edits, to check the harness); never run with a model",
         "reason": "the agent's file tool writes only under rtl/, verif/ and docs/, and in 53 of the 75 problems the hidden tests read files elsewhere; "
                   "the design tree is a git workspace volume, not a bind mount, so no agent run was tried; 3 i2c problems produced no test output under the null agent (docs/reports/M1_report.md, Known gaps)"},
        {"file": "nonagentic_code_generation_no_commercial", "part": "the held-out 100", "n": n("copilot_heldout100"),
         "by_category": p["copilot_heldout100"]["by_category"], "status": "attempted",
         "where": "M3g to M3k, and 3 of them in M3l (tools/m3g_heldout_ids.txt; counted here, never named on the site)", "reason": ""},
        {"file": "nonagentic_code_generation_no_commercial", "part": "3 smoke problems", "n": n("copilot_smoke3"),
         "by_category": p["copilot_smoke3"]["by_category"], "status": "smoke only",
         "where": "M3g smoke runs, not scored (tools/m3g_smoke_ids.txt)", "reason": "kept apart from the 100 on purpose"},
        {"file": "nonagentic_code_generation_no_commercial", "part": "eligible, not sampled", "n": n("copilot_unsampled"),
         "by_category": p["copilot_unsampled"]["by_category"], "status": "left out by rule",
         "where": "", "reason": "the freeze rule samples 100 of the 193 eligible problems (seed 20261030) when more than 120 are eligible; the reports record no reason for 100"},
        {"file": "nonagentic_code_generation_no_commercial", "part": "design name shared with an agentic problem", "n": n("copilot_name_shared"),
         "by_category": p["copilot_name_shared"]["by_category"], "status": "left out by rule",
         "where": "", "reason": "so the held-out set shares no design with the 92 agentic problems the agent was developed on (tools/m3g_heldout.py)"},
        {"file": "nonagentic_code_generation_no_commercial", "part": "code improvement and bug fixing", "n": n("copilot_cid007_cid016"),
         "by_category": p["copilot_cid007_cid016"]["by_category"], "status": "left out by rule",
         "where": "", "reason": "the held-out rule took only cid002, cid003 and cid004. The M3g pre-registration records no reason for leaving out cid007 and cid016. "
                   "Under the rule's other conditions %d of these %d would have been eligible (%s); the other %d share a design name with an agentic problem"
                   % (p["copilot_cid007_cid016"]["eligible_under_other_rules"], n("copilot_cid007_cid016"),
                      ", ".join("%s %d" % kv for kv in p["copilot_cid007_cid016"]["eligible_by_category"].items()),
                      p["copilot_cid007_cid016"]["name_shared"])},
        {"file": "nonagentic_code_comprehension", "part": "all", "n": n("comprehension_all"),
         "by_category": p["comprehension_all"]["by_category"], "status": "never run",
         "where": "", "reason": "correspondence and question-answering tasks, not RTL to write, change or fix; outside what the project set out to do. No separate decision is recorded"},
        {"file": "agentic_code_generation_commercial", "part": "all", "n": f["agentic_commercial"]["problems"],
         "by_category": f["agentic_commercial"]["by_category"], "status": "cannot be run", "where": "",
         "reason": "needs Cadence Xcelium, a commercial simulator"},
        {"file": "agentic_heavy_code_generation_commercial", "part": "all", "n": f["heavy_commercial"]["problems"],
         "by_category": f["heavy_commercial"]["by_category"], "status": "cannot be run", "where": "",
         "reason": "needs Cadence Xcelium, a commercial simulator"},
        {"file": "nonagentic_code_generation_commercial", "part": "all", "n": f["copilot_commercial"]["problems"],
         "by_category": f["copilot_commercial"]["by_category"], "status": "cannot be run", "where": "",
         "reason": "needs Cadence Xcelium, a commercial simulator"},
    ]


def summary(rows):
    s = collections.Counter()
    for r in rows:
        s[r["status"]] += r["n"]
    return dict(s)


def build_record(c):
    rows = table_rows(c)
    for r in rows:
        r["by_category"] = dict(r["by_category"])
    return {
        "dataset": "nvidia/cvdp-benchmark-dataset", "revision": REVISION, "release": "1.1.0",
        "files": [{k: v for k, v in x.items()} for x in c["files"]],
        "older_release_files_not_used": OLDER, "heavy_directory": HEAVY_DIR,
        "total_problems": sum(x["problems"] for x in c["files"]),
        "table": rows, "summary": summary(rows),
        "commercial_check": c["commercial_check"],
        "copilot_rule": {"in_rule_categories": c["in_rule"], "eligible": c["pool"], "excluded_name_shared": len(c["parts"]["copilot_name_shared"]["ids"]),
                         "excluded_other": len(c["parts"]["copilot_other_excluded"]["ids"])},
        "ids": {k: v["ids"] for k, v in c["parts"].items() if "ids" in v and k not in ("agentic_dev86", "agentic_excluded6")},
    }


def render_md(rec):
    short = {"agentic_code_generation_no_commercial": "agentic, free", "agentic_heavy_code_generation_no_commercial": "agentic heavy, free",
             "nonagentic_code_generation_no_commercial": "non-agentic code generation, free", "nonagentic_code_comprehension": "non-agentic comprehension, free",
             "agentic_code_generation_commercial": "agentic, commercial", "agentic_heavy_code_generation_commercial": "agentic heavy, commercial",
             "nonagentic_code_generation_commercial": "non-agentic code generation, commercial"}
    o = ["# M4: which problems were attempted, and which were left out", "",
         "Every problem file of CVDP 1.1.0 at revision `%s`, with the problems each run covered and the reason for each omission." % rec["revision"],
         "Made by `docs/reports/m4/coverage.py` (stdlib only; `--dataset-dir` recomputes every count from the dataset files, with no flag it checks",
         "`coverage.json` against the ids files and run CSVs in this repo). Counts are by the problem's first category.", "",
         "## In short", ""]
    s = rec["summary"]
    o += ["- **%d problems in the %d files.** %d were scored (the agentic 92 and the held-out 100), and 3 more ran as smoke checks only." % (
              rec["total_problems"], len(rec["files"]), s["attempted"]),
          "- **%d were left out by rule or never run, although they are in the free (open-tool) files:** %d left out by rule (%d name shared with an agentic problem, %d not sampled, %d code improvement and bug fixing outside the held-out rule), %d never run (the heavy split and the comprehension file)." % (
              s["left out by rule"] + s["never run"], s["left out by rule"], rec["table"][6]["n"], rec["table"][5]["n"], rec["table"][7]["n"], s["never run"]),
          "- **%d cannot be run** here: they need Cadence Xcelium, a commercial simulator. They hold the verification-writing categories cid012 to cid014." % s["cannot be run"],
          "", "## The table", "",
          "| File | Part | Problems | By category | Status | Run in | Why |", "|---|---|---|---|---|---|---|"]
    for r in rec["table"]:
        cats = "; ".join("%s %s %d" % (k, CATS[k], v) for k, v in r["by_category"].items())
        o.append("| `%s` | %s | %d | %s | %s | %s | %s |" % (r["file"], r["part"], r["n"], cats, r["status"], r["where"] or "", r["reason"] or ""))
    o += ["", "## The files", "", "| File (`cvdp_v1.1.0_` prefix) | SHA-256 (first 16) | Free (open tools) | Problems | By category |", "|---|---|---|---|---|"]
    for x in rec["files"]:
        o.append("| `%s` | `%s` | %s | %d | %s |" % (x["file"].replace("cvdp_v1.1.0_", ""), x["sha256_16"], "yes" if x["free"] else "no, commercial", x["problems"],
                                                   "; ".join("%s %d" % kv for kv in x["by_category"].items())))
    o += ["", "Also in the dataset repository at this revision: the directory %s; and older release files, %s." % (rec["heavy_directory"], rec["older_release_files_not_used"]),
          "", "## Notes", "",
          "- **The commercial files.** The same test as `tools/m3g_heldout.py` (open simulation image named, no commercial tool named) finds no problem in them that names open tools only:",
          "  open-tool-only problems in agentic commercial: %d of %d; heavy commercial: %d of %d; non-agentic commercial: %d of %d." % (
              rec["commercial_check"]["agentic_commercial"]["open_tools"], rec["commercial_check"]["agentic_commercial"]["problems"],
              rec["commercial_check"]["heavy_commercial"]["open_tools"], rec["commercial_check"]["heavy_commercial"]["problems"],
              rec["commercial_check"]["copilot_commercial"]["open_tools"], rec["commercial_check"]["copilot_commercial"]["problems"]),
          "- **No reason was recorded** for leaving cid007 and cid016 out of the held-out rule, or for choosing 100 of the 193 eligible. The table says so rather than supply one.",
          "- **The verification categories cid012 to cid014 are in no free file.** The free files hold cid002 to cid010 and cid016.",
          "- **Code improvement (cid007) is in the free split**: the non-agentic code-generation file has %d such problems. None was run." % rec["table"][7]["by_category"].get("cid007", 0),
          "- Held-out ids are not listed here. `coverage.json` carries ids only for the problems that were not scored."]
    return "\n".join(o) + "\n"


# ---- offline check: coverage.json against the repo --------------------------------------------------------------------

def csv_ids_by_cat(pattern):
    out = {}
    for f in sorted(glob.glob(os.path.join(ROOT, pattern))):
        for r in csv.DictReader(open(f)):
            out[r["id"]] = r["cid"]
    return out


def offline(rec):
    err = []
    ck = lambda cond, msg: err.append(msg) if not cond else None
    rows = {(r["file"], r["part"]): r for r in rec["table"]}
    dev, ex = read_ids("tools/m3b_eval_ids.txt"), read_ids("tools/m3b_excluded_ids.txt")
    held, smoke = read_ids("tools/m3g_heldout_ids.txt"), read_ids("tools/m3g_smoke_ids.txt")
    m2 = csv_ids_by_cat("docs/reports/m2/x86/results_gpt-6-luna_default.csv")
    ck(len(dev) == 86 and len(ex) == 6 and sorted(dev + ex) == sorted(m2), "the 86 + 6 are the 92 problems of M2")
    ck(rows[("agentic_code_generation_no_commercial", "the 86 development problems")]["n"] == 86, "table: 86")
    ck(rows[("agentic_code_generation_no_commercial", "the 6 problems excluded from the development set")]["n"] == 6, "table: 6")
    for name, ids in (("the 86 development problems", dev), ("the 6 problems excluded from the development set", ex)):
        c = collections.Counter(m2[i] for i in ids)
        ck(rows[("agentic_code_generation_no_commercial", name)]["by_category"] == {k: c[k] for k in sorted(c)}, "by category: " + name)
    # every one of the 92 has a row in every M3 sweep
    for pat in ("docs/reports/m3/runs/A?_*.csv",):
        for f in sorted(glob.glob(os.path.join(ROOT, pat))):
            ck({r["id"] for r in csv.DictReader(open(f))} == set(m2), "M3 sweep covers the 92: " + os.path.basename(f))
    ex_run = set()
    for f in glob.glob(os.path.join(ROOT, "docs/reports/m3b/runs_excluded/*.csv")):
        ex_run |= {r["id"] for r in csv.DictReader(open(f))}
    ck(ex_run == set(ex), "M3b's excluded-problem sweeps cover the 6")
    # held-out header
    hdr = "\n".join(l for l in open(os.path.join(ROOT, "tools", "m3g_heldout_ids.txt")) if l.startswith("#"))
    ho = rows[("nonagentic_code_generation_no_commercial", "the held-out 100")]
    ck(len(held) == 100 == ho["n"], "held-out 100")
    for cid, k in ho["by_category"].items():
        ck(("%s (%s) %d" % (cid, CATS[cid], k)) in hdr, "held-out header category " + cid)
    ck(len(smoke) == 3 == rows[("nonagentic_code_generation_no_commercial", "3 smoke problems")]["n"] and not set(smoke) & set(held), "smoke 3")
    ck("eligible: %d; excluded from %d: design name shared with an agentic problem %d" % (
        rec["copilot_rule"]["eligible"], rec["copilot_rule"]["in_rule_categories"], rec["copilot_rule"]["excluded_name_shared"]) in hdr, "freeze header counts")
    ck(rec["copilot_rule"]["excluded_other"] == 0, "no other exclusion reason in the rule")
    # the held-out ids never appear in coverage.json
    text = open(OUT_JSON).read()
    ck(not [i for i in held if i in text], "no held-out id in coverage.json")
    # internal sums
    ck(sum(r["n"] for r in rec["table"]) == rec["total_problems"] == sum(x["problems"] for x in rec["files"]), "table sums to the files")
    for x in rec["files"]:
        ck(sum(x["by_category"].values()) == x["problems"], "file sums: " + x["key"])
    byfile = collections.defaultdict(int)
    for r in rec["table"]:
        byfile[r["file"]] += r["n"]
    for x in rec["files"]:
        ck(byfile[x["file"].replace("cvdp_v1.1.0_", "").replace(".jsonl", "")] == x["problems"], "parts sum to file: " + x["key"])
    cp = rows[("nonagentic_code_generation_no_commercial", "eligible, not sampled")]["n"]
    ck(cp + 100 + 3 == rec["copilot_rule"]["eligible"], "193 = 100 + 3 + not sampled")
    ck(set(rec["summary"]) <= {"attempted", "smoke only", "left out by rule", "never run", "cannot be run"}, "status words")
    free_cats = {c for x in rec["files"] if x["free"] for c in x["by_category"]}
    ck(not free_cats & {"cid012", "cid013", "cid014"}, "cid012 to cid014 are in no free file")
    ck(all(v["open_tools"] == 0 for v in rec["commercial_check"].values()), "commercial files name a commercial tool throughout")
    return err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset-dir", default="")
    ap.add_argument("--write", action="store_true", help="with --dataset-dir: rewrite coverage.json")
    ap.add_argument("--md", action="store_true", help="rewrite coverage.md from coverage.json")
    a = ap.parse_args()
    if a.dataset_dir:
        rec = build_record(compute(a.dataset_dir))
        if a.write:
            with open(OUT_JSON, "w") as f:
                json.dump(rec, f, indent=1)
                f.write("\n")
            print("wrote", OUT_JSON)
        elif json.load(open(OUT_JSON)) != json.loads(json.dumps(rec)):
            sys.exit("coverage.json differs from the dataset recomputation; rerun with --write and review the diff")
        else:
            print("dataset recomputation matches coverage.json")
    rec = json.load(open(OUT_JSON))
    if a.md:
        open(OUT_MD, "w").write(render_md(rec))
        print("wrote", OUT_MD)
    err = offline(rec)
    if err:
        sys.exit("coverage check failed:\n  " + "\n  ".join(err))
    if os.path.exists(OUT_MD) and open(OUT_MD).read() != render_md(rec):
        sys.exit("coverage.md is stale: rerun with --md")
    print("ok: coverage.json agrees with the ids files and run CSVs (%d problems in %d files)" % (rec["total_problems"], len(rec["files"])))


if __name__ == "__main__":
    main()

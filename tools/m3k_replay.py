"""M3k: replay arm K's pre-submit check offline, with no model call, on the final RTL of finished runs.

For each problem-run in a downloaded sweep artifact (`gh run download <id>`), rebuild the task tree the agent saw
(prompt.json and the context files from work.problems.jsonl; the reference patch and the harness files in that
file are never read), read the given interface from it, apply the agent's own `agent_changes.patch` (its final
RTL), and run the check. Only a run that ended with `submit` is checked (K runs only at a submit).

Usage: python3 tools/m3k_replay.py <artifact dir>... [--csv out.csv] [--md-out out.md]
Needs pyslang (agent/requirements.txt); Yosys is used as the fallback if installed."""
import argparse
import collections
import csv
import glob
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

from cvdp_agent.presubmit import PresubmitCheck  # noqa: E402


def rebuild(rec, patch_text, dest):
    """Write the task tree the agent started with into dest; return it. The patch is applied by the caller."""
    os.makedirs(dest, exist_ok=True)
    with open(os.path.join(dest, "prompt.json"), "w") as f:
        json.dump({"prompt": rec.get("prompt", "")}, f)
    for rel, text in (rec.get("context") or {}).items():
        full = os.path.join(dest, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(text if isinstance(text, str) else "")
    return dest


def replay_run(art):
    """Rows for one artifact directory (the one `gh run download` made)."""
    base = glob.glob(os.path.join(art, "*"))
    base = base[0] if len(base) == 1 and os.path.isdir(base[0]) else art
    probs = {}
    with open(os.path.join(base, "work.problems.jsonl")) as f:
        for ln in f:
            r = json.loads(ln)
            probs[r["id"]] = r
    rows = []
    with open(os.path.join(base, "work", "results.csv")) as f:
        results = list(csv.DictReader(f))
    for row in results:
        pid, seed = row["id"], row["seed"]
        out = {"run": os.path.basename(art), "id": pid, "seed": seed, "pass": row.get("pass", ""),
               "label": row.get("failure_label", ""), "stop": row.get("stop_reason", ""), "checked": 0,
               "findings_n": 0, "kinds": "", "first": ""}
        parts = pid.split("_")
        d = os.path.join(base, "work", f"seed{seed}", "_".join(parts[:-1]), "harness", str(int(parts[-1])))
        patch = os.path.join(d, "agent_changes.patch")
        if row.get("stop_reason") != "submit" or pid not in probs:
            rows.append(out)
            continue
        with tempfile.TemporaryDirectory() as tmp:
            root = rebuild(probs[pid], "", os.path.join(tmp, "code"))
            chk = PresubmitCheck(root)  # the given interface is read before the patch is applied
            if os.path.isfile(patch) and os.path.getsize(patch):
                subprocess.run(["patch", "-s", "-p1", "-d", root, "-i", os.path.abspath(patch)],
                               capture_output=True, check=False)
            res = chk.check()
        out.update(checked=1, findings_n=len(res["findings"]),
                   kinds="+".join(sorted({f["kind"] for f in res["findings"]})),
                   first="; ".join(f["detail"] for f in res["findings"][:3])[:300])
        rows.append(out)
    return rows


def summarise(rows):
    chk = [r for r in rows if r["checked"]]
    fired = [r for r in chk if r["findings_n"]]
    fail = [r for r in chk if r["pass"] == "0"]
    ok = [r for r in chk if r["pass"] == "1"]
    ff = [r for r in fired if r["pass"] == "0"]
    fp = [r for r in fired if r["pass"] == "1"]
    lab = collections.Counter(r["label"] or "(none)" for r in ff)
    kinds = collections.Counter(k for r in fired for k in r["kinds"].split("+"))
    return {"problem_runs": len(rows), "checked": len(chk), "fires": len(fired), "failing_checked": len(fail),
            "passing_checked": len(ok), "fires_on_failing": len(ff), "fires_on_passing": len(fp),
            "labels_of_failing_fires": dict(lab), "kinds": dict(kinds)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("artifacts", nargs="+")
    ap.add_argument("--csv")
    a = ap.parse_args()
    rows = []
    for art in a.artifacts:
        rows += replay_run(art)
    if a.csv:
        with open(a.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    print(json.dumps(summarise(rows), indent=1))


if __name__ == "__main__":
    main()

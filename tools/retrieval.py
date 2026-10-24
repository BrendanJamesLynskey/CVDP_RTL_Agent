"""Which lessons a snapshot gives each problem, and how often each lesson is retrieved. The same deterministic BM25
retrieval the agent runs (cvdp_agent.memory.retrieve, k=5), queried with what the agent queries with: the task
prompt and the problem's docs/ files. From the dataset, so it needs no run.

With --runs, it counts instead what the agents' summaries say they retrieved (the `lessons` field), over the work
dirs of real runs.

Usage: python3 tools/retrieval.py <snapshot.json> <dataset.jsonl> [--ids tools/m3b_eval_ids.txt] [--k 5]
       python3 tools/retrieval.py <snapshot.json> --runs <work_dir> [<work_dir> ...]
"""
import argparse
import collections
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

from cvdp_agent import memory  # noqa: E402
from cvdp_agent.files import TEXT_EXT  # noqa: E402  (the agent's own list, so the query is the agent's)


def from_dataset(snap, dataset, ids=None, k=5):
    out = {}
    for ln in open(dataset):
        if not ln.strip():
            continue
        rec = json.loads(ln)
        if ids and rec["id"] not in ids:
            continue
        docs = "\n".join(v or "" for p, v in sorted((rec.get("context") or {}).items())
                         if p.startswith("docs/") and os.path.splitext(p)[1] in TEXT_EXT)
        out[rec["id"]] = [x["id"] for x, _ in memory.retrieve(snap["lessons"], f"{rec.get('prompt', '')}\n{docs}", k)]
    return out


def from_runs(works):
    out = {}
    for w in works:
        for s in glob.glob(os.path.join(w, "**", "agent_out", "summary.json"), recursive=True):
            summ = json.load(open(s))
            if summ.get("lessons") is not None:
                out[os.path.relpath(s, w)] = summ["lessons"]
    return out


def table(snap, picks):
    counts = collections.Counter(i for v in picks.values() for i in v)
    lines = [f"Snapshot `{snap['hash']}`: {len(snap['lessons'])} lessons, retrieved for {len(picks)} problems.\n",
             "| Lesson | Retrieved for | Text |", "|---|---|---|"]
    for x in snap["lessons"]:
        lines.append(f"| {x['id']} | {counts.get(x['id'], 0)} | {x['text']} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("snapshot")
    ap.add_argument("dataset", nargs="?")
    ap.add_argument("--ids")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--runs", nargs="*")
    a = ap.parse_args(argv)
    snap = memory.load(a.snapshot)
    if a.runs:
        picks = from_runs(a.runs)
    else:
        ids = {ln.strip() for ln in open(a.ids) if ln.strip() and not ln.startswith("#")} if a.ids else None
        picks = from_dataset(snap, a.dataset, ids, a.k)
    print(table(snap, picks))


if __name__ == "__main__":
    main()

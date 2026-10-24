"""The M3b learning set the agent can actually work on: the heavy problems whose files to change all lie inside the
agent's edit roots (`cvdp_agent.files.EDIT_ROOTS`: rtl/, verif/, docs/). Deterministic, from the dataset alone; no
LLM and no run.

"Files to change" are the keys of the record's `patch` (the files the reference solution changes). A problem is
kept when every one of them starts with an edit root. The agent's file policy refuses writes anywhere else, so on
the other heavy problems it cannot make the reference change, and lessons learned from those failures would be
about the policy, not about RTL. The order is that of tools/m3b_learn_ids.txt (the full heavy split, kept for the
record), and the output is a subset of it.

Usage: python3 tools/learn_in_roots.py <agentic_heavy_code_generation_no_commercial.jsonl>
           [--out tools/m3b_learn_in_roots_ids.txt]
"""
import argparse
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

from cvdp_agent.files import EDIT_ROOTS  # noqa: E402

LEARN_IDS = os.path.join(HERE, "m3b_learn_ids.txt")


def read_ids(path):
    return [ln.strip() for ln in open(path) if ln.strip() and not ln.startswith("#")]


def in_roots(record, roots=EDIT_ROOTS):
    files = list((record.get("patch") or {}).keys())
    return bool(files) and all(f.split("/", 1)[0] in roots for f in files)


def select(records, order):
    by_id = {r["id"]: r for r in records}
    missing = [i for i in order if i not in by_id]
    if missing:
        raise ValueError(f"{len(missing)} learning-set ids are not in the dataset ({', '.join(missing[:3])})")
    return [i for i in order if in_roots(by_id[i])]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset")
    ap.add_argument("--learn-ids", default=LEARN_IDS)
    ap.add_argument("--out", default=os.path.join(HERE, "m3b_learn_in_roots_ids.txt"))
    a = ap.parse_args(argv)
    raw = open(a.dataset, "rb").read()
    records = [json.loads(ln) for ln in raw.decode().splitlines() if ln.strip()]
    order = read_ids(a.learn_ids)
    kept = select(records, order)
    with open(a.out, "w") as f:
        f.write(f"# M3b learning set: the {len(kept)} of the {len(order)} heavy problems (tools/m3b_learn_ids.txt) whose\n"
                f"# files to change (the keys of the record's `patch`) all lie inside the agent's edit roots\n"
                f"# ({', '.join(r + '/' for r in EDIT_ROOTS)}). Made by tools/learn_in_roots.py from\n"
                f"# {os.path.basename(a.dataset)} (SHA-256 {hashlib.sha256(raw).hexdigest()[:16]}...).\n"
                "# The lessons memory learns only from these.\n")
        f.writelines(i + "\n" for i in kept)
    print(f"{len(kept)} of {len(order)} -> {a.out}")


if __name__ == "__main__":
    main()

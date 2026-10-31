"""M3h descriptive secondary: problem-runs whose own files reproduce pack text, per arm and per skill.

    python3 tools/m3h_copied.py --pack <generic dir> [--public DIR ...] --arm NAME=artifact_dir[,withheld.csv...] ...

For each arm, scans the model-written files left in its downloaded sweep artifacts (agent_changes.patch, agent_out,
agent_tb, report logs) with the leak guard's matcher, and adds the rows of the sweep's withheld.csv (files the
guard removed before upload). Run it with the same `--public` set for every arm, so the arms are comparable: in
particular without the repo's public copy of v1.0, which the workflow allows for v1.0 arms only. Prints names and
counts only, never text. Local use: the pack directory is the private checkout.
"""
import argparse
import collections
import csv
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import leak_guard  # noqa: E402


def arm_hits(pack, pub, spec):
    """{(id, seed): set(skills)} for one arm."""
    hits = collections.defaultdict(set)
    for part in spec.split(","):
        if part.endswith(".csv"):
            for r in csv.DictReader(open(part)):
                hits[(r["id"], r["seed"])].add(r["skill"])
            continue
        for work in glob.glob(os.path.join(part, "**", "work"), recursive=True):
            for f, _, _, lab, _ in leak_guard.scan(pack, [work], pub):
                key = leak_guard.model_file(f, work)
                if key:
                    hits[key].add(lab)
    return hits


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", required=True)
    ap.add_argument("--public", action="append", default=[])
    ap.add_argument("--arm", action="append", required=True, help="NAME=dir[,withheld.csv,...]; runs counted: "
                    "NAME:N=... gives the number of problem-runs for the share")
    a = ap.parse_args(argv)
    pub = leak_guard.Public(a.public)
    out = ["| Arm | Problem-runs | Reproducing pack text (≥ 80 bytes) | Skills (problem-runs) |", "|---|---|---|---|"]
    for spec in a.arm:
        name, _, rest = spec.partition("=")
        name, _, n = name.rpartition(":") if ":" in name else (name, "", "")
        hits = arm_hits(a.pack, pub, rest)
        per = collections.Counter(s for v in hits.values() for s in v)
        share = f"{len(hits)} ({100 * len(hits) / int(n):.1f}%)" if n else str(len(hits))
        out.append(f"| {name} | {n or '?'} | {share} | "
                   + (", ".join(f"`{k}` {v}" for k, v in per.most_common()) or "none") + " |")
    print("\n".join(out))


if __name__ == "__main__":
    sys.exit(main())

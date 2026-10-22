"""Pick a fixed, seeded sample of problems: a quota per category, with exactly\n`--amba` problems from the AMBA slice.

Usage: python3 tools/pick_ids.py <file.jsonl> [--seed 1] [--quota cid003=3,cid004=3,cid005=2,cid016=2] [--amba 2]
The M1 live check used the defaults; the output is tools/m1_ids.txt.
"""
import argparse
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))


def load_amba(path=os.path.join(HERE, "amba_ids.txt")):
    return {ln.strip() for ln in open(path) if ln.strip() and not ln.startswith("#")}


def pick(rows, quota, n_amba, seed):
    rng = random.Random(seed)
    amba = load_amba()
    by_cid = {c: sorted(r["id"] for r in rows if r["categories"][0] == c) for c in quota}
    chosen, left = [], dict(quota)
    amba_pool = sorted(i for c in quota for i in by_cid[c] if i in amba)
    for pid in rng.sample(amba_pool, n_amba):
        cid = next(c for c in quota if pid in by_cid[c])
        if left[cid] > 0:
            chosen.append(pid)
            left[cid] -= 1
    for c in quota:
        pool = [i for i in by_cid[c] if i not in chosen and i not in amba]  # AMBA count stays at n_amba
        chosen += rng.sample(pool, left[c])
    return sorted(chosen)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--quota", default="cid003=3,cid004=3,cid005=2,cid016=2")
    ap.add_argument("--amba", type=int, default=2)
    a = ap.parse_args()
    rows = [json.loads(ln) for ln in open(a.jsonl) if ln.strip()]
    quota = {k: int(v) for k, v in (x.split("=") for x in a.quota.split(","))}
    for pid in pick(rows, quota, a.amba, a.seed):
        print(pid)


if __name__ == "__main__":
    main()

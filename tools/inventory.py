"""Freeze the problem list: SHA-256 of each dataset file and a count of problems per category and difficulty.

Usage: python3 tools/inventory.py <file.jsonl> [<file.jsonl> ...] > inventory.md
"""
import collections
import hashlib
import json
import sys


def main(paths):
    print("| File | SHA-256 | Problems | Category, difficulty: count |")
    print("|---|---|---|---|")
    for path in paths:
        data = open(path, "rb").read()
        rows = [json.loads(line) for line in data.decode().splitlines() if line.strip()]
        counts = collections.Counter(", ".join(r.get("categories", [])) for r in rows)
        cells = "; ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
        print(f"| `{path.rsplit('/', 1)[-1]}` | `{hashlib.sha256(data).hexdigest()[:16]}` | {len(rows)} | {cells} |")


if __name__ == "__main__":
    main(sys.argv[1:])

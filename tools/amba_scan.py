"""List AMBA candidates: problems whose id or prompt matches the AMBA regex. Each match is then read by hand and
false positives dropped; the kept ids are in tools/amba_ids.txt.

Usage: python3 tools/amba_scan.py <file.jsonl> [<file.jsonl> ...]
"""
import json
import re
import sys

AMBA = re.compile(r"AXI4?(-|_)?(Lite|Stream)?|AXIS|APB|AHB|AMBA", re.IGNORECASE)


def scan(paths):
    for path in paths:
        for line in open(path):
            if not line.strip():
                continue
            r = json.loads(line)
            hits = sorted({m.group(0) for m in AMBA.finditer(r["id"] + "\n" + r.get("prompt", ""))})
            if hits:
                yield r["id"], r.get("categories", []), hits


if __name__ == "__main__":
    for pid, cats, hits in scan(sys.argv[1:]):
        print(pid, " ".join(cats), ",".join(hits), sep="\t")

"""Write the problems of a dataset file that match a comma-separated id list (blank = all); print how many.

Usage: python3 tools/subset.py <in.jsonl> "<id,id,...>" <out.jsonl>
"""
import json
import sys


def main(src, ids, dst):
    want = [i.strip() for i in ids.replace("\n", ",").split(",") if i.strip() and not i.strip().startswith("#")]
    rows = [ln for ln in open(src) if ln.strip()]
    if want:
        by_id = {json.loads(ln)["id"]: ln for ln in rows}
        missing = [i for i in want if i not in by_id]
        if missing:
            sys.exit(f"not in {src}: {', '.join(missing)}")
        rows = [by_id[i] for i in want]
    with open(dst, "w") as f:
        f.writelines(ln if ln.endswith("\n") else ln + "\n" for ln in rows)
    print(len(rows))


if __name__ == "__main__":
    main(*sys.argv[1:4])

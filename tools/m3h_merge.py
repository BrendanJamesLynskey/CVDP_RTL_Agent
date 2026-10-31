"""M3h: one valid row per (problem, seed) from a sweep's CSV and its reruns.

    python3 tools/m3h_merge.py first.csv [rerun.csv ...] > merged.csv

A row with stop_reason `rate_limited` was stopped by the Claude plan's limit before the model finished: it was not
run. Such problems are rerun in the same arm with the same seed number (`seed_offset`) after the limit resets. This
keeps, for each (id, seed), the first row that is not rate-limited, taking the files in the order given; a problem
still rate-limited in every file keeps its last row (ablate.py then leaves it out). Only rate-limited rows are ever
replaced: a failure is never rerun. The header is the first file's; every file must have the same one. A count of
replaced and still-limited rows goes to stderr."""
import csv
import sys


def merge(paths):
    header, best, order = None, {}, []
    for p in paths:
        with open(p) as f:
            r = csv.DictReader(f)
            if header is None:
                header = r.fieldnames
            elif r.fieldnames != header:
                raise SystemExit(f"m3h_merge.py: {p} has a different header from {paths[0]}")
            for row in r:
                key = (row["id"], row.get("seed", ""))
                if key not in best:
                    best[key] = row
                    order.append(key)
                elif best[key].get("stop_reason") == "rate_limited":
                    best[key] = row
    return header, [best[k] for k in order]


def main(argv):
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    header, rows = merge(argv)
    w = csv.DictWriter(sys.stdout, fieldnames=header)
    w.writeheader()
    w.writerows(rows)
    left = sum(1 for r in rows if r.get("stop_reason") == "rate_limited")
    print(f"m3h_merge.py: {len(rows)} rows, {left} still rate-limited", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

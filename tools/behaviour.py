"""How the agent spent its turns, per run: problems where it ran its own testbench, and pass rates for problems it
submitted after one turn against those that took more. Reads collect.py CSVs written since M3 (they carry the
`selfcheck_runs` evidence column).

Usage: python3 tools/behaviour.py NAME=results.csv [NAME=results.csv ...]
"""
import csv
import sys


def row(name, path):
    rows = list(csv.DictReader(open(path)))
    tb = sum(1 for r in rows if (r.get("selfcheck_runs") or "0") not in ("", "0"))
    one = [r for r in rows if r["turns"] == "1"]
    more = [r for r in rows if r["turns"] not in ("1", "")]
    rate = lambda rs: f"{sum(r['pass'] == '1' for r in rs)}/{len(rs)}"  # noqa: E731
    stops = {}
    for r in rows:
        stops[r["stop_reason"]] = stops.get(r["stop_reason"], 0) + 1
    stop = ", ".join(f"{k} {v}" for k, v in sorted(stops.items(), key=lambda kv: -kv[1]))
    return (f"| {name} | {sum(r['pass'] == '1' for r in rows)}/{len(rows)} | {tb} | {len(one)} | {rate(one)} | "
            f"{rate(more)} | {stop} |")


def main(argv):
    print("| Run | Passed | Ran own testbench | Submitted after 1 turn | Passed, 1 turn | Passed, 2+ turns | Stop reasons |")
    print("|---|---|---|---|---|---|---|")
    for a in argv:
        name, path = a.split("=", 1)
        print(row(name, path))


if __name__ == "__main__":
    main(sys.argv[1:])

"""M3h's descriptive tables from collect.py CSVs (after tools/m3h_merge.py): how often each arm loaded pack skills,
each skill's load count, the turn of the first load, pass rate with and without each load (by problem-run; not
causal, the model chooses), Claude Code's bundled skills loaded, and effort (turns, wall time, tokens, wall-cap
stops). Rate-limited rows are left out, as in ablate.py. Names and counts only: no skill text is read or written.
No test is run here; the pre-registered comparisons are ablate.py's.

Usage: python3 tools/m3h_tables.py --arm A=a1.csv,... --arm S2c=... [--ids FILE] [--bundled-a NAME=dir ...]

`--bundled-a NAME=dir` counts arm NAME's Skill calls from the claude_stream.jsonl files under an artifact dir (arm A
keeps its stream; the pack arms record calls in the CSV).
"""
import argparse
import collections
import csv
import glob
import os
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agent"))


# The skill names of each tag (names are public: M3g's report and M3h's pre-registration list them; no text here)
V1 = ["spec-reading", "reset-strategy", "sequential-and-combinational-coding", "fsm-design", "valid-ready-handshake",
      "pipelining-and-latency", "fifo-design", "clock-domain-crossing", "arithmetic-and-widths",
      "counters-timers-and-edges", "memories-and-register-files", "bus-and-register-interfaces",
      "arbiters-encoders-and-muxes", "synthesisable-subset-and-parameters", "self-check-and-cocotb"]
V2_NEW = ["working-in-existing-code", "minimal-change-modification", "rtl-debugging", "module-integration",
          "block-ciphers-in-hardware", "fixed-point-and-dsp-datapaths", "crc-lfsr-and-line-codes",
          "serial-and-network-protocols", "caches-and-memory-systems", "hardware-algorithms"]
PACK_NAMES = {"v1.0": set(V1), "v2.0": set(V1 + V2_NEW)}


def load(spec, ids):
    rows = []
    for f in spec.split(","):
        rows += [r for r in csv.DictReader(open(f)) if (ids is None or r["id"] in ids)
                 and r.get("stop_reason") != "rate_limited"]
    return rows


def pct(n, d):
    return f"{100 * n / d:.1f}%" if d else "–"


def calls(r):
    return [s for s in (r.get("skills_loaded") or "").split(";") if s]


def is_pack(r):
    return bool(r.get("skill_pack"))


def num(r, k):
    try:
        return float(r.get(k) or "")
    except ValueError:
        return None


def overview(arms):
    out = ["#### Pack skill use per arm\n",
           "| Arm | Problem-runs | Pack skills offered (mean `skills_listed`) | Loading any pack skill | "
           "Distinct pack skills per loading run (mean) | First-load turn: median [min–max] | Pass rate, loading / not |",
           "|---|---|---|---|---|---|---|"]
    for name, rows in arms.items():
        n = len(rows)
        if not rows or not is_pack(rows[0]):
            out.append(f"| {name} | {n} | — | — | — | — | — |")
            continue
        listed = [num(r, "skills_listed") for r in rows if num(r, "skills_listed") is not None]
        used = [r for r in rows if int(r.get("skills_n") or 0) > 0]
        not_used = [r for r in rows if int(r.get("skills_n") or 0) == 0]
        turns = [int(r["skill_first_turn"]) for r in used if (r.get("skill_first_turn") or "").strip()]
        dist = statistics.mean(int(r["skills_n"]) for r in used) if used else 0
        ft = f"{statistics.median(turns):g} [{min(turns)}–{max(turns)}]" if turns else "–"
        pu = pct(sum(int(r["pass"]) for r in used), len(used))
        pn = pct(sum(int(r["pass"]) for r in not_used), len(not_used))
        out.append(f"| {name} | {n} | {statistics.mean(listed):.1f} | {len(used)} ({pct(len(used), n)}) | "
                   f"{dist:.2f} | {ft} | {pu} / {pn} |" if listed else
                   f"| {name} | {n} | – | {len(used)} ({pct(len(used), n)}) | {dist:.2f} | {ft} | {pu} / {pn} |")
    return out


def per_skill(name, rows):
    packs = {r["skill_pack"] for r in rows if r.get("skill_pack")}
    loads = collections.Counter()
    for r in rows:
        for s in set(calls(r)):
            loads[s] += 1
    out = [f"\n#### {name}: each skill loaded ({len(rows)} problem-runs; pack {', '.join(sorted(packs))})\n",
           "Counted once per problem-run in which it was loaded. Descriptive only: the model chooses what to load, so "
           "a skill's pass rate mostly reflects the problems it is chosen for.\n",
           "| Skill | Problem-runs loading it | Share | Pass rate when loaded | Pass rate when not |",
           "|---|---|---|---|---|"]
    for s, c in loads.most_common():
        w = [r for r in rows if s in calls(r)]
        wo = [r for r in rows if s not in calls(r)]
        out.append(f"| `{s}` | {c} | {pct(c, len(rows))} | {pct(sum(int(r['pass']) for r in w), len(w))} | "
                   f"{pct(sum(int(r['pass']) for r in wo), len(wo))} |")
    if not loads:
        out.append("| (none) | 0 | | | |")
    return out


def bundled_from_streams(d):
    from cvdp_agent import native_skills

    c, runs = collections.Counter(), 0
    for f in glob.glob(os.path.join(d, "**", "claude_stream.jsonl"), recursive=True):
        runs += 1
        for _, n in native_skills.skill_calls(open(f).read().splitlines()):
            c[n] += 1
    return c, runs


def effort(arms):
    out = ["\n#### Effort per arm (Claude Code's own counts; nothing billed per call)\n",
           "| Arm | Problem-runs | Turns: median (mean) | Wall s: median | Wall-cap stops | "
           "Prompt tokens incl. cache, per run (mean) | Completion tokens per run (mean) |",
           "|---|---|---|---|---|---|---|"]
    for name, rows in arms.items():
        t = [num(r, "turns") for r in rows if num(r, "turns") is not None]
        w = [num(r, "wall_time_s") for r in rows if num(r, "wall_time_s") is not None]
        p = [num(r, "prompt_tokens") for r in rows if num(r, "prompt_tokens") is not None]
        c = [num(r, "completion_tokens") for r in rows if num(r, "completion_tokens") is not None]
        cap = sum(1 for r in rows if r.get("stop_reason") == "wall_time")
        out.append(f"| {name} | {len(rows)} | {statistics.median(t):g} ({statistics.mean(t):.1f}) | "
                   f"{statistics.median(w):.0f} | {cap} | {statistics.mean(p):,.0f} | {statistics.mean(c):,.0f} |")
    return out


def stops(arms):
    out = ["\n#### Stop reasons per arm\n", "| Arm | Stop reasons |", "|---|---|"]
    for name, rows in arms.items():
        c = collections.Counter(r.get("stop_reason") for r in rows)
        out.append(f"| {name} | " + ", ".join(f"{k} {v}" for k, v in sorted(c.items())) + " |")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", action="append", required=True)
    ap.add_argument("--ids")
    ap.add_argument("--bundled-a", action="append", default=[])
    a = ap.parse_args(argv)
    ids = None
    if a.ids:
        ids = {ln.strip() for ln in open(a.ids) if ln.strip() and not ln.startswith("#")}
    arms = {}
    for spec in a.arm:
        name, _, files = spec.partition("=")
        arms[name] = load(files, ids)
    out = overview(arms)
    for name, rows in arms.items():
        if rows and is_pack(rows[0]):
            out += per_skill(name, rows)
    out += ["\n#### Bundled (Claude Code's own) skills loaded\n", "| Arm | Problem-runs | Bundled skill calls |",
            "|---|---|---|"]
    for name, rows in arms.items():
        if rows and is_pack(rows[0]):
            c = collections.Counter(s for r in rows for s in calls(r) if s not in PACK_NAMES[r["skill_pack"]])
            out.append(f"| {name} | {len(rows)} | " + (", ".join(f"`{k}` {v}" for k, v in c.most_common()) or "none")
                       + " |")
    for spec in a.bundled_a:
        name, _, d = spec.partition("=")
        c, runs = bundled_from_streams(d)
        out.append(f"| {name} (from its kept streams) | {runs} | "
                   + (", ".join(f"`{k}` {v}" for k, v in c.most_common()) or "none") + " |")
    out += effort(arms)
    out += stops(arms)
    print("\n".join(out))


if __name__ == "__main__":
    main()

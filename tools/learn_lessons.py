"""Build a lessons-memory snapshot (M3b) from learning-set work dirs: short, general lessons an RTL agent can use on
other problems. The LLM writes lessons; it never scores anything. Every outcome it reads comes from the harness
(hidden-test pass/fail) and the taxonomy's deterministic label.

For each (problem, run) in the work dirs: its hidden-test outcome, its taxonomy label if it failed, and a digest of
its trace and summary (stop reason, turns, checks it ran and their results, its own testbench's last result, the
plan's approach, the hidden-test log's first error line). The digests go to the model in batches, one call per
batch, asking for general advice. The lessons are then cut to at most 60 words each and 40 in all, de-duplicated,
and written as a snapshot named by its content hash (`lessons_<hash>.json`).

**The evaluation set is never seen.** A work dir that holds any problem in tools/m3b_eval_ids.txt is refused
before anything is read from it.

**Only the learning set is learned from**: by default tools/m3b_learn_in_roots_ids.txt, the heavy problems whose
files to change lie inside the agent's edit roots (tools/learn_in_roots.py), so the agent that learns is the agent
that is scored. A work dir holding any other problem is refused too (`--learn-ids ''` lifts this, for fixtures).

Usage: OPENROUTER_API_KEY=... python3 tools/learn_lessons.py --work <dir> [--work <dir> ...]
           --out-dir docs/reports/m3b/lessons [--model openai/gpt-6-luna] [--batch 15] [--max-lessons 40]
           [--learn-ids tools/m3b_learn_in_roots_ids.txt]
       (--provider fake --fake-script <json> for tests: no LLM)
"""
import argparse
import glob
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

EVAL_IDS = os.path.join(HERE, "m3b_eval_ids.txt")
LEARN_IDS = os.path.join(HERE, "m3b_learn_in_roots_ids.txt")
MAX_WORDS, MAX_LESSONS = 60, 40
PROMPT = """You are improving an AI agent that writes and fixes SystemVerilog RTL for a benchmark. Each problem gives it
a task prompt and spec files under docs/; it edits rtl/, can compile, lint, synthesize and run its own testbench,
then submits. Hidden tests it cannot see then score the design.

Below are records of {n} attempts on other problems: whether the hidden tests passed, a failure label from
deterministic rules, and what the agent did. Write at most {k} short lessons that would help the agent on
DIFFERENT problems. Each lesson is general advice, at most 60 words, e.g. "Before submitting, check that every port
and parameter name in the spec's interface table appears exactly in the top module." Never include code, module or
signal names from these problems, or anything that only fits one problem.

Failure labels: signal_missing_hidden = the hidden testbench read a signal, instance or parameter the design does
not have; compile_fail_hidden = the hidden build failed on code the agent's own compile accepted;
tests_failed_selfcheck_passed = the agent's own testbench passed but the hidden tests failed;
tests_failed_no_selfcheck = hidden tests failed and the agent never ran a testbench; stopped_by_cap = it ran out of
turns, budget or time.

Records:
{records}

Reply with a JSON list of strings only."""


class EvalLeak(ValueError):
    """A learning work dir holds an evaluation-set problem."""


class OutsideLearningSet(ValueError):
    """A learning work dir holds a problem that is not in the learning set."""


def eval_ids(path=EVAL_IDS):
    return {ln.strip() for ln in open(path) if ln.strip() and not ln.startswith("#")}


def seed_dirs(work):
    dirs = sorted((d for d in glob.glob(os.path.join(work, "seed*")) if re.search(r"/seed\d+$", d)),
                  key=lambda d: int(d.rsplit("seed", 1)[1]))
    return dirs or [work]


def guard(works, ids_path=EVAL_IDS, learn_path=None):
    """Refuse the whole build if any work dir holds an evaluation problem (raw_result.json or a problem dir), or,
    with `learn_path`, a problem outside the learning set."""
    forbidden = eval_ids(ids_path)
    allowed = eval_ids(learn_path) if learn_path else None
    for w in works:
        for d in seed_dirs(w):
            seen = set()
            raw = os.path.join(d, "raw_result.json")
            if os.path.exists(raw):
                seen |= set(json.load(open(raw)))
            for sub in os.listdir(d) if os.path.isdir(d) else []:
                if os.path.isdir(os.path.join(d, sub, "harness")):
                    seen |= {f"{sub}_{int(n):04d}" for n in os.listdir(os.path.join(d, sub, "harness"))
                             if n.isdigit()}
            leak = sorted(seen & forbidden)
            if leak:
                raise EvalLeak(f"{d} holds {len(leak)} evaluation-set problem(s) ({', '.join(leak[:5])}); "
                               "the lessons memory must never see an evaluation result")
            if allowed is not None and seen - allowed:
                out = sorted(seen - allowed)
                raise OutsideLearningSet(f"{d} holds {len(out)} problem(s) outside the learning set {learn_path} "
                                         f"({', '.join(out[:5])})")


def digest(row):
    """One attempt as a few lines for the model: outcome, label, and what the agent did (no code)."""
    events = (row.get("_paths") or {}).get("events", [])
    checks = [f"{e.get('check')}={'ok' if e.get('exit_code') == 0 else 'FAIL'}" for e in events
              if e.get("kind") == "tool" and e.get("check") in ("compile", "lint", "synth", "testbench_run",
                                                               "testbench_cocotb") and e.get("exit_code") is not None]
    plan = next((str(e.get("completion") or "")[:300] for e in events if e.get("kind") == "llm"
                 and e.get("node") == "plan"), "")
    err = ""
    for p in (row.get("_paths") or {}).get("logs", [])[:1]:
        err = next((ln.strip()[:200] for ln in open(p, errors="replace")
                    if re.search(r"AttributeError|AssertionError|Error|error:", ln)), "")
    outcome = "PASSED" if row["pass"] == "1" else f"FAILED ({row.get('_label') or row.get('failure_label')})"
    plan = re.sub(r"\s+", " ", plan)
    return (f"- hidden tests {outcome}; category {row.get('cid')}; stop {row.get('stop_reason')}; "
            f"turns {row.get('turns')}; own testbench runs {row.get('selfcheck_runs')} "
            f"(last {row.get('selfcheck_last')}); checks run: {', '.join(checks[-6:]) or 'none'}\n"
            f"  plan: {plan}\n  first hidden-test error: {err or 'n/a'}")


def clean(texts, max_words=MAX_WORDS):
    """Trim each lesson to max_words words, drop empties, code-looking ones and duplicates (case-insensitive)."""
    out, seen = [], set()
    for t in texts:
        if not isinstance(t, str):
            continue
        t = re.sub(r"\s+", " ", t).strip()
        if not t or re.search(r"```|module\s+\w+\s*[(#]|<=|assign\s", t):
            continue
        words = t.split(" ")
        if len(words) > max_words:
            t = " ".join(words[:max_words]).rstrip(",;:") + "…"
        key = re.sub(r"\W+", " ", t.lower()).strip()
        if key not in seen:
            seen.add(key)
            out.append(t)
    return out


def parse_list(text):
    m = re.search(r"\[.*\]", text or "", re.DOTALL)
    if not m:
        return []
    try:
        v = json.loads(m.group(0))
    except ValueError:
        return []
    return v if isinstance(v, list) else []


def build(works, llm, model, batch=15, max_lessons=MAX_LESSONS, ids_path=EVAL_IDS, learn_path=None):
    """The snapshot dict for these work dirs (after the guard: no evaluation problem, and with `learn_path` none
    outside the learning set)."""
    import taxonomy
    from cvdp_agent.memory import canonical_hash

    guard(works, ids_path, learn_path)
    rows = []
    for w in works:
        rows += taxonomy.rows_from_work(os.path.basename(os.path.normpath(w)) or "work", w)
    for r in rows:
        if r["pass"] != "1":
            r["_label"], r["_flags"] = taxonomy.label(r)
    rows.sort(key=lambda r: (r["id"], r["_run"]))
    n_batches = max(1, math.ceil(len(rows) / batch))
    per = max(1, math.ceil(max_lessons / n_batches))
    lessons, calls = [], []
    for b in range(n_batches):
        chunk = rows[b * batch:(b + 1) * batch]
        msg = PROMPT.format(n=len(chunk), k=per, records="\n".join(digest(r) for r in chunk))
        res = llm.invoke("lessons", [{"role": "user", "content": msg}], max_tokens=4000, timeout=150)
        calls.append({"batch": b, "attempts": len(chunk), "cost_usd": res.cost, "prompt_tokens": res.prompt_tokens,
                      "completion_tokens": res.completion_tokens, "provider": res.provider})
        lessons += clean(parse_list(res.text))
    lessons = clean(lessons)[:max_lessons]
    reported = [c["cost_usd"] for c in calls if c["cost_usd"] is not None]
    snap = {"lessons": [{"id": f"L{i + 1:02d}", "text": t} for i, t in enumerate(lessons)],
            "provenance": {"model": model, "work_dirs": [os.path.basename(os.path.normpath(w)) for w in works],
                           "attempts": len(rows), "problems": len({r["id"] for r in rows}),
                           "passed": sum(r["pass"] == "1" for r in rows), "batches": n_batches,
                           "calls": calls, "cost_usd": round(sum(reported), 8) if reported else None,
                           "cost_unreported_calls": sum(c["cost_usd"] is None for c in calls)}}
    if learn_path:
        snap["provenance"]["learning_set"] = os.path.basename(learn_path)
    snap["hash"] = canonical_hash(snap)
    return snap


def write(snap, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"lessons_{snap['hash']}.json")
    with open(path, "w") as f:
        json.dump(snap, f, indent=1, sort_keys=True)
        f.write("\n")
    return path


def main(argv=None):
    from cvdp_agent import llm as llm_mod
    from cvdp_agent.config import Config

    ap = argparse.ArgumentParser()
    ap.add_argument("--work", action="append", required=True)
    ap.add_argument("--out-dir", default=os.path.join(HERE, "..", "docs", "reports", "m3b", "lessons"))
    ap.add_argument("--model", default="openai/gpt-6-luna")
    ap.add_argument("--provider", default="openrouter")
    ap.add_argument("--fake-script", default="")
    ap.add_argument("--batch", type=int, default=15)
    ap.add_argument("--max-lessons", type=int, default=MAX_LESSONS)
    ap.add_argument("--eval-ids", default=EVAL_IDS)
    ap.add_argument("--learn-ids", default=LEARN_IDS, help="the learning set ('' for no check, e.g. fixtures)")
    a = ap.parse_args(argv)
    llm = llm_mod.make(Config(provider=a.provider, model=a.model, fake_script=a.fake_script))
    snap = build(a.work, llm, a.model, a.batch, a.max_lessons, a.eval_ids, a.learn_ids or None)
    path = write(snap, a.out_dir)
    print(f"{len(snap['lessons'])} lessons from {snap['provenance']['attempts']} attempts -> {path} "
          f"(cost ${snap['provenance']['cost_usd']}, {snap['provenance']['cost_unreported_calls']} unreported)")


if __name__ == "__main__":
    main()

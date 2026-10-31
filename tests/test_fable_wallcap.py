"""Brief 21: the sweep's `wall_s` input (blank = everything as before) and the Fable wall-cap rerun tools. No test
needs a network, an LLM or a plan."""
import csv
import json
import os
import subprocess

import fable_wallcap
from test_graph import PLAN, decide, edit
from test_m2a import FAKE_HARNESS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LADDER = os.path.join(ROOT, "docs", "reports", "claude_code", "runs", "claude-fable-5-1.csv")
IDS = os.path.join(ROOT, "tools", "fable_wallcap_ids.txt")
# The variables the sweep passed into the agent's container before this brief (langgraph, fake provider).
AGENT_ENV_BEFORE = ("CVDP_PROVIDER,CVDP_MODEL,CVDP_BUDGET_USD,CVDP_MAX_TURNS,CVDP_SELF_CHECK,CVDP_LINT,CVDP_LEDGER_DIR,"
                    "CVDP_RUN_BUDGET_USD,CVDP_REASONING,CVDP_SEED,CVDP_PROVIDER_ORDER,CVDP_HARNESS,CVDP_MEMORY,"
                    "CVDP_MUTATION_GATE,CVDP_INTERFACE_CHECK,CVDP_VERIFY_SUBMIT,CVDP_SPEC_VECTORS")


def test_ids_file_is_the_ladders_wall_capped_rows():
    rows = fable_wallcap.read_rows(LADDER)
    want = fable_wallcap.wall_capped(rows)
    assert fable_wallcap.read_ids(IDS) == want and len(want) == 17
    by_id = {r["id"]: r for r in rows}
    assert sum(by_id[i]["pass"] == "1" for i in want) == 7
    head = [ln for ln in open(IDS) if ln.startswith("#")]
    assert any("count: 17: passed under the cap 7, failed 10" in ln for ln in head)


def _sweep(tmp_path, **env):
    cvdp = tmp_path / "cvdp"
    cvdp.mkdir(exist_ok=True)
    # the stand-in harness also records the env names it was given and the harness timeout it would use
    harness = FAKE_HARNESS.replace(
        'with open(os.environ["SEEN_ENV"], "a") as f:',
        'json.dump({"env": os.environ["CVDP_AGENT_ENV"], "harness_timeout": os.environ.get("DOCKER_TIMEOUT_AGENT")}, '
        'open(os.environ["SEEN_ENV"] + ".m", "w"))\nwith open(os.environ["SEEN_ENV"], "a") as f:')
    (cvdp / "run_benchmark.py").write_text(harness)
    (cvdp / "run_benchmark.py").chmod(0o755)
    data = tmp_path / "data"
    data.mkdir(exist_ok=True)
    (data / "agentic_code_generation_no_commercial.jsonl").write_text(
        json.dumps({"id": "cvdp_agentic_lfsr_0001", "categories": ["cid016", "easy"]}) + "\n")
    work = tmp_path / env.pop("WORK_NAME", "work")
    e = dict(os.environ, MODEL="fake", THREADS="1", WORK=str(work), CVDP_DIR=str(cvdp), DATA_DIR=str(data),
             AGENT_IMAGE="unused", AGENT_PYTHONPATH=os.path.join(ROOT, "agent"),
             FAKE_SCRIPT=json.dumps([{"text": PLAN}, {"text": edit()}, {"text": decide("submit")}]),
             SEEN_ENV=str(work) + ".seen.jsonl", OPENROUTER_API_KEY="", **env)
    r = subprocess.run(["bash", os.path.join(ROOT, "tools", "sweep.sh")], env=e, capture_output=True, text=True,
                       timeout=300, cwd=ROOT)
    return r, work


def test_blank_wall_s_leaves_the_agent_env_and_the_harness_timeout_as_before(tmp_path):
    r, work = _sweep(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    seen = json.load(open(str(work) + ".seen.jsonl.m"))
    assert seen == {"env": AGENT_ENV_BEFORE, "harness_timeout": None}
    run = json.load(open(str(work) + ".run.json"))
    assert "wall_s" not in run and "harness_agent_timeout_s" not in run
    s = json.load(open(work / "seed1" / "cvdp_agentic_lfsr" / "harness" / "1" / "rundir" / "agent_out" / "summary.json"))
    assert s["switches"]["wall_s"] == 480.0
    assert "wall cap:" not in r.stdout


def test_wall_s_sets_the_agent_cap_and_the_harness_kill_120_s_above(tmp_path):
    r, work = _sweep(tmp_path, WALL_S="1500")
    assert r.returncode == 0, r.stdout + r.stderr
    seen = json.load(open(str(work) + ".seen.jsonl.m"))
    assert seen == {"env": AGENT_ENV_BEFORE + ",CVDP_WALL_S", "harness_timeout": "1620"}
    run = json.load(open(str(work) + ".run.json"))
    assert (run["wall_s"], run["harness_agent_timeout_s"]) == (1500, 1620)
    s = json.load(open(work / "seed1" / "cvdp_agentic_lfsr" / "harness" / "1" / "rundir" / "agent_out" / "summary.json"))
    assert s["switches"]["wall_s"] == 1500.0
    assert "wall cap: agent 1500 s, harness kill 1620 s, seed worst case 1680 s/problem" in r.stdout


def test_seed_worst_case_follows_the_wall_cap(tmp_path):
    # 1 problem, 1 thread: worst case 1680 + 300 = 1980 s, more than a 1000 s step budget, so the seed is not started
    r, work = _sweep(tmp_path, WALL_S="1500", STEP_BUDGET_S="1000")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "under this seed's worst case of 1980 s" in (work / "seed1.skipped").read_text()
    # the default caps keep the old 660 s worst case: 960 s fits the same budget
    r, work = _sweep(tmp_path, STEP_BUDGET_S="1000", WORK_NAME="work2")
    assert r.returncode == 0 and not (work / "seed1.skipped").exists(), r.stdout + r.stderr


def test_sweep_rejects_a_bad_wall_s(tmp_path):
    for v in ("abc", "0", "-5", "1.5"):
        e = dict(os.environ, WORK=str(tmp_path / "w"), AGENT_IMAGE="x", WALL_S=v)
        r = subprocess.run(["bash", os.path.join(ROOT, "tools", "sweep.sh")], env=e, capture_output=True, text=True)
        assert r.returncode == 2 and "WALL_S" in r.stderr, (v, r.stderr)


def _csv(path, rows, fields):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def test_analyze_substitutes_the_rerun_rows_and_counts(tmp_path):
    fields = ["label", "id", "pass", "difficulty", "wall_time_s", "stop_reason", "turns", "tool_calls"]
    ladder = [{"label": "f", "id": f"p{i}", "pass": p, "difficulty": "medium", "wall_time_s": w, "stop_reason": s,
               "turns": "1", "tool_calls": "1"}
              for i, (p, w, s) in enumerate([("1", "100", "submit"), ("1", "480.0", "wall_time"),
                                             ("0", "480.1", "wall_time"), ("0", "480.0", "wall_time"), ("0", "50", "submit")])]
    rerun = [{"label": "f", "id": "p1", "pass": "0", "difficulty": "medium", "wall_time_s": "700", "stop_reason": "submit",
              "turns": "9", "tool_calls": "8", "extra": "x"},
             {"label": "f", "id": "p2", "pass": "1", "difficulty": "medium", "wall_time_s": "1200", "stop_reason": "submit",
              "turns": "12", "tool_calls": "11", "extra": "x"},
             {"label": "f", "id": "p3", "pass": "0", "difficulty": "medium", "wall_time_s": "1500.0",
              "stop_reason": "wall_time", "turns": "0", "tool_calls": "0", "extra": "x"}]
    _csv(tmp_path / "ladder.csv", ladder, fields)
    _csv(tmp_path / "rerun.csv", rerun, fields + ["extra"])
    fable_wallcap.write_ids(ladder, "ladder.csv", tmp_path / "ids.txt")
    assert fable_wallcap.read_ids(tmp_path / "ids.txt") == ["p1", "p2", "p3"]
    import io
    out = io.StringIO()
    res = fable_wallcap.analyze(ladder, rerun, ["p1", "p2", "p3"], 1500.0, str(tmp_path / "sub.csv"), out=out)
    assert res == {"old_pass": 1, "new_pass": 1, "cap_hits": 1, "invalid": 0, "old_total": 2, "new_total": 2, "total": 5,
                   "transitions": {"pass→pass": 0, "pass→fail": 1, "fail→pass": 1, "fail→fail": 1}}
    md = out.getvalue()
    assert "| Passed | 1 / 3 | 1 / 3 |" in md and "**2/5 = 40.0%**" in md and "stopped on the 1500 s cap | 1 | 0 |" in md
    sub = list(csv.DictReader(open(tmp_path / "sub.csv")))
    assert [r["id"] for r in sub] == ["p0", "p1", "p2", "p3", "p4"]
    assert [r["wall_time_s"] for r in sub] == ["100", "700", "1200", "1500.0", "50"]
    assert "extra" not in sub[0]  # the ladder's columns, so ablate.py reads it like the ladder's CSVs
    # a rerun that does not cover the ids exactly is refused
    try:
        fable_wallcap.analyze(ladder, rerun[:2], ["p1", "p2", "p3"], 1500.0, out=io.StringIO())
    except SystemExit as e:
        assert "missing ['p3']" in str(e)
    else:
        raise AssertionError("accepted a rerun missing a problem")

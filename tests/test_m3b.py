"""M3b: the LangGraph agent unchanged (golden), the Deep Agents harness on the fake provider, reachable.py, the
lessons memory (builder guard, retrieval, the memory column) and the sweep's new inputs. No test needs an LLM."""
import csv
import json
import os
import subprocess

import pytest

import collect
import golden_langgraph
import learn_lessons
import reachable
from conftest import ORIGINAL_RTL
from cvdp_agent import memory
from test_graph import GOOD, PLAN, decide, edit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX_LESSONS = os.path.join(ROOT, "tests", "fixtures", "lessons")


def snapshot_path():
    return next(os.path.join(FIX_LESSONS, f) for f in sorted(os.listdir(FIX_LESSONS)) if f.startswith("lessons_"))


def trace(cfg):
    return [json.loads(x) for x in open(os.path.join(cfg.agent_out, "trace.jsonl"))]


# ---------- harness=langgraph: byte-for-byte what it was ----------

def test_langgraph_golden_prompts_trace_and_summary_are_unchanged():
    """The golden was written from main before any M3b change (commit e136091): the same prompts, the same trace
    events (kinds and fields, timestamps aside) and the same summary fields."""
    got = json.loads(json.dumps(golden_langgraph.run_all(), sort_keys=True))
    want = json.load(open(golden_langgraph.GOLDEN))
    assert set(got) == set(want)
    for name in want:
        assert [e["kind"] for e in got[name]["trace"]] == [e["kind"] for e in want[name]["trace"]], name
        assert sorted(got[name]["summary"]) == sorted(want[name]["summary"]), name
        assert got[name] == want[name], name


# ---------- harness=deepagents on the fake provider ----------

def call(name, cost=0.001, **args):
    return {"tool_calls": [{"name": name, "args": args}], "cost": cost}


FIX = [call("write_todos", todos=[{"content": "fix the adder", "status": "in_progress"}]),
       call("read_file", file_path="/rtl/adder.sv"),
       call("write_file", cost=0.002, file_path="/rtl/adder.sv", content=GOOD),
       call("run_checks", checks=["compile", "lint"])]


def test_deepagents_runs_to_submit(make_cfg, run_agent, task_tree):
    cfg = make_cfg(harness="deepagents")
    s, llm, checker = run_agent(cfg, FIX + [{"text": "Done: y = a + b.", "cost": 0.001}])
    assert s["stop_reason"] == "submit" and s["harness"] == "deepagents" and s["max_rounds"] == 22
    assert (task_tree / "rtl" / "adder.sv").read_text() == GOOD and s["files_changed"] == ["rtl/adder.sv"]
    assert s["turns"] == 5 and s["llm_calls"] == 5 and s["cost_usd"] == pytest.approx(0.006)
    assert checker.requests[0][0] == ["compile", "lint"]
    # what Deep Agents offers the model: its planning tool and file tools on the real tree, and our checks; no
    # shell (execute) and no sub-agents (task)
    assert set(llm.requests[0]["tools"]) == {"ls", "read_file", "write_file", "edit_file", "glob", "grep",
                                             "write_todos", "run_checks"}
    kinds = {e["kind"] for e in trace(cfg)}
    assert kinds <= {"start", "tool", "llm", "summary", "error", "lessons"} and "error" not in kinds


def test_deepagents_summary_has_the_langgraph_fields_and_collect_reads_it(make_cfg, run_agent, task_tree):
    cfg = make_cfg(harness="deepagents")
    s, _, _ = run_agent(cfg, FIX + [{"text": "done", "cost": 0.001}])
    lg = json.load(open(golden_langgraph.GOLDEN))["submit"]["summary"]
    assert set(lg) <= set(s)  # every field the results tools read
    # lay it out as the harness does and collect it
    work = task_tree.parent / "work"
    pdir = work / "cvdp_agentic_adder" / "harness" / "1" / "rundir"
    pdir.mkdir(parents=True)
    os.rename(cfg.agent_out, pdir / "agent_out")
    (work / "raw_result.json").write_text(json.dumps({"cvdp_agentic_adder_0001": {
        "category": "cid016", "difficulty": "easy", "tests": [{"result": 0, "log": "/x/1.txt"}]}}))
    row = collect.rows(str(work))[0]
    assert (row["pass"], row["stop_reason"], row["cost_usd"], row["turns"], row["memory"]) == (1, "submit", 0.006, 5,
                                                                                               "")


def test_deepagents_stops_on_the_budget(make_cfg, run_agent):
    cfg = make_cfg(harness="deepagents", budget_usd=0.004)
    s, llm, _ = run_agent(cfg, [call("read_file", cost=0.003, file_path="/rtl/adder.sv"),
                                call("write_file", cost=0.002, file_path="/rtl/adder.sv", content=GOOD),
                                {"text": "done", "cost": 0.001}])
    assert s["stop_reason"] == "budget" and len(llm.calls) == 2 and s["cost_usd"] == pytest.approx(0.005)
    assert s["final_compiled"] is True  # the edit made before the stop was compiled by finalize, as in LangGraph


def test_deepagents_stops_on_the_round_cap(make_cfg, run_agent):
    cfg = make_cfg(harness="deepagents", max_rounds=3)
    s, llm, _ = run_agent(cfg, [call("read_file", file_path="/rtl/adder.sv")] * 6)
    assert s["stop_reason"] == "max_turns" and len(llm.calls) == 3 and s["turns"] == 3


def test_deepagents_stops_on_wall_time(make_cfg, run_agent):
    cfg = make_cfg(harness="deepagents", wall_s=100)
    s, llm, _ = run_agent(cfg, [dict(call("read_file", file_path="/rtl/adder.sv"), sleep=150),
                                {"text": "done"}])
    assert s["stop_reason"] == "wall_time" and len(llm.calls) == 1


def test_deepagents_cost_accounting_matches_the_langgraph_agent_in_kind(make_cfg, run_agent, tmp_path):
    """Unreported cost stops the problem and is counted, and the ledger gets one entry, exactly as in graph.py."""
    ledger = tmp_path / "ledger"
    ledger.mkdir()
    cfg = make_cfg(harness="deepagents", ledger_dir=str(ledger), run_budget_usd=1.0)
    s, llm, _ = run_agent(cfg, [call("read_file", cost=0.002, file_path="/rtl/adder.sv"),
                                call("read_file", cost=None, file_path="/rtl/adder.sv"), {"text": "done"}])
    assert s["stop_reason"] == "cost_unreported" and s["cost_unreported_calls"] == 1
    assert s["cost_usd"] == pytest.approx(0.002) and len(llm.calls) == 2
    from cvdp_agent.graph import ledger_totals

    assert ledger_totals(str(ledger)) == (pytest.approx(0.002), 1, pytest.approx(0.102))


def test_deepagents_writes_obey_the_file_policy(make_cfg, run_agent, task_tree):
    cfg = make_cfg(harness="deepagents")
    s, _, _ = run_agent(cfg, [call("write_file", file_path="/prompt.json", content="PWNED"),
                              call("write_file", file_path="/rundir/agent_out/summary.json", content="PWNED"),
                              call("edit_file", file_path="/prompt.json", old_string="Fix", new_string="PWNED"),
                              {"text": "done"}])
    assert "PWNED" not in (task_tree / "prompt.json").read_text() and s["files_changed"] == []
    refused = [e for e in trace(cfg) if e.get("check") == "file_write" and e["exit_code"] == 1]
    assert len(refused) == 3


def test_deepagents_empty_reply_is_retried_once(make_cfg, run_agent):
    cfg = make_cfg(harness="deepagents", reasoning="low")
    s, llm, _ = run_agent(cfg, [{"text": "", "cost": 0.001}, {"text": "done", "cost": 0.001}])
    assert (s["empty_replies"], s["empty_retries"], s["stop_reason"]) == (1, 1, "submit")
    assert llm.requests[1]["body"]["reasoning"] == {"effort": "none", "exclude": True}


def test_deepagents_give_up(make_cfg, run_agent):
    s, _, _ = run_agent(make_cfg(harness="deepagents"), [{"text": "GIVE_UP: the spec is missing"}])
    assert s["stop_reason"] == "give_up"


# ---------- reachable.py ----------

def record(spec, test_py, env="TOPLEVEL = top\n", runner="parameters = {\"WIDTH\": 8}\n", prompt="Design `top`."):
    return {"id": "cvdp_agentic_x_0001", "categories": ["cid003", "easy"], "prompt": prompt,
            "context": {"docs/spec.md": spec}, "harness": {"src/.env": env, "src/test_runner.py": runner,
                                                           "src/test_top.py": test_py}}


def test_reachable_handle_given_in_the_spec_is_reachable():
    rec = record("Ports: `clk`, `data_out`. Parameter `WIDTH`.", "x = dut.data_out.value\nawait RisingEdge(dut.clk)\n")
    h = reachable.handles(rec)
    assert {"top", "WIDTH", "data_out", "clk"} <= set(h)
    row = reachable.check([rec], {"cvdp_agentic_x_0001": {"signal_missing_hidden": 14}}, 14)[0]
    assert row["missing"] == {} and not row["unreachable"]


def test_reachable_handle_only_in_the_hidden_testbench_is_unreachable():
    rec = record("Ports: `clk`, `data_out`. Parameter `WIDTH`.", "s = int(dut.state_ff.value)\n")
    row = reachable.check([rec], {"cvdp_agentic_x_0001": {"signal_missing_hidden": 9, "passed": 5}}, 14)[0]
    assert set(row["missing"]) == {"state_ff"} and row["unreachable"]
    # missing, but the problem does not fail on the interface in at least half of its runs: kept
    row = reachable.check([rec], {"cvdp_agentic_x_0001": {"signal_missing_hidden": 6}}, 14)[0]
    assert row["missing"] and not row["unreachable"]


def test_reachable_a_name_only_in_an_assert_fstring_is_not_a_handle():
    test_py = ('assert int(dut.data_out.value) == 5, f"got {dut.m_axis_tvalid.value} want 5"\n'
               'assert dut.data_out.value == 1, "see dut.other_signal"\n')
    rec = record("Ports: `data_out`.", test_py)
    h = reachable.handles(rec)
    assert "data_out" in h and "m_axis_tvalid" not in h and "other_signal" not in h


def test_reachable_prose_word_is_not_given_but_an_identifier_shaped_one_is():
    texts = reachable.given_texts({"prompt": "Assert enable when the INDEX_WIDTH bits are set.", "context": {}})
    assert not reachable.is_given("enable", texts) and reachable.is_given("INDEX_WIDTH", texts)
    texts = reachable.given_texts({"prompt": "", "context": {"rtl/top.sv": "module top(input enable);"}})
    assert reachable.is_given("enable", texts)


def test_reachable_paths_and_parameters():
    assert reachable.dut_paths("x = dut.poly_branches[0].u_poly_filter.TAPS.value") == [
        ["poly_branches", "u_poly_filter", "TAPS"]]
    tops, params = reachable.runner_names({"src/run.sh": "iverilog -s my_top -Pmy_top.DEPTH=4 x.sv",
                                           "src/test_runner.py": 'param = {"NS": 3, "NBW": 8}'})
    assert tops == {"my_top"} and params == {"DEPTH", "NS", "NBW"}


def test_committed_eval_and_learning_sets_do_not_overlap():
    ev = learn_lessons.eval_ids()
    learn = {ln.strip() for ln in open(os.path.join(ROOT, "tools", "m3b_learn_ids.txt"))
             if ln.strip() and not ln.startswith("#")}
    assert len(ev) == 86 and len(learn) == 75 and not ev & learn


# ---------- lessons memory ----------

def test_snapshot_builder_refuses_a_work_dir_with_an_evaluation_id(tmp_path):
    work = tmp_path / "work" / "seed1"
    work.mkdir(parents=True)
    pid = sorted(learn_lessons.eval_ids())[0]
    (work / "raw_result.json").write_text(json.dumps({pid: {"tests": [{"result": 1}]}}))
    with pytest.raises(learn_lessons.EvalLeak):
        learn_lessons.build([str(tmp_path / "work")], llm=None, model="fake")
    # a problem dir alone (no raw_result.json yet) is refused too
    (work / "raw_result.json").unlink()
    repo, n = pid.rsplit("_", 1)
    (work / repo / "harness" / str(int(n))).mkdir(parents=True)
    with pytest.raises(learn_lessons.EvalLeak):
        learn_lessons.guard([str(tmp_path / "work")])


def test_snapshot_from_fixtures_is_reproducible_and_named_by_its_hash(tmp_path):
    from cvdp_agent.llm import FakeLLM

    script = json.load(open(os.path.join(FIX_LESSONS, "fake_replies.json")))
    snap = learn_lessons.build([os.path.join(ROOT, "tests", "fixtures", "taxonomy", "work")], FakeLLM(script),
                               "fake")
    path = learn_lessons.write(snap, str(tmp_path))
    committed = snapshot_path()
    assert os.path.basename(path) == os.path.basename(committed)
    assert json.load(open(path)) == json.load(open(committed))
    assert all(len(x["text"].split()) <= 60 for x in snap["lessons"]) and len(snap["lessons"]) <= 40
    assert len({x["text"] for x in snap["lessons"]}) == len(snap["lessons"])  # the duplicate was dropped
    assert snap["provenance"]["cost_usd"] == pytest.approx(0.002)


def test_lesson_cleaning_caps_words_and_drops_code():
    long = " ".join(["word"] * 80)
    out = learn_lessons.clean([long, "assign y = a;", "```verilog\nx\n```", "Check the port list.",
                               "check the port list"])
    assert len(out) == 2 and len(out[0].split()) == 60 and out[1] == "Check the port list."


def test_retrieval_is_deterministic():
    snap = memory.load(snapshot_path())
    q = "Design an APB register block; the spec lists the ports and the parameters of the top module."
    a = memory.retrieve(snap["lessons"], q, k=5)
    b = memory.retrieve(json.loads(json.dumps(snap["lessons"])), q, k=5)
    assert [x["id"] for x, _ in a] == [x["id"] for x, _ in b] and len(a) == 5
    assert [s for _, s in a] == sorted([s for _, s in a], reverse=True)
    assert memory.retrieve([], q) == []


def test_snapshot_with_a_wrong_hash_is_refused(tmp_path):
    snap = json.load(open(snapshot_path()))
    snap["lessons"][0]["text"] = "edited after hashing"
    p = tmp_path / "lessons_bad.json"
    p.write_text(json.dumps(snap))
    with pytest.raises(ValueError):
        memory.load(str(p))


@pytest.mark.parametrize("harness", ["langgraph", "deepagents"])
def test_lessons_reach_the_plan_prompt_and_are_traced(make_cfg, run_agent, harness):
    cfg = make_cfg(harness=harness, memory=snapshot_path())
    script = [PLAN, edit(), decide("submit")] if harness == "langgraph" else [{"text": "done"}]
    s, llm, _ = run_agent(cfg, script)
    snap = memory.load(snapshot_path())
    assert s["memory"] == snap["hash"] and len(s["lessons"]) == 5
    first_user = llm.requests[0]["messages"][-1]["content"]
    assert "# Lessons from other problems" in first_user
    by_id = {x["id"]: x["text"] for x in snap["lessons"]}
    assert all(by_id[i] in first_user for i in s["lessons"])
    ev = [e for e in trace(cfg) if e["kind"] == "lessons"]
    assert len(ev) == 1 and [x["id"] for x in ev[0]["retrieved"]] == s["lessons"]


def test_memory_column_is_written_and_blank_without_memory(make_cfg, run_agent, task_tree):
    for mem, want in ((snapshot_path(), memory.load(snapshot_path())["hash"]), ("", "")):
        work = task_tree.parent / f"work{bool(mem)}"
        cfg = make_cfg(memory=mem, out_dir=str(work / "cvdp_agentic_adder" / "harness" / "1" / "rundir" /
                                               "agent_out"))
        run_agent(cfg, [PLAN, edit(), decide("submit")])
        (work / "raw_result.json").write_text(json.dumps({"cvdp_agentic_adder_0001": {
            "category": "cid016", "difficulty": "easy", "tests": [{"result": 0, "log": "/x/1.txt"}]}}))
        rows = collect.rows(str(work))
        assert collect.FIELDS[-1] == "memory" and rows[0]["memory"] == want
        (task_tree / "rtl" / "adder.sv").write_text(ORIGINAL_RTL)


# ---------- the sweep's new inputs ----------

def test_sweep_rejects_bad_harness_and_memory(tmp_path):
    for k, v in (("HARNESS", "crew"), ("MEMORY", "nope.json"), ("MEMORY", "x;rm -rf .json")):
        env = dict(os.environ, WORK=str(tmp_path / "w"), AGENT_IMAGE="x", **{k: v})
        r = subprocess.run(["bash", os.path.join(ROOT, "tools", "sweep.sh")], env=env, capture_output=True,
                           text=True)
        assert r.returncode == 2 and k in r.stderr, (k, v, r.stderr)


def test_sweep_mounts_the_snapshot_read_only_and_passes_harness(tmp_path):
    from test_m2a import FAKE_HARNESS

    cvdp = tmp_path / "cvdp"
    cvdp.mkdir()
    # the stand-in harness also records the mounts and env names it was given
    harness = FAKE_HARNESS.replace('with open(os.environ["SEEN_ENV"], "a") as f:',
                                   'json.dump({"mounts": os.environ["CVDP_AGENT_MOUNTS"], "env": '
                                   'os.environ["CVDP_AGENT_ENV"], "memory": os.environ.get("CVDP_MEMORY")}, open(os.environ["SEEN_ENV"] + ".m", "w"))\n'
                                   'with open(os.environ["SEEN_ENV"], "a") as f:')
    harness = harness.replace("CVDP_FAKE_SCRIPT=os.environ[\"FAKE_SCRIPT\"])",
                              "CVDP_FAKE_SCRIPT=os.environ[\"FAKE_SCRIPT\"], CVDP_MEMORY=os.environ[\"HOST_MEMORY\"])")
    (cvdp / "run_benchmark.py").write_text(harness)
    (cvdp / "run_benchmark.py").chmod(0o755)
    data = tmp_path / "data"
    data.mkdir()
    (data / "agentic_code_generation_no_commercial.jsonl").write_text(
        json.dumps({"id": "cvdp_agentic_lfsr_0001", "categories": ["cid016", "easy"]}) + "\n")
    work = tmp_path / "work"
    snap = os.path.relpath(snapshot_path(), ROOT)
    env = dict(os.environ, MODEL="fake", THREADS="1", WORK=str(work), CVDP_DIR=str(cvdp), DATA_DIR=str(data),
               AGENT_IMAGE="unused", FAKE_SCRIPT=json.dumps([{"text": "done"}]), HARNESS="deepagents", MEMORY=snap,
               HOST_MEMORY=snapshot_path(), AGENT_PYTHONPATH=os.path.join(ROOT, "agent"),
               SEEN_ENV=str(tmp_path / "seen.jsonl"), OPENROUTER_API_KEY="")
    r = subprocess.run(["bash", os.path.join(ROOT, "tools", "sweep.sh")], env=env, capture_output=True, text=True,
                       timeout=300, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    seen = json.load(open(str(tmp_path / "seen.jsonl") + ".m"))
    name = os.path.basename(snap)
    assert seen["mounts"].endswith(f"{name}:/memory/{name}:ro") and "CVDP_HARNESS" in seen["env"]
    assert seen["memory"] == f"/memory/{name}"  # the path inside the agent's container
    rows = list(csv.DictReader(open(work / "results.csv")))
    assert rows[0]["memory"] == memory.load(snapshot_path())["hash"] and rows[0]["stop_reason"] == "submit"
    run = json.load(open(str(work) + ".run.json"))
    assert (run["harness"], run["memory"]) == ("deepagents", snap)


def test_ablate_ids_keeps_only_the_listed_problems(tmp_path):
    import ablate

    for name, passes in (("a", "1100"), ("b", "1111")):
        with open(tmp_path / f"{name}.csv", "w") as f:
            f.write("id,seed,pass,cid,cost_usd,cost_unreported_calls,wall_time_s,prompt_tokens,completion_tokens\n"
                    + "".join(f"p{i},1,{p},cid003,0.01,0,10,1,1\n" for i, p in enumerate(passes)))
    (tmp_path / "ids.txt").write_text("# two problems\np0\np2\n")
    out = tmp_path / "out.csv"
    ablate.main(["--arm", f"A={tmp_path / 'a.csv'}", "--arm", f"B={tmp_path / 'b.csv'}", "--base", "A",
                 "--ids", str(tmp_path / "ids.txt"), "--pareto-csv", str(out)])
    rows = {r["arm"]: r for r in csv.DictReader(open(out))}
    assert float(rows["A"]["pass_rate"]) == 0.5 and float(rows["B"]["pass_rate"]) == 1.0


def test_retrieval_report_counts_k_per_problem(tmp_path):
    import retrieval

    ds = tmp_path / "ds.jsonl"
    ds.write_text("".join(json.dumps({"id": f"p{i}", "prompt": f"Design an APB block number {i} with ports",
                                      "context": {"docs/spec.md": "parameters and ports"}}) + "\n" for i in range(4)))
    snap = memory.load(snapshot_path())
    picks = retrieval.from_dataset(snap, str(ds), {"p0", "p1", "p2"})
    assert set(picks) == {"p0", "p1", "p2"} and all(len(v) == 5 for v in picks.values())
    assert retrieval.from_dataset(snap, str(ds), {"p0"})["p0"] == picks["p0"]  # deterministic
    assert "| L01 |" in retrieval.table(snap, picks)

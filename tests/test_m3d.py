"""M3d: verify before submit (verify_submit) and blind specification cases (spec_vectors), each a fixed step of the
LangGraph graph behind a switch that is off by default. The spec testbench tests run real Icarus; the rest use the
fake provider and the fake checker. No test needs an LLM."""
import csv
import json
import os
import shutil
import subprocess
import sys

import pytest

import collect
import golden_langgraph
import taxonomy
from conftest import FakeChecker
from cvdp_agent import config as config_mod
from cvdp_agent import spec as spec_mod
from test_m3c import COUNTER, RESET_ONLY_TB, STRONG_TB, decide, edit, harness_row, run_real, tree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICARUS = shutil.which("iverilog") and shutil.which("vvp")
needs_icarus = pytest.mark.skipif(not ICARUS, reason="needs iverilog (the Tests workflow installs it)")

PLAN = json.dumps({"files_to_change": ["rtl/counter.sv"], "approach": "counter", "check_plan": "testbench"})
BUGGY = COUNTER.replace("count + 1'b1", "count + 2'd2")
CASES = {
    "top": "counter", "params": {"WIDTH": 4}, "clock": "clk",
    "ports": {"clk": {"dir": "in", "width": 1}, "rst": {"dir": "in", "width": 1}, "en": {"dir": "in", "width": 1},
              "count": {"dir": "out", "width": 4}, "wrap": {"dir": "out", "width": 1}},
    "cases": [
        {"name": "reset", "steps": [{"in": {"rst": 1}}, {"in": {"rst": 1}, "expect": {"count": 0, "wrap": "x"}}]},
        {"name": "count up", "steps": [{"in": {"rst": 0, "en": 1}, "expect": {"count": 1}},
                                       {"expect": {"count": "0x2"}}, {"in": {"en": 0}, "expect": {"count": 2}}]},
        {"name": "wrap", "steps": [{"in": {"en": 1}, "until": {"signal": "count", "value": 15, "max_cycles": 40},
                                    "expect": {"wrap": 1}}, {"expect": {"count": 0, "wrap": 0}}]},
    ]}


# ---------- defaults: the M2/M3b/M3c agent, byte-for-byte ----------

def test_langgraph_golden_unchanged_with_both_m3d_switches_explicitly_off():
    got = json.loads(json.dumps(golden_langgraph.run_all({"verify_submit": False, "spec_vectors": False}),
                                sort_keys=True))
    assert got == json.load(open(golden_langgraph.GOLDEN))


def test_m3d_switches_default_off_and_are_absent_from_the_summary(monkeypatch):
    for k in ("CVDP_VERIFY_SUBMIT", "CVDP_SPEC_VECTORS"):
        monkeypatch.delenv(k, raising=False)
    cfg = config_mod.from_env()
    assert (cfg.verify_submit, cfg.spec_vectors) == (False, False)
    assert not {"verify_submit", "spec_vectors"} & set(cfg.switches())
    monkeypatch.setenv("CVDP_VERIFY_SUBMIT", "0")  # what the sweep sends for arm A
    monkeypatch.setenv("CVDP_SPEC_VECTORS", "0")
    assert config_mod.from_env().switches() == cfg.switches()
    monkeypatch.setenv("CVDP_SPEC_VECTORS", "1")  # S implies V
    on = config_mod.from_env()
    assert on.verify_submit and on.spec_vectors
    assert on.switches()["verify_submit"] is True and on.switches()["spec_vectors"] is True


def test_default_graph_has_no_m3d_node():
    from cvdp_agent.graph import mermaid

    g = mermaid()
    assert "verify" not in g and "spec" not in g
    assert "verify(verify)" in mermaid(verify_submit=True) and "spec(spec)" in mermaid(spec_vectors=True)
    with pytest.raises(ValueError):
        mermaid(verify_submit=True, mutation_gate=True)


def test_readme_has_the_m3d_graph():
    import re

    from cvdp_agent.graph import mermaid

    text = open(os.path.join(ROOT, "README.md")).read()
    m = re.search(r"<!-- graph-m3d:begin -->\s*```mermaid\n(.*?)```\s*<!-- graph-m3d:end -->", text, re.DOTALL)
    assert m, "README.md has no M3d graph block"
    assert m.group(1).strip() == mermaid(spec_vectors=True).strip()


# ---------- the case format ----------

def test_parse_cases_values_and_drops():
    bad_case = {"name": "bad", "steps": [{"in": {"nope": 1}}]}
    neg = {"name": "neg", "steps": [{"in": {"rst": 0}, "expect": {"count": "-1"}}]}
    reply = "Here are the cases:\n```json\n" + json.dumps({**CASES, "cases": CASES["cases"] + [bad_case, neg]}) + \
        "\n```"
    spec, notes = spec_mod.parse_cases(reply)
    assert [c["name"] for c in spec["cases"]] == ["reset", "count_up", "wrap", "neg"]
    assert any("case bad dropped" in n for n in notes)
    assert spec["cases"][3]["steps"][0]["expect"]["count"] == 15  # -1 at 4 bits
    assert spec["cases"][1]["steps"][1]["expect"]["count"] == 2
    assert spec["cases"][0]["steps"][1]["expect"]["wrap"] == "x"
    assert spec_mod.count(spec) == (4, 8)
    assert spec_mod.parse_cases("no json here")[0] is None
    assert spec_mod.parse_cases(json.dumps({**CASES, "top": "bad name"}))[0] is None
    assert spec_mod.parse_cases(json.dumps({**CASES, "clock": "count"}))[0] is None  # an output is no clock
    assert spec_mod.value("8'hff", 8) == 255 and spec_mod.value(256, 8) is None and spec_mod.value("0b101", 3) == 5


def run_spec_on(tmp_path, rtl):
    from cvdp_agent.checks import Checker, detect_tools
    from cvdp_agent.trace import Tracer

    root = tree(tmp_path, rtl={"counter.sv": rtl})
    spec, _ = spec_mod.parse_cases(json.dumps(CASES))
    spec_mod.write(str(root), spec)
    checker = Checker(str(root), Tracer(None), detect_tools(sys.executable))
    return spec_mod.run(checker, str(root), spec)


@needs_icarus
def test_spec_testbench_passes_a_correct_design_and_fails_a_wrong_one(tmp_path):
    good = run_spec_on(tmp_path / "good", COUNTER)
    assert good["status"] == "pass" and (good["passed"], good["total"]) == (3, 3), good
    bad = run_spec_on(tmp_path / "bad", BUGGY)
    assert bad["status"] == "fail" and "count_up" in bad["failed_cases"], bad
    assert any("signal=count" in m for m in bad["mismatches"])
    text = spec_mod.render(bad)
    assert "of 3 specification cases passed" in text and "expected=" in text


@needs_icarus
def test_spec_testbench_that_does_not_build_is_unbuildable(tmp_path):
    res = run_spec_on(tmp_path, COUNTER.replace("rst", "reset"))
    assert res["status"] == "unbuildable"


@needs_icarus
def test_spec_testbench_never_hangs(tmp_path):
    stuck = COUNTER.replace("else if (en) count <= count + 1'b1;", "")
    res = run_spec_on(tmp_path, stuck)
    assert res["status"] == "fail" and any("never became" in m for m in res["mismatches"]), res


# ---------- verify_submit on the fake provider ----------

class TbChecker(FakeChecker):
    """FakeChecker whose testbench check behaves like the real one: not run without a testbench, and its result
    set by `tb_ok`."""

    def __init__(self, root, tb_ok=True, **kw):
        super().__init__(root, **kw)
        self.tb_ok = tb_ok

    def run(self, names, tb=None):
        out = super().run(names, tb)
        if "testbench" in names:
            out["testbench"] = ({"ok": None, "summary": "not run: no <tb> block"} if not tb or not tb.get("files")
                                else {"ok": self.tb_ok, "summary": "fake testbench"})
        return out


def tb_edit(content=golden_langgraph.GOOD, checks="compile,testbench"):
    return (f'<file path="rtl/adder.sv">\n{content}</file>\n'
            f'<tb path="agent_tb/tb.sv" top="tb">\nmodule tb; endmodule\n</tb>\n<checks>{checks}</checks>')


def test_verify_refuses_twice_without_a_testbench_then_lets_through(make_cfg, run_agent, task_tree):
    cfg = make_cfg(verify_submit=True)
    script = [PLAN, golden_langgraph.edit(), decide("submit"), golden_langgraph.edit(), decide("submit"),
              golden_langgraph.edit(), decide("submit")]
    s, llm, _ = run_agent(cfg, script, checker=TbChecker(str(task_tree)))
    assert llm.calls == ["plan", "edit", "reflect", "edit", "reflect", "edit", "reflect"]
    assert s["stop_reason"] == "submit" and s["turns"] == 3
    assert (s["verify_runs"], s["verify_refusals"], s["verify_let_through"]) == (3, 2, 1)
    assert s["verify_outcomes"] == ["refused_no_tb", "refused_no_tb", "let_through"]
    assert s["verified_at_submit"] is False and s["testbench_runs"] == 0
    # the refusal reached the next edit's feedback, with what to do
    fb = llm.requests[3]["messages"][-1]["content"]
    assert "Submit refused" in fb and "reference model" in fb


def test_verify_passes_when_the_testbench_passed_on_the_current_files(make_cfg, run_agent, task_tree):
    cfg = make_cfg(verify_submit=True)
    s, llm, _ = run_agent(cfg, [PLAN, tb_edit(), decide("submit")], checker=TbChecker(str(task_tree)))
    assert llm.calls == ["plan", "edit", "reflect"] and s["stop_reason"] == "submit"
    assert s["verify_outcomes"] == ["pass"] and s["verified_at_submit"] is True and s["testbench_runs"] == 1
    assert s["verify_reruns"] == 0


def test_verify_reruns_the_testbench_after_an_edit_that_did_not_run_it(make_cfg, run_agent, task_tree):
    cfg = make_cfg(verify_submit=True)
    script = [PLAN, tb_edit(), decide("edit_again"), tb_edit(golden_langgraph.GOOD + "// v2\n", checks="compile"),
              decide("submit")]
    chk = TbChecker(str(task_tree))
    s, llm, _ = run_agent(cfg, script, checker=chk)
    assert s["verify_reruns"] == 1 and s["verify_outcomes"] == ["pass"] and s["testbench_runs"] == 2
    assert chk.requests[-1][0] == ["testbench"]  # the verify step's own run


def test_verify_refuses_a_failing_testbench_and_the_agent_edits(make_cfg, run_agent, task_tree):
    cfg = make_cfg(verify_submit=True)
    chk = TbChecker(str(task_tree), tb_ok=False)
    s, llm, _ = run_agent(cfg, [PLAN, tb_edit(), decide("submit"), tb_edit(), decide("give_up")], checker=chk)
    assert llm.calls == ["plan", "edit", "reflect", "edit", "reflect"] and s["stop_reason"] == "give_up"
    assert s["verify_outcomes"] == ["refused_tb_fail"] and s["verify_refusals"] == 1


def test_verify_lets_through_on_the_last_turn(make_cfg, run_agent, task_tree):
    cfg = make_cfg(verify_submit=True, max_turns=1)
    s, llm, _ = run_agent(cfg, [PLAN, golden_langgraph.edit(), decide("submit")], checker=TbChecker(str(task_tree)))
    assert s["stop_reason"] == "submit" and s["verify_outcomes"] == ["let_through"] and s["verify_refusals"] == 0


# ---------- spec_vectors end to end (real Icarus, fake provider) ----------

@needs_icarus
def test_spec_call_is_blind_and_its_cases_block_a_wrong_design(tmp_path):
    root = tree(tmp_path, rtl={"counter.sv": COUNTER.replace("endmodule", "  // ORIGINAL_BODY_MARK\nendmodule")})
    (root / "verif" / "given_tb.sv").write_text("module given_tb; // VERIF_MARK\nendmodule\n")
    cfg = config_mod.Config(root=str(root), provider="fake", spec_vectors=True)
    script = [json.dumps(CASES), PLAN, edit(BUGGY, RESET_ONLY_TB), decide("submit"), edit(COUNTER, RESET_ONLY_TB),
              decide("submit")]
    s, llm = run_real(cfg, script)
    assert llm.calls == ["spec", "plan", "edit", "reflect", "edit", "reflect"]
    spec_req = llm.requests[0]
    assert spec_req["node"] == "spec"
    text = "\n".join(m["content"] for m in spec_req["messages"])
    assert "ORIGINAL_BODY_MARK" not in text and "always_ff" not in text and "VERIF_MARK" not in text
    assert "docs/spec.md" in text and "module counter" in text and "input clk [1 bits]" in text  # docs and the port table
    assert s["spec_status"] == "generated" and s["spec_cases"] == 3 and not s["spec_failed_open"]
    assert s["verify_outcomes"] == ["refused_spec_fail", "pass"]
    assert (s["spec_final_status"], s["spec_final_passed"], s["spec_final_total"]) == ("pass", 3, 3)
    # the refusal showed the mismatches, not the cases' source
    fb = llm.requests[4]["messages"][-1]["content"]
    assert "specification cases passed" in fb and "signal=count" in fb and '"cases"' not in fb
    row = harness_row(root, cfg, tmp_path)
    assert (row["verify_submit"], row["spec_vectors"], row["spec_cases"], row["spec_final_status"]) == (1, 1, 3,
                                                                                                        "pass")
    assert row["verify_outcomes"] == "refused_spec_fail+pass"


@needs_icarus
def test_spec_call_fails_open_on_an_unusable_reply(tmp_path):
    root = tree(tmp_path)
    cfg = config_mod.Config(root=str(root), provider="fake", spec_vectors=True)
    s, llm = run_real(cfg, ["I cannot do that.", PLAN, edit(COUNTER, STRONG_TB), decide("submit")])
    assert llm.calls == ["spec", "plan", "edit", "reflect"]
    assert s["spec_status"] == "unusable" and s["spec_failed_open"] and s["verify_outcomes"] == ["pass"]
    assert s["spec_final_status"] is None


# ---------- results tools ----------

@needs_icarus
def test_arm_a_rows_have_blank_m3d_columns(tmp_path):
    root = tree(tmp_path)
    cfg = config_mod.Config(root=str(root), provider="fake")
    s, _ = run_real(cfg, [PLAN, edit(), decide("submit")])
    assert not {k for k in s if k.startswith(("verify_", "spec_", "testbench_runs"))}
    row = harness_row(root, cfg, tmp_path)
    assert (row["verify_submit"], row["spec_vectors"]) == (0, 0)
    assert all(row[k] == "" for k in collect.FIELDS[collect.FIELDS.index("verify_runs"):])


def test_taxonomy_flags_for_m3d():
    base = {"pass": "0", "stop_reason": "submit", "log_class": "tests_failed", "own_compile_last": "pass",
            "selfcheck_runs": "2", "selfcheck_last": "pass", "rtl_changed": "1", "turns": "3"}
    label, flags = taxonomy.label({**base, "verify_let_through": "1", "spec_final_status": "pass"})
    assert label == "tests_failed_selfcheck_passed" and {"verify_let_through", "spec_checks_passed"} <= set(flags)
    assert "spec_checks_failed" in taxonomy.label({**base, "spec_final_status": "fail"})[1]
    assert "spec_failed_open" in taxonomy.label({**base, "spec_failed_open": "1"})[1]
    assert taxonomy.label(base) == ("tests_failed_selfcheck_passed", [])


def test_old_csv_still_reads(tmp_path):
    import ablate

    old = os.path.join(ROOT, "docs", "reports", "m3c", "runs", "A1_40257040625.csv")
    rows = ablate.load(old)
    assert rows and "verify_submit" not in rows[0]
    assert taxonomy.label({k: v or "" for k, v in rows[0].items()})


# ---------- the sweep's new inputs ----------

def test_sweep_passes_the_m3d_switches_off_by_default_and_on_when_asked(tmp_path):
    from test_m3c import sweep

    for name, extra, want in (("off", {}, ("0", "0")), ("v", {"VERIFY_SUBMIT": "1"}, ("1", "0")),
                              ("s", {"SPEC_VECTORS": "1"}, ("1", "1"))):
        d = tmp_path / name
        d.mkdir()
        r = sweep(d, **extra)
        assert r.returncode == 0, r.stdout + r.stderr
        seen = json.loads(open(d / "seen.jsonl").readline())
        assert (seen["CVDP_VERIFY_SUBMIT"], seen["CVDP_SPEC_VECTORS"]) == want
        run = json.load(open(str(d / "work") + ".run.json"))
        assert ("verify_submit" in run) == (want[0] == "1")
        rows = list(csv.DictReader(open(d / "work" / "results.csv")))
        assert (rows[0]["verify_submit"], rows[0]["spec_vectors"]) == want


def test_sweep_refuses_bad_m3d_combinations(tmp_path):
    for extra in ({"HARNESS": "deepagents", "VERIFY_SUBMIT": "1"}, {"VERIFY_SUBMIT": "1", "MUTATION_GATE": "1"},
                  {"SPEC_VECTORS": "1", "SELF_CHECK": "0"}, {"VERIFY_SUBMIT": "yes"}):
        env = dict(os.environ, WORK=str(tmp_path / "w"), AGENT_IMAGE="x", **extra)
        r = subprocess.run(["bash", os.path.join(ROOT, "tools", "sweep.sh")], env=env, capture_output=True,
                           text=True)
        assert r.returncode == 2 and ("VERIFY_SUBMIT" in r.stderr or "SPEC_VECTORS" in r.stderr), r.stderr

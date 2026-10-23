"""The graph with the fake provider: stop rules, path refusal, budget cap, best-edit-kept rule and switches.
No test needs an LLM."""
import json
import os

import pytest

from cvdp_agent import config as config_mod
from conftest import ORIGINAL_RTL

PLAN = json.dumps({"files_to_change": ["rtl/adder.sv"], "approach": "y = a + b", "check_plan": "compile"})
GOOD = "module adder(input [3:0] a, b, output [4:0] y);\n  assign y = a + b;\nendmodule\n"
BAD = "module adder(input [3:0] a, b, output [4:0] y);\n  SYNTAX_ERROR\nendmodule\n"


def edit(content=GOOD, path="rtl/adder.sv", checks="compile,lint,testbench", extra=""):
    return f'<file path="{path}">\n{content}</file>\n{extra}<checks>{checks}</checks>'


def decide(d):
    return json.dumps({"decision": d, "reason": "test"})


def rtl(task_tree, name="adder.sv"):
    return (task_tree / "rtl" / name).read_text()


def test_submit(make_cfg, run_agent, task_tree):
    cfg = make_cfg()
    s, llm, _ = run_agent(cfg, [{"text": PLAN, "cost": 0.001}, {"text": edit(), "cost": 0.002},
                                {"text": decide("submit"), "cost": 0.003}])
    assert s["stop_reason"] == "submit"
    assert s["turns"] == 1 and s["llm_calls"] == 3
    assert llm.calls == ["plan", "edit", "reflect"]
    assert s["cost_usd"] == pytest.approx(0.006)
    assert s["kept"] == "last" and s["files_changed"] == ["rtl/adder.sv"]
    assert rtl(task_tree) == GOOD
    assert os.path.exists(os.path.join(cfg.agent_out, "trace.jsonl"))


def test_give_up(make_cfg, run_agent):
    s, _, _ = run_agent(make_cfg(), [PLAN, edit(), decide("give_up")])
    assert s["stop_reason"] == "give_up" and s["turns"] == 1


def test_turn_cap(make_cfg, run_agent):
    s, llm, _ = run_agent(make_cfg(max_turns=2), [PLAN, edit(), decide("edit_again"), edit(),
                                                  decide("edit_again"), edit()])
    assert s["stop_reason"] == "max_turns"
    assert s["turns"] == 2
    assert llm.calls == ["plan", "edit", "reflect", "edit", "reflect"]


def test_budget_cap(make_cfg, run_agent):
    # 0.04 per call against 0.10: plan (0.04), edit (0.08), reflect (0.12) -> no further LLM call.
    script = [{"text": t, "cost": 0.04} for t in (PLAN, edit(), decide("edit_again"), edit())]
    s, llm, _ = run_agent(make_cfg(budget_usd=0.10), script)
    assert s["stop_reason"] == "budget"
    assert llm.calls == ["plan", "edit", "reflect"]
    assert s["cost_usd"] == pytest.approx(0.12)


def test_budget_cap_before_first_call(make_cfg, run_agent):
    s, llm, _ = run_agent(make_cfg(budget_usd=0.0), [PLAN])
    assert s["stop_reason"] == "budget" and llm.calls == [] and s["kept"] == "none"


def test_wall_time_cap_runs_compile_on_unchecked_edit(make_cfg, run_agent, task_tree):
    s, llm, checker = run_agent(make_cfg(wall_s=100), [PLAN, {"text": edit(), "sleep": 150}])
    assert s["stop_reason"] == "wall_time"
    assert llm.calls == ["plan", "edit"]
    assert checker.requests == [([], None)]  # finalize compiled the unchecked edit
    assert s["final_compiled"] is True and rtl(task_tree) == GOOD


def test_wall_time_cap_between_check_and_reflect(make_cfg, run_agent):
    s, llm, _ = run_agent(make_cfg(wall_s=100), [PLAN, edit(), decide("submit")], check_cost_s=120)
    assert s["stop_reason"] == "wall_time" and llm.calls == ["plan", "edit"]


def test_best_edit_kept_on_cap(make_cfg, run_agent, task_tree):
    script = [PLAN, edit(GOOD), decide("edit_again"),
              edit(BAD, extra=f'<file path="rtl/extra.sv">\nmodule extra; endmodule\n</file>\n'),
              decide("edit_again")]
    s, _, _ = run_agent(make_cfg(max_turns=2), script)
    assert s["stop_reason"] == "max_turns"
    assert s["kept"] == "best_compiled_turn_1"
    assert rtl(task_tree) == GOOD
    assert not (task_tree / "rtl" / "extra.sv").exists()  # created after the best edit: removed


def test_best_edit_kept_on_give_up(make_cfg, run_agent, task_tree):
    s, _, _ = run_agent(make_cfg(), [PLAN, edit(GOOD), decide("edit_again"), edit(BAD), decide("give_up")])
    assert s["kept"] == "best_compiled_turn_1" and rtl(task_tree) == GOOD


def test_last_edit_kept_when_nothing_compiled(make_cfg, run_agent, task_tree):
    s, _, _ = run_agent(make_cfg(max_turns=1), [PLAN, edit(BAD), decide("edit_again")])
    assert s["kept"] == "last" and rtl(task_tree) == BAD


def test_path_refusal(make_cfg, run_agent, task_tree):
    bad_paths = ["/etc/passwd", "../outside.sv", "rtl/../prompt.json", "prompt.json", "rundir/x.sv",
                 "/code/rundir/agent_out/summary.json", "src/test_runner.py", "rtl/../../escape.sv"]
    blocks = "".join(f'<file path="{p}">\nPWNED\n</file>\n' for p in bad_paths)
    blocks += '<tb path="rtl/sneaky_tb.sv" top="t">\nPWNED\n</tb>\n'
    blocks += '<tb path="agent_tb/../../rtl/sneaky2.sv" top="t">\nPWNED\n</tb>\n'
    s, _, _ = run_agent(make_cfg(), [PLAN, blocks + "<checks>compile</checks>", decide("submit")])
    assert s["files_changed"] == []
    for root, _, files in os.walk(task_tree.parent):
        for fn in files:
            p = os.path.join(root, fn)
            if not p.endswith(".jsonl"):
                assert "PWNED" not in open(p, errors="replace").read(), p
    events = [json.loads(x) for x in open(os.path.join(str(task_tree), "rundir/agent_out/trace.jsonl"))]
    refused = [e for e in events if e.get("check") in ("file_write", "tb_write") and e["exit_code"] == 1]
    assert len(refused) == len(bad_paths) + 2


def test_switch_self_check_off(make_cfg, run_agent, task_tree):
    tb = '<tb path="agent_tb/tb.sv" top="tb">\nmodule tb; endmodule\n</tb>\n'
    s, _, checker = run_agent(make_cfg(self_check=False), [PLAN, edit(extra=tb), decide("submit")])
    names, tbarg = checker.requests[0]
    assert "testbench" not in names and tbarg is None
    assert not (task_tree / "rundir" / "agent_tb" / "tb.sv").exists()
    assert s["switches"]["self_check"] is False


def test_switch_self_check_on(make_cfg, run_agent, task_tree):
    tb = '<tb path="agent_tb/tb.sv" top="tb">\nmodule tb; endmodule\n</tb>\n'
    _, _, checker = run_agent(make_cfg(), [PLAN, edit(extra=tb), decide("submit")])
    names, tbarg = checker.requests[0]
    assert "testbench" in names and tbarg == {"files": ["rundir/agent_tb/tb.sv"], "top": "tb"}


def test_switch_lint_off(make_cfg, run_agent):
    _, _, checker = run_agent(make_cfg(lint=False), [PLAN, edit(checks="compile,lint,synth"), decide("submit")])
    assert checker.requests[0][0] == ["compile"]
    _, _, checker = run_agent(make_cfg(lint=True), [PLAN, edit(checks="compile,lint,synth"), decide("submit")])
    assert checker.requests[0][0] == ["compile", "lint", "synth"]


def test_switches_from_env(monkeypatch):
    for k, v in {"CVDP_SELF_CHECK": "0", "CVDP_LINT": "0", "CVDP_MAX_TURNS": "3", "CVDP_BUDGET_USD": "0.05",
                 "CVDP_MODEL": "x/y", "CVDP_PROVIDER": "fake"}.items():
        monkeypatch.setenv(k, v)
    c = config_mod.from_env()
    assert (c.self_check, c.lint, c.max_turns, c.budget_usd, c.model, c.provider) == (False, False, 3, 0.05,
                                                                                      "x/y", "fake")
    for k in ("CVDP_SELF_CHECK", "CVDP_LINT", "CVDP_MAX_TURNS", "CVDP_BUDGET_USD"):
        monkeypatch.delenv(k)
    c = config_mod.from_env()
    assert (c.self_check, c.lint, c.max_turns, c.budget_usd) == (True, True, 10, 0.10)


def test_prompt_follows_switches(make_cfg, run_agent):
    from cvdp_agent import prompts
    from cvdp_agent.llm import FakeLLM

    seen = []

    class Spy(FakeLLM):
        def invoke(self, node, messages, max_tokens=None, timeout=None):
            seen.append((node, messages[-1]["content"]))
            return super().invoke(node, messages, max_tokens, timeout)

    from cvdp_agent.graph import run
    from conftest import FakeChecker
    cfg = make_cfg(self_check=False, lint=False)
    run(cfg, llm=Spy([PLAN, edit(), decide("submit")]), checker=FakeChecker(cfg.root), tools={"verilator": True})
    edit_prompt = dict(seen)["edit"]
    assert prompts.TB_OFF in edit_prompt and "testbench" not in edit_prompt.split("choose the checks")[1]


def test_unreported_cost_is_null_and_stops_the_problem(make_cfg, run_agent):
    s, llm, _ = run_agent(make_cfg(), [{"text": PLAN, "cost": None}, {"text": edit(), "cost": None},
                                       {"text": decide("submit"), "cost": None}])
    assert s["cost_usd"] is None and s["cost_unreported_calls"] == 1
    assert s["stop_reason"] == "cost_unreported" and llm.calls == ["plan"]


def test_unreported_cost_after_reported_keeps_reported_sum(make_cfg, run_agent, task_tree):
    s, llm, _ = run_agent(make_cfg(), [{"text": PLAN, "cost": 0.01}, {"text": edit(), "cost": None},
                                       {"text": decide("submit"), "cost": 0.01}])
    assert s["stop_reason"] == "cost_unreported" and llm.calls == ["plan", "edit"]
    assert s["cost_usd"] == pytest.approx(0.01) and s["cost_unreported_calls"] == 1
    assert rtl(task_tree) == GOOD  # the edit was applied and checked before stopping


def test_errored_call_counts_as_unreported(make_cfg, run_agent):
    s, _, _ = run_agent(make_cfg(), [{"text": PLAN, "cost": 0.01}, {"raise": "timeout"}])
    assert s["stop_reason"] == "llm_error" and s["cost_unreported_calls"] == 1


def test_llm_error_keeps_best_and_stops(make_cfg, run_agent, task_tree):
    s, _, _ = run_agent(make_cfg(), [PLAN, edit(GOOD), decide("edit_again"), {"raise": "HTTP 500"}])
    assert s["stop_reason"] == "llm_error" and rtl(task_tree) == GOOD


def test_run_budget_ledger(make_cfg, run_agent, tmp_path):
    ledger = tmp_path / "ledger"
    ledger.mkdir()
    (ledger / "a.json").write_text(json.dumps({"cost_usd": 0.6}))
    s, llm, _ = run_agent(make_cfg(ledger_dir=str(ledger), run_budget_usd=0.5), [PLAN])
    assert s["stop_reason"] == "run_budget_exhausted" and llm.calls == []
    s, llm, _ = run_agent(make_cfg(ledger_dir=str(ledger), run_budget_usd=5.0),
                          [{"text": PLAN, "cost": 0.01}, {"text": edit(), "cost": 0.01},
                           {"text": decide("submit"), "cost": 0.01}])
    assert s["stop_reason"] == "submit"
    from cvdp_agent.graph import ledger_total
    assert ledger_total(str(ledger)) == pytest.approx(0.63)


def test_run_guard_charges_unreported_calls(make_cfg, run_agent, tmp_path):
    from cvdp_agent.graph import ledger_totals

    ledger = tmp_path / "ledger"
    ledger.mkdir()
    # one problem with a reported $0.01 and one unreported call: the guard charges the $0.10 budget for it
    run_agent(make_cfg(ledger_dir=str(ledger), run_budget_usd=0.5),
              [{"text": PLAN, "cost": 0.01}, {"text": edit(), "cost": None}])
    reported, unreported, charge = ledger_totals(str(ledger))
    assert (reported, unreported) == (pytest.approx(0.01), 1) and charge == pytest.approx(0.11)
    for _ in range(4):
        run_agent(make_cfg(ledger_dir=str(ledger), run_budget_usd=0.5), [{"text": PLAN, "cost": None}])
    s, llm, _ = run_agent(make_cfg(ledger_dir=str(ledger), run_budget_usd=0.5), [PLAN])
    assert s["stop_reason"] == "run_budget_exhausted" and llm.calls == []  # 0.11 + 4 x 0.10 >= 0.5


class CrashingChecker:
    tb_dir = "/nonexistent"
    calls = 0

    def run(self, names, tb=None):
        raise RuntimeError("checker blew up")


def test_crash_still_finalizes(make_cfg, run_agent, task_tree, tmp_path):
    ledger = tmp_path / "ledger"
    ledger.mkdir()
    s, _, _ = run_agent(make_cfg(ledger_dir=str(ledger), run_budget_usd=5.0),
                        [{"text": PLAN, "cost": 0.01}, {"text": edit(), "cost": 0.02}], checker=CrashingChecker())
    assert s["stop_reason"] == "error" and "checker blew up" in s["error"]
    assert s["cost_usd"] == pytest.approx(0.03) and s["turns"] == 1
    assert len(list(ledger.iterdir())) == 1  # the ledger entry is written
    assert rtl(task_tree) == GOOD


def test_non_utf8_file_is_an_edit_error_not_a_crash(make_cfg, run_agent, task_tree):
    (task_tree / "rtl" / "latin1.sv").write_bytes(b"// caf\xe9\nmodule m; endmodule\n")
    diff = '<diff path="rtl/latin1.sv">\n@@\n-module m; endmodule\n+module m2; endmodule\n</diff>\n'
    s, _, _ = run_agent(make_cfg(), [PLAN, edit(extra=diff), decide("submit")])
    assert s["stop_reason"] == "submit" and s["files_changed"] == ["rtl/adder.sv"]


def test_dangling_symlink_does_not_break_snapshot(make_cfg, run_agent, task_tree):
    os.symlink("/nonexistent/target.sv", task_tree / "rtl" / "dangling.sv")
    s, _, _ = run_agent(make_cfg(max_turns=2), [PLAN, edit(GOOD), decide("edit_again"), edit(BAD),
                                                decide("edit_again")])
    assert s["stop_reason"] == "max_turns" and s["kept"] == "best_compiled_turn_1"
    assert rtl(task_tree) == GOOD


def test_bad_env_input_still_exits_zero(monkeypatch, task_tree):
    from cvdp_agent.__main__ import main

    monkeypatch.setenv("CVDP_ROOT", str(task_tree))
    monkeypatch.setenv("CVDP_PROVIDER", "fake")
    monkeypatch.setenv("CVDP_MAX_TURNS", "10.0")
    monkeypatch.delenv("CVDP_OUT_DIR", raising=False)
    assert main([]) == 0
    s = json.load(open(task_tree / "rundir" / "agent_out" / "summary.json"))
    assert s["stop_reason"] == "error" and "ValueError" in s["error"]


def test_no_prompt_json(make_cfg, run_agent, task_tree):
    (task_tree / "prompt.json").unlink()
    s, llm, _ = run_agent(make_cfg(), [])
    assert s["stop_reason"] == "no_task" and llm.calls == []


def test_default_fake_script_runs(make_cfg, run_agent, task_tree):
    s, llm, checker = run_agent(make_cfg(), [])
    assert s["stop_reason"] == "submit" and llm.calls == ["plan", "edit", "reflect"]
    assert rtl(task_tree) == ORIGINAL_RTL  # the smoke script never changes the design
    assert checker.requests[0][1]["files"] == ["rundir/agent_tb/agent_smoke_tb.sv"]


def test_main_exits_zero_on_error(monkeypatch, task_tree):
    from cvdp_agent.__main__ import main

    monkeypatch.setenv("CVDP_ROOT", str(task_tree))
    monkeypatch.setenv("CVDP_PROVIDER", "openrouter")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("CVDP_MODEL", raising=False)
    assert main([]) == 0
    s = json.load(open(task_tree / "rundir" / "agent_out" / "summary.json"))
    assert s["stop_reason"] == "error"


def test_existing_verif_testbench_is_run_not_written(make_cfg, run_agent, task_tree):
    (task_tree / "verif" / "adder_tb.sv").write_text("module adder_tb; endmodule\n")
    blocks = ('<tb path="verif/adder_tb.sv" top="adder_tb"></tb>\n'
              '<tb path="verif/missing_tb.sv" top="x"></tb>\n<tb path="rtl/adder.sv" top="x"></tb>\n')
    _, _, checker = run_agent(make_cfg(), [PLAN, edit(extra=blocks), decide("submit")])
    assert checker.requests[0][1] == {"files": ["verif/adder_tb.sv"], "top": "adder_tb"}
    assert (task_tree / "verif" / "adder_tb.sv").read_text() == "module adder_tb; endmodule\n"

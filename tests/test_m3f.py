"""M3f: per-role models. With no role model set the agent is the M3d one byte-for-byte (golden); with one set, that
role's calls go to its own client, at the roles' reasoning level and budget, and the summary, the trace, the CSV and
the sweep record who did what and what it cost. Fake provider only: no test needs an LLM."""
import csv
import json
import os
import subprocess

import golden_langgraph
from cvdp_agent import config as config_mod
from cvdp_agent.config import Config
from cvdp_agent.llm import FakeLLM, RoleLLM, make_role

import collect

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN = golden_langgraph.PLAN
STRONG = "anthropic/claude-sonnet-5.5"
ROLE_ENV = ("CVDP_PLAN_MODEL", "CVDP_SPEC_MODEL", "CVDP_ROLE_REASONING", "CVDP_ROLE_BUDGET_USD")


def decide(d):
    return golden_langgraph.decide(d)


def trace(cfg):
    return [json.loads(x) for x in open(os.path.join(cfg.agent_out, "trace.jsonl"))]


# ---------- defaults: the M3d agent, byte-for-byte ----------

def test_langgraph_golden_unchanged_with_the_role_settings_explicitly_blank():
    got = json.loads(json.dumps(golden_langgraph.run_all({"plan_model": "", "spec_model": "", "role_reasoning": "",
                                                          "role_budget_usd": 0.5}), sort_keys=True))
    assert got == json.load(open(golden_langgraph.GOLDEN))


def test_role_settings_default_blank_and_are_absent_from_the_summary(monkeypatch):
    for k in ROLE_ENV:
        monkeypatch.delenv(k, raising=False)
    cfg = config_mod.from_env()
    assert (cfg.plan_model, cfg.spec_model, cfg.role_reasoning) == ("", "", "") and cfg.role_models() == {}
    assert not {"plan_model", "spec_model", "role_reasoning", "role_budget_usd"} & set(cfg.switches())
    for k in ROLE_ENV:  # blank values, as a sweep that passed them would send
        monkeypatch.setenv(k, "")
    assert config_mod.from_env().switches() == cfg.switches()
    monkeypatch.setenv("CVDP_PLAN_MODEL", STRONG)
    monkeypatch.setenv("CVDP_ROLE_REASONING", "low")
    on = config_mod.from_env()
    assert on.role_models() == {"plan": STRONG}
    assert on.switches()["plan_model"] == STRONG and on.switches()["role_reasoning"] == "low"


def test_default_runtime_has_no_role_client(task_tree, run_agent):
    s, llm, _ = run_agent(Config(root=str(task_tree), provider="fake"), [PLAN, golden_langgraph.edit(),
                                                                          decide("submit")])
    assert "role_models" not in s and all("model" not in r for r in llm.requests)


# ---------- routing ----------

def test_plan_model_gets_the_plan_call_only(task_tree, run_agent):
    cfg = Config(root=str(task_tree), provider="fake", model="openai/gpt-6-luna", plan_model=STRONG)
    s, llm, _ = run_agent(cfg, [{"text": PLAN, "cost": 0.02}, {"text": golden_langgraph.edit(), "cost": 0.003},
                                {"text": decide("submit"), "cost": 0.001}])
    assert [(r["node"], r.get("model")) for r in llm.requests] == [("plan", STRONG), ("edit", None),
                                                                   ("reflect", None)]
    served = {e["node"]: e["model"] for e in trace(cfg) if e["kind"] == "llm"}
    assert served == {"plan": STRONG, "edit": "fake", "reflect": "fake"}
    start = next(e for e in trace(cfg) if e["kind"] == "start")
    assert start["switches"]["plan_model"] == STRONG
    assert s["role_models"] == {"plan": STRONG} and s["role_calls"] == 1
    assert s["role_cost_usd"] == 0.02 and s["main_cost_usd"] == 0.004 and s["cost_usd"] == 0.024
    assert s["cost_by_model"] == {STRONG: 0.02, "fake": 0.004}
    assert s["switches"]["plan_model"] == STRONG and s["stop_reason"] == "submit"


def test_spec_model_gets_the_spec_call_only(task_tree, run_agent):
    cfg = Config(root=str(task_tree), provider="fake", model="openai/gpt-6-luna", spec_model=STRONG,
                 spec_vectors=True, max_turns=1)
    s, llm, _ = run_agent(cfg, [{"text": "no cases", "cost": 0.01}, PLAN, golden_langgraph.edit(),
                                decide("submit")])
    routed = [(r["node"], r.get("model")) for r in llm.requests]
    assert routed[0] == ("spec", STRONG) and all(m is None for n, m in routed[1:])
    assert s["role_models"] == {"spec": STRONG} and s["spec_status"] == "unusable"


def test_plan_and_spec_models_together_and_a_different_edit_model(task_tree, run_agent):
    """Arm PT, and arm C's shape: `model` is the edit-and-fix model, the roles name the others."""
    cfg = Config(root=str(task_tree), provider="fake", model="some/coder", plan_model=STRONG, spec_model="x/tester",
                 spec_vectors=True, max_turns=1)
    s, llm, _ = run_agent(cfg, ["no cases", PLAN, golden_langgraph.edit(), decide("submit")])
    assert [(r["node"], r.get("model")) for r in llm.requests][:3] == [("spec", "x/tester"), ("plan", STRONG),
                                                                       ("edit", None)]
    assert s["role_models"] == {"plan": STRONG, "spec": "x/tester"}


def test_role_reasoning_applies_to_the_roles_only(task_tree, run_agent):
    cfg = Config(root=str(task_tree), provider="fake", reasoning="default", plan_model=STRONG, role_reasoning="low")
    s, llm, _ = run_agent(cfg, [PLAN, golden_langgraph.edit(), decide("submit")])
    bodies = {r["node"]: r["body"]["reasoning"] for r in llm.requests}
    assert bodies["plan"] == {"effort": "low", "exclude": True} and bodies["edit"] is None
    assert s["role_reasoning_used"] == "low" and s["reasoning_used"] == "default"


def test_a_role_model_refusing_reasoning_falls_back_alone(task_tree, clock):
    from conftest import FakeChecker
    from cvdp_agent.graph import run
    from cvdp_agent.trace import Tracer

    cfg = Config(root=str(task_tree), provider="fake", reasoning="default", plan_model=STRONG, role_reasoning="low")
    main = FakeLLM([PLAN, golden_langgraph.edit(), decide("submit")], clock=clock)
    strong = FakeLLM([], clock=clock, rejects_reasoning=True)
    strong.script = main.script  # one script, as RoleLLM shares it; this client refuses the reasoning field
    s = run(cfg, llm=main, role_llms={"plan": RoleLLM(strong, STRONG)}, checker=FakeChecker(str(task_tree), clock=clock),
            tools={"iverilog": True, "verilator": True, "yosys": True, "cocotb": True}, clock=clock,
            tracer=Tracer(cfg.agent_out))
    assert s["reasoning_rejected"] == 1 and s["role_reasoning_used"] == "default" and s["reasoning_used"] == "default"
    assert [r["body"]["reasoning"] for r in strong.requests] == [{"effort": "low", "exclude": True}, None]
    assert s["stop_reason"] == "submit"


def test_role_spend_is_kept_out_of_the_edit_loops_budget(task_tree, run_agent):
    script = [{"text": PLAN, "cost": 0.04}, {"text": golden_langgraph.edit(), "cost": 0.03},
              {"text": decide("edit_again"), "cost": 0.01}, {"text": golden_langgraph.edit(), "cost": 0.03},
              {"text": decide("submit"), "cost": 0.01}]
    base = Config(root=str(task_tree), provider="fake", budget_usd=0.05)
    s0, _, _ = run_agent(base, json.loads(json.dumps(script)))
    assert s0["stop_reason"] == "budget" and s0["llm_calls"] == 2  # the M3d rule: 0.07 of 0.05 after edit
    roles = Config(root=str(task_tree), provider="fake", budget_usd=0.05, plan_model=STRONG,
                   out_dir=str(task_tree / "rundir" / "out2"))
    s1, _, _ = run_agent(roles, json.loads(json.dumps(script)))
    assert s1["stop_reason"] == "budget" and s1["llm_calls"] == 4  # the edit loop's own 0.07 of 0.05
    assert s1["role_cost_usd"] == 0.04 and s1["main_cost_usd"] == 0.07


def test_role_budget_stops_a_role_call(task_tree, run_agent):
    cfg = Config(root=str(task_tree), provider="fake", spec_model=STRONG, plan_model=STRONG, spec_vectors=True,
                 role_budget_usd=0.01)
    s, llm, _ = run_agent(cfg, [{"text": "no cases", "cost": 0.02}, PLAN])
    assert [r["node"] for r in llm.requests] == ["spec"] and s["stop_reason"] == "budget"


def test_make_role_clients():
    base = FakeLLM()
    assert isinstance(make_role(Config(provider="fake"), STRONG, base), RoleLLM)
    os.environ.setdefault("OPENROUTER_API_KEY", "")
    if os.environ["OPENROUTER_API_KEY"]:
        return  # never build a real client with a real key in a test
    os.environ["OPENROUTER_API_KEY"] = "test-not-a-key"
    try:
        c = make_role(Config(provider="openrouter", model="m", provider_order=["OpenAI"]), STRONG, base)
        assert c.model == STRONG and c.provider_order == []  # the main model's pin is not applied to a role
    finally:
        os.environ["OPENROUTER_API_KEY"] = ""


# ---------- records ----------

def test_collect_columns_blank_by_default_and_filled_with_roles():
    blank = collect.m3f_columns({"switches": {}})
    assert set(blank) == set(collect.FIELDS[collect.FIELDS.index("plan_model"):]) and not any(blank.values())
    got = collect.m3f_columns({"role_models": {"plan": STRONG}, "role_reasoning_used": "low", "role_calls": 1,
                               "role_cost_usd": 0.02, "main_cost_usd": 0.004,
                               "cost_by_model": {STRONG: 0.02, "openai/gpt-6-luna": 0.004}})
    assert got["plan_model"] == STRONG and got["spec_model"] == "" and got["role_cost_usd"] == 0.02
    assert got["cost_by_model"] == f"{STRONG}:0.02+openai/gpt-6-luna:0.004"


def test_sweep_passes_role_models_only_when_set(tmp_path):
    from test_m3c import sweep

    for name, extra in (("off", {}), ("on", {"PLAN_MODEL": STRONG, "ROLE_REASONING": "low"})):
        d = tmp_path / name
        d.mkdir()
        r = sweep(d, **extra)
        assert r.returncode == 0, r.stdout + r.stderr
        seen = json.loads(open(d / "seen.jsonl").readline())
        run = json.load(open(str(d / "work") + ".run.json"))
        rows = list(csv.DictReader(open(d / "work" / "results.csv")))
        if name == "off":
            assert not {k for k in seen if k in ROLE_ENV} and "plan_model" not in run
            assert rows[0]["plan_model"] == ""
        else:
            assert seen["CVDP_PLAN_MODEL"] == STRONG and seen["CVDP_ROLE_REASONING"] == "low"
            assert run["plan_model"] == STRONG and run["role_reasoning"] == "low"
            assert rows[0]["plan_model"] == STRONG


def test_sweep_refuses_bad_role_settings(tmp_path):
    for extra in ({"SPEC_MODEL": STRONG}, {"PLAN_MODEL": STRONG, "HARNESS": "deepagents"},
                  {"PLAN_MODEL": "bad model"}, {"ROLE_REASONING": "lots"}):
        env = dict(os.environ, WORK=str(tmp_path / "w"), AGENT_IMAGE="x", **extra)
        r = subprocess.run(["bash", os.path.join(ROOT, "tools", "sweep.sh")], env=env, capture_output=True,
                           text=True)
        assert r.returncode == 2 and ("MODEL" in r.stderr or "ROLE_REASONING" in r.stderr), r.stderr

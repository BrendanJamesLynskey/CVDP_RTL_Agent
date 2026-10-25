"""Golden runs of the LangGraph agent on the fake provider: the prompts it sends, the trace (without timestamps)
and the summary, for a few scripted problems. Written once from `main` before M3b (`write`), and compared by
tests/test_m3b.py, so `harness=langgraph` with no memory stays byte-for-byte what it was.

Usage (repo root): python3 tests/golden_langgraph.py write
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "agent"))
sys.path.insert(0, HERE)

GOLDEN = os.path.join(HERE, "fixtures", "golden", "langgraph_fake.json")
PLAN = json.dumps({"files_to_change": ["rtl/adder.sv"], "approach": "y = a + b", "check_plan": "compile"})
GOOD = "module adder(input [3:0] a, b, output [4:0] y);\n  assign y = a + b;\nendmodule\n"
BAD = "module adder(input [3:0] a, b, output [4:0] y);\n  SYNTAX_ERROR\nendmodule\n"


def edit(content=GOOD):
    return f'<file path="rtl/adder.sv">\n{content}</file>\n<checks>compile,lint,testbench</checks>'


def decide(d):
    return json.dumps({"decision": d, "reason": "golden"})


SCENARIOS = {
    "submit": ({"reasoning": "low"}, [{"text": PLAN, "cost": 0.001}, {"text": edit(), "cost": 0.002},
                                      {"text": decide("submit"), "cost": 0.001}]),
    "empty_retry_then_best_edit": ({"reasoning": "default", "max_turns": 2},
                                   [{"text": PLAN, "cost": 0.001}, {"text": "", "cost": 0.004},
                                    {"text": edit(), "cost": 0.002}, {"text": decide("edit_again"), "cost": 0.001},
                                    {"text": edit(BAD), "cost": 0.002}, {"text": "not json", "cost": 0.001},
                                    {"text": decide("edit_again"), "cost": 0.001}]),
    "budget": ({"budget_usd": 0.05}, [{"text": PLAN, "cost": 0.03}, {"text": edit(), "cost": 0.03},
                                      {"text": decide("edit_again"), "cost": 0.01}]),
}
VOLATILE = {"t", "latency_s", "wall_time_s", "remaining_s", "agent_version"}


def scrub(x, root):
    if isinstance(x, dict):
        return {k: scrub(v, root) for k, v in x.items() if k not in VOLATILE}
    if isinstance(x, list):
        return [scrub(v, root) for v in x]
    if isinstance(x, str):
        return x.replace(root, "<ROOT>")
    return x


def run_all(extra=None):
    """Every scenario; `extra` adds settings to each one's Config (M3c: its switches, explicitly off)."""
    from conftest import ORIGINAL_RTL, FakeChecker, FakeClock
    from cvdp_agent.config import Config
    from cvdp_agent.graph import run
    from cvdp_agent.llm import FakeLLM
    from cvdp_agent.trace import Tracer

    out = {}
    for name, (kw, script) in SCENARIOS.items():
        with tempfile.TemporaryDirectory() as d:
            root = os.path.join(d, "code")
            for sub in ("docs", "rtl", "verif", "rundir"):
                os.makedirs(os.path.join(root, sub))
            json.dump({"prompt": "Fix the adder in rtl/adder.sv so y = a + b."}, open(os.path.join(root, "prompt.json"), "w"))
            open(os.path.join(root, "rtl", "adder.sv"), "w").write(ORIGINAL_RTL)
            open(os.path.join(root, "docs", "spec.md"), "w").write("# adder\ny = a + b\n")
            cfg = Config(root=root, provider="fake", **kw, **(extra or {}))
            clock = FakeClock()
            llm = FakeLLM(json.loads(json.dumps(script)), clock=clock)
            summary = run(cfg, llm=llm, checker=FakeChecker(root, clock=clock),
                          tools={"iverilog": True, "verilator": True, "yosys": True, "cocotb": True}, clock=clock,
                          tracer=Tracer(cfg.agent_out))
            trace = [json.loads(x) for x in open(os.path.join(cfg.agent_out, "trace.jsonl"))]
            out[name] = scrub({"requests": llm.requests, "trace": trace, "summary": summary}, root)
    return out


if __name__ == "__main__" and sys.argv[1:] == ["write"]:
    with open(GOLDEN, "w") as f:
        json.dump(run_all(), f, indent=1, sort_keys=True)

import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "agent"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from cvdp_agent.config import Config  # noqa: E402
from cvdp_agent.trace import Tracer  # noqa: E402

ORIGINAL_RTL = "module adder(input [3:0] a, b, output [4:0] y);\n  assign y = a;\nendmodule\n"


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def advance(self, s):
        self.t += s


class FakeChecker:
    """Compiles iff no file under rtl/ contains SYNTAX_ERROR. Records which checks were asked for."""

    def __init__(self, root, clock=None, check_cost_s=0.0):
        self.root = root
        self.calls = 0
        self.requests = []
        self.clock = clock
        self.check_cost_s = check_cost_s
        self.tb_dir = os.path.join(root, "rundir", "agent_tb")

    def run(self, names, tb=None):
        self.requests.append((list(names), tb))
        self.calls += 1
        if self.clock is not None:
            self.clock.advance(self.check_cost_s)
        bad = False
        for dirpath, _, fns in os.walk(os.path.join(self.root, "rtl")):
            for fn in fns:
                try:
                    if b"SYNTAX_ERROR" in open(os.path.join(dirpath, fn), "rb").read():
                        bad = True
                except OSError:  # a dangling symlink, like a compiler skipping a missing file
                    continue
        out = {"compile": {"ok": not bad, "summary": "fake compile"}}
        for n in names:
            if n != "compile":
                out[n] = {"ok": True, "summary": f"fake {n}"}
        return out


@pytest.fixture
def task_tree(tmp_path):
    root = tmp_path / "code"
    for d in ("docs", "rtl", "verif", "rundir"):
        (root / d).mkdir(parents=True)
    (root / "prompt.json").write_text(json.dumps({"prompt": "Fix the adder in rtl/adder.sv so y = a + b."}))
    (root / "rtl" / "adder.sv").write_text(ORIGINAL_RTL)
    (root / "docs" / "spec.md").write_text("# adder\ny = a + b\n")
    return root


@pytest.fixture
def make_cfg(task_tree):
    def _make(**kw):
        base = dict(root=str(task_tree), provider="fake", model="", max_turns=10, budget_usd=0.10, wall_s=480.0)
        base.update(kw)
        return Config(**base)
    return _make


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def run_agent(task_tree, clock):
    from cvdp_agent.graph import run
    from cvdp_agent.llm import FakeLLM

    def _run(cfg, script, checker=None, check_cost_s=0.0):
        llm = FakeLLM(script, clock=clock)
        checker = checker or FakeChecker(str(task_tree), clock=clock, check_cost_s=check_cost_s)
        summary = run(cfg, llm=llm, checker=checker, tools={"iverilog": True, "verilator": True, "yosys": True,
                                                            "cocotb": True}, clock=clock,
                      tracer=Tracer(cfg.agent_out))
        return summary, llm, checker
    return _run

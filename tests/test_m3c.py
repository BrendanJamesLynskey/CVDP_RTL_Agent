"""M3c: the interface check (elaboration against the given interface) and the mutation-score gate, each a fixed step
of the LangGraph graph behind a switch that is off by default. The gate's tests run real Icarus and Yosys (the Tests
workflow installs both); the interface check's run pyslang. No test needs an LLM."""
import csv
import io
import json
import os
import shutil
import subprocess
import sys

import pytest

import collect
import golden_langgraph
import taxonomy
from cvdp_agent import config as config_mod
from cvdp_agent import interface as iface_mod
from cvdp_agent.mutation import NO_TB, MutationGate
from cvdp_agent.trace import Tracer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = shutil.which("yosys") and shutil.which("iverilog") and shutil.which("vvp")
needs_tools = pytest.mark.skipif(not TOOLS, reason="needs yosys and iverilog (the Tests workflow installs both)")

SPEC = """# Counter

## Parameters
- **WIDTH**: counter width, default 4.

## Interface
| Signal | Direction | Width | Description |
|---|---|---|---|
| `clk` | input | 1 | clock |
| `rst` | input | 1 | synchronous reset, active high |
| `en` | input | 1 | count enable |
| `count` | output | [WIDTH-1:0] | the count |
| `wrap` | output | 1 | high while en is high and count is all ones |
"""
COUNTER = """module counter #(parameter WIDTH = 4) (
  input  logic clk,
  input  logic rst,
  input  logic en,
  output logic [WIDTH-1:0] count,
  output logic wrap
);
  always_ff @(posedge clk) begin
    if (rst) count <= '0;
    else if (en) count <= count + 1'b1;
  end
  assign wrap = en && (count == {WIDTH{1'b1}});
endmodule
"""
STRONG_TB = """module tb;
  logic clk = 0, rst = 1, en = 0;
  logic [3:0] count; logic wrap;
  integer i, errors = 0; logic [3:0] exp;
  counter dut(.clk(clk), .rst(rst), .en(en), .count(count), .wrap(wrap));
  always #5 clk = ~clk;
  initial begin
    @(negedge clk); @(negedge clk); rst = 0; exp = 0;
    if (count !== 0) begin $display("MISMATCH reset"); errors = errors + 1; end
    for (i = 0; i < 40; i = i + 1) begin
      en = (i % 3) != 0;
      #1;
      if (wrap !== (en && exp == 4'hf)) begin $display("MISMATCH wrap"); errors = errors + 1; end
      @(posedge clk); #1;
      if (en) exp = exp + 1;
      if (count !== exp) begin $display("MISMATCH count %0d exp %0d", count, exp); errors = errors + 1; end
      @(negedge clk);
    end
    if (errors == 0) $display("AGENT_TB_PASS"); else $display("TB FAILED");
    $finish;
  end
endmodule
"""
RESET_ONLY_TB = """module tb;
  logic clk = 0, rst = 1, en = 0;
  logic [3:0] count; logic wrap;
  counter dut(.clk(clk), .rst(rst), .en(en), .count(count), .wrap(wrap));
  always #5 clk = ~clk;
  initial begin
    @(negedge clk); @(negedge clk);
    if (count !== 0) $display("TB FAILED"); else $display("AGENT_TB_PASS");
    $finish;
  end
endmodule
"""


def tree(tmp_path, prompt="Design a `counter` module in SystemVerilog. See `docs/spec.md`.", spec=SPEC, rtl=None):
    root = tmp_path / "code"
    for d in ("docs", "rtl", "verif", "rundir/agent_tb"):
        (root / d).mkdir(parents=True, exist_ok=True)
    (root / "prompt.json").write_text(json.dumps({"prompt": prompt}))
    (root / "docs" / "spec.md").write_text(spec)
    for name, text in (rtl or {}).items():
        (root / "rtl" / name).write_text(text)
    return root


# ---------- defaults: the M2/M3b agent, byte-for-byte ----------

def test_langgraph_golden_unchanged_with_both_m3c_switches_explicitly_off():
    got = json.loads(json.dumps(golden_langgraph.run_all({"mutation_gate": False, "interface_check": False}),
                                sort_keys=True))
    assert got == json.load(open(golden_langgraph.GOLDEN))


def test_m3c_switches_default_off_and_are_absent_from_the_summary(monkeypatch):
    for k in ("CVDP_MUTATION_GATE", "CVDP_INTERFACE_CHECK"):
        monkeypatch.delenv(k, raising=False)
    cfg = config_mod.from_env()
    assert (cfg.mutation_gate, cfg.interface_check) == (False, False)
    assert not {"mutation_gate", "interface_check"} & set(cfg.switches())
    monkeypatch.setenv("CVDP_MUTATION_GATE", "0")  # what the sweep sends for arm A
    monkeypatch.setenv("CVDP_INTERFACE_CHECK", "0")
    assert config_mod.from_env().switches() == cfg.switches()
    monkeypatch.setenv("CVDP_MUTATION_GATE", "1")
    monkeypatch.setenv("CVDP_INTERFACE_CHECK", "true")
    on = config_mod.from_env()
    assert on.mutation_gate and on.interface_check and on.switches()["mutation_gate"] is True


def test_readme_has_the_m3c_graph():
    import re

    from cvdp_agent.graph import mermaid

    text = open(os.path.join(ROOT, "README.md")).read()
    m = re.search(r"<!-- graph-m3c:begin -->\s*```mermaid\n(.*?)```\s*<!-- graph-m3c:end -->", text, re.DOTALL)
    assert m, "README.md has no M3c graph block"
    assert m.group(1).strip() == mermaid(mutation_gate=True, interface_check=True).strip()


# ---------- the interface check ----------

def check_after(root, files):
    c = iface_mod.InterfaceCheck(str(root))  # the given interface is read before the design exists
    for name, text in files.items():
        (root / "rtl" / name).write_text(text)
    return c.check()


def kinds(res):
    return sorted((f["kind"], f["name"]) for f in res["findings"])


def test_interface_missing_port_is_reported(tmp_path):
    res = check_after(tree(tmp_path), {"counter.sv": COUNTER.replace("input  logic en,\n", "")
                                       .replace("else if (en)", "else").replace("en &&", "")})
    assert res["ok"] is False and ("missing_port", "en") in kinds(res)
    assert "missing_port: port `en`" in res["summary"]


def test_interface_matching_design_is_clean(tmp_path):
    res = check_after(tree(tmp_path), {"counter.sv": COUNTER})
    assert res["ok"] is True and res["findings"] == [] and res["engine"] == "pyslang"


def test_interface_case_only_difference_is_a_spelling_finding(tmp_path):
    res = check_after(tree(tmp_path), {"counter.sv": COUNTER.replace("clk", "CLK")})
    assert res["ok"] is False
    assert kinds(res) == [("spelling", "CLK")]
    assert "`CLK`" in res["summary"] and "`clk`" in res["summary"]


def test_interface_width_only_when_both_widths_are_constant(tmp_path):
    # count is [WIDTH-1:0] in the spec: a constant [7:0] in the design is not a width finding
    res = check_after(tree(tmp_path), {"counter.sv": COUNTER.replace("[WIDTH-1:0] count", "[7:0] count")})
    assert res["ok"] is True, res["summary"]
    # wrap is 1 bit in the spec: a constant 2 bits is
    wide = COUNTER.replace("output logic wrap", "output logic [1:0] wrap")
    res = check_after(tree(tmp_path / "b"), {"counter.sv": wide})
    assert kinds(res) == [("width", "wrap")]
    # and a non-constant width in the design is never compared
    param = COUNTER.replace("output logic wrap", "output logic [WIDTH-4:0] wrap")
    res = check_after(tree(tmp_path / "c"), {"counter.sv": param})
    assert res["ok"] is True, res["summary"]


def test_interface_given_by_the_original_rtl_for_a_modification_task(tmp_path):
    root = tree(tmp_path, prompt="Add a load input to the `counter` module in rtl/counter.sv.", spec="# notes\n",
                rtl={"counter.sv": COUNTER})
    res = check_after(root, {"counter.sv": COUNTER.replace("rst", "reset")})
    assert res["findings"] and ("missing_port", "rst") in kinds(res)
    assert "in the original RTL" in res["summary"]


def test_interface_falls_back_to_yosys_when_pyslang_cannot_elaborate(tmp_path, monkeypatch):
    if not shutil.which("yosys"):
        pytest.skip("needs yosys")
    root = tree(tmp_path)
    c = iface_mod.InterfaceCheck(str(root))
    (root / "rtl" / "counter.sv").write_text(COUNTER)
    monkeypatch.setattr(iface_mod, "_modules_pyslang", lambda texts: ({}, ["Forced"]))
    res = c.check()
    assert res["engine"] == "yosys" and res["ok"] is True, res["summary"]


class Audit:
    """Every file the process opens and every subprocess it starts, while on (sys.addaudithook cannot be removed,
    so the hook stays and only records when on)."""
    on, opened, spawned = False, [], []

    @classmethod
    def hook(cls, event, args):
        if not cls.on:
            return
        if event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
            cls.opened.append(os.fsdecode(args[0]))
        elif event == "subprocess.Popen":
            cls.spawned.append((args[1], args[3]))


sys.addaudithook(Audit.hook)


def test_interface_check_never_opens_a_path_outside_the_workspace(tmp_path, monkeypatch):
    """Not the hidden testbench, not a harness file, not a symlink out of the tree: every open and every Yosys
    argument is inside the task tree (pyslang gets text, never a path)."""
    root = tree(tmp_path)
    hidden = tmp_path / "harness" / "src"
    hidden.mkdir(parents=True)
    (hidden / "test_counter.py").write_text("dut.count")
    (hidden / ".env").write_text("TOPLEVEL=counter")
    os.symlink(hidden / "test_counter.py", root / "docs" / "linked.md")
    os.symlink(hidden / ".env", root / "rtl" / "inc.vh")
    (root / "rtl" / "counter.sv").write_text('`include "inc.vh"\n' + COUNTER)

    def inside(p):
        p = os.path.realpath(p if os.path.isabs(p) else os.path.join(str(root), p))
        return p == os.path.realpath(str(root)) or p.startswith(os.path.realpath(str(root)) + os.sep)

    Audit.opened, Audit.spawned, Audit.on = [], [], True
    try:
        c = iface_mod.InterfaceCheck(str(root.parent / "code"))
        (root / "rtl" / "counter.sv").write_text('`include "inc.vh"\n' + COUNTER.replace("rst", "reset"))
        res = c.check()
        if shutil.which("yosys"):  # the fallback too
            monkeypatch.setattr(iface_mod, "_modules_pyslang", lambda texts: ({}, ["Forced"]))
            c.check()
    finally:
        Audit.on = False
    assert res["findings"]
    data_opens = [p for p in Audit.opened if not p.endswith((".py", ".pyc", ".so")) and "site-packages" not in p
                  and "dist-packages" not in p and not p.startswith(("/usr", "/lib", "/proc", "/dev", "/etc"))]
    assert data_opens and all(inside(p) for p in data_opens), [p for p in data_opens if not inside(p)]
    assert not any("harness" in p for p in Audit.opened)
    for args, cwd in Audit.spawned:
        files = [a for a in (args or []) if isinstance(a, str) and a.endswith((".sv", ".v", ".vh", ".py", ".env"))]
        assert all(inside(os.path.join(cwd or str(root), f)) for f in files)
        script = " ".join(a for a in args if isinstance(a, str))
        assert "harness" not in script


# ---------- the mutation gate (real Icarus and Yosys) ----------

def gate(root, tb_text, rtl=COUNTER, **kw):
    (root / "rtl" / "counter.sv").write_text(rtl)
    (root / "rundir" / "agent_tb" / "tb.sv").write_text(tb_text)
    g = MutationGate(str(root), Tracer(None), {"yosys": True, "iverilog": True}, **kw)
    return g.run({"files": ["rundir/agent_tb/tb.sv"], "top": "tb"})


@needs_tools
def test_gate_strong_testbench_kills_half_and_passes(tmp_path):
    r = gate(tree(tmp_path), STRONG_TB)
    assert r["outcome"] == "pass" and r["passed"] and r["ok"] is True, r["summary"]
    assert r["generated"] == 12 and r["compiled"] == 12 and r["killed"] / r["compiled"] >= 0.5
    assert r["method"] == "wrapper" and r["unfinished"] == 0
    assert not os.path.exists(tmp_path / "code" / "rundir" / "agent_tb" / "mutation")  # cleaned up


@needs_tools
def test_gate_reset_only_testbench_fails_and_lists_survivors(tmp_path):
    r = gate(tree(tmp_path), RESET_ONLY_TB)
    assert r["outcome"] == "fail" and r["ok"] is False and r["killed"] / r["compiled"] < 0.5, r["summary"]
    assert r["survivors"] and all(s.startswith("mutant ") and "rtl/counter.sv:" in s for s in r["survivors"])
    assert "Not detected" in r["summary"] and "mutant " in r["summary"]
    assert "assign" not in r["summary"] and "always_ff" not in r["summary"]  # locations, never the code


@needs_tools
def test_gate_falls_back_to_one_build_per_mutant(tmp_path):
    # a testbench that reads an internal signal through the hierarchy: the wrapper hides it, the per-mutant
    # netlist (module counter itself) keeps it
    rtl = COUNTER.replace("count <= count + 1'b1", "count <= nxt").replace(
        "  always_ff", "  logic [WIDTH-1:0] nxt;\n  assign nxt = count + 1'b1;\n  always_ff")
    tb = STRONG_TB.replace('if (errors == 0)',
                           'if (dut.nxt !== count + 4\'d1) errors = errors + 1;\n    if (errors == 0)')
    r = gate(tree(tmp_path), tb, rtl=rtl)
    assert r["method"] == "per_mutant" and r["outcome"] in ("pass", "fail") and r["compiled"] > 0, r["summary"]


@needs_tools
@pytest.mark.parametrize("internal", [False, True])
def test_gate_handles_parameters_the_testbench_sets_through_its_own_parameters(tmp_path, internal):
    """CVDP testbenches pass their own parameters (`parameter W = 'd4;` ... `#(.WIDTH(W))`): resolved, applied
    with chparam, and declared on the wrapper and on each per-mutant netlist so the testbench compiles."""
    rtl = COUNTER.replace("count <= count + 1'b1", "count <= nxt").replace(
        "  always_ff", "  logic [WIDTH-1:0] nxt;\n  assign nxt = count + 1'b1;\n  always_ff")
    tb = STRONG_TB.replace("module tb;", "module tb;\n  parameter W = 'd8 / 2;").replace(
        "counter dut(", "counter #(.WIDTH(W)) dut(")
    if internal:
        tb = tb.replace('if (errors == 0)', 'if (dut.nxt !== count + 4\'d1) errors = errors + 1;\n    if (errors == 0)')
    r = gate(tree(tmp_path), tb, rtl=rtl)
    assert r["outcome"] == "pass" and r["method"] == ("per_mutant" if internal else "wrapper"), r["summary"]


def test_gate_without_a_testbench_fails_with_the_message(tmp_path):
    g = MutationGate(str(tree(tmp_path)), Tracer(None), {"yosys": True, "iverilog": True})
    r = g.run(None)
    assert (r["outcome"], r["ok"], r["passed"]) == ("no_tb", False, False)
    assert NO_TB in r["summary"]


@needs_tools
def test_gate_bound_counts_unfinished_mutants_as_not_killed(tmp_path, monkeypatch):
    """A deliberately slow testbench: every mutant's run takes at least 1 s more, so 12 cannot fit in a 4 s bound
    on any machine."""
    import time

    real = MutationGate._sim

    def slow(self, name, *a, **kw):
        if name.startswith("mutant"):
            time.sleep(1.0)
        return real(self, name, *a, **kw)

    monkeypatch.setattr(MutationGate, "_sim", slow)
    r = gate(tree(tmp_path), STRONG_TB, bound_s=4.0)
    assert r["wall_s"] < 4.0 + 2.0  # the bound holds (each tool call is cut at it)
    assert r["outcome"] == "timeout" and r["unfinished"] > 0, r["summary"]
    assert r["killed"] + r["unfinished"] <= r["compiled"]  # unfinished mutants are never counted as killed
    assert r["ok"] == (r["killed"] / r["compiled"] >= 0.5)
    assert "not finished" in r["note"] or "did not finish" in r["note"] or "ran out" in r["note"]
    assert any("time ran out" in s for s in r["survivors"])


# ---------- the graph with the fake provider ----------

PLAN = json.dumps({"files_to_change": ["rtl/counter.sv"], "approach": "counter", "check_plan": "testbench"})


def edit(rtl=COUNTER, tb=STRONG_TB, checks="compile,testbench"):
    tb_block = f'<tb path="agent_tb/tb.sv" top="tb">\n{tb}</tb>\n' if tb else ""
    return f'<file path="rtl/counter.sv">\n{rtl}</file>\n{tb_block}<checks>{checks}</checks>'


def decide(d):
    return json.dumps({"decision": d, "reason": "test"})


def run_real(cfg, script):
    """The real graph and the real checks (Icarus, Yosys), the fake provider."""
    from cvdp_agent.checks import detect_tools
    from cvdp_agent.graph import run
    from cvdp_agent.llm import FakeLLM

    llm = FakeLLM(script)
    return run(cfg, llm=llm, tools=detect_tools(sys.executable)), llm


def harness_row(root, cfg, tmp_path, passed=True):
    """Lay the agent's output out as the harness does and collect it."""
    work = tmp_path / "work"
    pdir = work / "cvdp_agentic_counter" / "harness" / "1" / "rundir"
    pdir.mkdir(parents=True)
    shutil.copytree(cfg.agent_out, pdir / "agent_out")
    rep = work / "cvdp_agentic_counter" / "reports"
    rep.mkdir(parents=True)
    (rep / "1.txt").write_text("" if passed else "FAILED test_counter.py::test_count - AssertionError\n"
                               "=== 1 failed in 0.1s ===\n")
    (work / "raw_result.json").write_text(json.dumps({"cvdp_agentic_counter_0001": {
        "category": "cid003", "difficulty": "easy",
        "tests": [{"result": 0 if passed else 1, "log": "/x/cvdp_agentic_counter/reports/1.txt"}]}}))
    return collect.rows(str(work))[0]


@needs_tools
@pytest.mark.parametrize("arm", ["A", "M", "I"])
def test_each_arm_end_to_end_on_the_fake_provider(arm, tmp_path):
    root = tree(tmp_path)
    cfg = config_mod.Config(root=str(root), provider="fake", mutation_gate=arm == "M", interface_check=arm == "I")
    s, llm = run_real(cfg, [PLAN, edit(), decide("submit")])
    assert s["stop_reason"] == "submit" and llm.calls == ["plan", "edit", "reflect"]
    row = harness_row(root, cfg, tmp_path)
    assert (row["mutation_gate"], row["interface_check"]) == (int(arm == "M"), int(arm == "I"))
    if arm == "A":
        assert not {k for k in s if k.startswith(("gate_", "mutants_", "interface_"))}
        assert all(row[k] == "" for k in collect.FIELDS[collect.FIELDS.index("gate_runs"):
                                                         collect.FIELDS.index("verify_submit")])  # M3d's after
    if arm == "M":
        assert (s["gate_runs"], s["gate_outcomes"], s["gate_failures"], s["gate_overridden"]) == (1, ["pass"], 0,
                                                                                                  False)
        assert s["mutants_generated"] == 12 and s["mutants_killed"] >= 6 and s["gate_wall_s"] > 0
        assert (row["gate_runs"], row["gate_outcomes"], row["mutants_generated"]) == (1, "pass", 12)
    if arm == "I":
        assert (s["interface_runs"], s["interface_mismatch_runs"], s["interface_mismatch_unresolved"]) == (1, 0,
                                                                                                           False)
        assert (row["interface_runs"], row["interface_unresolved"], row["interface_fallbacks"]) == (1, 0, 0)


def test_gate_fails_twice_then_the_agent_submits_anyway(make_cfg, run_agent):
    """No testbench: the gate fails, reflect sees it, the agent submits again, the gate fails again, and on the
    third submit the agent submits anyway with gate_overridden."""
    cfg = make_cfg(mutation_gate=True)
    s, llm, _ = run_agent(cfg, [PLAN.replace("counter", "adder"), golden_langgraph.edit(),
                                decide("submit"), decide("submit"), decide("submit")])
    assert s["stop_reason"] == "submit" and llm.calls == ["plan", "edit", "reflect", "reflect", "reflect"]
    assert (s["gate_runs"], s["gate_outcomes"], s["gate_failures"], s["gate_overridden"]) == (2, ["no_tb", "no_tb"],
                                                                                              2, True)
    # the second reflect saw the gate's message among the check results
    assert NO_TB in llm.requests[3]["messages"][-1]["content"]


def test_gate_failure_goes_back_to_reflect_and_can_lead_to_an_edit(make_cfg, run_agent):
    cfg = make_cfg(mutation_gate=True)
    s, llm, _ = run_agent(cfg, [PLAN, golden_langgraph.edit(), decide("submit"), decide("edit_again"),
                                golden_langgraph.edit(), decide("give_up")])
    assert llm.calls == ["plan", "edit", "reflect", "reflect", "edit", "reflect"]
    assert s["stop_reason"] == "give_up" and s["gate_failures"] == 1 and not s["gate_overridden"]
    assert "mutation_gate: FAIL" in llm.requests[4]["messages"][-1]["content"]  # the next edit's feedback


@needs_tools
def test_interface_mismatch_blocks_one_submit_then_lets_it_through(tmp_path):
    root = tree(tmp_path)
    cfg = config_mod.Config(root=str(root), provider="fake", interface_check=True)
    bad = COUNTER.replace("rst", "reset")
    s, llm = run_real(cfg, [PLAN, edit(bad), decide("submit"), edit(bad), decide("submit")])
    assert llm.calls == ["plan", "edit", "reflect", "edit", "reflect"] and s["stop_reason"] == "submit"
    assert (s["interface_runs"], s["interface_mismatch_runs"], s["interface_blocks"]) == (2, 2, 1)
    assert s["interface_kinds"] == {"missing_port": 2} and s["interface_mismatch_unresolved"] is True
    assert "## interface: FAIL" in llm.requests[2]["messages"][-1]["content"]  # reflect sees it like lint
    row = harness_row(root, cfg, tmp_path, passed=False)
    assert row["interface_unresolved"] == 1 and row["interface_blocks"] == 1
    assert "interface_mismatch_unresolved" in row["failure_flags"].split("+")


def test_taxonomy_flags_for_m3c_and_none_on_an_old_row():
    base = {"pass": "0", "stop_reason": "submit", "log_class": "tests_failed", "own_compile_last": "pass",
            "selfcheck_runs": "0", "selfcheck_last": "none", "rtl_changed": "1", "turns": "3"}
    label, flags = taxonomy.label({**base, "gate_overridden": "1", "gate_outcomes": "no_tb+no_tb",
                                   "interface_unresolved": "1"})
    assert label == "tests_failed_no_selfcheck"
    assert {"gate_overridden", "gate_no_tb", "interface_mismatch_unresolved"} <= set(flags)
    assert taxonomy.label(base) == ("tests_failed_no_selfcheck", [])


def test_results_tools_read_old_and_new_csvs(tmp_path):
    """table.py, ablate.py and taxonomy.py on an M3b CSV (no M3c columns) and on one with them."""
    import ablate
    import table

    old = os.path.join(ROOT, "docs", "reports", "m3b", "runs", "A1_40126423704.csv")
    rows = list(csv.DictReader(open(old)))
    new = tmp_path / "new.csv"
    with open(new, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=collect.FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({**{k: r.get(k, "") for k in collect.FIELDS}, "mutation_gate": 1, "gate_runs": 1,
                        "gate_outcomes": "fail", "gate_overridden": 0})
    for p in (old, str(new)):
        buf = io.StringIO()
        sys_stdout, sys.stdout = sys.stdout, buf
        try:
            table.main([p])
            ablate.main(["--arm", f"A={old}", "--arm", f"M={p}", "--base", "A"])
            taxonomy.main(["--arm", f"X={p}"])
        finally:
            sys.stdout = sys_stdout
        assert "Primary label by arm" in buf.getvalue()
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "table.py"), old, str(new)], capture_output=True,
                       text=True)
    assert r.returncode == 0 and "pass@1" in r.stdout.lower()


# ---------- the sweep's new inputs ----------

def sweep(tmp_path, **env_extra):
    from test_m2a import FAKE_HARNESS

    cvdp = tmp_path / "cvdp"
    cvdp.mkdir()
    (cvdp / "run_benchmark.py").write_text(FAKE_HARNESS)
    (cvdp / "run_benchmark.py").chmod(0o755)
    data = tmp_path / "data"
    data.mkdir()
    (data / "agentic_code_generation_no_commercial.jsonl").write_text(
        json.dumps({"id": "cvdp_agentic_lfsr_0001", "categories": ["cid016", "easy"]}) + "\n")
    env = dict(os.environ, MODEL="fake", THREADS="1", WORK=str(tmp_path / "work"), CVDP_DIR=str(cvdp),
               DATA_DIR=str(data), AGENT_IMAGE="unused", FAKE_SCRIPT=json.dumps([{"text": "done"}]),
               AGENT_PYTHONPATH=os.path.join(ROOT, "agent"), SEEN_ENV=str(tmp_path / "seen.jsonl"),
               OPENROUTER_API_KEY="", **env_extra)
    return subprocess.run(["bash", os.path.join(ROOT, "tools", "sweep.sh")], env=env, capture_output=True, text=True,
                          timeout=300, cwd=ROOT)


def test_sweep_passes_the_m3c_switches_off_by_default_and_on_when_asked(tmp_path):
    for name, extra, want in (("off", {}, "0"), ("on", {"MUTATION_GATE": "1", "INTERFACE_CHECK": "1"}, "1")):
        d = tmp_path / name
        d.mkdir()
        r = sweep(d, **extra)
        assert r.returncode == 0, r.stdout + r.stderr
        seen = json.loads(open(d / "seen.jsonl").readline())
        assert (seen["CVDP_MUTATION_GATE"], seen["CVDP_INTERFACE_CHECK"]) == (want, want)
        run = json.load(open(str(d / "work") + ".run.json"))
        assert ("mutation_gate" in run) == (want == "1")
        rows = list(csv.DictReader(open(d / "work" / "results.csv")))
        assert rows[0]["mutation_gate"] == want and rows[0]["interface_check"] == want


def test_sweep_refuses_m3c_switches_on_deep_agents_and_bad_values(tmp_path):
    for extra in ({"HARNESS": "deepagents", "MUTATION_GATE": "1"}, {"INTERFACE_CHECK": "yes"}):
        env = dict(os.environ, WORK=str(tmp_path / "w"), AGENT_IMAGE="x", **extra)
        r = subprocess.run(["bash", os.path.join(ROOT, "tools", "sweep.sh")], env=env, capture_output=True,
                           text=True)
        assert r.returncode == 2 and ("INTERFACE_CHECK" in r.stderr or "MUTATION_GATE" in r.stderr), r.stderr


def test_interface_given_tool_counts_the_hidden_top(tmp_path):
    import interface_given

    rec = {"id": "cvdp_agentic_counter_0001", "categories": ["cid003", "easy"],
           "prompt": "Design a `counter` module.", "context": {"docs/spec.md": SPEC},
           "harness": {"src/.env": "TOPLEVEL=counter\n",
                       "src/test_counter.py": "async def t(dut):\n    dut.rst.value = 1\n    x = dut.count.value\n"}}
    rows = interface_given.rows([rec])
    assert rows[0]["given"] and rows[0]["source"] == "doc" and (rows[0]["covered"], rows[0]["dut"]) == (2, 2)
    assert "**1 of 1**" in interface_given.report(rows)


def test_interface_module_named_only_in_a_document_is_never_required(tmp_path):
    spec = SPEC + "\n## Related\nA wider system may also use a `slicer_top` module (see `rtl/slicer_top.sv`).\n"
    res = check_after(tree(tmp_path, spec=spec), {"counter.sv": COUNTER})
    assert res["ok"] is True, res["summary"]
    # but a module the prompt itself asks for is
    res = check_after(tree(tmp_path / "b", prompt="Design a `counter` module and a `limiter` module."),
                      {"counter.sv": COUNTER})
    assert ("missing_module", "limiter") in kinds(res)

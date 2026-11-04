"""M3k: arm K (a pre-submit interface/file/compile check) and arm T (a timing-claims first turn) on the plain API
loop, and the guard's repricing. Fake client only; no model, no network."""
import json
import os
import subprocess

import collect
import pytest
from cvdp_agent import apiloop, presubmit
from cvdp_agent.config import Config, from_env
from test_m3h import sweep
from test_m3j import KEY, FakeClient, api_cfg, block, reply

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden_apiloop.json")


@pytest.fixture(autouse=True)
def _key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)


def text(t):
    return reply([block(type="text", text=t)], stop="end_turn")


def write(path, content, i=1):
    return reply([block(type="tool_use", id=f"w{i}", name="Write", input={"path": path, "content": content})])


# ---------- R is unchanged ----------

def test_r_request_path_is_byte_identical_to_the_m3j_golden(tmp_path):
    cfg = api_cfg(tmp_path)
    think = block(type="thinking", thinking="", signature="sig1")
    c = FakeClient([reply([think, block(type="tool_use", id="t1", name="Write",
                                        input={"path": "rtl/top.sv", "content": "module top; endmodule\n"})]),
                    reply([block(type="tool_use", id="t2", name="Bash", input={"command": "echo hi"})], cread=900),
                    reply([block(type="text", text="done")], stop="end_turn", cread=900)])
    s = apiloop.run(cfg, client=c)
    for r in c.requests:
        r.pop("timeout")
    golden = json.load(open(GOLDEN))  # recorded from main at 5f569e9, before any M3k change
    assert json.dumps(c.requests, sort_keys=True, indent=1) == json.dumps(golden, sort_keys=True, indent=1)
    for k in ("presubmit_findings_n", "presubmit_rounds", "timing_claims_n"):
        assert k not in s
    assert "presubmit_iface" not in s["switches"] and "timing_claims" not in s["switches"]
    assert not os.path.exists(os.path.join(cfg.agent_out, "presubmit.jsonl"))


# ---------- the guard's pricing ----------

def test_call_cost_prices_cached_input_apart_and_by_tier():
    assert apiloop.call_cost(100_000, 0, 0, 0) == pytest.approx(0.010)  # at the threshold: the short tier
    assert apiloop.call_cost(0, 100_000, 0, 0) == pytest.approx(0.001)
    assert apiloop.call_cost(0, 0, 100_000, 0) == pytest.approx(0.0125)
    assert apiloop.call_cost(0, 0, 0, 1_000_000) == pytest.approx(0.50)
    assert apiloop.call_cost(100_001, 0, 0, 0) == pytest.approx(0.0500005)  # one token over: the long tier
    # over 100,000 prompt tokens (cache reads count) the whole request is at the long-context tier
    assert apiloop.call_cost(1_000, 100_000, 0, 1_000) == pytest.approx((1_000 * .5 + 100_000 * .05 + 1_000 * 2.5) / 1e6)
    # a typical held-out run (46,570 prompt tokens, 6,190 out, mostly cache reads) is cents, not the old $0.06
    assert apiloop.call_cost(2_000, 40_000, 4_500, 6_190) < 0.01
    assert apiloop.call_cost(0, 50_000, 0, 0) < 50_000 * 0.50 / 1e6 / 40  # old: every token at $0.50 per million


def test_guard_charge_is_the_repriced_estimate(tmp_path):
    cfg = api_cfg(tmp_path)
    s = apiloop.run(cfg, client=FakeClient([reply([block(type="text", text="done")], stop="end_turn", cread=40_000)]))
    assert s["guard_estimate_usd"] == s["api_cost_estimate_usd"] == round(apiloop.call_cost(1000, 40_000, 0, 100), 6)
    assert s["guard_estimate_usd"] < 0.001


# ---------- K: the check on fixture designs ----------

DOC = """# Spec
## Interface
| Signal | Direction | Width | Description |
|---|---|---|---|
| clk | input | 1 | clock |
| din | input | 8 | data |
| dout | output | 8 | result |
"""
TASK = "Write module `filt` in rtl/filt.sv. See docs/spec.md."
GOOD = "module filt(input logic clk, input logic [7:0] din, output logic [7:0] dout);\n" \
       "  always_ff @(posedge clk) dout <= din;\nendmodule\n"


def tree(tmp_path, rtl=None, files=None, prompt=TASK):
    root = tmp_path / "code"
    (root / "rtl").mkdir(parents=True, exist_ok=True)
    (root / "docs").mkdir(exist_ok=True)
    (root / "prompt.json").write_text(json.dumps({"prompt": prompt}))
    (root / "docs" / "spec.md").write_text(DOC)
    pc = presubmit.PresubmitCheck(str(root))  # the given interface is read before the design exists
    for name, body in (files or {"rtl/filt.sv": rtl if rtl is not None else GOOD}).items():
        (root / name).write_text(body)
    return pc


def kinds(pc):
    return sorted({f["kind"] for f in pc.check()["findings"]})


def test_k_clean_design_does_not_fire(tmp_path):
    assert tree(tmp_path).check()["findings"] == []


def test_k_port_name_direction_width_and_param(tmp_path):
    assert kinds(tree(tmp_path / "a", GOOD.replace("dout", "q"))) == ["missing_port"]
    assert "direction" in kinds(tree(tmp_path / "b", GOOD.replace("output logic [7:0] dout", "input logic [7:0] dout")))
    bad_w = GOOD.replace("[7:0] din", "[3:0] din")
    f = tree(tmp_path / "c", bad_w.replace("dout <= din", "dout <= {4'b0, din}")).check()["findings"]
    # a width read from the docs' prose/table is not trusted (precise()); the original RTL's or a header's is
    assert all(x["kind"] != "width" for x in f)
    hdr = "module filt(input logic clk, input logic [7:0] din, output logic [7:0] dout);"
    pc = tree(tmp_path / "d", prompt=TASK + "\n\n```\n" + hdr + "\n```\n",
              rtl=GOOD.replace("[7:0] din", "[3:0] din").replace("dout <= din", "dout <= {4'b0, din}"))
    assert "width" in kinds(pc)


def test_k_file_extension_and_missing_file(tmp_path):
    pc = tree(tmp_path / "a", files={"rtl/filt.v": GOOD})
    fs = pc.check()["findings"]
    assert [f["kind"] for f in fs if f["kind"].startswith("file")] == ["file_extension"]
    assert "rtl/filt.v" in fs[0]["detail"] or any("rtl/filt.v" in f["detail"] for f in fs)
    pc = tree(tmp_path / "b", files={"rtl/other.sv": GOOD.replace("filt", "other")})
    assert "missing_file" in kinds(pc)


def test_k_compile_error(tmp_path):
    # a syntax error: pyslang and Yosys both refuse it
    assert "compile_error" in kinds(tree(tmp_path, GOOD.replace("<= din;", "<= ;")))


def test_k_declared_module_is_never_missing(tmp_path):
    """Yosys' `hierarchy -top` prunes unused modules, so absence from the elaborated design is not absence from
    rtl/: a module declared in any rtl/ file is not reported missing (smoke run, dev gcd_0007)."""
    orig = "module helper(input logic a, output logic y);\n assign y = a;\nendmodule\n"
    root = tmp_path / "code"
    (root / "rtl").mkdir(parents=True)
    (root / "rtl" / "helper.sv").write_text(orig)
    (root / "prompt.json").write_text(json.dumps({"prompt": "Add a top."}))
    pc = presubmit.PresubmitCheck(str(root))
    (root / "rtl" / "top.sv").write_text("module top(input logic a, output logic y);\n assign y = a;\nendmodule\n")
    fake = {"findings": [{"kind": "missing_module", "module": "helper", "name": "helper", "detail": "x"},
                         {"kind": "missing_module", "module": "ghost", "name": "ghost", "detail": "y"}]}
    given = {"helper": {"source": "rtl", "ports": {}, "params": {}}, "ghost": {"source": "rtl", "ports": {},
                                                                              "params": {}}}
    kept = presubmit.precise(given, fake["findings"], presubmit.declared_modules(str(root)))
    assert [f["name"] for f in kept] == ["ghost"]
    assert pc.check()["findings"] == [] or all(f["name"] != "helper" for f in pc.check()["findings"])


def test_k_message_template_is_fixed():
    m = presubmit.message([{"detail": "port `q` is wrong"}])
    assert m.startswith("Before you finish: an automatic check of your files under rtl/ against the task, the docs "
                        "and the files you were given found 1 problem:\n- port `q` is wrong\n")
    assert "say so in one line and stop." in m and "problems" in presubmit.message([{"detail": "a"}, {"detail": "b"}])


# ---------- K in the loop ----------

def k_cfg(tmp_path, **kw):
    cfg = api_cfg(tmp_path, presubmit_iface=True, **kw)
    root = tmp_path / "code"
    (root / "docs").mkdir(exist_ok=True)
    (root / "prompt.json").write_text(json.dumps({"prompt": TASK}))
    (root / "docs" / "spec.md").write_text(DOC)
    return cfg


def test_k_sends_findings_once_then_ends_clean(tmp_path):
    cfg = k_cfg(tmp_path)
    c = FakeClient([write("rtl/filt.sv", GOOD.replace("dout", "q")), text("done"),
                    write("rtl/filt.sv", GOOD, 2), text("fixed")])
    s = apiloop.run(cfg, client=c)
    assert s["stop_reason"] == "submit" and s["llm_calls"] == 4
    assert s["presubmit_findings_n"] >= 1 and s["presubmit_rounds"] == 1 and s["presubmit_final_findings_n"] == 0
    back = c.requests[2]["messages"][-1]
    assert back["role"] == "user" and back["content"].startswith("Before you finish:") and "`dout`" in back["content"]
    log = [json.loads(ln) for ln in open(os.path.join(cfg.agent_out, "api_tools.jsonl"))]
    assert [r["tool"] for r in log if r["tool"] == "presubmit"] == ["presubmit", "presubmit"]
    assert s["switches"]["presubmit_iface"] is True


def test_k_round_trips_are_capped_at_two(tmp_path):
    cfg = k_cfg(tmp_path)
    bad = GOOD.replace("dout", "q")
    c = FakeClient([write("rtl/filt.sv", bad), text("a"), text("b"), text("c")])
    s = apiloop.run(cfg, client=c)
    assert s["presubmit_rounds"] == 2 and s["llm_calls"] == 4 and s["stop_reason"] == "submit"
    assert s["presubmit_final_findings_n"] >= 1


def test_k_clean_run_ends_exactly_as_r_would(tmp_path):
    cfg = k_cfg(tmp_path)
    s = apiloop.run(cfg, client=FakeClient([write("rtl/filt.sv", GOOD), text("done")]))
    assert s["llm_calls"] == 2 and s["presubmit_rounds"] == 0 and s["presubmit_findings_n"] == 0


def test_k_does_not_check_a_give_up(tmp_path):
    cfg = k_cfg(tmp_path)
    s = apiloop.run(cfg, client=FakeClient([text("GIVE_UP: cannot")]))
    assert s["stop_reason"] == "give_up" and s["presubmit_rounds"] == 0


# ---------- T ----------

def test_t_first_turn_text_and_it_stays_in_the_conversation(tmp_path):
    cfg = api_cfg(tmp_path, timing_claims=True)
    c = FakeClient([text("- latency: \"two cycles\"\n- reset: not stated\n"), write("rtl/top.sv", "module top; endmodule\n"),
                    text("done")])
    s = apiloop.run(cfg, client=c)
    first = c.requests[0]
    assert first["tool_choice"] == {"type": "none"} and first["tools"] == c.requests[1]["tools"]
    user0 = first["messages"][0]["content"]
    assert user0.startswith("You are solving one hardware-design task.") and user0.endswith(apiloop.TIMING_INSTRUCTION)
    assert "tool_choice" not in c.requests[1]
    m = c.requests[1]["messages"]
    assert m[0]["content"] == user0 and m[1]["role"] == "assistant" and m[1]["content"][0]["text"].startswith("- latency")
    assert m[2] == {"role": "user", "content": apiloop.TIMING_GO}
    assert s["timing_claims_n"] == 2 and s["llm_calls"] == 3 and s["stop_reason"] == "submit"
    assert s["switches"]["timing_claims"] is True


def test_t_error_on_the_first_call_is_a_stop_not_a_crash(tmp_path):
    class RateLimitError(Exception):
        pass
    s = apiloop.run(api_cfg(tmp_path, timing_claims=True), client=FakeClient([RateLimitError("429")]))
    assert s["stop_reason"] == "rate_limited" and s["llm_calls"] == 0


# ---------- config, sweep, workflow, columns ----------

def test_config_validation_per_harness(monkeypatch):
    with pytest.raises(ValueError, match="apiloop"):
        Config(harness="langgraph", presubmit_iface=True)
    with pytest.raises(ValueError, match="apiloop"):
        Config(harness="claudecode", provider="claude_plan", timing_claims=True)
    with pytest.raises(ValueError, match="separate"):
        Config(harness="apiloop", provider="anthropic", presubmit_iface=True, timing_claims=True)
    monkeypatch.setenv("CVDP_HARNESS", "apiloop")
    monkeypatch.setenv("CVDP_PROVIDER", "anthropic")
    monkeypatch.setenv("CVDP_PRESUBMIT_IFACE", "1")
    assert from_env().presubmit_iface is True


def test_sweep_fixed_checks_per_harness(tmp_path):
    for name, extra, want in (("off", {}, ("0", "0")), ("k", {"PRESUBMIT_IFACE": "1"}, ("1", "0")),
                              ("t", {"TIMING_CLAIMS": "1"}, ("0", "1"))):
        (tmp_path / name).mkdir()
        r, seen = sweep(tmp_path / name, HARNESS="apiloop", ANTHROPIC_API_KEY=KEY, **extra)
        assert r.returncode == 0, r.stdout + r.stderr
        if name == "off":
            assert "CVDP_PRESUBMIT_IFACE" not in seen["env"] and "CVDP_TIMING_CLAIMS" not in seen["env"]
            assert "presubmit_iface" not in json.load(open(str(tmp_path / name / "work") + ".run.json"))
        else:
            assert seen["env"].endswith("CVDP_PRESUBMIT_IFACE,CVDP_TIMING_CLAIMS")
            assert json.load(open(str(tmp_path / name / "work") + ".run.json"))["presubmit_iface"] == (name == "k")
    for i, extra in enumerate(({"HARNESS": "langgraph", "PRESUBMIT_IFACE": "1"},
                               {"HARNESS": "claudecode", "TIMING_CLAIMS": "1"},
                               {"HARNESS": "apiloop", "PRESUBMIT_IFACE": "1", "TIMING_CLAIMS": "1"},
                               {"HARNESS": "apiloop", "INTERFACE_CHECK": "1"},
                               {"HARNESS": "apiloop", "VERIFY_SUBMIT": "1"},
                               {"HARNESS": "apiloop", "PRESUBMIT_IFACE": "yes"})):
        (tmp_path / f"bad{i}").mkdir()
        r, _ = sweep(tmp_path / f"bad{i}", ANTHROPIC_API_KEY=KEY, **extra)
        assert r.returncode == 2, extra


def test_workflow_fixed_checks_and_input_count():
    import yaml
    wf = yaml.safe_load(open(os.path.join(ROOT, ".github", "workflows", "sweep.yml")))
    on = wf.get("on") or wf.get(True)
    inp = on["workflow_dispatch"]["inputs"]
    assert len(inp) <= 25 and len(inp) == 24
    assert {"presubmit_iface", "timing_claims", "interface_check", "none"} <= set(inp["fixed_checks"]["options"])
    assert "'presubmit_iface'" in wf["env"]["PRESUBMIT_IFACE"] and "'timing_claims'" in wf["env"]["TIMING_CLAIMS"]
    for k in ("MUTATION_GATE", "INTERFACE_CHECK", "VERIFY_SUBMIT", "SPEC_VECTORS"):  # no substring overlap
        for v in ("presubmit_iface", "timing_claims"):
            assert k.lower() not in v


def test_collect_m3k_columns_only_with_the_flag():
    assert "presubmit_rounds" not in collect.FIELDS and "presubmit_rounds" not in collect.M3J_FIELDS
    cols = collect.m3k_columns({"presubmit_findings_n": 2, "presubmit_rounds": 1, "presubmit_final_findings_n": 0})
    assert cols == {"presubmit_findings_n": 2, "presubmit_rounds": 1, "presubmit_final_findings_n": 0,
                    "timing_claims_n": ""}

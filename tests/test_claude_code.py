"""The claudecode comparison harness, with a fake `claude` on PATH: the summary it writes (no billed cost, the plan's
estimate kept apart), its stop reasons, the network audit and token redaction. No test needs an LLM or a plan."""
import json
import os
import stat

from cvdp_agent import claude_code
from cvdp_agent.config import from_env

TOKEN = "sk-ant-oat01-" + "x" * 40

FAKE = """#!/usr/bin/env python3
import json, os, sys
open(os.path.join("rtl", "top.sv"), "w").write("module top; endmodule\\n")
ev = [
  {"type": "assistant", "message": {"model": "claude-opus-5-5", "content": [
    {"type": "tool_use", "name": "Bash", "input": {"command": "iverilog -g2012 rtl/top.sv"}},
    {"type": "tool_use", "name": "Bash", "input": {"command": "curl -s https://huggingface.co/x"}},
    {"type": "tool_use", "name": "Write", "input": {"file_path": "rtl/top.sv"}}]}},
  {"type": "assistant", "message": {"model": "claude-opus-5-5", "content": [
    {"type": "text", "text": "token " + os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "")}]}},
  {"type": "result", "subtype": os.environ.get("FAKE_SUBTYPE", "success"), "result": "done", "num_turns": 3,
   "total_cost_usd": 0.42, "usage": {"input_tokens": 10, "cache_read_input_tokens": 900,
   "cache_creation_input_tokens": 90, "output_tokens": 50}},
]
for e in ev:
    print(json.dumps(e))
"""


def setup(tmp_path, monkeypatch, subtype="success"):
    root = tmp_path / "code"
    (root / "rtl").mkdir(parents=True)
    (root / "docs").mkdir()
    (root / "prompt.json").write_text(json.dumps({"prompt": "Write module top."}))
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "claude"
    fake.write_text(FAKE)
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", TOKEN)
    monkeypatch.setenv("FAKE_SUBTYPE", subtype)
    monkeypatch.setenv("CVDP_HARNESS", "claudecode")
    monkeypatch.setenv("CVDP_PROVIDER", "claude_plan")
    monkeypatch.setenv("CVDP_MODEL", "claude-opus-5-5")
    monkeypatch.setenv("CVDP_ROOT", str(root))
    monkeypatch.setenv("CVDP_OUT_DIR", str(tmp_path / "out"))
    return root, from_env()


def test_summary_has_no_billed_cost_and_keeps_the_estimate_apart(tmp_path, monkeypatch):
    root, cfg = setup(tmp_path, monkeypatch)
    assert cfg.max_rounds == 60
    s = claude_code.run(cfg)
    assert s["provider"] == "claude_plan" and s["harness"] == "claudecode"
    assert s["cost_usd"] is None and s["cost_unreported_calls"] == 0
    assert s["plan_cost_estimate_usd"] == 0.42
    assert s["prompt_tokens"] == 1000 and s["completion_tokens"] == 50 and s["cache_read_tokens"] == 900
    assert s["turns"] == 3 and s["tool_calls"] == 3 and s["stop_reason"] == "submit"
    assert s["model"] == "claude-opus-5-5"
    assert s["visible_top_level"] == ["docs", "prompt.json", "rtl"]
    assert (root / "rtl" / "top.sv").exists()  # the harness scores what is on disk


def test_network_commands_are_flagged(tmp_path, monkeypatch):
    _, cfg = setup(tmp_path, monkeypatch)
    s = claude_code.run(cfg)
    assert s["network_flags"] == ["curl -s https://huggingface.co/x"]


def test_token_never_reaches_the_outputs(tmp_path, monkeypatch):
    _, cfg = setup(tmp_path, monkeypatch)
    claude_code.run(cfg)
    for name in os.listdir(cfg.agent_out):
        text = open(os.path.join(cfg.agent_out, name)).read()
        assert TOKEN not in text and "sk-ant-" not in text


def test_stop_reasons(tmp_path, monkeypatch):
    _, cfg = setup(tmp_path, monkeypatch, subtype="error_max_turns")
    assert claude_code.run(cfg)["stop_reason"] == "max_turns"
    assert claude_code.stop_reason(None, timed_out=True) == "wall_time"
    assert claude_code.stop_reason({"subtype": "success", "result": "GIVE_UP"}, False) == "give_up"


def test_no_token_records_an_error(tmp_path, monkeypatch):
    _, cfg = setup(tmp_path, monkeypatch)
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN")
    s = claude_code.run(cfg)
    assert s["stop_reason"] == "error" and "not set" in s["error"]


def test_api_error_is_an_llm_error_not_a_submit():
    r = {"subtype": "success", "is_error": True, "terminal_reason": "api_error", "result": "Failed to authenticate."}
    assert claude_code.stop_reason(r, False) == "llm_error"

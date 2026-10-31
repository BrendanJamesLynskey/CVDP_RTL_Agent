"""F1B: the two options added for the cheap-model screen, both off by default.

- `CVDP_DATA_COLLECTION=deny`: our OpenRouter client asks for `provider: {data_collection: "deny"}`; blank, the request
  body is exactly as before (no `provider` field unless the order is pinned).
- `CVDP_PROVIDER=claude_openrouter` (sweep `claude_endpoint=openrouter`): Claude Code pointed at OpenRouter's
  Anthropic-compatible endpoint, the plan's token never passed, cost provider-reported per message id.
No test needs a network, an LLM or a plan."""
import json
import os
import stat
import subprocess

import pytest

from cvdp_agent import claude_code
from cvdp_agent import config as config_mod
from cvdp_agent.config import from_env
from cvdp_agent.llm import OpenRouterLLM

KEY = "sk-or-v1-" + "k" * 40
TOKEN = "sk-ant-oat01-" + "x" * 40
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_request_body_unchanged_when_off():
    llm = OpenRouterLLM.__new__(OpenRouterLLM)
    llm.provider_order, llm.data_collection = [], ""
    assert "provider" not in llm.request_body("default")
    llm.provider_order = ["A"]
    assert llm.request_body("default")["provider"] == {"order": ["A"], "allow_fallbacks": False}


def test_request_body_denies_data_collection():
    llm = OpenRouterLLM.__new__(OpenRouterLLM)
    llm.provider_order, llm.data_collection = [], "deny"
    assert llm.request_body("off")["provider"] == {"data_collection": "deny"}
    llm.provider_order = ["A"]
    assert llm.request_body("off")["provider"] == {"order": ["A"], "allow_fallbacks": False, "data_collection": "deny"}


def test_data_collection_from_env_and_switches(monkeypatch):
    monkeypatch.delenv("CVDP_DATA_COLLECTION", raising=False)
    cfg = from_env()
    assert cfg.data_collection == "" and "data_collection" not in cfg.switches()
    monkeypatch.setenv("CVDP_DATA_COLLECTION", "deny")
    cfg = from_env()
    assert cfg.data_collection == "deny" and cfg.switches()["data_collection"] == "deny"
    monkeypatch.setenv("CVDP_DATA_COLLECTION", "allow")
    with pytest.raises(ValueError):
        config_mod.from_env()


FAKE = """#!/usr/bin/env python3
import json, os
seen = {k: os.environ.get(k) for k in ("ANTHROPIC_BASE_URL", "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL",
        "ANTHROPIC_SMALL_FAST_MODEL", "CLAUDE_CODE_SUBAGENT_MODEL")}
seen["has_auth"] = bool(os.environ.get("ANTHROPIC_AUTH_TOKEN"))
seen["has_oauth"] = "CLAUDE_CODE_OAUTH_TOKEN" in os.environ
open(os.environ["FAKE_SEEN"], "w").write(json.dumps(seen))
for e in [
  {"type": "assistant", "message": {"id": "gen-1", "model": "z-ai/glm", "content": [
    {"type": "tool_use", "name": "Bash", "input": {"command": "iverilog rtl/top.sv"}}]}},
  {"type": "assistant", "message": {"id": "gen-1", "model": "z-ai/glm", "content": [{"type": "text", "text": "x"}]}},
  {"type": "assistant", "message": {"id": "gen-2", "model": "z-ai/glm", "content": [{"type": "text", "text": "done"}]}},
  {"type": "result", "subtype": "success", "result": "done", "num_turns": 2, "total_cost_usd": 0.9,
   "usage": {"input_tokens": 10, "output_tokens": 5}},
]:
    print(json.dumps(e))
"""


def setup(tmp_path, monkeypatch):
    root = tmp_path / "code"
    (root / "rtl").mkdir(parents=True)
    (root / "prompt.json").write_text(json.dumps({"prompt": "Write module top."}))
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "claude"
    fake.write_text(FAKE)
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_SEEN", str(tmp_path / "seen.json"))
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", TOKEN)  # set in the env, and still never passed in this mode
    monkeypatch.setenv("CVDP_HARNESS", "claudecode")
    monkeypatch.setenv("CVDP_PROVIDER", "claude_openrouter")
    monkeypatch.setenv("CVDP_MODEL", "z-ai/glm-5.3-flash")
    monkeypatch.setenv("CVDP_ROOT", str(root))
    monkeypatch.setenv("CVDP_OUT_DIR", str(tmp_path / "out"))
    return from_env()


def test_openrouter_endpoint_env_and_key_usage(tmp_path, monkeypatch):
    cfg = setup(tmp_path, monkeypatch)
    seen_keys, usage = [], iter([10.0, 10.25])

    def fake_usage(key):
        seen_keys.append(key)
        return next(usage)
    monkeypatch.setattr(claude_code, "key_usage", fake_usage)
    s = claude_code.run(cfg)
    seen = json.load(open(tmp_path / "seen.json"))
    assert seen == {"ANTHROPIC_BASE_URL": "https://openrouter.ai/api", "ANTHROPIC_API_KEY": "",
                    "ANTHROPIC_MODEL": "z-ai/glm-5.3-flash", "ANTHROPIC_SMALL_FAST_MODEL": "z-ai/glm-5.3-flash",
                    "CLAUDE_CODE_SUBAGENT_MODEL": "z-ai/glm-5.3-flash", "has_auth": True, "has_oauth": False}
    assert seen_keys == [KEY, KEY]
    assert s["provider"] == "claude_openrouter" and s["stop_reason"] == "submit"
    assert s["cost_usd"] is None and s["cost_unreported_calls"] == 0  # nothing estimated, nothing charged per call
    assert s["key_usage_before_usd"] == 10.0 and s["key_usage_after_usd"] == 10.25
    assert s["plan_cost_estimate_usd"] == 0.9  # Claude Code's own figure, kept apart
    for name in os.listdir(cfg.agent_out):
        text = open(os.path.join(cfg.agent_out, name)).read()
        assert KEY not in text and TOKEN not in text


def test_openrouter_endpoint_needs_the_key_not_the_token(tmp_path, monkeypatch):
    cfg = setup(tmp_path, monkeypatch)
    monkeypatch.delenv("OPENROUTER_API_KEY")
    s = claude_code.run(cfg)
    assert s["stop_reason"] == "error" and "OPENROUTER_API_KEY" in s["error"]


def _guard_cfg(tmp_path, monkeypatch, budget="0.5"):
    ledger = tmp_path / "ledger"
    ledger.mkdir(exist_ok=True)
    monkeypatch.setenv("CVDP_LEDGER_DIR", str(ledger))
    monkeypatch.setenv("CVDP_RUN_BUDGET_USD", budget)
    return setup(tmp_path, monkeypatch), ledger


def test_key_guard_baseline_then_stop(tmp_path, monkeypatch):
    cfg, ledger = _guard_cfg(tmp_path, monkeypatch)
    assert claude_code.key_guard(cfg, 20.0) == (False, 20.0)  # the first problem sets the baseline
    assert claude_code.key_guard(cfg, 20.3) == (False, 20.0)
    assert claude_code.key_guard(cfg, 20.5) == (True, 20.0)
    assert claude_code.key_guard(cfg, None) == (True, 20.0)  # unreadable usage fails safe
    assert (ledger / "key_baseline.txt").read_text() == "20.000000"
    assert not list(ledger.glob("*.json"))  # not a ledger entry


def test_openrouter_endpoint_stops_on_the_key_guard(tmp_path, monkeypatch):
    cfg, ledger = _guard_cfg(tmp_path, monkeypatch)
    (ledger / "key_baseline.txt").write_text("1.0")
    monkeypatch.setattr(claude_code, "key_usage", lambda key: 1.6)
    s = claude_code.run(cfg)
    assert s["stop_reason"] == "run_budget_exhausted" and s["key_usage_baseline_usd"] == 1.0
    assert not (tmp_path / "seen.json").exists()  # Claude Code never started


def test_key_usage_reads_only_usage():
    assert claude_code.key_usage("k", get=lambda: (200, {"data": {"usage": 3.5, "label": "sk-or-x"}})) == 3.5
    assert claude_code.key_usage("k", get=lambda: (401, {})) is None


def _sweep(tmp_path, **env):
    e = dict(os.environ, WORK=str(tmp_path / "w"), DATA_DIR=str(tmp_path), CVDP_DIR=str(tmp_path), **env)
    return subprocess.run(["bash", os.path.join(REPO, "tools/sweep.sh"), "run"], env=e, capture_output=True,
                          text=True)


def test_sweep_refuses_bad_combinations(tmp_path):
    r = _sweep(tmp_path, AGENT_IMAGE="x", CLAUDE_ENDPOINT="openrouter", HARNESS="langgraph")
    assert r.returncode == 2 and "needs HARNESS=claudecode" in r.stderr
    r = _sweep(tmp_path, AGENT_IMAGE="x", DATA_COLLECTION="deny", HARNESS="claudecode")
    assert r.returncode == 2 and "Claude Code makes its own requests" in r.stderr
    r = _sweep(tmp_path, AGENT_IMAGE="x", DATA_COLLECTION="allow")
    assert r.returncode == 2 and "blank or deny" in r.stderr


def test_reliability_counts_from_a_trace(tmp_path):
    import reliability

    out = tmp_path / "art" / "work" / "seed2" / "cvdp_agentic_lfsr" / "harness" / "1" / "rundir" / "agent_out"
    out.mkdir(parents=True)
    ev = [
        {"kind": "llm", "node": "edit", "turn": 1, "finish_reason": "length", "completion": "<diff>x</diff>",
         "decision": {"changed": [], "errors": 1, "checks": ["compile"], "testbench": []}},
        {"kind": "tool", "check": "file_write", "exit_code": 1},
        {"kind": "llm", "node": "edit", "turn": 2, "finish_reason": "stop", "completion": "<diff>x</diff>",
         "decision": {"changed": [], "errors": 1, "checks": ["compile"], "testbench": []}},
        {"kind": "llm", "node": "edit", "turn": 3, "finish_reason": "stop", "completion": "prose only",
         "decision": {"changed": [], "errors": 0, "checks": [], "testbench": []}},
        {"kind": "llm", "node": "reflect", "decision": "unparseable"},
        {"kind": "llm", "node": "reflect", "error": "APIError: 502", "cost": None},
        {"kind": "llm", "node": "plan", "error": "HTTP 400", "reasoning_rejected": True},
    ]
    (out / "trace.jsonl").write_text("\n".join(json.dumps(e) for e in ev) + "\nnot json\n")
    (out / "summary.json").write_text(json.dumps({"stop_reason": "max_turns", "empty_replies": 1}))
    r = reliability.runs(str(tmp_path / "art"))
    (key, probs), = r.items()
    assert key[1] == "2" and list(probs) == ["cvdp_agentic_lfsr_0001"]
    c, stop = probs["cvdp_agentic_lfsr_0001"]
    assert stop == "max_turns"
    assert c == {"unparsable": 2, "invalid_edit": 1, "length": 1, "empty": 1, "provider_err": 1, "loop": 2,
                 "cap_stop": 1}

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


def test_openrouter_endpoint_env_and_provider_reported_cost(tmp_path, monkeypatch):
    cfg = setup(tmp_path, monkeypatch)
    looked = []

    def fake_costs(ids, key, deadline=None):
        looked.extend(ids)
        assert key == KEY
        return {"gen-1": 0.0012, "gen-2": None}
    monkeypatch.setattr(claude_code, "generation_costs", fake_costs)
    s = claude_code.run(cfg)
    seen = json.load(open(tmp_path / "seen.json"))
    assert seen == {"ANTHROPIC_BASE_URL": "https://openrouter.ai/api", "ANTHROPIC_API_KEY": "",
                    "ANTHROPIC_MODEL": "z-ai/glm-5.3-flash", "ANTHROPIC_SMALL_FAST_MODEL": "z-ai/glm-5.3-flash",
                    "CLAUDE_CODE_SUBAGENT_MODEL": "z-ai/glm-5.3-flash", "has_auth": True, "has_oauth": False}
    assert looked == ["gen-1", "gen-2"]  # one lookup per distinct message id
    assert s["provider"] == "claude_openrouter"
    assert s["cost_usd"] == 0.0012 and s["cost_unreported_calls"] == 1
    assert s["plan_cost_estimate_usd"] == 0.9  # Claude Code's own figure, kept apart
    for name in os.listdir(cfg.agent_out):
        text = open(os.path.join(cfg.agent_out, name)).read()
        assert KEY not in text and TOKEN not in text


def test_openrouter_endpoint_needs_the_key_not_the_token(tmp_path, monkeypatch):
    cfg = setup(tmp_path, monkeypatch)
    monkeypatch.delenv("OPENROUTER_API_KEY")
    s = claude_code.run(cfg)
    assert s["stop_reason"] == "error" and "OPENROUTER_API_KEY" in s["error"]


def test_openrouter_endpoint_respects_the_run_guard(tmp_path, monkeypatch):
    ledger = tmp_path / "ledger"
    ledger.mkdir()
    (ledger / "a.json").write_text(json.dumps({"cost_usd": 1.0, "cost_unreported_calls": 0, "guard_charge_usd": 1.0}))
    monkeypatch.setenv("CVDP_LEDGER_DIR", str(ledger))
    monkeypatch.setenv("CVDP_RUN_BUDGET_USD", "0.5")
    cfg = setup(tmp_path, monkeypatch)
    s = claude_code.run(cfg)
    assert s["stop_reason"] == "run_budget_exhausted"
    assert not (tmp_path / "seen.json").exists()  # Claude Code never started


def test_generation_costs_waits_for_lag_and_gives_up_on_other_errors():
    calls = []

    def get(gid):
        calls.append(gid)
        if gid == "lagging" and calls.count(gid) < 2:
            return 404, {}
        if gid == "bad":
            return 400, {}
        return 200, {"data": {"total_cost": 0.5}}
    out = claude_code.generation_costs(["lagging", "bad"], KEY, get=get, waits=(0.01, 0.01))
    assert out == {"lagging": 0.5, "bad": None}
    assert calls.count("bad") == 1


def test_message_ids_dedupes():
    lines = [json.dumps({"type": "assistant", "message": {"id": i}}) for i in ("a", "a", "b")] + ["not json"]
    assert claude_code.message_ids(lines) == ["a", "b"]


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

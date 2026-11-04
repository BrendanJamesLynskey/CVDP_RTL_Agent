"""M3j: arms billed to the Anthropic API key (the plan's monthly API credit). Claude Code with an API key
(`claude_endpoint=api`, profile plain or bare) and the plain API harness (`harness=apiloop`). The key reaches only
those arms; a plan arm never sees it. Fake `claude` and a scripted fake API client only; no model is called."""
import json
import os
import stat
from types import SimpleNamespace

import collect
import pytest
from cvdp_agent import apiloop, claude_code
from cvdp_agent.config import Config, from_env
from cvdp_agent.graph import ledger_totals
from cvdp_agent.prompts import SYSTEM
from test_m3h import sweep
from test_m3i import FAKE

KEY = "sk-ant-api03-" + "k" * 40
TOKEN = "sk-ant-oat01-" + "t" * 40
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The M3i fake, recording which Anthropic credentials it was started with (names only)
FAKE_AUTH = FAKE.replace(
    '"no_memory": os.environ.get("CLAUDE_CODE_DISABLE_AUTO_MEMORY"), "cwd": os.getcwd()}',
    '"no_memory": os.environ.get("CLAUDE_CODE_DISABLE_AUTO_MEMORY"), "cwd": os.getcwd(),\n'
    '           "auth": sorted(k for k in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_AUTH_TOKEN")\n'
    '                          if os.environ.get(k))}')
# and reporting its credential in the init event, as Claude Code does (FAKE_SOURCE overrides it)
FAKE_AUTH = FAKE_AUTH.replace(
    '"model": "claude-haiku-5-5"})',
    '"model": "claude-haiku-5-5", "apiKeySource": os.environ.get("FAKE_SOURCE") or '
    '("ANTHROPIC_API_KEY" if os.environ.get("ANTHROPIC_API_KEY") else "none")})', 1)
# the fake writes its design only for the four plain tools; the bare profile's three are fine too
FAKE_AUTH = FAKE_AUTH.replace('set(tools) == {"Bash", "Edit", "Read", "Write"}',
                              'set(tools) in ({"Bash", "Edit", "Read", "Write"}, {"Bash", "Edit", "Read"})')


def cc_setup(tmp_path, monkeypatch, provider, profile, **env):
    root = tmp_path / "code"
    (root / "rtl").mkdir(parents=True)
    (root / "prompt.json").write_text(json.dumps({"prompt": "Write module top."}))
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "claude"
    fake.write_text(FAKE_AUTH)
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    for k, v in dict(CLAUDE_CODE_OAUTH_TOKEN=TOKEN, ANTHROPIC_API_KEY=KEY, CVDP_HARNESS="claudecode",
                     CVDP_PROVIDER=provider, CVDP_MODEL="claude-haiku-5-5", CVDP_ROOT=str(root),
                     CVDP_OUT_DIR=str(tmp_path / "out"), FAKE_RECORD=str(tmp_path / "rec.json"),
                     CVDP_CC_PROFILE=profile, **env).items():
        monkeypatch.setenv(k, v)
    return root, from_env()


# ---------- the inputs ----------

def test_config_refusals():
    assert Config(harness="claudecode", provider="claude_api", cc_profile="bare").switches()["cc_profile"] == "bare"
    with pytest.raises(ValueError, match="API key"):
        Config(harness="claudecode", provider="claude_plan", cc_profile="bare")
    with pytest.raises(ValueError, match="anthropic"):
        Config(harness="apiloop", provider="openrouter")
    Config(harness="apiloop", provider="anthropic")


def test_apiloop_defaults_to_claude_codes_turn_cap(monkeypatch):
    monkeypatch.setenv("CVDP_HARNESS", "apiloop")
    monkeypatch.setenv("CVDP_PROVIDER", "anthropic")
    assert from_env().max_rounds == 60


# ---------- Claude Code on the API key ----------

def test_bare_command_is_plain_plus_bare():
    plain = claude_code.plain_command("P", 60, "claude-haiku-5-5")
    assert claude_code.bare_command("P", 60, "claude-haiku-5-5") == plain + ["--bare"]
    assert claude_code.profile_problems({"tools": ["Bash", "Edit", "Read"]}, claude_code.BARE_TOOLS) == []
    assert claude_code.profile_problems({"tools": ["Bash", "Edit", "Read"]})  # not the plain four


@pytest.mark.parametrize("profile,tools", [("plain", "Bash,Edit,Read,Write"), ("bare", "Bash,Edit,Read")])
def test_api_arm_gets_the_key_and_not_the_plan_token(tmp_path, monkeypatch, profile, tools):
    _, cfg = cc_setup(tmp_path, monkeypatch, "claude_api", profile, FAKE_TOOLS=tools)
    s = claude_code.run(cfg)
    rec = json.load(open(tmp_path / "rec.json"))
    assert rec["auth"] == ["ANTHROPIC_API_KEY"], rec["auth"]
    assert ("--bare" in rec["argv"]) == (profile == "bare")
    assert s["provider"] == "claude_api" and s["cc_profile"] == profile and s["stop_reason"] == "submit"
    assert s["cost_usd"] is None and s["guard_estimate_usd"] == 0.01


def test_plan_arm_never_sees_the_api_key(tmp_path, monkeypatch):
    # Claude Code prefers ANTHROPIC_API_KEY to the plan's token: a plan arm must not have it, or it bills the credit
    _, cfg = cc_setup(tmp_path, monkeypatch, "claude_plan", "plain")
    s = claude_code.run(cfg)
    assert json.load(open(tmp_path / "rec.json"))["auth"] == ["CLAUDE_CODE_OAUTH_TOKEN"]
    assert s["provider"] == "claude_plan" and "guard_estimate_usd" not in s


def test_bare_profile_refuses_the_plain_four(tmp_path, monkeypatch):
    _, cfg = cc_setup(tmp_path, monkeypatch, "claude_api", "bare", FAKE_TOOLS="Bash,Edit,Read,Write")
    s = claude_code.run(cfg)
    assert s["stop_reason"] == "profile_error" and "bare profile refused" in s["error"]


def test_api_arm_refuses_a_run_billed_to_anything_but_the_key(tmp_path, monkeypatch):
    _, cfg = cc_setup(tmp_path, monkeypatch, "claude_api", "plain", FAKE_SOURCE="none")
    s = claude_code.run(cfg)
    assert s["stop_reason"] == "profile_error" and "ANTHROPIC_API_KEY" in s["error"]
    assert not (tmp_path / "code" / "rtl" / "top.sv").exists()


def test_api_arm_records_its_credential(tmp_path, monkeypatch):
    _, cfg = cc_setup(tmp_path, monkeypatch, "claude_api", "plain")
    assert claude_code.run(cfg)["cc_api_key_source"] == "ANTHROPIC_API_KEY"


def test_api_arm_without_the_key_stops_before_claude_runs(tmp_path, monkeypatch):
    _, cfg = cc_setup(tmp_path, monkeypatch, "claude_api", "plain")
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    s = claude_code.run(cfg)
    assert s["stop_reason"] == "error" and not (tmp_path / "rec.json").exists()


def test_api_arm_guard_charges_the_estimate_and_stops(tmp_path, monkeypatch):
    ledger = tmp_path / "ledger"
    ledger.mkdir()
    _, cfg = cc_setup(tmp_path, monkeypatch, "claude_api", "plain", CVDP_LEDGER_DIR=str(ledger),
                      CVDP_RUN_BUDGET_USD="0.015")
    claude_code.run(cfg)
    assert ledger_totals(str(ledger)) == (0.0, 0, 0.01)
    claude_code.run(cfg)  # 0.02 >= 0.015 after this one
    os.remove(tmp_path / "rec.json")
    assert claude_code.run(cfg)["stop_reason"] == "run_budget_exhausted"
    assert not (tmp_path / "rec.json").exists()


# ---------- the plain API harness ----------

def block(**kw):
    b = SimpleNamespace(**kw)
    b.model_dump = lambda exclude_none=True: {k: v for k, v in kw.items() if v is not None}
    return b


def reply(content, stop="tool_use", inp=1000, out=100, cread=0):
    return SimpleNamespace(content=content, stop_reason=stop, model="claude-haiku-5-5",
                           usage=SimpleNamespace(input_tokens=inp, output_tokens=out, cache_read_input_tokens=cread,
                                                 cache_creation_input_tokens=0))


class FakeClient:
    def __init__(self, replies):
        self.replies, self.requests = list(replies), []
        self.messages = self

    def create(self, **kw):
        self.requests.append(json.loads(json.dumps(kw, default=str)))
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def api_cfg(tmp_path, **kw):
    root = tmp_path / "code"
    (root / "rtl").mkdir(parents=True, exist_ok=True)
    (root / "prompt.json").write_text(json.dumps({"prompt": "Write module top."}))
    return Config(root=str(root), provider="anthropic", harness="apiloop", model="claude-haiku-5-5", max_rounds=60,
                  out_dir=str(tmp_path / "out"), **kw)


def test_apiloop_request_is_bare_and_matches_the_plain_profile(tmp_path):
    cfg = api_cfg(tmp_path)
    think = block(type="thinking", thinking="", signature="sig1")
    c = FakeClient([reply([think, block(type="tool_use", id="t1", name="Write",
                                        input={"path": "rtl/top.sv", "content": "module top; endmodule\n"})]),
                    reply([block(type="text", text="done")], stop="end_turn", cread=900)])
    s = apiloop.run(cfg, client=c)
    assert open(tmp_path / "code" / "rtl" / "top.sv").read() == "module top; endmodule\n"
    req = c.requests[0]
    assert req["system"] == SYSTEM  # our prompt only: no fixed Claude Code blocks
    assert [t["name"] for t in req["tools"]] == ["Read", "Write", "Edit", "Bash"]
    assert req["thinking"] == {"type": "adaptive"} and req["output_config"] == {"effort": "medium"}
    assert req["messages"][0]["content"] == claude_code.PROMPT.format(task="Write module top.")
    # the thinking block goes back unchanged, then the tool result
    assert c.requests[1]["messages"][1]["content"][0] == {"type": "thinking", "thinking": "", "signature": "sig1"}
    assert c.requests[1]["messages"][2]["content"][0]["type"] == "tool_result"
    assert s["stop_reason"] == "submit" and s["llm_calls"] == 2 and s["tool_calls"] == 1
    assert s["prompt_tokens"] == 2900 and s["cache_read_tokens"] == 900 and s["cost_usd"] is None
    # M3k: priced per request by usage (fresh, cache reads, cache writes), not every input token at the long rate
    assert s["api_cost_estimate_usd"] == s["guard_estimate_usd"] == round(
        apiloop.call_cost(1000, 0, 0, 100) + apiloop.call_cost(1000, 900, 0, 100), 6)
    assert s["cc_profile"] == "apiloop" and s["cc_tools"] == "Read;Write;Edit;Bash"


def test_apiloop_tools_stay_in_the_tree_and_off_the_network(tmp_path):
    root = str(api_cfg(tmp_path).root)
    out, err, _ = apiloop.run_tool(root, "Read", {"path": "/etc/passwd"}, 1e12)
    assert err and "outside" in out
    out, err, _ = apiloop.run_tool(root, "Write", {"path": "../x.sv", "content": "x"}, 1e12)
    assert err and not os.path.exists(os.path.join(os.path.dirname(root), "x.sv"))
    for cmd in ("curl https://x", "cd rtl && wget x", "FOO=1 pip install y", "ls | nc host 1", "echo $(git log)"):
        out, err, _ = apiloop.run_tool(root, "Bash", {"command": cmd}, 1e12)
        assert err and "not allowed" in out, cmd
    out, err, rec = apiloop.run_tool(root, "Bash", {"command": "echo hi"}, 1e12)
    assert not err and "hi" in out and rec["exit_code"] == 0


def test_apiloop_edit_needs_one_exact_match(tmp_path):
    root = str(api_cfg(tmp_path).root)
    open(os.path.join(root, "rtl", "a.sv"), "w").write("x x\n")
    out, err, _ = apiloop.run_tool(root, "Edit", {"path": "rtl/a.sv", "old_string": "x", "new_string": "y"}, 1e12)
    assert err and "2 times" in out
    out, err, _ = apiloop.run_tool(root, "Edit", {"path": "rtl/a.sv", "old_string": "x x", "new_string": "y"}, 1e12)
    assert not err and open(os.path.join(root, "rtl", "a.sv")).read() == "y\n"


def test_apiloop_turn_cap_and_errors(tmp_path):
    cfg = api_cfg(tmp_path, max_turns=10)
    cfg.max_rounds = 2
    bash = lambda i: reply([block(type="tool_use", id=f"t{i}", name="Bash", input={"command": "true"})])
    assert apiloop.run(cfg, client=FakeClient([bash(1), bash(2)]))["stop_reason"] == "max_turns"

    class RateLimitError(Exception):
        pass
    s = apiloop.run(api_cfg(tmp_path / "b"), client=FakeClient([RateLimitError("429")]))
    assert s["stop_reason"] == "rate_limited" and s["llm_calls"] == 0
    s = apiloop.run(api_cfg(tmp_path / "c"), client=FakeClient([reply([], stop="refusal")]))
    assert s["stop_reason"] == "refusal"


def test_apiloop_without_a_key_does_nothing(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert apiloop.run(api_cfg(tmp_path))["stop_reason"] == "error"


def test_apiloop_redacts_the_key_from_what_it_writes(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    cfg = api_cfg(tmp_path)
    c = FakeClient([reply([block(type="tool_use", id="t1", name="Bash", input={"command": f"echo {KEY}"})]),
                    reply([block(type="text", text="done")], stop="end_turn")])
    apiloop.run(cfg, client=c)
    for fn in os.listdir(cfg.agent_out):
        assert KEY not in open(os.path.join(cfg.agent_out, fn)).read() and "sk-ant-api03" not in \
            open(os.path.join(cfg.agent_out, fn)).read()


# ---------- the sweep and the workflow ----------

def test_sweep_api_arm_passes_the_key_and_not_the_token(tmp_path):
    r, seen = sweep(tmp_path, CLAUDE_ENDPOINT="api", CC_PROFILE="bare", ANTHROPIC_API_KEY=KEY)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ANTHROPIC_API_KEY" in seen["env"] and "CLAUDE_CODE_OAUTH_TOKEN" not in seen["env"]
    run_json = json.load(open(str(tmp_path / "work") + ".run.json"))
    assert run_json["claude_endpoint"] == "api" and run_json["cc_profile"] == "bare"


def test_sweep_plan_arm_never_forwards_the_key(tmp_path):
    r, seen = sweep(tmp_path, ANTHROPIC_API_KEY=KEY)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ANTHROPIC_API_KEY" not in seen["env"] and "CLAUDE_CODE_OAUTH_TOKEN" in seen["env"]


def test_sweep_apiloop_needs_the_key(tmp_path):
    r, _ = sweep(tmp_path, HARNESS="apiloop", ANTHROPIC_API_KEY="")
    assert r.returncode == 2 and "ANTHROPIC_API_KEY" in r.stderr
    (tmp_path / "b").mkdir()
    r, seen = sweep(tmp_path / "b", HARNESS="apiloop", ANTHROPIC_API_KEY=KEY)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ANTHROPIC_API_KEY" in seen["env"] and "CLAUDE_CODE_OAUTH_TOKEN" not in seen["env"]


def test_workflow_gives_the_key_only_to_api_arms():
    import yaml
    wf = yaml.safe_load(open(os.path.join(ROOT, ".github", "workflows", "sweep.yml")))
    gate = wf["env"]["USES_API_KEY"]
    assert "apiloop" in gate and "claude_endpoint == 'api'" in gate and "workflow_dispatch" in gate
    steps = {s.get("name"): s for s in wf["jobs"]["sweep"]["steps"]}
    for name in ("Run", "Secret check on what gets uploaded"):
        assert "env.USES_API_KEY == 'true' && secrets.ANTHROPIC_API_KEY" in steps[name]["env"]["ANTHROPIC_API_KEY"]
    assert "ANTHROPIC_API_KEY" in steps["Secret check on what gets uploaded"]["run"]
    on = wf.get("on") or wf.get(True)
    inp = on["workflow_dispatch"]["inputs"]
    assert "api" in inp["claude_endpoint"]["options"] and "apiloop" in inp["harness"]["options"]
    assert len(inp) <= 25


def test_collect_api_columns_only_with_the_flag(tmp_path):
    assert "api_cost_estimate_usd" not in collect.FIELDS
    cols = collect.m3j_columns({"cache_read_tokens": 5, "api_cost_estimate_usd": 0.1, "network_flags": ["curl x"]})
    assert cols["cache_read_tokens"] == 5 and cols["network_flags_n"] == 1 and cols["plan_cost_estimate_usd"] == ""


def test_ablate_zero_bound_is_not_an_effect():
    """M3j: a bootstrap bound that is exactly 0 (thirds summing to +/-1e-17) must read as no detectable effect."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("ablate", os.path.join(ROOT, "tools", "ablate.py"))
    ab = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ab)
    assert ab.verdict({"lo": round(1e-17, 9), "hi": 0.07}) == "no detectable effect"
    rows = lambda vals: [{"id": f"p{i}", "pass": v, "_run": "r#seed1"} for i, v in enumerate(vals)]
    p = ab.paired(rows(["1", "0"]), rows(["1", "0"]))
    assert ab.verdict(p) == "no detectable effect"

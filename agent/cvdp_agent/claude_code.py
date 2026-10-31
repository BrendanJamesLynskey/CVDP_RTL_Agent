"""The Claude Code harness (`CVDP_HARNESS=claudecode`): Claude Code itself, headless (`claude -p`), as an
off-the-shelf agent on the same task tree, scored by the same hidden tests. It is a comparison point, not our agent:
none of graph.py's stop rules, checks, best-edit rule or prompts apply; the harness scores whatever is on disk.

Billing: Claude Code runs on the owner's Claude plan (`CLAUDE_CODE_OAUTH_TOKEN`), not a metered API, so there is no
provider-billed cost. `cost_usd` stays None with no unreported calls (nothing was billed), and Claude Code's own
API-rate figure goes in `plan_cost_estimate_usd`, an estimate that the results must never treat as a cost.

What it may use: Read, Edit, Write, Glob, Grep and Bash (for Icarus, Verilator, Yosys, cocotb), in /code. Not
offered: WebFetch, WebSearch, sub-agents (Task), and Bash commands that fetch from the network (curl, wget, git,
pip, uv, npm). The container still has a network (Claude Code needs it), so every Bash command in the transcript is
audited afterwards: `network_flags` lists any that names a host, URL or fetch tool, so a run that reached for the
public dataset (which holds the hidden tests) can be found and excluded.

Endpoint (F1B): with `CVDP_PROVIDER=claude_openrouter`, Claude Code talks to OpenRouter's Anthropic-compatible
endpoint (`ANTHROPIC_BASE_URL=https://openrouter.ai/api`, the OpenRouter key as `ANTHROPIC_AUTH_TOKEN`, an empty
`ANTHROPIC_API_KEY`) and runs any OpenRouter model given as `CVDP_MODEL`, including for its background calls. The
plan's token is not passed. Cost: the endpoint's message ids are not OpenRouter generation ids (the F1B smoke: every
lookup failed), so no per-call cost can be read. The provider-reported cost is the key's own usage
(`/api/v1/key`): each problem records the usage before and after it (`key_usage_before_usd`/`_after_usd`, which
overlap when problems run in parallel), the sweep records it before and after the whole run, and `cost_usd` stays
None with no unreported calls (nothing is estimated). The whole-run guard is the key's usage since the run's first
problem started (`key_guard`). Claude Code's own figure stays in `plan_cost_estimate_usd` (an estimate at
Anthropic's prices, never a cost).

Caps: the same 480 s wall time as the LangGraph agent (the harness kills at 600 s), and `--max-turns`
(`CVDP_MAX_ROUNDS`, here a cap on Claude Code's own turns, default 60)."""
import json
import os
import re
import subprocess
import tempfile
import time

from .graph import write_ledger
from .trace import redact

OPENROUTER_ANTHROPIC = "https://openrouter.ai/api"
OPENROUTER_KEY = "https://openrouter.ai/api/v1/key"

ALLOWED = ["Read", "Edit", "Write", "Glob", "Grep", "Bash"]
DENIED = ["WebFetch", "WebSearch", "Task", "NotebookEdit",
          "Bash(curl:*)", "Bash(wget:*)", "Bash(git:*)", "Bash(pip:*)", "Bash(pip3:*)", "Bash(uv:*)",
          "Bash(npm:*)", "Bash(npx:*)", "Bash(ssh:*)", "Bash(nc:*)"]
NETWORK = re.compile(r"https?://|huggingface|github\.com|\bcurl\b|\bwget\b|\bnc\b|urllib|requests\.|socket|"
                     r"\bgit\s+(clone|fetch|pull)|\bpip3?\s+install|\buv\s+pip", re.IGNORECASE)

PROMPT = """You are solving one hardware-design task. The task tree is the current directory (/code).

# Task
{task}

# Rules
- Change files only under rtl/, verif/ and docs/. You may write your own testbench under rundir/agent_tb/.
- Icarus Verilog (iverilog, vvp), Verilator, Yosys and cocotb are installed: compile and test your design with them.
- Do not use the network: no downloads, no package installs, no web lookups. Everything you need is in /code.
- When the design is done and your checks pass, stop with a one-line summary."""


def _summary_base(cfg):
    provider = "claude_openrouter" if cfg.provider == "claude_openrouter" else "claude_plan"
    return {"provider": provider, "requested_model": cfg.model or None, "model": cfg.model or None,
            "harness": "claudecode", "seed": cfg.seed or None, "switches": cfg.switches(),
            "cost_usd": None, "cost_unreported_calls": 0, "plan_cost_estimate_usd": None,
            "prompt_tokens": 0, "completion_tokens": 0, "llm_calls": 0, "tool_calls": 0, "turns": 0,
            "kept": "", "network_flags": []}


def _write(cfg, summary):
    os.makedirs(cfg.agent_out, exist_ok=True)
    summary = redact(summary)
    with open(os.path.join(cfg.agent_out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    write_ledger(cfg, summary)
    return summary


def key_usage(key, get=None):
    """The OpenRouter key's cumulative usage in USD (`/api/v1/key`), or None if it cannot be read."""
    if get is None:
        import httpx

        def get():
            r = httpx.get(OPENROUTER_KEY, timeout=10.0, headers={"Authorization": f"Bearer {key}"})
            return r.status_code, (r.json() if r.status_code == 200 else {})
    try:
        code, body = get()
    except Exception:
        return None
    u = ((body or {}).get("data") or {}).get("usage") if code == 200 else None
    return float(u) if isinstance(u, (int, float)) else None


def key_guard(cfg, usage):
    """Whole-run guard by the key's own usage: the first problem of a run records the usage it saw in the ledger
    directory (`key_baseline.txt`, not a .json ledger entry); a later problem stops if usage has risen by the run
    budget or more since then. Usage the guard cannot read stops the problem (it fails safe). Returns
    (stop?, baseline)."""
    if not cfg.ledger_dir or not os.path.isdir(cfg.ledger_dir):
        return usage is None, None
    path = os.path.join(cfg.ledger_dir, "key_baseline.txt")
    if usage is not None:
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
            with os.fdopen(fd, "w") as f:
                f.write(f"{usage:.6f}")
        except FileExistsError:
            pass
    try:
        base = float(open(path).read().strip())
    except (OSError, ValueError):
        base = None
    if usage is None or base is None:
        return True, base
    return cfg.run_budget_usd is not None and usage - base >= cfg.run_budget_usd, base


def openrouter_env(env, model, key):
    """Claude Code pointed at OpenRouter's Anthropic-compatible endpoint, every model slot set to `model`."""
    env = dict(env)
    env.pop("CLAUDE_CODE_OAUTH_TOKEN", None)
    env.update(ANTHROPIC_BASE_URL=OPENROUTER_ANTHROPIC, ANTHROPIC_AUTH_TOKEN=key, ANTHROPIC_API_KEY="",
               ANTHROPIC_MODEL=model, ANTHROPIC_SMALL_FAST_MODEL=model, ANTHROPIC_DEFAULT_HAIKU_MODEL=model,
               ANTHROPIC_DEFAULT_SONNET_MODEL=model, ANTHROPIC_DEFAULT_OPUS_MODEL=model,
               CLAUDE_CODE_SUBAGENT_MODEL=model, CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1")
    return env


def parse_stream(lines):
    """Claude Code's stream-json lines -> (result event or None, tool calls, Bash commands, served models)."""
    result, tools, bash, models = None, 0, [], set()
    for line in lines:
        try:
            ev = json.loads(line)
        except (ValueError, TypeError):
            continue
        if ev.get("type") == "assistant":
            msg = ev.get("message") or {}
            if msg.get("model"):
                models.add(msg["model"])
            for c in msg.get("content") or []:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    tools += 1
                    if c.get("name") == "Bash":
                        bash.append(str((c.get("input") or {}).get("command", "")))
        elif ev.get("type") == "result":
            result = ev
    return result, tools, bash, sorted(models)


def stop_reason(result, timed_out):
    if timed_out:
        return "wall_time"
    if result is None:
        return "error"
    sub = result.get("subtype", "")
    if result.get("is_error") or result.get("terminal_reason") == "api_error":
        return "llm_error"
    if sub == "success":
        return "give_up" if "GIVE_UP" in str(result.get("result", "")).upper() else "submit"
    if sub == "error_max_turns":
        return "max_turns"
    return "llm_error"


def run(cfg):
    summary = _summary_base(cfg)
    t0 = time.time()
    via_openrouter = cfg.provider == "claude_openrouter"
    key = os.environ.get("OPENROUTER_API_KEY", "") if via_openrouter else ""
    if via_openrouter and not key:
        summary.update(stop_reason="error", error="OPENROUTER_API_KEY is not set", wall_time_s=0)
        return _write(cfg, summary)
    if not via_openrouter and not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        summary.update(stop_reason="error", error="CLAUDE_CODE_OAUTH_TOKEN is not set", wall_time_s=0)
        return _write(cfg, summary)
    if via_openrouter:
        before = key_usage(key)
        stop, base = key_guard(cfg, before)
        summary.update(key_usage_before_usd=before, key_usage_baseline_usd=base)
        if stop:
            summary.update(stop_reason="run_budget_exhausted", wall_time_s=0,
                           error=None if before is not None else "key usage could not be read")
            return _write(cfg, summary)
    try:
        with open(os.path.join(cfg.root, "prompt.json")) as f:
            task = json.load(f).get("prompt", "")
    except (OSError, ValueError) as e:
        summary.update(stop_reason="no_task", error=str(e), wall_time_s=0)
        return _write(cfg, summary)
    # What Claude Code can see: recorded, so the report can show the hidden tests were not in the tree.
    summary["visible_top_level"] = sorted(os.listdir(cfg.root))
    cmd = ["claude", "-p", PROMPT.format(task=task), "--output-format", "stream-json", "--verbose",
           "--max-turns", str(cfg.max_rounds), "--permission-mode", "acceptEdits",
           "--allowedTools", *ALLOWED, "--disallowedTools", *DENIED]
    if cfg.model:
        cmd += ["--model", cfg.model]
    os.makedirs(cfg.agent_out, exist_ok=True)
    # Claude Code writes its settings under $HOME; the harness's user may have none it can write, so give it one.
    env = dict(os.environ)
    home = env.get("HOME", "")
    if not home or not os.access(home, os.W_OK):
        env["HOME"] = tempfile.mkdtemp(prefix="claude_home_")
    if via_openrouter:
        env = openrouter_env(env, cfg.model, key)
    timed_out = False
    try:
        p = subprocess.run(cmd, cwd=cfg.root, capture_output=True, text=True, timeout=cfg.wall_s,
                           stdin=subprocess.DEVNULL, env=env)
        out, err = p.stdout, p.stderr
    except OSError as e:  # claude missing or not executable
        summary.update(stop_reason="error", error=f"{type(e).__name__}: {e}", wall_time_s=round(time.time() - t0, 1))
        return _write(cfg, summary)
    except subprocess.TimeoutExpired as e:
        timed_out = True
        out = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        err = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
    lines = out.splitlines()
    with open(os.path.join(cfg.agent_out, "claude_stream.jsonl"), "w") as f:
        for line in lines:  # redact parsed values, so a redaction cannot break the line's JSON
            try:
                f.write(json.dumps(redact(json.loads(line))) + "\n")
            except ValueError:
                f.write(json.dumps({"unparsed": redact(line)}) + "\n")
    result, tools, bash, models = parse_stream(lines)
    usage = (result or {}).get("usage") or {}
    summary.update(
        model="+".join(models) or cfg.model or None,
        prompt_tokens=sum(int(usage.get(k) or 0) for k in
                          ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")),
        completion_tokens=int(usage.get("output_tokens") or 0),
        cache_read_tokens=int(usage.get("cache_read_input_tokens") or 0),
        plan_cost_estimate_usd=(result or {}).get("total_cost_usd"),
        turns=int((result or {}).get("num_turns") or 0),
        llm_calls=int((result or {}).get("num_turns") or 0),
        tool_calls=tools,
        network_flags=[c[:200] for c in bash if NETWORK.search(c)],
        stop_reason=stop_reason(result, timed_out),
        wall_time_s=round(time.time() - t0, 1),
    )
    if via_openrouter:  # the key's usage after this problem (other problems in parallel are in it too)
        summary["key_usage_after_usd"] = key_usage(key)
    if summary["stop_reason"] in ("error", "llm_error"):
        summary["error"] = ((err or "") + "\n" + str((result or {}).get("result", "")))[-2000:]
        tok = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "")  # its shape only, never its value: for a 401
        summary["token_shape"] = {"length": len(tok), "oat_prefix": tok.startswith("sk-ant-oat01-"),
                                  "whitespace": any(c.isspace() for c in tok)}
    return _write(cfg, summary)

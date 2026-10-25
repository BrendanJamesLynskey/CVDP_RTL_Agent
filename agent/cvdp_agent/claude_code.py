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
    return {"provider": "claude_plan", "requested_model": cfg.model or None, "model": cfg.model or None,
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
    if sub == "success":
        return "give_up" if "GIVE_UP" in str(result.get("result", "")).upper() else "submit"
    if sub == "error_max_turns":
        return "max_turns"
    return "llm_error"


def run(cfg):
    summary = _summary_base(cfg)
    t0 = time.time()
    if not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        summary.update(stop_reason="error", error="CLAUDE_CODE_OAUTH_TOKEN is not set", wall_time_s=0)
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
        for line in lines:
            f.write(redact(line) + "\n")
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
    if summary["stop_reason"] in ("error", "llm_error"):
        summary["error"] = (err or "")[-2000:]
    return _write(cfg, summary)

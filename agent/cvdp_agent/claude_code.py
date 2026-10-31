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
(`CVDP_MAX_ROUNDS`, here a cap on Claude Code's own turns, default 60).

M3h (`CVDP_SKILL_PACK`, a tag of the private knowledge pack): the pack is checked against its pinned manifest hash
and installed as Claude Code's own user skills in a fresh HOME outside the task tree (native_skills.py). The raw
stream then holds the bodies of any skill the model loads, so it is not written; agent_out gets `claude_tools.jsonl`
(turn and tool name per call, a Skill call's skill name) instead. With the pack blank nothing changes.

Plan limits: a problem cut off by the plan's session or weekly limit (HTTP 429, `usage_limit_reached`, or a
`rate_limit_event` whose status is `rejected`) ends with stop reason `rate_limited`, not `llm_error`, so it is
counted as not run and rerun, never as a failure."""
import json
import os
import re
import subprocess
import tempfile
import time

from . import native_skills
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
    if result.get("is_error") or result.get("terminal_reason") == "api_error":
        return "llm_error"
    if sub == "success":
        return "give_up" if "GIVE_UP" in str(result.get("result", "")).upper() else "submit"
    if sub == "error_max_turns":
        return "max_turns"
    return "llm_error"


def rate_limited(lines, result):
    """The rate-limit type ("five_hour", "seven_day", ...) if the plan's limit stopped this run, else None."""
    rejected = None
    for line in lines:
        try:
            ev = json.loads(line)
        except (ValueError, TypeError):
            continue
        if isinstance(ev, dict) and ev.get("type") == "rate_limit_event":
            info = ev.get("rate_limit_info") or {}
            if str(info.get("status", "")).lower() == "rejected":
                rejected = str(info.get("rateLimitType") or "unknown")[:40]
    r = result or {}
    if r.get("api_error_status") == 429 or r.get("api_error") in ("usage_limit_reached", "rate_limit_error"):
        return rejected or str(r.get("api_error") or "429")[:40]
    if rejected and (result is None or r.get("is_error")):
        return rejected
    return None


def _install_pack(cfg, summary, env):
    """M3h: verify and install the pack in a fresh HOME; record names and hashes only. False on a bad pack."""
    summary.update(skill_pack=cfg.skill_pack, skill_pack_sha=None, skills_installed=0, skills_loaded=[],
                   skills_n=0, skill_first_turn=None)
    try:
        summary["skill_pack_sha"] = native_skills.verify(cfg.skill_pack_dir, cfg.skill_pack)
        home = tempfile.mkdtemp(prefix="claude_home_")
        names = native_skills.install(cfg.skill_pack_dir, home, hint=cfg.skill_hint)
    except (native_skills.PackError, OSError) as e:
        summary.update(stop_reason="skills_error", error=f"skill pack refused: {e}"[:500], wall_time_s=0)
        return None
    env["HOME"] = home
    env.pop("CLAUDE_CONFIG_DIR", None)  # Claude Code would read its user skills from there instead
    summary["skills_installed"] = len(names)
    return names


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
    pack_names = None
    if cfg.skill_pack:  # before any model call: a pack that is not the pinned one stops the problem here
        pack_names = _install_pack(cfg, summary, env)
        if pack_names is None:
            return _write(cfg, summary)
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
    if pack_names is None:
        with open(os.path.join(cfg.agent_out, "claude_stream.jsonl"), "w") as f:
            for line in lines:  # redact parsed values, so a redaction cannot break the line's JSON
                try:
                    f.write(json.dumps(redact(json.loads(line))) + "\n")
                except ValueError:
                    f.write(json.dumps({"unparsed": redact(line)}) + "\n")
    else:  # M3h: the raw stream holds loaded skill bodies; keep only the tool skeleton
        with open(os.path.join(cfg.agent_out, "claude_tools.jsonl"), "w") as f:
            for rec in native_skills.tool_skeleton(lines):
                f.write(json.dumps(rec) + "\n")
        calls = native_skills.skill_calls(lines)
        known = set(pack_names)
        pack_calls = [(t, n) for t, n in calls if n in known]
        summary.update(skills_loaded=[n for _, n in calls], skills_n=len({n for _, n in pack_calls}),
                       skill_first_turn=pack_calls[0][0] if pack_calls else None)
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
    limit = None if timed_out else rate_limited(lines, result)
    if limit and summary["stop_reason"] in ("llm_error", "error"):
        summary.update(stop_reason="rate_limited", rate_limit=limit)
    if summary["stop_reason"] in ("error", "llm_error", "rate_limited"):
        summary["error"] = ((err or "") + "\n" + str((result or {}).get("result", "")))[-2000:]
        tok = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "")  # its shape only, never its value: for a 401
        summary["token_shape"] = {"length": len(tok), "oat_prefix": tok.startswith("sk-ant-oat01-"),
                                  "whitespace": any(c.isspace() for c in tok)}
    return _write(cfg, summary)

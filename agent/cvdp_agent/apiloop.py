"""The plain API harness (`CVDP_HARNESS=apiloop`, M3j): the model called straight through the Anthropic Messages API
with four tools of our own, in a loop of our own. No Claude Code: no fixed system blocks, no environment message, no
Claude Code tool schemas, no placeholder tool, no compaction or permission system. It is M3i's plain profile with
Claude Code taken away, to measure what is left of Claude Code once its prompt, tools and settings are stripped.

What the model gets, matched to M3i's plain profile where it can be:
- system prompt: `prompts.SYSTEM`, the LangGraph agent's own (the same text Claude Code's `--system-prompt` got);
- user message: `claude_code.PROMPT` with the task, unchanged;
- tools: Read, Write, Edit and Bash, each with a one-line description and a minimal JSON schema (below), run in the
  task tree (/code). File tools refuse paths outside it; Bash refuses the same network commands Claude Code's arms
  deny, and every Bash command is audited afterwards for network use (`network_flags`), as in claude_code.py;
- request settings: adaptive thinking and effort `medium`, the values Claude Code 2.1.310 sent for this model in the
  local capture (docs/reports/m3j/preregistration.md); automatic prompt caching (`cache_control` at the top level);
  thinking blocks are passed back unchanged, as the API requires;
- caps: 60 model calls (`CVDP_MAX_ROUNDS`, Claude Code's `--max-turns`) and the 480 s wall cap (`CVDP_WALL_S`).

Billing: the Anthropic API key (`ANTHROPIC_API_KEY`). The API reports tokens, not cost, so `cost_usd` stays None
with no unreported calls (nothing is estimated as a cost). `api_cost_estimate_usd` is an upper bound from the tokens
at the long-context list rates for Claude Haiku 5.5 (UPPER_RATES), written beside the result and charged to the
whole-run guard (`guard_estimate_usd`); the real spend is the Console's, read before and after a sweep.

The transcript is not kept whole: `api_tools.jsonl` has one line per tool call (turn, tool, path or the first 200
characters of a Bash command, exit code, output size), redacted."""
import hashlib
import json
import os
import re
import subprocess
import time

from .claude_code import NETWORK, PROMPT
from .graph import ledger_totals, write_ledger
from .prompts import SYSTEM
from .trace import redact

EFFORT = "medium"
MAX_TOKENS = 32_000
BASH_TIMEOUT_S = 120.0     # Claude Code's own Bash default
OUTPUT_CAP = 30_000        # characters of a tool result the model sees
READ_LINES = 2_000
# USD per million tokens, the upper bound used for the estimate and the guard: Claude Haiku 5.5's list rates for
# prompts beyond 100K tokens ($0.50 in, $2.50 out), applied to every input token, cached or not
UPPER_RATES = {"input": 0.50, "output": 2.50}
DENY = ("curl", "wget", "git", "pip", "pip3", "uv", "npm", "npx", "ssh", "nc")

TOOLS = [
    {"name": "Read", "description": "Read a text file. Returns its lines, numbered.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"],
                      "additionalProperties": False}},
    {"name": "Write", "description": "Write a text file, replacing it if it exists.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                      "required": ["path", "content"], "additionalProperties": False}},
    {"name": "Edit", "description": "Replace one exact, unique occurrence of old_string in a file with new_string.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_string": {"type": "string"},
                                                       "new_string": {"type": "string"}},
                      "required": ["path", "old_string", "new_string"], "additionalProperties": False}},
    {"name": "Bash", "description": "Run a shell command in the task directory. Returns its output and exit code.",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"],
                      "additionalProperties": False}},
]


def _inside(root, path):
    """The absolute path if it lies inside the task tree, else None."""
    full = os.path.realpath(os.path.join(root, path)) if not os.path.isabs(path) else os.path.realpath(path)
    base = os.path.realpath(root)
    return full if full == base or full.startswith(base + os.sep) else None


def denied(command):
    """The first denied program named at the start of any part of a command line, or None."""
    for part in re.split(r"&&|\|\||[;|&\n]|\$\(|`", command):
        words = part.strip().split()
        while words and "=" in words[0] and not words[0].startswith("="):  # FOO=bar cmd
            words = words[1:]
        if words and os.path.basename(words[0]) in DENY:
            return os.path.basename(words[0])
    return None


def _cap(text):
    return text if len(text) <= OUTPUT_CAP else text[:OUTPUT_CAP] + f"\n[output cut at {OUTPUT_CAP} characters]"


def run_tool(root, name, args, deadline):
    """(result text, is_error, log record). Never raises."""
    rec = {"tool": name}
    try:
        if name in ("Read", "Write", "Edit"):
            path = str(args.get("path", ""))
            rec["path"] = path[:200]
            full = _inside(root, path)
            if full is None:
                return f"refused: {path} is outside the task directory {root}", True, rec
            if name == "Read":
                with open(full, errors="replace") as f:
                    lines = f.read().splitlines()
                body = "\n".join(f"{i + 1:6d}\t{line}" for i, line in enumerate(lines[:READ_LINES]))
                if len(lines) > READ_LINES:
                    body += f"\n[{len(lines) - READ_LINES} more lines not shown]"
                return _cap(body or "(empty file)"), False, rec
            if name == "Write":
                os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
                with open(full, "w") as f:
                    f.write(str(args.get("content", "")))
                return f"wrote {path}", False, rec
            old, new = str(args.get("old_string", "")), str(args.get("new_string", ""))
            with open(full, errors="replace") as f:
                text = f.read()
            n = text.count(old) if old else 0
            if n != 1:
                return f"refused: old_string occurs {n} times in {path}; it must occur exactly once", True, rec
            with open(full, "w") as f:
                f.write(text.replace(old, new, 1))
            return f"edited {path}", False, rec
        if name == "Bash":
            command = str(args.get("command", ""))
            rec["command"] = command[:200]
            bad = denied(command)
            if bad:
                return f"refused: {bad} is not allowed (no network, no installs)", True, rec
            left = deadline - time.time()
            if left <= 1:
                return "refused: the wall-time cap has been reached", True, rec
            try:
                p = subprocess.run(["bash", "-c", command], cwd=root, capture_output=True, text=True,
                                   timeout=min(BASH_TIMEOUT_S, left), stdin=subprocess.DEVNULL)
            except subprocess.TimeoutExpired as e:
                out = (e.stdout or "") if isinstance(e.stdout, str) else (e.stdout or b"").decode(errors="replace")
                rec["exit_code"] = "timeout"
                return _cap(out + "\n[command timed out]"), True, rec
            rec["exit_code"] = p.returncode
            out = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
            return _cap(f"{out}\n[exit code {p.returncode}]"), p.returncode != 0, rec
        return f"unknown tool {name}", True, rec
    except (OSError, ValueError) as e:
        return f"{type(e).__name__}: {e}", True, rec


def upper_estimate(prompt_tokens, completion_tokens):
    return round(prompt_tokens / 1e6 * UPPER_RATES["input"] + completion_tokens / 1e6 * UPPER_RATES["output"], 6)


def _blocks(content):
    """Response content blocks as plain dicts, passed back unchanged (thinking blocks included)."""
    return [b.model_dump(exclude_none=True) if hasattr(b, "model_dump") else dict(b) for b in content]


def _client():
    import anthropic

    return anthropic.Anthropic(max_retries=2)


def _write(cfg, summary, tool_log):
    os.makedirs(cfg.agent_out, exist_ok=True)
    summary = redact(summary)
    with open(os.path.join(cfg.agent_out, "api_tools.jsonl"), "w") as f:
        for rec in tool_log:
            f.write(json.dumps(redact(rec)) + "\n")
    with open(os.path.join(cfg.agent_out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    write_ledger(cfg, summary)
    return summary


def run(cfg, client=None):
    t0 = time.time()
    deadline = t0 + cfg.wall_s
    summary = {"provider": "anthropic", "requested_model": cfg.model or None, "model": cfg.model or None,
               "harness": "apiloop", "seed": cfg.seed or None, "switches": cfg.switches(),
               "cost_usd": None, "cost_unreported_calls": 0, "api_cost_estimate_usd": 0.0, "guard_estimate_usd": 0.0,
               "prompt_tokens": 0, "completion_tokens": 0, "cache_read_tokens": 0, "cache_write_tokens": 0,
               "llm_calls": 0, "tool_calls": 0, "turns": 0, "kept": "", "network_flags": [],
               "effort": EFFORT, "cc_profile": "apiloop", "cc_tools": ";".join(t["name"] for t in TOOLS),
               "cc_skills_n": 0, "cc_mcp_n": 0, "cc_model": cfg.model or "",
               "cc_prompt_sha256": hashlib.sha256(SYSTEM.encode()).hexdigest()}
    tool_log = []
    if client is None and not os.environ.get("ANTHROPIC_API_KEY"):
        summary.update(stop_reason="error", error="ANTHROPIC_API_KEY is not set", wall_time_s=0)
        return _write(cfg, summary, tool_log)
    if cfg.ledger_dir and cfg.run_budget_usd is not None and os.path.isdir(cfg.ledger_dir) \
            and ledger_totals(cfg.ledger_dir)[2] >= cfg.run_budget_usd:
        summary.update(stop_reason="run_budget_exhausted", wall_time_s=0)
        return _write(cfg, summary, tool_log)
    try:
        with open(os.path.join(cfg.root, "prompt.json")) as f:
            task = json.load(f).get("prompt", "")
    except (OSError, ValueError) as e:
        summary.update(stop_reason="no_task", error=str(e), wall_time_s=0)
        return _write(cfg, summary, tool_log)
    summary["visible_top_level"] = sorted(os.listdir(cfg.root))
    client = client or _client()
    messages = [{"role": "user", "content": PROMPT.format(task=task)}]
    stop, models, bash = None, set(), []
    while stop is None:
        if summary["llm_calls"] >= cfg.max_rounds:
            stop = "max_turns"
            break
        left = deadline - time.time()
        if left <= 5:
            stop = "wall_time"
            break
        try:
            r = client.messages.create(
                model=cfg.model, max_tokens=MAX_TOKENS, system=SYSTEM, messages=messages, tools=TOOLS,
                thinking={"type": "adaptive"}, output_config={"effort": EFFORT},
                cache_control={"type": "ephemeral"}, timeout=max(5.0, left - 2))
        except Exception as e:  # the SDK has retried; whatever is on disk is scored
            summary["error"] = redact(f"{type(e).__name__}: {e}")[-2000:]
            stop = "rate_limited" if type(e).__name__ == "RateLimitError" else "llm_error"
            break
        summary["llm_calls"] += 1
        u = r.usage
        fresh = int(getattr(u, "input_tokens", 0) or 0)
        cread = int(getattr(u, "cache_read_input_tokens", 0) or 0)
        cwrite = int(getattr(u, "cache_creation_input_tokens", 0) or 0)
        summary["prompt_tokens"] += fresh + cread + cwrite
        summary["cache_read_tokens"] += cread
        summary["cache_write_tokens"] += cwrite
        summary["completion_tokens"] += int(getattr(u, "output_tokens", 0) or 0)
        if getattr(r, "model", None):
            models.add(r.model)
        messages.append({"role": "assistant", "content": _blocks(r.content)})
        uses = [b for b in r.content if getattr(b, "type", None) == "tool_use"]
        if r.stop_reason == "refusal":
            stop = "refusal"
            break
        if r.stop_reason == "max_tokens" and not uses:
            stop = "llm_error"
            summary["error"] = "reply cut at max_tokens"
            break
        if not uses:
            text = " ".join(getattr(b, "text", "") for b in r.content if getattr(b, "type", None) == "text")
            stop = "give_up" if "GIVE_UP" in text.upper() else "submit"
            break
        results = []
        for b in uses:
            args = b.input if isinstance(b.input, dict) else {}
            out, is_err, rec = run_tool(cfg.root, b.name, args, deadline)
            rec.update(turn=summary["llm_calls"], is_error=is_err, output_chars=len(out))
            tool_log.append(rec)
            summary["tool_calls"] += 1
            if b.name == "Bash":
                bash.append(str(args.get("command", "")))
            results.append({"type": "tool_result", "tool_use_id": b.id, "content": out, "is_error": is_err})
        messages.append({"role": "user", "content": results})
    est = upper_estimate(summary["prompt_tokens"], summary["completion_tokens"])
    summary.update(model="+".join(sorted(models)) or cfg.model or None, turns=summary["llm_calls"],
                   api_cost_estimate_usd=est, guard_estimate_usd=est, stop_reason=stop,
                   network_flags=[c[:200] for c in bash if NETWORK.search(c)],
                   wall_time_s=round(time.time() - t0, 1))
    return _write(cfg, summary, tool_log)

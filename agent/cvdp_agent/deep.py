"""The Deep Agents harness (M3b, `CVDP_HARNESS=deepagents`): LangGraph's Deep Agents (`deepagents`) driving the same
model, provider code, stop rules, cost accounting, trace and summary as the LangGraph agent in graph.py.

What is shared with graph.py, unchanged: `Runtime` (every model call goes through `Runtime.call`, so the hard
deadline, the reasoning field and its fallback, per-call provider-reported cost, unreported-cost handling, the
in-flight checkpoint and the trace are the same), the `Checker` (compile, lint, synth, the agent's own testbench),
the `FileTool` path policy (writes only under rtl/, verif/, docs/ and the scratch rundir/agent_tb/), the best-edit
rule and `finish()` (summary, ledger entry, exit 0).

What Deep Agents adds, and what is on:
- its agent loop (model -> tool calls -> model ...), with its own system prompt assembly: ON;
- the planning tool `write_todos` (TodoListMiddleware): ON;
- its file tools (ls, read_file, write_file, edit_file, glob, grep), here backed by the real task tree through
  the FileTool policy, so they are the agent's existing file read/write, not a virtual file system: ON;
  large-result eviction to its virtual file system: OFF (check output is already cut to 2,500 characters);
- `execute` (shell): OFF (not offered);
- sub-agents (`task`): OFF (the general-purpose sub-agent is disabled), so every model call is the main agent's;
- conversation summarization (SummarizationMiddleware, part of its base stack): as shipped; a summarizing call
  goes through the same model and is counted as a round.

Caps: the $ budget and the wall-time cap are the LangGraph agent's (`Runtime.llm_cap`). The turn cap becomes a cap
on model calls (tool-call rounds), `cfg.max_rounds` = 22: the most LLM calls any M2 problem made in 10 turns.
That one row is DeepSeek on x86, AES_encryption_decryption_0005: 1 plan + 10 edits + 10 reflects = 21, plus one
reflect-parse retry. For openai/gpt-6-luna, the M3b model, M2's maximum is 21. Hitting it stops the problem with
stop_reason `max_turns`, so the results tools read it as they always have. `turns` in the summary counts rounds.
"""
import json
import os

from . import checks as checks_mod
from . import prompts
from .files import TEXT_EXT, PathRefused
from .graph import Runtime, allowed_check, finish, run_budget_exhausted
from .llm import LOWER
from .trace import truncate

ROUND_MESSAGE = """Your last reply was empty. Continue: call a tool, or, if you are done, reply with a one-line
summary and no tool call (or GIVE_UP if you cannot make progress)."""

TASK = """# Task
{task}

# Files under /code
{listing}

# File contents
{contents}

# How to work
Edit the design with the file tools (paths under /rtl, /verif or /docs; a scratch testbench under
/rundir/agent_tb, never submitted). Check your work with `run_checks`, which always compiles rtl/ and can also run:
{check_options}. To run your own testbench, write it first, then pass its path and top module to `run_checks`.
{tb_instructions}
When the design is done and your checks pass, reply with a one-line summary and no tool call: that submits.
If you cannot make progress, reply GIVE_UP."""


def _to_dicts(messages):
    """LangChain messages -> the OpenAI chat format Runtime.call sends."""
    out = []
    for m in messages:
        kind = m.type
        content = m.content if isinstance(m.content, str) else "".join(
            c.get("text", "") for c in m.content if isinstance(c, dict))
        if kind == "system":
            out.append({"role": "system", "content": content})
        elif kind == "human":
            out.append({"role": "user", "content": content})
        elif kind == "ai":
            d = {"role": "assistant", "content": content}
            if getattr(m, "tool_calls", None):
                d["tool_calls"] = [{"id": c["id"], "type": "function",
                                    "function": {"name": c["name"], "arguments": json.dumps(c.get("args") or {})}}
                                   for c in m.tool_calls]
            out.append(d)
        elif kind == "tool":
            out.append({"role": "tool", "tool_call_id": m.tool_call_id, "content": content})
    return out


def make_model(rt):
    """A LangChain chat model whose every call is `rt.call` (or a cap stop). Defined in a function so the
    LangChain imports happen only for this harness."""
    from typing import Any

    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import AIMessage
    from langchain_core.outputs import ChatGeneration, ChatResult
    from langchain_core.utils.function_calling import convert_to_openai_tool

    class CvdpChatModel(BaseChatModel):
        tools_: list = []
        runtime: Any = None

        @property
        def _llm_type(self):
            return "cvdp"

        def _get_ls_params(self, stop=None, **kw):  # deepagents picks its harness profile by this provider name
            params = super()._get_ls_params(stop=stop, **kw)
            params["ls_provider"] = "cvdp"
            return params

        def bind_tools(self, tools, **kw):
            return self.model_copy(update={"tools_": [convert_to_openai_tool(t) for t in tools]})

        def _stop(self, reason):
            self.runtime.stop_reason = reason
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=""))])

        def _generate(self, messages, stop=None, run_manager=None, **kw):
            rt = self.runtime
            cap = rt.llm_cap() or ("max_turns" if rt.rounds >= rt.cfg.max_rounds else None)
            if cap:
                return self._stop(cap)
            msgs = _to_dicts(messages)
            state = {"turn": rt.rounds + 1}
            rt.rounds += 1
            r = rt.call("agent", msgs, state, tools=self.tools_ or None)
            if r is None:
                return self._stop("llm_error")
            r.empty = not r.tool_calls and not (r.text or "").strip()
            if r.empty:  # the same one retry as the LangGraph agent: reasoning one step lower, a short nudge
                rt.empty_replies += 1
                if not rt.llm_cap() and rt.rounds < rt.cfg.max_rounds:
                    rt.log_llm("agent", r, state, decision="empty")
                    rt.empty_retries += 1
                    rt.rounds += 1
                    r2 = rt.call("agent", msgs + [{"role": "user", "content": ROUND_MESSAGE}], state,
                                 reasoning=LOWER.get(r.reasoning, "low"), retry_of=r.call_id,
                                 tools=self.tools_ or None)
                    if r2 is None:
                        return self._stop("llm_error")
                    r2.empty = not r2.tool_calls and not (r2.text or "").strip()
                    rt.empty_replies += int(r2.empty)
                    r = r2
            calls = r.tool_calls or []
            rt.log_llm("agent", r, state, decision={"tools": [c["name"] for c in calls]} if calls else
                       ("give_up" if "GIVE_UP" in (r.text or "").upper().replace(" ", "_") else "submit"))
            msg = AIMessage(content=r.text or "", tool_calls=[{"name": c["name"], "args": c["args"], "id": c["id"]}
                                                               for c in calls])
            return ChatResult(generations=[ChatGeneration(message=msg)])

    return CvdpChatModel(runtime=rt)


def make_backend(rt):
    """Deep Agents' file tools on the real task tree, with the FileTool's write policy."""
    from deepagents.backends import FilesystemBackend
    from deepagents.backends.protocol import EditResult, WriteResult

    class CvdpBackend(FilesystemBackend):
        def _note(self, rel, ok, err=""):
            rt.tracer.log("tool", check="file_write", command=f"write {rel}", exit_code=0 if ok else 1,
                          output=err or None, turn=rt.rounds)
            if ok and not rel.startswith("rundir/"):
                rt.edited = True
                rt.changed_all.add(rel)
                rt.checked = False

        def _policy(self, file_path):
            rel = file_path.lstrip("/")
            try:
                return rt.files.resolve_edit(rel)[1], "edit"
            except PathRefused:
                return rt.files.resolve_tb(rel)[1], "tb"  # raises PathRefused if outside both

        def write(self, file_path, content):
            try:
                rel, kind = self._policy(file_path)
                rel = rt.files.write(rel, content) if kind == "edit" else rt.files.write_tb(rel, content)
            except Exception as e:  # refused path or I/O: reported to the model, as in the LangGraph agent
                self._note(file_path, False, f"{type(e).__name__}: {e}")
                return WriteResult(error=f"{type(e).__name__}: {e}")
            self._note(rel, True)
            return WriteResult(path=file_path)

        def edit(self, file_path, old_string, new_string, replace_all=False):
            try:
                rel, _ = self._policy(file_path)
            except PathRefused as e:
                self._note(file_path, False, str(e))
                return EditResult(error=f"PathRefused: {e}")
            res = super().edit(file_path, old_string, new_string, replace_all)
            self._note(rel, not res.error, res.error or "")
            return res

        def delete(self, file_path):
            from deepagents.backends.protocol import DeleteResult

            return DeleteResult(error="deleting files is not allowed")

    return CvdpBackend(root_dir=rt.cfg.root, virtual_mode=True)


def make_tools(rt):
    from langchain_core.tools import tool

    @tool
    def run_checks(checks: list[str] | None = None, testbench: str = "", top: str = "") -> str:
        """Run the checks on the design under rtl/. Compile always runs. `checks` may add lint, synth and testbench.
        For `testbench`, give the path of a testbench you wrote under /rundir/agent_tb (or one under /verif) and its
        top module (for a cocotb test, the design's top module)."""
        names = [c.strip().lower() for c in (checks or []) if c]
        requested = [c for c in names if allowed_check(c, rt.cfg)]
        tb = None
        if testbench and rt.cfg.self_check:
            rel = testbench.lstrip("/")
            try:
                full, rel = rt.files.resolve_edit(rel) if rel.startswith("verif/") else rt.files.resolve_tb(rel)
                if not os.path.isfile(full):
                    raise PathRefused(f"{testbench}: no such file")
                tb = {"files": [rel], "top": top}
                if "testbench" not in requested:
                    requested.append("testbench")
            except PathRefused as e:
                return f"testbench refused: {e}"
        results = rt.checker.run(requested, tb)
        compiled = results.get("compile", {}).get("ok")
        rt.last_compiled, rt.checked = compiled, True
        if compiled:
            rt.best, rt.best_turn = rt.files.snapshot(), rt.rounds
        return checks_mod.render(results)

    return [run_checks]


def run(cfg, llm, tracer, **kw):
    from deepagents import FilesystemMiddleware, HarnessProfile, create_deep_agent, register_harness_profile
    from deepagents.profiles.harness.harness_profiles import GeneralPurposeSubagentProfile
    from langchain.agents.middleware import TodoListMiddleware

    rt = Runtime(cfg, llm, tracer=tracer, **kw)
    rt.rounds, rt.last_compiled, rt.checked = 0, None, True
    rt.summary_extra.update({"harness": "deepagents", "max_rounds": cfg.max_rounds})
    rt.tracer.log("start", model=cfg.model or None, provider=cfg.provider, seed=cfg.seed or None,
                  switches=cfg.switches())
    state = {"turn": 0}
    try:
        path = os.path.join(cfg.root, "prompt.json")
        try:
            with open(path) as f:
                task = json.load(f).get("prompt", "")
        except (OSError, json.JSONDecodeError) as e:
            rt.tracer.log("tool", check="read_task", command=f"read {path}", exit_code=1, output=str(e))
            return _done(rt, {"turn": 0, "stop_reason": "no_task"})
        listing = rt.files.list_files()
        rt.tracer.log("tool", check="read_task", command="list /code", exit_code=0,
                      output=truncate("\n".join(listing), 3000), tools=rt.tools)
        if run_budget_exhausted(cfg, rt.tracer):
            return _done(rt, {"turn": 0, "stop_reason": "run_budget_exhausted"})
        msg = TASK.format(task=task, listing="\n".join(listing), contents=rt.contents(),
                          check_options=prompts.check_options(cfg, rt.tools),
                          tb_instructions="" if cfg.self_check else "Do not write a testbench.")
        msg += rt.lessons_block(task)
        register_harness_profile("cvdp", HarnessProfile(
            general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False)))
        agent = create_deep_agent(
            model=make_model(rt), tools=make_tools(rt), system_prompt=prompts.SYSTEM,
            middleware=[TodoListMiddleware(),
                        FilesystemMiddleware(backend=make_backend(rt),
                                             tools=["ls", "read_file", "write_file", "edit_file", "glob", "grep"],
                                             tool_token_limit_before_evict=None)])
        out = agent.invoke({"messages": [{"role": "user", "content": msg}]},
                           {"recursion_limit": 4 * cfg.max_rounds + 20})
        last = out["messages"][-1] if out.get("messages") else None
        text = (last.content if last is not None and isinstance(last.content, str) else "") or ""
        stop = rt.stop_reason or ("give_up" if "GIVE_UP" in text.upper().replace(" ", "_") else "submit")
        return _done(rt, {"turn": rt.rounds, "stop_reason": stop, "decision": stop,
                          "compiled": rt.last_compiled, "checked": rt.checked})
    except Exception as e:
        import traceback

        from .trace import redact

        rt.tracer.log("error", error=truncate(redact(f"{type(e).__name__}: {e}\n{traceback.format_exc()}"), 4000))
        finish(rt, {"turn": rt.rounds, "compiled": rt.last_compiled, "checked": rt.checked},
               error=f"{type(e).__name__}: {e}")
        return _read(cfg)


def _done(rt, state):
    finish(rt, state)
    return _read(rt.cfg)


def _read(cfg):
    with open(os.path.join(cfg.agent_out, "summary.json")) as f:
        return json.load(f)


__all__ = ["run", "TEXT_EXT"]

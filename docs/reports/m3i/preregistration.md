# M3i pre-registration: how much of Claude Code is the harness?

Written on 2026-11-02, on the branch `m3i-plain` (from `m3h-cc-skills`), before any scored dispatch. Nothing here may
change after the first scored dispatch. Anything learned later goes in the report, marked as such.

## The question

M3e found Claude Code with Opus no better than our LangGraph agent with Opus. M3i strips Claude Code down to "the
model plus a minimal tool loop", holding the model fixed, and measures what Claude Code's default system prompt, its
full tool set and its defaults add. **Does the plain profile do worse (or better) than Claude Code as it ships?**

## Arms

Both arms: `harness=claudecode`, model `claude-haiku-5-5`, Claude Code **2.1.310** (M3h's pin, the agent image's
`CLAUDE_CODE_VERSION`), 60 turns at most, 480 s wall cap, no skill pack, `ubuntu-24.04-arm`, 4 threads.

| Arm | What | Sweep input |
|---|---|---|
| D (default) | M3h's arm A, as it ran: Claude Code's own system prompt and 24 tools, the user's usual settings loading, 19 bundled skills offered. **Not rerun.** The three held-out arm-A CSVs of M3h are reused (`m3h/runs/heldout_A{1,2,3}_*.csv`). | `cc_profile=default` |
| P (plain) | `claude -p` with **our LangGraph agent's system prompt** in place of Claude Code's, only Read, Write, Edit and Bash, no settings, CLAUDE.md, skills, MCP or hooks. The user message is D's, unchanged. | `cc_profile=plain` |

The user message is the same text in both arms (`claude_code.PROMPT`: the task and the rules about where files may
change, the installed tools and no network). So P − D is the effect of Claude Code's system prompt, its tool set
and its default customisation, not of the task wording.

## The plain profile

### The prompt

The system prompt is `cvdp_agent.prompts.SYSTEM`, the LangGraph agent's own text. The Claude Code harness imports it
from the agent code when it builds the command, so it cannot drift from the agent. Its sha256 is written to every
CSV row (`cc_prompt_sha256`).

- **sha256 at this pre-registration:** `e45ea1e3b3ca60c5a33169cce203a8b0e57e578d832e3577e23a4caad49019bd` (481 bytes).
- It names `/code`, the directories that may be changed, the scratch testbench directory and that the grader's tests
  are hidden. It does not mention Claude Code's tools by name (it says "the tools offered").

### The command line

Flags were read from `claude --help` of **2.1.310** (installed from npm into a scratch directory) and tried against
a local capture server that logs the request body (no model call, no spend). The command, with the task text elided:

```
claude -p <PROMPT with the task> --output-format stream-json --verbose --max-turns 60 --permission-mode acceptEdits
  --system-prompt <SYSTEM> --tools Read,Write,Edit,Bash
  --allowedTools Read Write Edit Bash
  --disallowedTools "Bash(curl:*)" "Bash(wget:*)" "Bash(git:*)" "Bash(pip:*)" "Bash(pip3:*)" "Bash(uv:*)"
                    "Bash(npm:*)" "Bash(npx:*)" "Bash(ssh:*)" "Bash(nc:*)"
  --setting-sources "" --strict-mcp-config --mcp-config '{"mcpServers":{}}'
  --disable-slash-commands --safe-mode --model claude-haiku-5-5
```

with the environment `HOME=<fresh empty temp dir>` and `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`. `CLAUDE_CONFIG_DIR` is
removed. The working directory is the task tree, as in D. The token reaches Claude Code as
`CLAUDE_CODE_OAUTH_TOKEN`, as in D.

| Flag | What it does (2.1.310 help text) | Checked |
|---|---|---|
| `--system-prompt` | Replaces Claude Code's system prompt. (`--append-system-prompt` would add to it, so it is not used.) | Request body: the system blocks are two fixed lines plus our text. |
| `--tools Read,Write,Edit,Bash` | Limits the tool set itself ("specify the list of available tools from the built-in set"). | `init` event: exactly those four, against 24 in D. |
| `--allowedTools`, `--disallowedTools` | Permissions. The Bash patterns are D's network rules, kept so both arms deny the same commands. D's other denials (WebFetch, WebSearch, Task, NotebookEdit) are not needed: those tools are not offered. | Same lists as D, minus the tools P does not have. |
| `--setting-sources ""` | Loads no user, project or local settings. | Accepted (empty string). |
| `--strict-mcp-config` + empty `--mcp-config` | No MCP server from any source. | `init`: `mcp_servers` is empty. |
| `--disable-slash-commands` | "Disable all skills and commands." | `init`: skills 0 (against 19), slash commands 0 (against 49). `--safe-mode` alone leaves the 19. |
| `--safe-mode` | Starts with CLAUDE.md, skills, plugins, hooks, MCP servers, custom agents, output styles and more disabled; auth, model and built-in tools work normally. | `init`: one custom-agent entry fewer. |
| empty `HOME`, `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` | No user settings, user skills or user CLAUDE.md can exist; auto-memory is off. | The test checks HOME is empty and outside the task tree. |
| `--model claude-haiku-5-5` | The pinned model. | `init` event's `model`, written to `cc_model`. |

**`--bare` is not used.** Its help says Anthropic authentication is strictly `ANTHROPIC_API_KEY` or an
`apiKeyHelper` and that OAuth is never read, and this project runs on the plan's OAuth token. Each thing `--bare`
switches off is covered above by a separate flag, or is listed below.

### Evidence that the profile took effect

The `system`/`init` event is read as it arrives. For every plain problem-run the CSV has `cc_profile`, `cc_tools`
(`;` list), `cc_skills_n`, `cc_mcp_n`, `cc_model` and `cc_prompt_sha256`. If the init event lists any tool other than
the four, any MCP server or any skill, or there is no init event, the process is killed at once, the problem ends
with stop reason **`profile_error`**, and the row is **not a result**: `ablate.py`, `m3h_tables.py` and the failure
taxonomy treat it like a rate-limited row (left out, rerun with `tools/m3h_merge.py`). No file has been changed by
then, as the init event is the first thing Claude Code prints. The pull-request test suite checks this with a fake
`claude`.

The leak guard of M3h stays in the workflow. It is a no-op without a pack, and it still runs.

## Known differences from a bare API call

P is not "the API with four tools". Things that remain, found by reading the request body Claude Code sent to a local
capture server (2.1.310, with the flags above):

1. **System blocks.** Claude Code puts two fixed lines before our prompt: a billing/entrypoint header
   (`x-anthropic-billing-header: cc_version=2.1.310…; cc_entrypoint=sdk-cli;`) and "You are a Claude agent, built on
   Anthropic's Claude Agent SDK." Our text follows. They cannot be switched off with a documented flag.
2. **Environment block.** A system-role message after the task holds the working directory, "Is a git repository",
   the platform, the shell, the OS version, a paragraph on handling downloaded files, the model name and knowledge
   cutoff, a `total_tokens` budget line and today's date. D has these too. They are not switched off.
3. **Attribution reminder.** A `<system-reminder>` in the first user turn says how to write commit and pull-request
   attribution lines. It can be removed with the `attribution` setting; it is kept, so that the only differences
   from D are the ones listed here. D has it too.
4. **Tool definitions are Claude Code's.** Read, Write, Edit and Bash have Claude Code's own names, JSON schemas and
   descriptions (the Bash description is about 1.8 KB, with its own rules on commands). These cannot be replaced
   with a documented flag. They are the same text in D.
5. **A placeholder tool.** The request carries a fifth tool, `DeferredToolPlaceholder` ("Reserved placeholder that
   keeps deferred tool loading active; never call this tool", `defer_loading: true`). The `init` event does not list
   it. It cannot be removed with a documented flag.
6. **Request settings.** Adaptive thinking, a `context_management` clear-thinking edit and an effort setting. **Effort
   is not passed**: D did not pass it either, so both arms use Claude Code's default for this model. In the local
   capture the default was `medium`; the run on the plan cannot be observed from the event stream, so the effort
   actually used is recorded as "the default" and is not asserted. If the default differs between a Max-plan and a
   placeholder-token session it is the same difference in D and P.
7. **Agent definitions.** `init` still lists four built-in agent names (`--safe-mode` removes one of five). The
   Agent tool is not in the tool set, so they cannot be called.
8. **Built-in plugins.** Three built-in plugins (agents-md, telemetry, plugin-authoring) are listed in `init`. They
   add no tools.
9. **Auto-compaction, retries, the permission system and the 60-turn cap** are Claude Code's, as in D.
10. **Time.** D's three runs were made on 2026-10-31 and P's will be made later, on the plan, so the model's
    serving and the runner may differ slightly. Not controllable. D is not rerun, to save plan usage; the report
    states this confound beside every P − D number.
11. **Stop reason.** With our prompt the model is not told how to end ("stop with a one-line summary" is in the user
    message, as in D). A run that ends without a summary is still scored by what is on disk, as in D.

## Sets and runs

| Set | P runs | D runs |
|---|---|---|
| Held-out 100 (`split=m3g_heldout`, `tools/m3g_heldout_ids.txt`) | **3** | 3 (M3h's A1–A3, reused) |
| The 86 (`split=agentic`, the development set) | 1 | M3h phase 2's one A run (descriptive only) |

The planner dispatches the sweeps, one at a time, after the pull request of this branch is merged or chosen as the
base. P seeds are numbered 1–3 on the held-out set. Rate limits: a `rate_limited` or `profile_error` row was not
run and is rerun, up to 3 times (as in M3h). Plan usage is noted before and after each sweep.

## Primary and decision rule

**Primary: P − D on the held-out set,** paired by problem:

- each problem's pass rate over its 3 runs per arm, and the mean difference (`tools/ablate.py --base D --ids
  tools/m3g_heldout_ids.txt`);
- a paired bootstrap 95% interval over problems (2,000 resamples);
- an exact two-sided sign test on the problems that did better or worse (ties dropped), at α = 0.05. This is the
  exact McNemar test on the discordant problems, as in M3g and M3h.

Reading, as in M3g and M3h: the interval excludes zero and the effect is positive → P is **better**; excludes zero
and negative → P is **worse** (Claude Code's own prompt and tools add something); otherwise **no detectable effect**,
reporting the interval and the size of effect it rules out.

**Decision rule (as M3g and M3h).** A held-out difference counts as a **finding** only if the development set agrees
with its sign: P − D on the 86 must have the same sign, whatever its interval. A held-out difference with a
development-set effect at or below zero (for a gain), or at or above zero (for a loss), is reported as a held-out
result the development set does not support. A development-set difference on its own is not a finding. The 86 has
one P run against one D run and is descriptive only.

**Power, stated in advance.** M3h's held-out comparison of arms with 3 runs each had a realised 95% half-width of
about 4.0 points (standard error about 2.0). Arm D's three run totals were 57, 56 and 62 of 100, a spread of about
3 problems per run. P − D is the same design, so about:

- **80%** chance to detect a true difference of **5.7 points**;
- **50%** chance for **4.0 points**;
- **25%** chance for **2.6 points**.

A different agent configuration can have a different run-to-run spread; the report gives the realised half-width.
On the 86 with one run per arm the half-width is wider, about 9 points, so that comparison is descriptive.

## Secondary (descriptive)

- P − D on the 86, with the 79-problem view beside it.
- **Effort:** median and mean turns, median wall time, tokens (prompt including cache, and completion) per
  problem-run, the number of wall-cap stops, and the stop-reason mix.
- Tool-call mix (Bash, Read, Write, Edit counts per problem-run) from `claude_stream.jsonl`.
- The failure taxonomy per arm (`tools/taxonomy.py`).
- Nothing is billed per call on the plan. `cost_usd` stays unreported; `plan_cost_estimate_usd` is Claude Code's own
  API-rate figure, shown apart, as a guide to plan usage only.

## Spend

No OpenRouter spend at all. Neither Fable nor Opus is called. Plan usage for the build and smoke is in the report.

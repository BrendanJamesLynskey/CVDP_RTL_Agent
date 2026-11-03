# M3j pre-registration: lean Claude Code against a plain API loop

Written on 2026-11-03, on the branch `m3j-api` (from `main` a735175), before any scored dispatch. Nothing here may
change after the first scored dispatch. Anything learned later goes in the report, marked as such.

## The question

M3i stripped Claude Code to our system prompt and four tools (arm P, on the Claude Max plan) and found it no worse
than Claude Code as shipped, on 37% of the input tokens. But P is still Claude Code: two fixed system blocks, an
environment message, Claude Code's own tool schemas, a placeholder tool and Claude Code's loop stay in every request
(M3i pre-registration, "Known differences from a bare API call"). `--bare`, which strips more, needs an API key, and
M3i ran on the plan's OAuth token.

The owner's Max plan now includes a monthly Claude API credit ($100, claimed 2026-11-03, linked to the Console
organization the `ANTHROPIC_API_KEY` repository secret belongs to; it expires 2026-12-06). M3j spends it to ask:
**at a fixed model, does a plain Messages API loop with our prompt and four tools of our own do worse (or better)
than lean Claude Code?** And, as secondaries, what `--bare` changes, and whether billing to the API key instead of
the plan changes the plan arm's result.

## Arms

Every arm: model `claude-haiku-5-5` (Anthropic Claude Haiku 5.5), 60 model turns at most, 480 s wall cap (harness
kill 600 s), our LangGraph agent's system prompt (`prompts.SYSTEM`, sha256 `e45ea1e3…`, recorded per row as
`cc_prompt_sha256`), the same user message (`claude_code.PROMPT` with the task), `ubuntu-24.04-arm`, 4 threads.

| Arm | What | Billing | Sweep input |
|---|---|---|---|
| P (reused) | M3i's plain profile, as it ran: Claude Code 2.1.310, `--system-prompt`, `--tools Read,Write,Edit,Bash`, no settings, skills, MCP or auto-memory. **Not rerun**: M3i's three held-out P CSVs (`m3i/runs/heldout_P*`) and its one dev-86 P run. | plan (OAuth) | `harness=claudecode cc_profile=plain` |
| PA | P exactly, billed to the API key instead of the plan. | API key | `harness=claudecode cc_profile=plain claude_endpoint=api` |
| B | PA plus `--bare`. | API key | `harness=claudecode cc_profile=bare claude_endpoint=api` |
| R | No Claude Code: `cvdp_agent/apiloop.py`, the Anthropic Messages API (`anthropic` 2.3.0) in a loop of our own, with four tools of our own. | API key | `harness=apiloop` |

### What each arm sends (from a local capture)

Read from the request bodies that Claude Code 2.1.310 sent to a local capture server with a placeholder key (no model
call, no spend; `tools/capture_requests.py`, output in `capture/plain.json` and `capture/bare.json`). R's request is
built by our code; its fields are checked by a unit test on the recorded request.

| | P and PA (plain) | B (plain + `--bare`) | R (apiloop) |
|---|---|---|---|
| System blocks | 3: billing header (74 chars), "You are a Claude agent, built on Anthropic's Claude Agent SDK." (62), our prompt (481) | the same 3 | 1: our prompt |
| Tools offered | Bash 3,628 B, Edit 1,006 B, Read 1,975 B, Write 663 B, `DeferredToolPlaceholder` 214 B (7,486 B in all) | **Bash 1,616 B, Edit 666 B, Read 1,200 B: no Write, no placeholder** (3,482 B) | Read, Write, Edit, Bash: our one-line descriptions and minimal schemas (about 1 KB in all) |
| First user turn | attribution `<system-reminder>` (581 chars) + the task (552) | the task only | the task only |
| Environment message | a system-role message (902 chars: directory, git, platform, shell, OS, model, cutoff, token budget, date) | none (empty) | none |
| Thinking | adaptive, `display: updates` | the same | adaptive (display left at its default) |
| Effort | `medium` (Claude Code's default for this model) | `medium` | `medium` |
| Context management | `clear_thinking_20251015`, `keep: all` | the same | none |
| `max_tokens` | 128,000 | 128,000 | 32,000 |
| Prompt caching | Claude Code's | Claude Code's | automatic (`cache_control` at the top level) |
| Loop | Claude Code's: permissions, retries, auto-compaction, 60 turns | the same | ours: 60 calls, 480 s, SDK retries (2), no compaction |
| `init` event | tools Bash, Edit, Read, Write; `apiKeySource` checked (PA) | tools Bash, Edit, Read; `apiKeySource` checked | none |

`--bare` dropping the Write tool is Claude Code's behaviour under `CLAUDE_CODE_SIMPLE`, not ours: `--tools` still
names four. B can create files with Edit or Bash. This is part of what B measures.

### R's tools and rules

- Read (numbered lines, at most 2,000), Write (replace or create), Edit (one exact, unique match), Bash (in `/code`,
  2-minute timeout per command, as Claude Code's default). Results over 30,000 characters are cut.
- File tools refuse any path outside the task tree. Bash refuses `curl`, `wget`, `git`, `pip`, `pip3`, `uv`, `npm`,
  `npx`, `ssh` and `nc` at the start of any part of a command line: the same programs the Claude Code arms deny.
  Every Bash command is audited afterwards for network use (`network_flags`), as in the Claude Code arms.
- Thinking blocks are passed back unchanged. A `refusal` stop ends the problem (stop reason `refusal`, scored as it
  stands). A `RateLimitError` after the SDK's retries is `rate_limited`: not run, rerun.

### Evidence that each arm is what it says

- PA and B: Claude Code's `init` event is read as it arrives. A tool set other than the arm's (four for PA, three for
  B), any MCP server, any skill, or **an `apiKeySource` other than `ANTHROPIC_API_KEY`** kills the run before the
  model acts: stop reason `profile_error`, not a result, rerun. `cc_api_key_source` is written to every row.
- The key reaches only these arms. The workflow passes `ANTHROPIC_API_KEY` to the Run step only for `harness=apiloop`
  or `claude_endpoint=api`; `sweep.sh` forwards it into the agent's container only for those providers; and
  `claude_code.py` removes it from every plan arm's environment (Claude Code prefers the key to the plan's token).
  Each of the three is under test (`tests/test_m3j.py`). The upload's secret scan also checks for the key.

## Sets and runs

| Set | PA | B | R | P |
|---|---|---|---|---|
| Held-out 100 (`split=m3g_heldout`) | 3 | 3 | 3 | 3 (M3i, reused) |
| The 86 (`split=agentic`) | 1 | 1 | 1 | 1 (M3i, reused; descriptive only) |

Seeds 1–3 on the held-out set, 1 on the 86. One sweep at a time. Before the scored sweeps, a smoke run of each arm
on `m3g_smoke` (3 problems, 1 seed) checks the plumbing (init events, `apiKeySource`, the CSV columns, R's
transcript skeleton); smoke rows are not results. A `rate_limited` or `profile_error` row is rerun, up to 3 times.

## Primary and decision rule

**Primary: R − PA on the held-out set,** paired by problem, as in M3i:

- each problem's pass rate over its 3 runs per arm, and the mean difference (`tools/ablate.py`);
- a paired bootstrap 95% interval over problems (2,000 resamples);
- an exact two-sided sign test on the problems that did better or worse (ties dropped), α = 0.05.

R is **worse** if the interval lies wholly below zero, **better** if wholly above, and otherwise there is **no
detectable effect**, reported with the interval's ends as the largest loss and gain it leaves open. The sign test is
reported beside it and does not decide. The 86 is reported beside it, descriptively.

PA and R share the billing route and the dispatch period, so R − PA is the effect of replacing Claude Code (its fixed
blocks, environment message, tool schemas, placeholder tool, request settings and loop) with our plain loop. It is
not the effect of any one of those parts.

**Secondaries** (exploratory; no correction; each reported with its interval):

1. B − PA: what `--bare` changes (fewer and shorter tools, no Write, no environment message, no attribution
   reminder), at the same billing.
2. PA − P: plan against API key for the same command line. It is confounded with time (P ran on 2 November), so a
   difference cannot be put down to billing alone.
3. R − D, with D as M3i's arm D (Claude Code as shipped, M3h's arm A): stock Claude Code against the plain loop.
   Different billing and dates, so descriptive only.
4. Input tokens (including cache) per problem-run, turns, wall time, and stop reasons, per arm.

## Cost and the guard

These arms are billed to the API key's credit, not the plan. The API reports tokens, not cost:

- `cost_usd` stays blank, with no unreported calls (nothing is estimated as a cost).
- PA and B record Claude Code's own figure at API rates (`plan_cost_estimate_usd`). R records an upper bound from its
  tokens at Claude Haiku 5.5's long-context list rates ($0.50 per million input tokens, cached or not; $2.50 per
  million output; `api_cost_estimate_usd`). Each is charged to the whole-run guard (`guard_estimate_usd`), never
  reported as spend. A Claude Code run whose stream was cut is charged the per-problem budget ($0.10).
- Guards: `run_budget_usd` 8 for each PA or B held-out dispatch (300 problem-runs) and 4 for each dev-86 one; 15 and
  5 for R's (its charge is an upper bound).
- The money actually spent is the Console's: the owner reads the organization's credit balance before the first
  sweep and after the last, and the report gives that figure.

Expected spend, from M3i's P token counts (61,805 input tokens per held-out problem-run, most of them cached): a few
dollars for all of M3j; the guards cap it at $60 even if every charge were at the upper bound.

## What it cannot show

- One model (Claude Haiku 5.5), one Claude Code version (2.1.310), one benchmark.
- R's tool descriptions and loop are ours. A different minimal loop (other descriptions, Anthropic's own
  `bash`/`text_editor` tools, compaction) could score differently. R − PA is "this plain loop", not "any".
- With 3 runs on 100 problems the resolution is about ±4 points, as in M3i. A smaller effect reads as no detectable
  effect.

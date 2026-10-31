# M3h pre-registration: the knowledge pack as Claude Code's own skills, with Haiku 5.5

Written on 2026-10-31, on the branch `m3h-cc-skills`, before any scored dispatch. Nothing here may change after the
first scored dispatch. Anything learned later goes in the report, marked as such.

**Amended on 2026-10-31, after the smoke runs and before any scored dispatch, with the owner's approval.** In the
smoke runs Haiku loaded a pack skill in 0 of 12 problem-runs without the hint, and in 3 of 3 with it. So the arms
without the hint would mostly measure "the pack is not used". The owner's question is what the pack does when it is
used. So the scored pack arms now all carry the one-line hint (S1c, S2c). One unhinted S2 run on the held-out set is
kept to measure the unprompted load rate, as a descriptive figure. The old conditional S2c rule is removed. The first
version of this file is in commit `4cd735c`. Nothing else changed: the mechanism, the sets, the rate-limit rule, the
statistics and the decision rule are as written there.

## The question

M3g put pack v1 into luna's prompts and found no effect, but it could not show that luna acted on the pack. Claude
Code has native skills. Each installed skill is listed to the model by its name and description, and the model
loads a skill's body only when it chooses to, with a `Skill` tool call that shows in the event stream. So M3h asks
two questions: **does Claude Code with Haiku 5.5 use the pack when it is installed as skills, and does using it help?**

## The pack

The pack is the private repository `RTL_Knowledge_Pack`. This public repository holds only its tags and hashes,
never its text.

| Tag | Commit | `generic/MANIFEST.sha256` SHA-256 | Skills |
|---|---|---|---|
| `v1.0` | `b30b32914532b1631a37e160200ebeb815a9bdf6` | `7ba7b4b39c1a3238e58eec963eb359d64b521305937fd5318eade79faa45285b` | 15 |
| `v2.0` | `19ac3ec485e8b14850f59c89e6244063e9dd81a4` | `e405fe319fcc3392a415c0911ecc20eb5a90093a1d27b1076e92593e6b9a3298` | 25 |

The 15 skills of `v1.0` are M3g's pack, byte for byte. Their manifest lines are the same as in M3g's manifest
`e6ca1610…`, which also lists a provenance file. `v2.0` adds 10 skills. Four are about the kind of task:
`working-in-existing-code`, `minimal-change-modification`, `rtl-debugging` and `module-integration`. Six are about
domains: `block-ciphers-in-hardware`, `fixed-point-and-dsp-datapaths`, `crc-lfsr-and-line-codes`,
`serial-and-network-protocols`, `caches-and-memory-systems` and `hardware-algorithms`. `v2.0` also has a new
index.

The pins are in [`agent/cvdp_agent/native_skills.py`](../../../agent/cvdp_agent/native_skills.py) (`PINNED`).

1. **Before any model call,** the workflow checks out the pack at its tag into `_pack/`, outside `work/`, using the
   deploy key `RTL_PACK_DEPLOY_KEY`.
2. `tools/skill_pack.py` then checks three things: the checkout's commit, every file against the manifest (no other
   `.md` file may be present), and the manifest's own hash.
3. The agent checks the manifest again inside its container. A pack that differs stops the problem with
   `skills_error` before Claude Code starts.
4. If the deploy key is missing, a pack arm fails before the run.

## The mechanism

- **Install.** Each skill is written as `<HOME>/.claude/skills/<name>/SKILL.md`, in a fresh HOME inside the
  agent's container. That HOME is outside the task tree `/code`, so a skill never appears in
  `agent_changes.patch`, `agent_out` or `agent_tb`.
  - Each file starts with YAML front matter: `name`, and `description` taken from that skill's line in `INDEX.md`.
  - The skill file's bytes follow, unchanged. A test checks every body against its source file.
  - Claude Code 2.1.310 reads user skills from `~/.claude/skills`. A run of the pinned binary with this HOME listed
    all 25 `v2.0` names in its `init` event, with `Skill` among its tools. In `-p` mode a `Skill` call ran without
    a permission rule, in a local check with a dummy skill.
  - Each arm runs the same command line (a test checks it). Only what is installed differs.
- **Recording.** Every `Skill` call is parsed from the event stream. It is written to `summary.json` and to the
  CSV as `skill_pack`, `skill_pack_sha`, `skills_installed`, `skills_listed`, `skills_loaded`, `skills_n` and
  `skill_first_turn`:
  - `skills_loaded` is every `Skill` call, in order, joined by `;`. It includes the names of Claude Code's bundled
    skills.
  - `skills_listed` is the number of pack skills in Claude Code's own `init` list of skills offered to the model.
  - `skills_n` is the number of distinct pack skills loaded.
  - `skill_first_turn` is the assistant turn of the first pack skill loaded, counting turns from 1.
- **The transcript.** In a pack arm the raw event stream holds the bodies of the skills loaded, so it is never
  written. `agent_out` gets `claude_tools.jsonl` instead: the turn and tool name of each call, and a Skill call's
  skill name. Arm A is unchanged and keeps its stream. Its `Skill` calls (bundled skills only) are counted from that
  stream with the same parser.
- **Leak guard.** Before the step summary, the per-problem rows in the log and the artifact upload,
  `tools/leak_guard.py` scans the whole work dir and the step summaries. It looks for any 80-byte window of any
  skill body or `INDEX.md` line, in raw bytes and again after normalising both sides (JSON escapes undone, diff
  markers dropped, white space collapsed).
  - A window that is also in the public dataset or harness checkout is not private text, so it is allowed.
  - Any other match fails the job, and nothing is uploaded.
- **The default is unchanged.** With `skill_pack` blank, the claudecode harness is byte-for-byte what it was. A
  golden fixture of its command line, environment, files and summary, written from `main` before M3h, checks this.
  The CSV header is the M3g header, also frozen. The M3h columns are added only when `skill_pack` is set.

## The arms

Settings common to all arms:

- `harness=claudecode`, model `claude-haiku-5-5`, Claude Code **2.1.310** (pinned in `docker/agent.Dockerfile`)
- 60 Claude Code turns at most (`CVDP_MAX_ROUNDS`, the ladder's), a 480 s wall cap, `ubuntu-24.04-arm`, 4 threads
- the agent image built from the last commit touching `agent/` or `docker/` on this branch
- harness `8e894cf`, dataset revision `5b807d9`

The ladder's other sweep inputs are kept as they were: `reasoning=low`, `budget_usd=0.10`, `max_turns=10`. All
three are labels only for this harness.

| Arm | Sweep inputs beyond the common ones | Skills installed | Runs |
|---|---|---|---|
| A | none | none (Claude Code's bundled skills only, as in every arm) | 3 held-out, 3 on the 86 |
| S1c | `skill_pack=v1.0`, `skill_hint=true` | the 15 of `v1.0`, plus the hint | 3 held-out, 3 on the 86 |
| S2c | `skill_pack=v2.0`, `skill_hint=true` | the 25 of `v2.0`, plus the hint | 3 held-out, 3 on the 86 |
| S2 | `skill_pack=v2.0` | the 25 of `v2.0`, no hint | 1 held-out (descriptive: the unprompted load rate) |

**The hint** is a user-level `CLAUDE.md`, in the same private HOME, with the one line "RTL design skills are
installed; check them before you start." **Caveat:** a hinted pack arm differs from A by the pack *and* this one
line. A has no hint, because with no skills installed the line would be false. So S1c − A and S2c − A measure "the
pack plus a nudge to use it", not the pack alone. S2c − S1c holds the hint fixed, and so isolates `v2.0`'s ten new
skills (and its new index).

## The problem sets and runs

- **Held-out set:** M3g's 100 frozen problems (`split=m3g_heldout`, `tools/m3g_heldout_ids.txt`, frozen in
  `943cef9`). They are built into the agentic format by `tools/m3g_heldout.py` and run with `--force-agentic`.
  - Claude Code reads the problem's `prompt.json` from `/code`, as on the agentic split. That prompt includes M3g's
    added sentence naming the output file.
  - The scores come from the benchmark's hidden tests, run outside the agent's container.
- **Development set:** M3b's 86 evaluation problems (`split=agentic`, `tools/m3b_eval_ids.txt`). The 79-problem
  view leaves out `tools/benchmark_limited_ids.txt`.
- **Runs:** as in the table above, dispatched one sweep at a time from one commit of `m3h-cc-skills`, with `seeds=1`
  and `seed_offset` 0, 1 and 2 (S2: `seed_offset` 0). That makes 10 held-out sweeps and 9 on the 86.
- **Order.** The held-out phase runs first, interleaved to spread drift over time: A1, S1c1, S2c1, A2, S1c2, S2c2,
  A3, S1c3, S2c3, then S2. The phase on the 86 runs after the weekly plan reset on 2026-11-02, in the same
  interleaved order without S2.
- Arm A is a fresh rerun on both sets. The ladder's one Haiku run on the 86 (2026-10-26) is shown for reference only.

## Rate limits

The plan's 5-hour and weekly limits stop a Claude Code session with HTTP 429 (`usage_limit_reached`) and a
`rate_limit_event` whose status is `rejected`. In the ladder such a problem ended as `llm_error` and was rerun by
hand. Now it ends as **`rate_limited`**, and the rule is:

- A rate-limited row was not run. `ablate.py` leaves it out and never counts it as a failure.
- After the limit resets, its problem is rerun in the same arm with the same seed number.
  `tools/m3h_merge.py` keeps, for each problem and seed, the first row that is not rate-limited.
- Only rate-limited rows are rerun. A failure, an `llm_error` of another kind or a wall-time stop is kept as it is.
- If a problem is still rate-limited after 3 reruns, it is left out of that run, and the report lists it.
- Sweeps run one at a time. Plan usage (`claude -p "/usage"`) is noted before and after each sweep.

## The comparisons

**Primary: S2c − A on the held-out set.** The test is paired over the 100 problems, computed with
`python3 tools/ablate.py --base A --ids tools/m3g_heldout_ids.txt --arm A=... --arm S2c=...`:

- each problem's pass rate over its 3 runs per arm, and the mean difference;
- a paired bootstrap 95% interval over problems (2,000 resamples);
- an exact two-sided sign test on the problems that did better or worse (ties dropped), at α = 0.05.

The outcome is read as follows:

- the interval excludes zero and the effect is positive → **better**;
- the interval excludes zero and the effect is negative → **worse**;
- otherwise → **no detectable effect**: report the interval and the size of effect it rules out.

**Decision rule (as M3g).** A held-out gain counts as a **finding** only if the development set agrees with it:
S2c − A must be positive on the 86 too, whatever its interval. A held-out gain with a development-set effect at or
below zero is reported as a held-out result that the development set does not support. A development-set gain on
its own is not a finding.

**Power, stated in advance.** The spread is taken from M3g, whose held-out interval with 3 runs per arm was ±3.7
points (standard error about 1.9).

- **About 80%** chance to detect a true effect of **+5.3 points**
- **About 50%** chance for **+3.7 points**
- **About 25%** chance for **+2.4 points**

On the 86, M3c, M3d and M3g had half-widths of 4.6–4.9 points (standard error about 2.4), so 80% power there needs
about +6.7 points. Claude Code with Haiku is a different agent, so its run-to-run spread may differ: a pass rate far
from 50% narrows the interval. The report gives the realised half-width.

**Secondary comparisons (descriptive unless stated):**

- S1c − A on the held-out set, and S2c − S1c on the held-out set, with the same tool and interval.
- The same three comparisons on the 86, labelled **development set**, with the 79-problem view beside them (never
  in place of them). The ladder's Haiku run is shown for reference only.
- **Skill-load rates** per arm and set, including the single unhinted S2 run (the unprompted rate):
  - the share of problem-runs that load any pack skill;
  - each skill's load count;
  - the distribution of `skill_first_turn`;
  - Claude Code's bundled skills loaded, in every arm.
- Pass rate with and without each load, by problem-run. This is descriptive only, because the model chooses which
  skills to load.
- **Effort:** median and mean turns, median wall time, tokens (prompt including cache, and completion) per
  problem-run, and the number of wall-cap stops.
  - Nothing is billed per call. `cost_usd` stays unreported, and Claude Code's own API-rate estimate
    (`plan_cost_estimate_usd`) is shown apart from it, as a guide to plan usage only.
- The failure taxonomy per arm (`tools/taxonomy.py`).

## Spend and limits

The sweeps cost no OpenRouter money. The claudecode harness uses `CLAUDE_CODE_OAUTH_TOKEN` on the owner's plan, and
`sweep.sh` passes the OpenRouter key only to the OpenRouter provider. The workflow's key-usage steps still read the
key's usage before and after each run, which spends nothing and should show a change of $0. The constraint is the plan's limits, so the sweeps run
one at a time. The planner dispatches the scored sweeps only after the owner agrees. The wall-time estimate is in
[`smoke.md`](smoke.md).

## Smoke runs (not scored, before this file was final)

See [`smoke.md`](smoke.md). In short, the 8 smoke runs showed the following:

- Claude Code offered every pack skill to the model in every pack problem-run.
- Haiku loaded none of them in any of the 12 S1 and S2 problem-runs.
- With S2c's one-line hint, it loaded pack skills at turn 1 in 3 of 3.
- The leak guard passed on every run.

These results are the reason for the amendment at the top of this file.

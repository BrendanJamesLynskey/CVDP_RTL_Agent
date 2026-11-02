# M3i report: how much of Claude Code is the harness?

**Status: held-out phase DONE (2026-11-02).** The primary result is in. The one descriptive run on the 86 has not
run yet (it waits for usage budget); its rows stay TODO.

- **Pre-registration:** [`m3i/preregistration.md`](m3i/preregistration.md).
- **Smoke runs:** [`m3i/smoke.md`](m3i/smoke.md).
- Arms: D = M3h's arm A (reused), P = the plain profile (Claude Code with our system prompt, Read/Write/Edit/Bash
  only, no settings, skills or MCP). Model `claude-haiku-5-5`, Claude Code 2.1.310.

## In short (held-out set only)

- **Primary: P − D = −0.3 points [−4.0, +3.3]** (9 better, 11 worse, 80 same; sign test p = 0.82): no detectable effect.
- **Development set (86), descriptive: P − D = TODO** (one run per arm).
- **Decision:** not a finding. The held-out interval includes zero, so the 86 cannot change that.
- **Effort:** median turns D 6, P 5; median wall time D 32 s, P 25 s; mean prompt tokens per problem-run D 167,423, P 61,805
  (P uses 37% of D's prompt tokens, all tokens 20.7 M against 53.3 M over 300 problem-runs).

## Setup

| Arm | Sweep inputs | Held-out runs |
|---|---|---|
| D | `harness=claudecode`, `model=claude-haiku-5-5`, `cc_profile=default` (M3h's A1–A3, reused) | 3 |
| P | the same with `cc_profile=plain`, from `m3i-plain` fb187eb | 3 |

## Runs

| Arm | Seed | Run | Passed | Rate-limited / profile errors |
|---|---|---|---|---|
| D | 1–3 | M3h A1–A3 | 57, 56, 62 | 0 |
| P | 1 | 41455576891 | 61 | 0 / 0 |
| P | 2 | 41460460754 | 58 | 0 / 0 |
| P | 3 | 41465352710 | 55 | 0 / 0 |
| P (the 86) | 1 | TODO | TODO | TODO |

Plan `/usage` (week, all models): 13% before P1, 16% after P3 (the plan is shared with other work, so this is an upper
bound on M3i's use).

## Results

### Primary: P − D (held-out)

| | D | P | P − D [95% CI] | better / worse / same | sign test p |
|---|---|---|---|---|---|
| pass@1, 100 problems × 3 runs | 175/300 = 58.3% | 174/300 = 58.0% | −0.3 [−4.0, +3.3] | 9 / 11 / 80 | 0.824 |

Realised half-width: 3.65 points (assumed about 4.0). The interval rules out a gain or loss larger than about 4 points
from Claude Code's own prompt, tools and defaults on this set.

### Secondary

- The 86: TODO (one P run, descriptive only).
- Stop reasons, P: submit 297, wall_time 3; no rate-limited or profile-error rows.
- Median tool calls per problem-run: D 5, P 4.
- Tokens: P's prompts are much shorter (no Claude Code system prompt, 4 tool schemas instead of 22, no skill list),
  so each turn costs about a third as many prompt tokens. At API prices this is the same pass rate for well under
  half the input tokens. This is descriptive; it was not a pre-registered outcome.

### Did the profile take effect?

Yes. All 300 P problem-runs have `cc_tools` = `Bash;Edit;Read;Write`, `cc_skills_n` = 0, `cc_mcp_n` = 0,
`cc_model` = `claude-haiku-5-5` and `cc_prompt_sha256` = `e45ea1e3…`; 0 `profile_error` rows.

## Reading

At a fixed model (Haiku 5.5), Claude Code's own system prompt, its 22-tool set and its default skills and settings
add nothing measurable to the pass rate on the held-out set: our LangGraph agent's prompt with four tools does as
well, with about a third of the prompt tokens. This agrees with M3e (Claude Code + Opus no better than our agent +
Opus). The benchmark gain from Claude Code over a plain loop, at this model, is within ±4 points.

Confounds, from the pre-registration: D ran on 2026-10-31 and P on 2026-11-02 (same Claude Code version and image,
but model serving can change); both arms keep Claude Code's fixed request lines, environment message and tool
schemas, so P is "Claude Code stripped down", not a bare API call; thinking effort is the CLI default in both.

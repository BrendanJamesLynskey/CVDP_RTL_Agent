# M3i report: how much of Claude Code is the harness?

**Status: SKELETON (2026-11-02).** The plain profile is built, tested and smoke-run; no scored sweep has run. Every
number below is TODO until the planner dispatches the sweeps.

- **Pre-registration:** [`m3i/preregistration.md`](m3i/preregistration.md).
- **Smoke runs:** [`m3i/smoke.md`](m3i/smoke.md).
- Arms: D = M3h's arm A (reused), P = the plain profile (Claude Code with our system prompt, Read/Write/Edit/Bash
  only, no settings, skills or MCP). Model `claude-haiku-5-5`, Claude Code 2.1.310.

## In short (held-out set only)

- **Primary: P − D = TODO points [TODO, TODO]** (TODO better, TODO worse, TODO same; sign test p = TODO).
- **Development set (86), descriptive: P − D = TODO** (one run per arm).
- **Decision:** TODO (the rule needs the 86 to agree with the sign of a held-out difference).
- **Effort:** median turns D TODO, P TODO; median wall time D TODO s, P TODO s; prompt tokens per problem-run D TODO, P TODO.

## Setup

| Arm | Sweep inputs | Held-out runs |
|---|---|---|
| D | `harness=claudecode`, `model=claude-haiku-5-5`, `cc_profile=default` (M3h's A1–A3, reused) | 3 |
| P | the same with `cc_profile=plain` | TODO |

## Runs

| Arm | Seed | Run | Passed | Rate-limited / profile errors |
|---|---|---|---|---|
| D | 1–3 | M3h A1–A3 | 57, 56, 62 | 0 |
| P | 1 | TODO | TODO | TODO |
| P | 2 | TODO | TODO | TODO |
| P | 3 | TODO | TODO | TODO |
| P (the 86) | 1 | TODO | TODO | TODO |

Plan `/usage` (week, all models): TODO before, TODO after.

## Results

### Primary: P − D (held-out)

| | D | P | P − D [95% CI] | better / worse / same | sign test p |
|---|---|---|---|---|---|
| pass@1, 100 problems × 3 runs | 175/300 = 58.3% | TODO | TODO | TODO | TODO |

Realised half-width: TODO (assumed about 4.0).

### Secondary

TODO: the 86; turns, wall time, tokens, stop reasons; tool-call mix; failure taxonomy.

### Did the profile take effect?

TODO: from the CSV columns `cc_tools`, `cc_skills_n`, `cc_mcp_n`, `cc_model`, `cc_prompt_sha256` over every P problem-run; the number of `profile_error` rows.

## Reading

TODO. What Claude Code's own system prompt, tool set and defaults add (or do not) at a fixed model; the confounds in
the pre-registration (time between D and P, the fixed lines Claude Code adds to every request).

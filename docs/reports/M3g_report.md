# M3g report: a frozen knowledge pack, loaded as skills

**Status: skeleton.** Code, pack, held-out set, pre-registration ([`m3g/preregistration.md`](m3g/preregistration.md))
and smoke runs ([`m3g/smoke.md`](m3g/smoke.md)) are on the branch `m3g-knowledge-pack`, PR #30. No scored sweep has
run. Every number below is TODO until the scored sweeps have run from one commit and the tables are made from their
CSVs by the committed tools.

Harness `8e894cf`, dataset revision `5b807d9`. The rules from the M1 report still apply:
- the LLM never produces a score or a label;
- every cost is provider-reported;
- a missing cost is recorded as unreported, never estimated.

**The question.** Can a frozen pack of outside RTL design know-how, written without sight of CVDP, loaded as skills,
give `openai/gpt-6-luna` some of what M3e found the stronger model brings?

| Arm | Sweep inputs | What changes |
|---|---|---|
| A | (defaults) | nothing: M3c's arm A, byte-for-byte |
| K | `skills=agent/cvdp_agent/skills/rtl_pack` | the plan sees the pack's index and names up to 3 skills; their text goes into every edit prompt |

## Runs

| Set | Arm | Seed | Run | Problems | Reported spend | Unreported calls |
|---|---|---|---|---|---|---|
| held-out 100 | A | 1 | TODO | TODO | TODO | TODO |
| held-out 100 | A | 2 | TODO | TODO | TODO | TODO |
| held-out 100 | A | 3 | TODO | TODO | TODO | TODO |
| held-out 100 | K | 1 | TODO | TODO | TODO | TODO |
| held-out 100 | K | 2 | TODO | TODO | TODO | TODO |
| held-out 100 | K | 3 | TODO | TODO | TODO | TODO |
| the 86 | K | 1 | TODO | TODO | TODO | TODO |
| the 86 | K | 2 | TODO | TODO | TODO | TODO |
| the 86 | K | 3 | TODO | TODO | TODO | TODO |
| the 86 | A (M3d) | 1–3 | 40353853802, 40368004835, 40376808643 | 86 | (M3d) | (M3d) |

Commit: TODO. Key usage before: TODO; after: TODO.

## Primary result: K − A on the held-out set

| | A | K | K − A [95% CI] | better / worse / same | sign test p |
|---|---|---|---|---|---|
| pass@1, 100 problems | TODO | TODO | TODO | TODO | TODO |

Verdict (pre-registered rule): TODO. Realised half-width: TODO (pre-registered estimate 4.3–4.5 points).

## Development set: K − A on the 86 (and the 79)

| View | A (M3d) | K | K − A [95% CI] | better / worse / same | sign test p |
|---|---|---|---|---|---|
| 86 problems | TODO | TODO | TODO | TODO | TODO |
| 79 problems | TODO | TODO | TODO | TODO | TODO |

Does the development set agree with the held-out set? TODO.

## Decision

TODO (a finding only if the held-out gain is matched by a development-set effect above zero).

## Skills loaded

| Skill | held-out loads (of 300) | pass rate when loaded | when not | the 86: loads (of 258) | pass rate when loaded | when not |
|---|---|---|---|---|---|---|
| TODO | TODO | TODO | TODO | TODO | TODO | TODO |

Unknown names asked for: TODO. Mean bytes loaded per problem-run: TODO. Cap reached: TODO. (Descriptive only: the
plan chooses the skills, so these rows are not causal.)

## Failure taxonomy per arm

| Label | held-out A | held-out K | 86 A (M3d) | 86 K |
|---|---|---|---|---|
| own testbench passed, hidden failed | TODO | TODO | TODO | TODO |
| interface mismatch | TODO | TODO | TODO | TODO |
| TODO | TODO | TODO | TODO | TODO |

## By category (held-out)

| Category | Problems | A | K | K − A |
|---|---|---|---|---|
| cid002 RTL completion | 42 | TODO | TODO | TODO |
| cid003 spec to RTL | 41 | TODO | TODO | TODO |
| cid004 RTL modification | 17 | TODO | TODO | TODO |

## Cost

| Arm, set | $/problem | $/solved | median wall time | prompt tokens per problem-run | added prompt tokens (K − A) |
|---|---|---|---|---|---|
| A, held-out | TODO | TODO | TODO | TODO | |
| K, held-out | TODO | TODO | TODO | TODO | TODO |
| A, 86 (M3d) | TODO | TODO | TODO | TODO | |
| K, 86 | TODO | TODO | TODO | TODO | TODO |

Total M3g spend: TODO.

## Known gaps

- The held-out problems are CVDP's single-file copilot problems run through the agent, not agentic ones; the prompt
  gains one sentence naming the output file. They may be easier, and a result on them may not carry to the agentic
  split.
- The 86-problem base (M3d's arm A) was run on an earlier agent image and day; the code path is the same (golden
  test).
- The pack's own index asks for two fixed skills on every task, leaving one free choice under the 3-skill cap.
- Possible later arms, not run: Opus + pack; Sonnet planning + pack.

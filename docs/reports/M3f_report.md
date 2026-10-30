# M3f: split the roles

**Status: skeleton.** The code, the tests, the pre-registration and the smoke runs are in. The scored runs have not
been dispatched; every number below is TODO until they are. The design is fixed in
[`m3f/preregistration.md`](m3f/preregistration.md), and the smoke runs are in [`m3f/smoke.md`](m3f/smoke.md).

## Question

M3e put the gap between our luna agent and Claude Code + Opus down to the model (+13.4 points [+4.0, +22.4]), not the
harness. M3f asks which part of the model's job carries that gap: **reading the spec and planning**, or **writing the
spec cases the design is checked against**. In both arms luna still writes and fixes the RTL.

| Arm | plan | spec cases | edit, reflect | Runs |
|---|---|---|---|---|
| A (base) | luna | off | luna | M3d's 3 fresh runs |
| P | `anthropic/claude-sonnet-5.5` | off | luna | 2 (seeds 1–2) |
| T | luna | `anthropic/claude-sonnet-5.5` (M3d's S step) | luna | 2 (seeds 1–2) |
| S (secondary base for T) | luna | luna | luna | M3d's 3 runs |

## Runs

| Arm | Run IDs | Commit | Spend (provider-reported) | Key usage change |
|---|---|---|---|---|
| P | TODO | TODO | TODO | TODO |
| T | TODO | TODO | TODO | TODO |

## Primary results (Holm over P − A and T − A, α = 0.05 overall)

| Comparison | Effect [97.5%] | Better / worse / same | Sign test p | Holm-adjusted decision |
|---|---|---|---|---|
| P − A | TODO | TODO | TODO | TODO |
| T − A | TODO | TODO | TODO | TODO |

Decision rule outcome: TODO.

## Secondary results (descriptive)

- T − S (the tester's model, the machinery fixed): TODO
- P and T against M3e's LG+Opus on its 67 attempted problems (partial): TODO
- The 79-problem view (`--exclude tools/benchmark_limited_ids.txt`): TODO
- Failure taxonomy per arm, and the share of "own testbench passed, hidden tests failed": TODO
- $/solved per arm, and the strong model's share of spend: TODO
- Spec-case agreement with the hidden tests, T against S: TODO

## Known gaps

- The strong planner reaches luna only through the plan JSON (`files_to_change`, `approach`, `check_plan`); luna
  still reads the task and files itself in every edit. P measures a better plan handed to luna, not luna replaced as
  the reader.
- The throughput clamp on `max_tokens` (time-short calls only) pools the tokens per second of every model in a
  problem.
- PT and C (strong plan, a code-specialised edit model) are later arms, not run here.

# M3g pre-registration: a frozen knowledge pack, loaded as skills

Written on 2026-10-30, on the branch `m3g-knowledge-pack`, before any scored dispatch. Nothing here may change
after the first scored dispatch; anything learned later goes in the report, marked as such.

## The question

The M3b lessons memory (lessons from luna's own runs) had no detectable effect. M3e found that most of the gap
between luna and Opus is the model: Opus knows how to read a spec and which conventions to assume. M3g asks: **can a
frozen pack of outside design know-how, loaded as skills, give luna some of that?**

The pack is `agent/cvdp_agent/skills/rtl_pack/`, written in brief 18A from outside sources only, by a writer barred
from this repo, CVDP and every benchmark. Its manifest is frozen: `MANIFEST.sha256` has SHA-256
`e6ca1610e84fc775a89d812d4f6fcd96cf3afce7d2a24d5add0a9caeae2a7245` and `INDEX.md`
`87d242eda20d1c97061e14acfb6d244ec9d35676c5c8a36700b20d1d32f62f69`. `tests/test_m3g.py` checks both, and the agent
refuses a pack that does not match its manifest. The pack has 15 skills (8,922 words, 60,760 bytes with the index).

## The arms

| Arm | Sweep inputs | What changes |
|---|---|---|
| A | (defaults) | nothing: M3c's arm A, byte-for-byte (golden test) |
| K | `skills=agent/cvdp_agent/skills/rtl_pack` | the pack, as below |

**K, the mechanism.** Close to how Claude skills work, and simple:

- the `plan` prompt gets `INDEX.md` as it is (one name and description per skill) and is asked to name at most 3
  skills in its JSON reply as `"skills": [...]`;
- names are matched exactly after trimming, lower-casing and dropping `.md`; unknown names are recorded and ignored;
  repeats are dropped; the first 3 known names are kept, in the plan's order;
- the chosen skills' text goes into every `edit` prompt, after the plan and before the files. The first edit prompt
  is the plan reply's follow-up. Reflect prompts get none;
- the loaded text is capped at 13,000 bytes. The pack's three largest skills come to 12,554 bytes, so the cap never
  binds on this pack; it is a guard for a changed one;
- every run records, in the trace and in the CSV, the pack's manifest hash, the names asked for, those loaded, those
  unknown, the bytes loaded and whether the cap cut anything (`skills_*` columns).

With `skills` blank the agent is byte-for-byte what it was: the M3b golden fixture (prompts, trace and summary on the
fake provider) is unchanged, checked by `tests/test_m3g.py::test_langgraph_golden_unchanged_with_no_pack` as well as
the M3b and M3d golden tests.

Note: `INDEX.md` says "Load `spec-reading` first on every task, `self-check-and-cocotb` last". With a cap of 3 names,
a plan that follows it has one free choice. The pack is not edited (the planner decides any change); the report
gives how often each skill was chosen.

**Settings, both arms:** M3c arm A's, exactly: `openai/gpt-6-luna`, reasoning `default`, `ubuntu-24.04-arm`, 4
threads, $0.10 per problem, 10 turns, self-check and lint on, 480 s wall cap, no lessons memory, LangGraph harness,
harness `8e894cf`, dataset revision `5b807d9`.

## The problem sets

**Held-out set** (`tools/m3g_heldout_ids.txt`, committed in `943cef9` before any run): 100 problems from CVDP's
non-agentic split `cvdp_v1.1.0_nonagentic_code_generation_no_commercial.jsonl` at revision
`5b807d945f6a99aa645f7e43a64a2115e281b4bf` (SHA-256 `cbcd8129...411857`, checked by the sweep).

- Eligible: categories cid002 (RTL completion), cid003 (spec to RTL) and cid004 (RTL modification); the harness
  runs on the open-source simulation image; every output file is under `rtl/` and in the harness's
  `VERILOG_SOURCES`; the design name is not one of the 92 agentic problems' names and no given file is identical to
  an agentic problem's file. 227 candidates, 34 excluded (all for a shared design name), 193 eligible.
- Sampled: `random.Random(20261030).sample(sorted eligible ids, 100)`: cid002 42, cid003 41, cid004 17
  (easy 51, medium 49).
- Inspection: only field names, categories, output file names and the harness's image and `VERILOG_SOURCES` lines
  were read by code. No prompt, hidden test, `patch` field or reference solution of these 100 has been read by
  anyone working on this project. The 3 smoke problems were drawn from the 57 eligible problems outside the set that
  share no design name with it (`tools/m3g_smoke_ids.txt`, seed 20261031).
- Format: `tools/m3g_heldout.py build` turns each problem into the harness's agentic format with the harness's own
  transformer (`src/data_transformer.py` at `8e894cf`), and adds one sentence to the prompt naming the file(s) the
  harness compiles ("Write your answer to `rtl/x.sv`: ..."). In copilot mode the harness writes a model's answer to
  that file itself; an agent has to be told. The harness runs them with `--force-agentic`. Scoring is the benchmark's
  own hidden tests, run by the harness outside the agent's container, as for the agentic split.

**Development set:** M3b's 86 evaluation problems (`tools/m3b_eval_ids.txt`). They have been read, annotated and
analysed in depth, so any result on them is a **development-set** result. The 79-problem view leaves out brief 09's 7
benchmark-limited problems (`tools/benchmark_limited_ids.txt`).

## The runs

| Set | Arm | Runs | Base |
|---|---|---|---|
| held-out 100 | A | 3 fresh, seeds 1–3 | (none exists) |
| held-out 100 | K | 3 fresh, seeds 1–3 | A, fresh |
| the 86 | K | 3, seeds 1–3 | M3d's arm A runs 40353853802, 40368004835, 40376808643 (`docs/reports/m3d/runs/A*.csv`) |

All scored runs are dispatched from one commit of `m3g-knowledge-pack`, `seed_offset` 0, 1, 2 with `seeds` 1, as
M3d did. The 86-problem K runs reuse M3d's arm A as base: the agent's code paths with no pack are unchanged since
then (golden test), but the agent image and the day differ, which the report states.

## The comparisons

**Primary: K − A on the held-out set.** Paired over the 100 problems: each problem's pass rate over its 3 runs per
arm, the mean difference, a paired bootstrap 95% interval over problems (2,000 resamples) and the exact two-sided
sign test on problems better or worse, ties dropped, at α = 0.05. Computed with
`python3 tools/ablate.py --base A --ids tools/m3g_heldout_ids.txt --arm A=... --arm K=...`.

- the interval excludes zero and the effect is positive → **better**;
- the interval excludes zero and the effect is negative → **worse**;
- otherwise → **no detectable effect**: report the interval and the effect size it rules out.

**Power, stated in advance.** There is no earlier run on the held-out set, so the spread is borrowed from the 86:
M3c's and M3d's paired 95% half-widths with 3 runs per arm were 4.6–4.9 points. Scaled to 100 problems
(× √(86/100)), the half-width is about 4.3–4.5 points, a standard error of about 2.2–2.3. So:

- a true effect of about **+6.5 points** has roughly an 80% chance of being detected;
- **+4.5 points** about 50%;
- **+3 points** about 25%; an effect that small will most likely read as no detectable effect.

The held-out problems are single-file copilot problems and may be easier than the agentic ones; a pass rate far from
50% narrows the interval, one near 50% with many problems that flip between runs widens it. The report gives the
realised half-width.

**Secondary (descriptive, no test unless stated):**

- K − A on the 86, labelled **development set**, with the same tool and interval, and the 79-problem view beside it
  (`--exclude tools/benchmark_limited_ids.txt`), never in its place;
- the failure taxonomy per arm on both sets (`tools/taxonomy.py`), especially the share "own testbench passed,
  hidden failed" and interface mismatches;
- which skills were loaded, and how often, by set and category; unknown names; bytes loaded;
- pass rate with and without each skill loaded, by problem-run (descriptive only: the plan chooses the skills, so
  this is not a causal comparison);
- $/solved, $/problem and median wall time per arm; the added prompt tokens per problem-run (K − A);
- pass rate by category (cid002, cid003, cid004) on the held-out set.

**Decision rule.** A held-out gain that the development set agrees with (K − A positive there too, whatever its
interval) is a **finding**. A held-out gain with a development-set effect at or below zero is reported as a held-out
result that the development set does not support. A development-set gain alone is **not** a finding.

## Spend and guards

The smoke runs cost $0.0437 (`smoke.md`). Expected for the 9 scored sweeps: about $7.14, $10.72 with 1.5× for
estimate error. Each scored sweep has a **$2.00 whole-run guard** (`run_budget_usd=2.00`), which charges every call
still in flight at `budget_usd`, so it stays far above 4 threads × $0.10 = $0.40 in flight and stops only a run gone
wrong; all 9 guards spent would be $18.00. **Hard stop: $15 for M3g in all**, smoke included: spend is checked
after each batch from the key-usage lines and the ledgers, and if the next batch could take M3g past $15, no more
runs start and the report says which are missing. The owner's ceiling for the whole project is $150 on the key, preferably less; the
planner dispatches the scored sweeps only after the owner agrees, and stops if the next sweep could take the key
past that ceiling. The key is never taken under $3 of its limit.

## Possible later arms (listed, not run, not part of this pre-registration)

- **Opus + pack**: does the pack help only weak models?
- **Sonnet planning + pack**: M3f's P combined with the pack.

## Smoke runs (not scored, before this file)

See [`smoke.md`](smoke.md).

# M3b confirming run: pre-registration

Written 2026-10-25, before any of these runs was dispatched. The commit that adds this file is the record of what was decided in advance.

## Why

M3b found a harness effect, B − A = +4.3 points [+0.0, +8.5] (sign test p = 0.21), on 3 runs per arm. With four planned comparisons, none passed a Bonferroni correction, so the report calls the harness gain a hypothesis to confirm. This run tests that one hypothesis on fresh data.

## The single test

- **Comparison:** B − A (Deep Agents against LangGraph, both without the lessons memory). One test, so no multiple-comparison correction. α = 0.05, two-sided.
- **Data:** 6 new runs per arm on `tools/m3b_eval_ids.txt` (86 problems), `seed_offset` 3 to 8. **The M3b runs (seeds 1 to 3) are not pooled in**: the confirmation uses only the new runs, so the data that suggested the hypothesis does not also test it.
- **Settings:** identical to M3b arms A and B: `openai/gpt-6-luna`, reasoning `default`, `ubuntu-24.04-arm`, 4 threads, the M2 defaults, `harness=deepagents` for B. Dispatched from the branch `m3b-confirm`, whose agent, docker and sweep code equals `main` at 2863145 (the M3b code).
- **Analysis:** `python3 tools/ablate.py --base A --ids tools/m3b_eval_ids.txt --arm A=... --arm B=...` on the 12 new CSVs: the paired bootstrap 95% interval and the sign test.
- **Decision rule, fixed now:**
  - the interval excludes zero and the effect is positive → **confirmed**;
  - the interval excludes zero and the effect is negative → **reversed**;
  - otherwise → **not confirmed**: report the interval, and say what effect size it rules out.
- **Power (stated in advance):** M3b's 3-run interval half-width was about 4.3 points. Six runs should narrow that to about 3 points, giving roughly an 80% chance of confirming a true +4-point effect. A smaller true effect may well be missed.
- **Secondary (descriptive only, no test):** pass@1 per arm, $/solved, and the `tests_failed_no_selfcheck` and round-cap counts from `taxonomy.py`, to check that the mechanism M3b described repeats.

Spend cap: $3.00 guard per sweep; about $7.30 expected in total.

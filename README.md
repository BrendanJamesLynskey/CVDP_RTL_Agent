# CVDP RTL Agent

A LangGraph agent for NVIDIA's [CVDP benchmark](https://github.com/NVlabs/cvdp_benchmark) of hardware design
problems. It writes and fixes SystemVerilog, **checks its own work in simulation before it submits** (Icarus,
Verilator and cocotb), and records what every problem cost. Results are reported as pass rate, **cost per solved
problem** and wall time, by category, against a null agent and against published leaderboard rows.

**Status:** milestone 0 (harness running in GitHub Actions). No results yet.

## What it is tested on

The free (open-source tools only) agentic splits of CVDP 1.1.0, frozen by hash:

| File | SHA-256 (first 16) | Problems | By category |
|---|---|---|---|
| `agentic_code_generation_no_commercial` | `2007f4311ed731a9` | 92 | spec to RTL (cid003) 34; RTL modification (cid004) 25; spec to RTL with module reuse (cid005) 22; bug fixing (cid016) 11 |
| `agentic_heavy_code_generation_no_commercial` | `809916fa3248a4b2` | 75 | cid003 6; cid004 6; cid005 7; bug fixing in large real repositories (cid016) 56 |

The verification-writing categories (testbench stimulus, checkers and assertions; cid012–014) are all in the
commercial split, which needs Cadence Xcelium, so they are out of scope. Verification here means the agent's own
check-before-submit loop, and whether it pays for itself is one of the ablations.

## Rules

- The LLM never produces a score. Every number comes from the CVDP harness's hidden tests or from provider-reported
  token usage.
- Results only from real runs, with model IDs, tokens and cost; losses to a baseline are shown first.
- The harness and dataset are pinned (commit and revision in
  [`.github/workflows/m0_harness.yml`](.github/workflows/m0_harness.yml)).

## Layout

- [`.github/workflows/m0_harness.yml`](.github/workflows/m0_harness.yml): M0. Builds the harness's simulation
  image, checks the harness's example problems score 100% with their solutions, and runs the null agent.
- [`agents/null/Dockerfile`](agents/null/Dockerfile): the null agent (changes nothing), the floor.
- [`tools/inventory.py`](tools/inventory.py): hashes the dataset files and counts problems per category.

## Milestones

| | Work |
|---|---|
| M0 | Harness in CI; golden check; null-agent floor; frozen problem list |
| M1 | The agent image: plan, edit, simulate and lint, reflect, with a per-problem budget |
| M2 | Sweep the free agentic split with two cheap models and one open-weights model |
| M3 | Ablations: self-check on and off, lint on and off, turn and budget caps; failure taxonomy |
| M4 | Write-up, logs packed for the Si2 LBC-bench leaderboard |

## Licence

MIT. The CVDP harness is Apache-2.0 and the dataset CC BY 4.0 / Apache-2.0; neither is redistributed here, both
are fetched at run time.

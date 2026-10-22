# CVDP RTL Agent

A LangGraph agent for NVIDIA's [CVDP benchmark](https://github.com/NVlabs/cvdp_benchmark) of hardware design
problems. It writes and fixes SystemVerilog, **checks its own work in simulation before it submits** (Icarus,
Verilator and cocotb), and records what every problem cost. Results are reported as pass rate, **cost per solved
problem** and wall time, by category, against a null agent and against published leaderboard rows.

**Status:** milestone 0 done (22 October 2026). No agent results yet.

| M0 check | x86-64 (`ubuntu-24.04`) | Arm64 (`ubuntu-24.04-arm`) |
|---|---|---|
| Golden: harness example problems with their solutions | 1/1 | 1/1 |
| Null agent, agentic split (92) | 0/92 | 0/92 |
| Null agent, heavy split (75) | 0/75 | not run |
| Whole job, including building the simulation image | 23 min | 18 min |

Runs: [39847610657](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39847610657),
[39851112062](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39851112062) (Arm64),
[39851116748](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39851116748) (heavy). No problem
passes without edits, so every pass an agent gets is its own.

## What it is tested on

The free (open-source tools only) agentic splits of CVDP 1.1.0, frozen by hash:

| File | SHA-256 (first 16) | Problems | By category |
|---|---|---|---|
| `agentic_code_generation_no_commercial` | `2007f4311ed731a9` | 92 | spec to RTL (cid003) 34; RTL modification (cid004) 25; spec to RTL with module reuse (cid005) 22; bug fixing (cid016) 11 |
| `agentic_heavy_code_generation_no_commercial` | `809916fa3248a4b2` | 75 | cid003 6; cid004 6; cid005 7; bug fixing in large real repositories (cid016) 56 |

The verification-writing categories (testbench stimulus, checkers and assertions; cid012–014) are all in the
commercial split, which needs Cadence Xcelium. Two things stand in for them:

- **The agent's own check-before-submit loop.** Whether it pays for itself is the main ablation.
- **An open verification track on AMBA IP (M5).** Permissively licensed AXI4-Lite, AXI-Stream and APB blocks with
  seeded bugs. The agent writes a test plan, a cocotb testbench with functional coverage, and SVA properties
  checked formally with SymbiYosys. It is scored by how many seeded bugs it catches (mutant kill rate) and by false
  alarms on the clean RTL, never by its own report.

**AMBA slice.** 20 of the free problems involve AMBA interfaces (AXI4-Lite, AXI-Stream, APB): 10 in each split,
mostly spec-to-RTL in the first and bug fixing in real repositories (verilog-axi, verilog-ethernet, axis) in the
second. Results are reported for this slice on its own as well as overall.

**Arm64.** Every workflow runs on GitHub's Arm64 runners as well as x86-64, and the sweep tables give wall time on
both.

## Rules

- The LLM never produces a score. Every number comes from the CVDP harness's hidden tests or from provider-reported
  token usage.
- Results only from real runs, with model IDs, tokens and cost; losses to a baseline are shown first.
- The harness and dataset are pinned (commit and revision in
  [`.github/workflows/m0_harness.yml`](.github/workflows/m0_harness.yml)).

## Layout

- [`.github/workflows/m0_harness.yml`](.github/workflows/m0_harness.yml): M0. Builds the harness's simulation
  image, checks the harness's example problems score 100% with their solutions, and runs the null agent; on an
  x86-64 or an Arm64 runner.
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
| M5 | Open AMBA verification track: test plan, cocotb testbench with coverage, SVA with SymbiYosys; scored by seeded-bug kill rate and false alarms |

## Licence

MIT. The CVDP harness is Apache-2.0 and the dataset CC BY 4.0 / Apache-2.0; neither is redistributed here, both
are fetched at run time.

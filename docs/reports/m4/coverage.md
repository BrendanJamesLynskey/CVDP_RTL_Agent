# M4: which problems were attempted, and which were left out

Every problem file of CVDP 1.1.0 at revision `5b807d945f6a99aa645f7e43a64a2115e281b4bf`, with the problems each run covered and the reason for each omission.
Made by `docs/reports/m4/coverage.py` (stdlib only; `--dataset-dir` recomputes every count from the dataset files, with no flag it checks
`coverage.json` against the ids files and run CSVs in this repo). Counts are by the problem's first category.

## In short

- **872 problems in the 7 files.** 192 were scored (the agentic 92 and the held-out 100), and 3 more ran as smoke checks only.
- **397 were left out by rule or never run, although they are in the free (open-tool) files:** 199 left out by rule (34 name shared with an agentic problem, 90 not sampled, 75 code improvement and bug fixing outside the held-out rule), 198 never run (the heavy split and the comprehension file).
- **280 cannot be run** here: they need Cadence Xcelium, a commercial simulator. They hold the verification-writing categories cid012 to cid014.

## The table

| File | Part | Problems | By category | Status | Run in | Why |
|---|---|---|---|---|---|---|
| `agentic_code_generation_no_commercial` | the 86 development problems | 86 | cid003 spec to RTL 33; cid004 RTL modification 24; cid005 spec to RTL, module reuse 18; cid016 bug fixing 11 | attempted | M2, M3, M3b to M3l, the Claude Code ladder (tools/m3b_eval_ids.txt) |  |
| `agentic_code_generation_no_commercial` | the 6 problems excluded from the development set | 6 | cid003 spec to RTL 1; cid004 RTL modification 1; cid005 spec to RTL, module reuse 4 | attempted | M2 and M3 (all 92 problems); left out of the 86 from M3b on, run only in M3b's own excluded-problem sweeps (tools/m3b_excluded_ids.txt) | the hidden testbench reads signal or parameter names the task never gives (tools/reachable.py, docs/reports/m3b/unreachable.md) |
| `agentic_heavy_code_generation_no_commercial` | all | 75 | cid003 spec to RTL 6; cid004 RTL modification 6; cid005 spec to RTL, module reuse 7; cid016 bug fixing 56 | never run | M0 and M1 null agent only (no edits, to check the harness); never run with a model | the agent's file tool writes only under rtl/, verif/ and docs/, and in 53 of the 75 problems the hidden tests read files elsewhere; the design tree is a git workspace volume, not a bind mount, so no agent run was tried; 3 i2c problems produced no test output under the null agent (docs/reports/M1_report.md, Known gaps) |
| `nonagentic_code_generation_no_commercial` | the held-out 100 | 100 | cid002 RTL completion 42; cid003 spec to RTL 41; cid004 RTL modification 17 | attempted | M3g to M3k, and 3 of them in M3l (tools/m3g_heldout_ids.txt; counted here, never named on the site) |  |
| `nonagentic_code_generation_no_commercial` | 3 smoke problems | 3 | cid002 RTL completion 2; cid004 RTL modification 1 | smoke only | M3g smoke runs, not scored (tools/m3g_smoke_ids.txt) | kept apart from the 100 on purpose |
| `nonagentic_code_generation_no_commercial` | eligible, not sampled | 90 | cid002 RTL completion 42; cid003 spec to RTL 29; cid004 RTL modification 19 | left out by rule |  | the freeze rule samples 100 of the 193 eligible problems (seed 20261030) when more than 120 are eligible; the reports record no reason for 100 |
| `nonagentic_code_generation_no_commercial` | design name shared with an agentic problem | 34 | cid002 RTL completion 8; cid003 spec to RTL 8; cid004 RTL modification 18 | left out by rule |  | so the held-out set shares no design with the 92 agentic problems the agent was developed on (tools/m3g_heldout.py) |
| `nonagentic_code_generation_no_commercial` | code improvement and bug fixing | 75 | cid007 code improvement 40; cid016 bug fixing 35 | left out by rule |  | the held-out rule took only cid002, cid003 and cid004. The M3g pre-registration records no reason for leaving out cid007 and cid016. Under the rule's other conditions 56 of these 75 would have been eligible (cid007 24, cid016 32); the other 19 share a design name with an agentic problem |
| `nonagentic_code_comprehension` | all | 123 | cid006 correspondence or question answering 34; cid008 correspondence or question answering 29; cid009 correspondence or question answering 34; cid010 correspondence or question answering 26 | never run |  | correspondence and question-answering tasks, not RTL to write, change or fix; outside what the project set out to do. No separate decision is recorded |
| `agentic_code_generation_commercial` | all | 68 | cid003 spec to RTL 3; cid005 spec to RTL, module reuse 3; cid012 testbench stimulus 16; cid013 testbench checker 18; cid014 assertion generation 28 | cannot be run |  | needs Cadence Xcelium, a commercial simulator |
| `agentic_heavy_code_generation_commercial` | all | 25 | cid003 spec to RTL 1; cid004 RTL modification 1; cid012 testbench stimulus 8; cid013 testbench checker 7; cid014 assertion generation 7; cid016 bug fixing 1 | cannot be run |  | needs Cadence Xcelium, a commercial simulator |
| `nonagentic_code_generation_commercial` | all | 187 | cid012 testbench stimulus 67; cid013 testbench checker 53; cid014 assertion generation 67 | cannot be run |  | needs Cadence Xcelium, a commercial simulator |

## The files

| File (`cvdp_v1.1.0_` prefix) | SHA-256 (first 16) | Free (open tools) | Problems | By category |
|---|---|---|---|---|
| `agentic_code_generation_no_commercial.jsonl` | `2007f4311ed731a9` | yes | 92 | cid003 34; cid004 25; cid005 22; cid016 11 |
| `agentic_heavy_code_generation_no_commercial.jsonl` | `809916fa3248a4b2` | yes | 75 | cid003 6; cid004 6; cid005 7; cid016 56 |
| `nonagentic_code_generation_no_commercial.jsonl` | `cbcd81295561ebb1` | yes | 302 | cid002 94; cid003 78; cid004 55; cid007 40; cid016 35 |
| `nonagentic_code_comprehension.jsonl` | `1f150413ba2cbbdc` | yes | 123 | cid006 34; cid008 29; cid009 34; cid010 26 |
| `agentic_code_generation_commercial.jsonl` | `a8af339131383298` | no, commercial | 68 | cid003 3; cid005 3; cid012 16; cid013 18; cid014 28 |
| `agentic_heavy_code_generation_commercial.jsonl` | `a4f6e9e9a0928aa8` | no, commercial | 25 | cid003 1; cid004 1; cid012 8; cid013 7; cid014 7; cid016 1 |
| `nonagentic_code_generation_commercial.jsonl` | `4364c118036f65f0` | no, commercial | 187 | cid012 67; cid013 53; cid014 67 |

Also in the dataset repository at this revision: the directory cvdp_v1.1.0_agentic_heavy_code_generation_public: a README and 41 git bundles, not a problem file; and older release files, v1.0.2, v1.0.3 and v1.0.4 (not used: the study is pinned to 1.1.0).

## Notes

- **The commercial files.** The same test as `tools/m3g_heldout.py` (open simulation image named, no commercial tool named) finds no problem in them that names open tools only:
  open-tool-only problems in agentic commercial: 0 of 68; heavy commercial: 0 of 25; non-agentic commercial: 0 of 187.
- **No reason was recorded** for leaving cid007 and cid016 out of the held-out rule, or for choosing 100 of the 193 eligible. The table says so rather than supply one.
- **The verification categories cid012 to cid014 are in no free file.** The free files hold cid002 to cid010 and cid016.
- **Code improvement (cid007) is in the free split**: the non-agentic code-generation file has 40 such problems. None was run.
- Held-out ids are not listed here. `coverage.json` carries ids only for the problems that were not scored.

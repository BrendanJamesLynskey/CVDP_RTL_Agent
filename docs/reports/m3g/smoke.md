# M3g: smoke runs

These runs check the plumbing, not the score. There were 4 runs, from `m3g-knowledge-pack` at `f5cff04`, on
2026-10-30, each on 3 problems with one seed, in arms A (no pack) and K (`skills=agent/cvdp_agent/skills/rtl_pack`).

- **Held-out format** (`split=m3g_smoke`): the 3 problems of `tools/m3g_smoke_ids.txt`. They are eligible for the
  held-out set but are not in it, and share no design name with it, so the frozen 100 stay uninspected.
- **Development set** (`split=agentic`): `queue_0001`, `lfsr_0005` and `binary_search_tree_algorithms_0001`, the
  3 brief-09 problems M3f smoked, which luna's arm A never solved in M3d.

Settings: those of M3c arm A (`openai/gpt-6-luna`, reasoning `default`, `ubuntu-24.04-arm`, $0.10 per problem, 10
turns, self-check and lint on), with 4 threads and a $0.35 guard per run. The per-problem CSVs are in
[`smoke/`](smoke/).

| Run | Set | Arm | Passed | Reported spend | Unreported calls |
|---|---|---|---|---|---|
| [41106554547](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41106554547) | held-out format | A | 2 of 3 | $0.0074 | 0 |
| [41106568719](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41106568719) | held-out format | K | 2 of 3 | $0.0091 | 0 |
| [41107030111](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41107030111) | development | A | 0 of 3 | $0.0165 | 0 |
| [41107045308](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41107045308) | development | K | 0 of 3 | $0.0107 | 0 |
| | | | | **$0.0437** | 0 |

**Key:** usage $80.2890 before (key check 41105276917) and $80.3328 after (key check 41107530471), a change of
$0.0437, the same as the reported spend. Limit $159 (the owner's ceiling is $150); $78.67 left on the key.

## What the smoke runs show

- **The held-out format runs end to end.** `tools/m3g_heldout.py build` made the agentic rows with the harness's own
  transformer, the harness ran them with `--force-agentic`, the agent saw only `prompt.json` in `/code` (no harness
  file), wrote the file the added sentence names, and the hidden tests scored it (1 test per problem). The same 2 of
  3 passed in both arms. `clock_jitter_detection_module_0003` failed in both, without a self-check.
- **The pack loads as designed.** In all 6 K rows the trace's `skills` event names the frozen manifest hash
  (`e6ca1610...`), the plan named exactly 3 known skills, none unknown, 11,344–12,225 bytes loaded, never cut.
  `spec-reading` was chosen first every time; `self-check-and-cocotb` was never chosen, although the index says to
  load it last (the cap of 3 leaves room for spec-reading and one other besides). Other choices:
  `fsm-design`, `arithmetic-and-widths`, `counters-timers-and-edges`, `reset-strategy` (twice),
  `sequential-and-combinational-coding` (twice), `synthesisable-subset-and-parameters` (three times),
  `fifo-design` (on `queue_0001`).
- **The default arm is unchanged:** the A rows have blank `skills_*` columns and no `skills` switch.
- **Added tokens.** The pack adds about 600 prompt tokens to the plan call (the index) and about 3,000 to each edit
  call (the skills). In M3d, arm A made about 223 edit calls per 86-problem run with 2.23M prompt tokens, so K adds
  about 0.72M prompt tokens per run, +32%.

## Cost estimate for the scored sweeps

M3d's arm A spent $0.570–0.596 per 86-problem run ($0.0069 per problem). The smoke runs are too small to give K's
cost directly, so K is taken as A plus 32% (all of it priced as if it were the whole cost, an upper bound, since
completion tokens are not added). The held-out problems cost $0.0025 (A) and $0.0030 (K) per problem in the smoke,
but these 3 may be easy, so they are priced at the 86's rate per problem.

| Sweep | Runs | Expected per run | Expected | With 1.5× for error | Guard per run |
|---|---|---|---|---|---|
| held-out A | 3 | $0.69 | $2.07 | $3.11 | $2.00 |
| held-out K | 3 | $0.91 | $2.73 | $4.10 | $2.00 |
| the 86, K | 3 | $0.78 | $2.34 | $3.51 | $2.00 |
| **all** | 9 | | **$7.14** | **$10.72** | at most $18.00 in all |

The held-out runs will most likely cost less (at the smoke's rate, about $0.25–0.30 per run). Each guard ($2.00) is
well above 4 threads × $0.10 = $0.40 in flight plus any run's expected spend, so it stops only a run gone wrong. The
worst case, all 9 guards spent, takes the key from $80.33 to about $98.33, under the owner's $150 ceiling. A hard
stop for M3g of **$15** (smoke included) is suggested: if the next batch could take M3g past it, no more runs start.

Dispatch, from one commit of `m3g-knowledge-pack`, for seed k = 1, 2, 3 (`seed_offset` k−1, `seeds` 1):

    gh workflow run sweep.yml --ref m3g-knowledge-pack -f model=openai/gpt-6-luna -f reasoning=default \
      -f runner=ubuntu-24.04-arm -f threads=4 -f budget_usd=0.10 -f seeds=1 -f seed_offset=<k-1> \
      -f run_budget_usd=2.00 -f split=m3g_heldout [-f skills=agent/cvdp_agent/skills/rtl_pack]
    gh workflow run sweep.yml --ref m3g-knowledge-pack -f model=openai/gpt-6-luna -f reasoning=default \
      -f runner=ubuntu-24.04-arm -f threads=4 -f budget_usd=0.10 -f seeds=1 -f seed_offset=<k-1> \
      -f run_budget_usd=2.00 -f split=agentic -f ids="$(grep -v '^#' tools/m3b_eval_ids.txt | paste -sd,)" \
      -f skills=agent/cvdp_agent/skills/rtl_pack

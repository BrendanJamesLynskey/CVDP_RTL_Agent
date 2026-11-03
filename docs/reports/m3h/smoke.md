# M3h: smoke runs

These runs check the plumbing, not the score. They ran on 2026-10-31 from `m3h-cc-skills`, with the agent image of
`be5c24f` (Claude Code 2.1.310, confirmed in the image build log). Each run had 3 problems and one seed. The
settings were the pre-registered ones: `harness=claudecode`, `claude-haiku-5-5`, `ubuntu-24.04-arm`, 4 threads.

- **Held-out format** (`split=m3g_smoke`): M3g's 3 smoke problems (`tools/m3g_smoke_ids.txt`). They are eligible for
  the held-out set but are not in it, so the frozen 100 stay uninspected.
- **Development set** (`split=agentic`): `queue_0001`, `lfsr_0005` and `binary_search_tree_algorithms_0001`, M3g's
  development-set smoke problems.

The per-problem CSVs are in [`smoke/`](smoke/). Nothing is billed per call on the plan.

| Run | Set | Arm | Passed | Pack skills offered (`skills_listed`) | Problem-runs loading a pack skill | Harness wall s |
|---|---|---|---|---|---|---|
| [41151265156](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41151265156) | held-out format | A | 2 of 3 | — | — (no `Skill` call of any kind) | 90 |
| [41151486314](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41151486314) | held-out format | S1 (`v1.0`) | 2 of 3 | 15 of 15 | 0 of 3 | 77 |
| [41151678874](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41151678874) | held-out format | S2 (`v2.0`) | 2 of 3 | 25 of 25 | 0 of 3 | 101 |
| [41151912625](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41151912625) | development | A | 0 of 3 | — | — (no `Skill` call of any kind) | 263 |
| [41152382385](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41152382385) | development | S1 (`v1.0`) | 0 of 3 | 15 of 15 | 0 of 3 | 374 |
| [41152963242](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41152963242) | development | S2 (`v2.0`) | 1 of 3 | 25 of 25 | 0 of 3 | 320 |
| [41153522813](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41153522813) | held-out format | S2c (`v2.0` + hint) | 2 of 3 | 25 of 25 | **3 of 3** | 111 |

There was one earlier S2 held-out-format run,
[41150656235](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41150656235). It used the image of
`dcc7ed4`, from before `skills_listed` was added. It passed 2 of 3 and loaded no skill. Its CSV is
`smoke/S2_heldout_first_image.csv`.

## What the smoke runs show

- **The private pack is fetched and checked before any model call.** In every pack run, the deploy-key checkout
  and `tools/skill_pack.py` passed. They printed only the tag, the skill count and the manifest hash (`v1.0`: 15,
  `7ba7b4b3…`; `v2.0`: 25, `e405fe31…`). `sweep.sh` checked the pack again before the harness started.
- **Claude Code sees the skills.** Its own `init` event offered all 15 (`v1.0`) or all 25 (`v2.0`) pack skills in
  every pack problem-run (`skills_listed`), alongside 19 bundled skills. The bundled skills are also offered in
  arm A.
- **Claude Code can load them in the container.** With S2c's one-line `CLAUDE.md`, Haiku loaded pack skills at turn
  1 in all 3 problem-runs: `spec-reading` in all 3, and `minimal-change-modification` and `fsm-design` in one.
- **Without the hint, Haiku loaded none.** It loaded no pack skill in any of the 12 S1/S2 problem-runs. Arm A made
  no `Skill` call at all, counted from its kept stream with the same parser. If the scored S2 runs look like this,
  the pre-registered S2c condition (S2 loading in under 25% of problem-runs) will be met.
- **No skill text was published.**
  - The leak guard step passed in every pack run.
  - Each pack arm's `agent_out` held only `summary.json` and `claude_tools.jsonl` (turn, tool name and skill name
    per call). There was no raw stream.
  - Every downloaded artifact passed the guard again locally, against the tag's own text: `v2.0` for the S2 and S2c
    runs, `v1.0` for the S1 runs. So did the public job logs of 3 pack runs and the CSVs committed here.
  - S2c loaded skill bodies, and its artifact is clean too. This is the case the guard exists for.
- **The default arm is unchanged in shape.** Both A CSVs have exactly M3g's 87 columns, and the pack arms add the
  M3h columns after them.
- **No rate limit was hit.** Every row ended `submit`.

## Plan usage and wall time

- **Plan usage.** `claude -p "/usage"` read 7% (5-hour session) and 66% (week, all models) before the smoke. It
  read 12% and 67% after.
  - That change includes this session's own use.
  - The 8 smoke runs add up to about 36 Claude Code session-minutes, so a session-minute costs at most about
    0.15% of the 5-hour limit.
- **Harness wall time per seed.** Held-out format: 77–111 s for 3 problems at 4 threads. Development set:
  263–374 s, set by the slowest problem.
- **Estimated wall time of the scored sweeps (one seed each):**
  - **Held-out 100:** a mean agent time of about 47 s per problem (these smoke runs) gives
    100 × (47 + 10) s / 4 + about 5 min of setup ≈ **30 min**.
  - **The 86:** the ladder's Haiku run spent 9,286 s of agent time on the 86. Over 4 threads, plus tests and setup,
    that comes to ≈ **50 min**.
  - **All 18 sweeps (A, S1, S2):** about 9 × 30 + 9 × 50 min ≈ **12 hours** of sweeps, run one at a time. S2c would
    add 6 sweeps, about 4 hours.
- **The 5-hour limit sets the pace.** At about 0.15% per session-minute, a held-out sweep (about 80
  session-minutes) uses about 12% of the 5-hour limit, and an 86 sweep (about 160 session-minutes) about 24%. So
  about 3 to 4 sweeps fit in one 5-hour window, alongside the owner's own use.
  - The weekly limit read 67% on 2026-10-31 and resets on 2026-11-02 at about 01:00 London time.
  - The smoke runs are too small to measure the weekly cost of a full sweep, because `/usage` moves in whole
    percent. The first scored sweep's change in `/usage` should be used to size the rest.
- **Rate limits in the ladder.** Running 4 models at 4 threads at once took the 5-hour limit from 26% to 89% in 10
  minutes. Problems after the cap ended `llm_error` and were rerun by hand.
  - Those problems now end `rate_limited`, detected from the 429 `usage_limit_reached` result and the `rejected`
    `rate_limit_event`. The real ladder event shape was checked against a downloaded artifact of run 40201690138.
  - `ablate.py` leaves those rows out, and `tools/m3h_merge.py` keeps the rerun's row.

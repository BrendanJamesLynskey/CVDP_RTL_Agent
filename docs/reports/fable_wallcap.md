# Fable 5.1 on the 17 wall-capped problems: a longer-cap rerun

**Status: EXPLORATORY AND INCOMPLETE (2026-11-02).** 12 of the 17 problems have a valid rerun row; **5 are not
measured**. No score on the 86 is computed from this. Not pre-registered. The ladder's own numbers
([`claude_code_ladder.md`](claude_code_ladder.md)) are unchanged.

## Why

In the Claude Code ladder, Fable 5.1 stopped on the 480 s wall cap on 17 of the 86 evaluation problems (7 of them
passed under the cap, 10 failed), so its 67.4% (58/86) could be a lower bound. The 17 ids are in
[`tools/fable_wallcap_ids.txt`](../../tools/fable_wallcap_ids.txt), computed from the ladder CSV by
`tools/fable_wallcap.py ids`. This rerun gives those problems a 1,500 s cap (the `wall_s` sweep input; the harness's
agent timeout is `wall_s + 120`), one run, on the owner's Max plan.

## Runs

| Dispatch | Run | What happened | Valid rows |
|---|---|---|---|
| 1 | [41224141945](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41224141945) | All 17 ids. The plan's 5-hour limit cut it short: 13 of the 17 ended as `llm_error` and are not attempts. | 4 (3 passed, 1 failed) |
| 2 | [41369146552](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41369146552) | Those 13 ids, `wall_s` 1500, 2 threads. **Cancelled at the 5-hour limit** with 8 completed (4 passed, 4 failed); 5 ended as `llm_error` (2 after 424 to 731 s, 3 in under 1 s). | 8 (4 passed, 4 failed) |

Both CSVs are in [`fable_wallcap/runs/`](fable_wallcap/runs/). `tools/fable_wallcap.py merge` keeps each problem's first
valid row (a limit or error stop is never an attempt, and a failure is never rerun); the merged CSV is
`fable_wallcap/runs/fable_1500s_merged.csv`. It is made by [`fable_wallcap/analyze.sh`](fable_wallcap/analyze.sh).

## Combined: 12 of 17 measured (7 passed, 5 failed)

- Of the 12, 7 passed under the 1,500 s cap and 5 failed. Under the 480 s ladder run the same 12 gave 6 passed.
  Only `rgb_color_space_conversion_0001` changed (fail to pass, after 248 s: that ladder failure was not a cap
  effect, so it is run-to-run variation).
- None of the 12 hit the 1,500 s cap; the longest took 1,075 s. Six took more than the old 480 s (562 to 1,075 s),
  and all six gave the same pass or fail as in the ladder.
- **Not measured (5):** `nmea_gps_0008`, `sigma_delta_audio_0001`, `sorter_0009`, `spi_complex_mult_0002`,
  `sync_serial_communication_0001`. In the ladder run, 1 of these passed (`nmea_gps_0008`) and 4 failed.

| Row set | Problems | Ladder (480 s cap) passed | Rerun (1,500 s cap) passed |
|---|---|---|---|
| measured | 12 | 6 | 7 |
| not measured | 5 | 1 | – |
| the other 69 of the 86 (unchanged) | 69 | 51 | – |

**Bounds, not a score.** With the rerun's 12 rows in place and the 5 unmeasured counted as all failed or all passed,
Fable's score on the 86 lies between 58 and 63 of 86 (67.4% to 73.3%), against the ladder's 58. So the rerun cannot
move the ladder's Fable figure down, and it can move it up by at most 5 problems; it shows no sign of a large
wall-cap penalty among the 12 it measured (1 problem changed).

Per-problem table: [`fable_wallcap/bounds.md`](fable_wallcap/bounds.md).

## Caveats

- Exploratory: one run, 12 of 17, a cap no other ladder arm had, and the plan's usage limits decided which problems
  were reached, so the 5 unmeasured are not a random sample.
- Fable on the Max plan only (never through OpenRouter); the rerun used plan usage and no OpenRouter spend.
- To finish the 5, a third dispatch of `wall_s` 1500 on those ids would do; it is parked (usage).

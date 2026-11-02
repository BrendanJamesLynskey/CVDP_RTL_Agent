# M3i: smoke runs

These runs check the plumbing, not the score. They ran on 2026-11-02 from `m3i-plain` (head `0b8e1b1`), on the plan (`CLAUDE_CODE_OAUTH_TOKEN`), with `harness=claudecode`, `claude-haiku-5-5`, Claude Code
2.1.310, `ubuntu-24.04-arm`, 4 threads, one seed. No pack, so the leak guard did not run.

| Run | Set | Profile | Passed | Harness wall | CSV |
|---|---|---|---|---|---|
| [41453468707](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41453468707) | held-out format (`m3g_smoke`: `tools/m3g_smoke_ids.txt`, 3 problems) | plain | 2 of 3 | about 30 s per problem; job 1 m 48 s | [`smoke/P_heldout.csv`](smoke/P_heldout.csv) |
| [41453837017](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41453837017) | development (`binary_search_tree_algorithms_0001`, `lfsr_0005`, `queue_0001`) | plain | 1 of 3 | 32 to 139 s per problem | [`smoke/P_dev.csv`](smoke/P_dev.csv) |
| [41454430618](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41454430618) | development (`queue_0001`) | default | 0 of 1 | 97 s | [`smoke/D_dev.csv`](smoke/D_dev.csv) |

## What they show

- **The `init` event is the profile, in all 6 plain problem-runs.** `tools` was exactly Bash, Edit, Read, Write.
  `skills` was empty, `slash_commands` empty, `mcp_servers` empty, `model` `claude-haiku-5-5`, Claude Code 2.1.310,
  permission mode `acceptEdits`. The default-profile smoke run's `init` (run 41454430618) offered 22 tools and 19 bundled skills.
  `init` still lists four built-in agent names (`claude`, `Explore`, `general-purpose`, `Plan`); the Agent tool is
  not offered, so they cannot be called.
- **The CSV columns are filled.** Every plain row has `cc_profile=plain`, `cc_tools=Bash;Edit;Read;Write`,
  `cc_skills_n=0`, `cc_mcp_n=0`, `cc_model=claude-haiku-5-5` and
  `cc_prompt_sha256=e45ea1e3b3ca60c5a33169cce203a8b0e57e578d832e3577e23a4caad49019bd`, the hash of the agent's
  `prompts.SYSTEM`.
- **The tools used were only the four.** Across the 6 plain problem-runs the model made 2 to 10 tool calls each: Bash in
  all of them, Edit in 2, Write in 2. No `profile_error`, no rate limit.
- **Problems are scored** by the CVDP harness as in every sweep (pass 3 of 6; the smoke is not a result).
- **The default arm is unchanged.** The default-profile CSV has the 87 columns of M3h's arm A smoke CSV, in the same
  order, with no `cc_*` column; `claude_code.py`'s default command line is byte-for-byte the frozen golden run
  (`tests/test_m3h.py::test_claudecode_golden_unchanged_with_no_pack`, and `tests/test_m3i.py`).
- **Time and effort.** Plain problems took 6 turns at the median (3 to 11) and a median of about 30 s each (19 to
  139 s). An arm A held-out sweep of M3h took about 5,100 s of summed problem time, which on 4 threads is about
  21 minutes. A plain held-out sweep should be the same or a little shorter: **an estimate of 20 to 25 minutes per
  held-out sweep including setup, and about 50 to 60 minutes for the 86.** Three held-out P sweeps are therefore
  about 1 h 15 min of Actions time.

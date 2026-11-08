# M3l pre-registration: retrieved real-RTL examples in the agent's context (arm E), on the plain API loop

Written on 2026-11-08, on the branch `m3l-examples` (from `main` 4357a17), before any smoke or scored dispatch. Nothing
here may change after the first scored dispatch. Anything learned later goes in the report, marked as such. Changes the
planner makes before the first scored dispatch go in "Amendments" at the end.

## The question

Written knowledge did not help: M3b's lessons, M3g's pack and M3h's skills were null; the one confirmed gain is harness
work (M3b, +4.7 [+1.0, +8.5]). M3l tests the other form: **real, well-reviewed modules shown as examples**, not prose.
Per problem the agent gets the one or two closest real modules from the private pack's `reference/` layer (pack tag
`v4.0`, 86 entries). Model (`claude-haiku-5-5`, Claude Haiku 5.5) and loop (M3j's arm R, `harness=apiloop`) are held
fixed: **does showing close real modules change the held-out pass rate?**

## Arms

| Arm | What | Sweep input |
|---|---|---|
| R (control) | M3j's arm R, **reused, not rerun**: its request path is proven byte-identical (below). The three held-out R CSVs (`m3j/runs/heldout_R12_41673126672.csv`, `heldout_R3_41709498919.csv`) and the dev-86 R run (`dev86_R_merged.csv`). | `harness=apiloop` |
| E | R, plus an example block appended to the first user message when the retriever finds a close module | `harness=apiloop fixed_checks=retrieved_examples skill_pack=v4.0` |

`workflow_dispatch` is at 24 of GitHub's 25 inputs, so E adds none: it extends the `fixed_checks` choice
(`retrieved_examples`) and reuses `skill_pack` for the pack tag. `sweep.sh` accepts `RETRIEVED_EXAMPLES=1` only with
`HARNESS=apiloop`, `SKILL_PACK` set, and no other fixed check; `SKILL_PACK` with apiloop is refused without it, and keeps its
Claude Code meaning with `HARNESS=claudecode`. `tests/test_m3l.py` covers the validation and the input count (24).

### R's path is unchanged

`tests/golden_apiloop.json` (recorded at 5f569e9 for M3k) holds the requests R's loop sends to a scripted fake client;
`tests/test_m3k.py::test_r_request_path_is_byte_identical_to_the_m3j_golden` compares today's requests with it and
passes on this branch. With the E switch off the summary gains no key, the CSV no column, `run.json` no key
(`test_r_is_unchanged_by_the_new_code`, `test_sweep_without_the_flag_does_not_mention_examples`). With E on but nothing
above the threshold, the whole request equals R's (`test_e_with_nothing_above_the_threshold_is_exactly_r`); with an
example, only the first user message differs (`test_e_examples_reach_the_first_user_message_after_the_task`). So R is
reused, not rerun.

## The retrieval rule (fixed here; code: `agent/cvdp_agent/examples.py`)

**What is shown.** Only real upstream code and its attribution, never the pack's own prose (Pattern, When to use it,
Pitfalls). An entry with `whole_module: true` is shown as the whole module (from its `module` line to `endmodule`, in the
upstream file at the pinned SHA) when that is at most **250 lines**, otherwise as the entry's byte-exact excerpt (runs of
the listed lines, separated by a `// ...` line). Each example starts with one fixed header line:

```
// repo: <repo> | path: <path> | sha: <sha> | licence: <licence> | notice: <the file's own copyright/SPDX line>
```

**Upstream files** are fetched once per file at run start, by `tools/fetch_examples.py` on the runner, from
`raw.githubusercontent.com/<repo>/<sha>/<path>` at the SHA pinned in the pack. The entry's excerpt must be byte-for-byte
in the fetched file and its notice must occur in it, or the entry is dropped and the drop is printed. The sha256 of every
fetched file goes into `work.run.json` (`examples_files`), with the bundle's sha256; each problem's `api_tools.jsonl`
records the sums of the files it was shown. The pack's reference layer is checked against the manifest pinned in
`examples.REFERENCE_PINNED` (commit `2af8e0e6ce68c8e1756192103904afc47ad73684`, `reference/MANIFEST.sha256`
`c36d5df5c65a1f49af2628ccd00cc7d5ca090a6dfd2ffbe0fb66e4543291a917`, 86 entries) before any fetch.

**Query.** What the agent can see: `prompt.json`'s prompt and the text files under `docs/`, `rtl/` and `verif/`. Nothing
else is opened: no hidden test, no harness file, nothing under `src/`, `rundir/` or `tests/` (`test_only_visible_files_are_opened`).

**Score** (stdlib only, deterministic). Words are lower-cased identifiers (also split at `_`), stop words and one- or
two-letter words dropped, a plural `s` removed from words of five letters or more. An entry is described by its title,
keywords, section and "also" sections, and module name (port and parameter names are in the index but not scored: they
are the words every module shares). The score is the **share of an entry's words that the query holds, each weighted by
its idf over the entries**, `idf = ln(1 + (N - df + 0.5) / (df + 0.5))` (BM25's idf), so 1.0 means every descriptive word
of the entry is in what the agent can see. A plain BM25 sum was tried first on the 86 dev problems: it grows with the
length of the query and scored the same module (a CRC) top for unrelated problems, so it was replaced before anything was
chosen from it; the share does not grow with the query.

**Constants (chosen on the 86 dev problems only, never on the held-out 100):**

| | |
|---|---|
| k (examples per problem) | **2** |
| minimum score | **0.55** (on the 86: 13 problems reach it; 0.50 would give 19, 0.60 would give 7; chosen by reading the top matches on the dev problems: below about 0.5 they were matches on generic words such as register or clock, from 0.55 up they were named by the task's own topic, such as an async FIFO, a UART, an AES step or a RAM) |
| bytes shown per problem | at most **12,000** (a second example that does not fit is left out; a whole module that does not fit becomes its excerpt) |
| whole module | at most 250 lines |

If nothing clears the minimum, **the run is exactly arm R**. The second example needs the minimum score too.

**Where it goes.** One fixed block appended to the first user message, after R's whole message (task and rules), under
this lead-in, verbatim (one example: `Below is 1 module`, `it looks`, `It is an example`, `Use it`):

```
# Reference examples
Below are {n} modules from well-reviewed open-source hardware projects, picked automatically because they look related to this task. They are examples of how such designs are written, not part of the task: the task's own interface, names and timing rules come first. Use them as you see fit.
```

then, per example, `## Example <i>` and the module in a `systemverilog` fence, header line first. No other change to
prompts, tools, caps or settings.

## Keeping the examples clean

The pack stays complete; filtering happens at retrieval. Two deny-lists, agreed with the owner.

1. **Repo deny-list, for every CVDP run.** `openhwfoundation/cv32e40p`, `openhwfoundation/cva6` (the pack names the same
   projects `openhwgroup/...`; both spellings are denied), `lowRISC/ibex` and any repo whose name contains `ibex` (for
   example cheriot-ibex), and every `pulp-platform/*` repo. These are the projects the benchmark's tasks are drawn from.
   **Removed 49 of the pack's 86 entries** (`pulp-platform/common_cells` 27, `pulp-platform/axi` 5, `lowRISC/ibex` 8,
   `openhwgroup/cva6` 5, `openhwgroup/cv32e40p` 4). **37 remain:** `lowRISC/opentitan` 26, `chipsalliance/caliptra-rtl` 5,
   `nvdla/hw` 3, `Xilinx/open-nic-shell` 3, from 35 upstream files.
2. **Per-problem overlap deny-list.** An entry is withheld for a problem when its **source file** (the whole upstream file)
   and any of the problem's visible files share **a declared module (or package or interface) name**, or when **at least 10% of
   the source file's 5-line shingles** appear in the problem's visible text (prompt, `docs/`, `rtl/`, `verif/`). A shingle is 5
   consecutive non-empty lines of code with comments dropped, lower-cased and white space collapsed, counted only when it
   has at least 40 characters. Computed by the same function in the run and in the dry run; the dry run commits the result
   (ids and scores only) as `overlap_deny.csv`. **Removed on the 186 problems of the dry run: 0 entry-problem pairs**
   (no visible file shares a module name with, or any shingle with, a remaining entry); the rule is in force and tested
   (`test_overlap_rule_by_module_name_and_by_text`) but binds on none of today's problems.
3. Every withheld entry is logged per problem-run: `examples_withheld_repo` (49, the same for every problem) and
   `examples_withheld_overlap` in the CSV, and the overlap rows by id in `api_tools.jsonl`.

## Leak guard

`tools/leak_guard.py --reference <pack>/reference` adds the layer's own prose to the private windows: `README.md` and
`SOURCES.yaml`, every entry's title and keywords (from `INDEX.jsonl`), and every entry's sections other than `## Excerpt`
and `## Source` (so Pattern, When to use it, Pitfalls). The code fetched from the public repos (`examples_bundle/upstream`)
is public text, like the dataset. The excerpts and Source blocks are upstream code and attribution, so they are not
secrets. `sweep.yml` runs it on the work dir, `work.*` and the step summary, with the existing withhold rule; a match
anywhere else fails the job and uploads nothing. The examples bundle is written next to the work dir, not in it (it holds
index titles and public code), and is mounted read-only into the container as `/examples/bundle.json`; the pack's prose
is never mounted. Tests prove both directions (`test_guard_flags_pack_prose_and_passes_public_upstream_code`,
`test_guard_covers_index_text_and_the_readme`, `test_guard_cli_with_reference_only`).

## Planned runs

| Set | E | R |
|---|---|---|
| Held-out 100 (`split=m3g_heldout`) | 3 | 3 (M3j, reused) |
| The 86 (`split=agentic`, ids `tools/m3b_eval_ids.txt`) | 1 | 1 (M3j, reused; descriptive) |

One dispatch per seed (`seeds=1`, `seed_offset` 0, 1, 2), `runner=ubuntu-24.04-arm`, `threads=4`, model
`claude-haiku-5-5`, `fixed_checks=retrieved_examples`, `skill_pack=v4.0`, one sweep at a time. A `rate_limited` or
`run_budget_exhausted` row is not run and is rerun (as M3j). **This brief builds, tests, pre-registers, dry-runs and
smoke-runs; it dispatches no scored sweep.**

## Dry run of the retriever (free, local; committed before any smoke)

[`dry_run.md`](dry_run.md), with [`retrieval.csv`](retrieval.csv) and [`overlap_deny.csv`](overlap_deny.csv), made by
`tools/m3l_dry_run.py` from the dataset records' prompts and context files (never their `harness` tests). Ids and numbers only.

- **86 dev problems:** 13 get an example (11 one, 2 two); 73 get none (exactly arm R).
- **Held-out 100: 3 get an example; 97 get none.** The held-out problems carry their whole specification in the prompt and
  have no `docs/`, `rtl/` or `verif/` files, so the query is the prompt alone, and the prompt rarely holds enough of an
  entry's words to reach 0.55. The constants were chosen on the dev problems before this was looked at, and are **not**
  changed to fit the held-out set.

**Known limitation, stated before any scored run:** with 3 of 100 held-out problems receiving an example, E − R on the
held-out set can move through at most those 3 problems (9 of 300 problem-runs): it cannot show an effect of more than
about 3 points, below the ~5-point resolution of three runs. The held-out primary below is therefore close to a test of
R against itself plus noise. The 86 dev problems (13 with examples) are where the retriever has material, but they are
the development set and cannot confirm anything. The planner decides before dispatch whether to run as planned, to
re-register a lower minimum score on the dev set only (which would need a new dry run and an amendment here), or to
use the dev problems with several seeds as the working evidence.

## Primary and decision rule

**Primary: E − R on the held-out 100, the only primary comparison,** paired by problem, as in M3g to M3k
(`tools/ablate.py`): each problem's pass rate over its 3 runs per arm, the mean difference, a paired bootstrap interval over
problems (2,000 resamples) and the exact two-sided sign test (ties dropped), **95% intervals, no correction**; the sign test
is reported beside them and does not decide. **The decision rule is M3j's:** E is **better** if its interval lies wholly
above zero, **worse** if wholly below, otherwise **no detectable effect**, reported with the interval's ends as the largest
loss and gain it leaves open (bounds rounded before the verdict, as `ablate.py` does). M3j's R - PA half-width on this set,
with 3 runs, was 4.3 points at 95%; an effect smaller than that reads as no detectable effect.

**Secondary (exploratory, no correction, decide nothing):**
- the effect on problems that received an example, against those that did not (E − R within each group, same statistics);
- the label shift on the 86 (`tools/taxonomy.py`);
- tokens (prompt, completion, cache) and turns, per problem-run;
- how often the examples are copied: leak-guard `skill_text_copied` is not used here (the code is public); copying of
  upstream code is counted in the report by shingles shared between the final `rtl/` and the shown example.

## Cost and guards

The smoke's numbers are in [`smoke.md`](smoke.md), appended before any scored dispatch (see "Amendments"). Before the
smoke: R's repriced cost was $1.44 for 300 held-out problem-runs ($0.0048 each) and $0.81 for 92 on the 86; E differs from R
only for the problems that get an example (an example adds at most about 3,000 tokens to the first message and is cached
after the first call), so E should cost about R's, **about $0.5 per held-out dispatch and $0.85-0.9 per 86 dispatch**.

## What it cannot show

One model, one loop, one benchmark, one retrieval rule with one threshold. The pool after the deny-lists is 37 modules,
mostly OpenTitan, so a task is rarely close to one. A null says that these 37 modules, shown this way, did not move
Claude Haiku 5.5 on this loop, not that retrieved examples never help.

## Amendments

None yet.

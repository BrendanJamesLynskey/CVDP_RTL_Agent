Snapshot `b783931cbf160595`: 40 lessons, retrieved for 86 problems.

| Lesson | Retrieved for | Text |
|---|---|---|
| L01 | 1 | Treat compilation, lint, and synthesis as necessary but insufficient: run a focused self-test before submitting, especially after behavioral changes. |
| L02 | 40 | Build tests from the specification’s corner cases, not just typical operation; check control-signal priority, reset behavior, stalls, and boundary conditions. |
| L03 | 50 | Use the interface documentation and existing instantiations to verify every required port, parameter, width, and connection before implementing or changing a module. |
| L04 | 2 | When a hidden test exposes a behavioral bug, trace the exact failing condition and add a regression for it; do not rely on a broad implementation plan alone. |
| L05 | 2 | For arithmetic and counters, verify operand widths, signedness, overflow, and wraparound explicitly rather than assuming the language infers the intended behavior. |
| L06 | 33 | For asynchronous or buffered designs, test empty/full transitions, simultaneous activity, pointer wraparound, and data integrity across clock domains. |
| L07 | 0 | If repeated tool checks fail, inspect the first diagnostic and resolve the underlying build issue before spending more turns on speculative edits. |
| L08 | 0 | Treat the first compile or lint failure as a blocker: inspect the full diagnostic, fix its root cause, and rerun the exact failing check before making more changes. |
| L09 | 12 | Read the specification and existing implementation before editing. Trace how the changed logic connects to surrounding modules, reset behavior, and handshakes instead of patching from a guessed symptom. |
| L10 | 22 | Preserve specified module interfaces and any externally observed hierarchy, signal, and parameter names; verify them against the spec before submitting. |
| L11 | 3 | Test the behavior hidden tests are likely to exercise, not just syntax: cover reset, boundary cases, transaction completion, and interactions across module boundaries. |
| L12 | 2 | Run a focused self-check after each meaningful change, then run the full available checks. A passing compile or a narrow test does not establish functional correctness. |
| L13 | 30 | When a test fails, use its first failing assertion to trace the expected behavior through the design and integration; do not assume a locally plausible implementation satisfies the system-level contract. |
| L14 | 2 | Use the available turn budget to converge: prefer a small, reviewable change and reserve time for a final compile, lint, and relevant behavioral test. |
| L15 | 29 | Treat the specification’s interface as exact: preserve required ports, parameters, module names, and any hierarchy the testbench may inspect. |
| L16 | 16 | Derive behavior from the specification and existing design conventions; do not assume standard defaults or address and state interpretations. |
| L17 | 0 | Resolve compile and lint failures before submission. A passing synthesis run or local testbench does not make other build failures safe to ignore. |
| L18 | 5 | Make self-checks exercise boundary cases, reset and recovery, and simultaneous or invalid operations—not just typical successful transactions. |
| L19 | 5 | Keep required source-file and submodule organization intact, and verify the design with the same kinds of build checks the submission harness is likely to use. |
| L20 | 3 | Work incrementally: make a focused change, run the relevant checks, and fix the first failure before adding more changes. |
| L21 | 6 | Budget time for validation; repeated failed tool runs without narrowing the cause are less useful than a minimal fix followed by a targeted test. |
| L22 | 1 | Treat synthesis failures as unresolved defects, even when compilation and lint pass. Do not submit until every required build check succeeds or you understand and justify a tool limitation. |
| L23 | 10 | Build a self-checking testbench before submission. Exercise the full behavioral contract, including corner cases, reset, stalls, and each supported operation—not just compilation or a few typical inputs. |
| L24 | 2 | When a self-check fails, use the failing case to isolate the defect, then rerun the complete test suite after each fix. Do not submit with a known failing test. |
| L25 | 9 | For arithmetic and encoding logic, test boundary values and combinations that challenge ordering, alignment, signedness, rounding, and special cases against an independent reference. |
| L26 | 4 | Read the specification and existing project structure before editing. Preserve required interfaces, hierarchy, and externally inspected internal objects unless the task explicitly permits changing them. |
| L27 | 4 | Keep changes focused, and verify that reset behavior, handshakes, and state updates match the stated timing and polarity conventions. |
| L28 | 0 | Manage time for validation: reserve turns for resolving build and test failures rather than spending the entire budget on implementation. |
| L29 | 20 | Read the specification and interface tables before editing. Preserve exact port names, widths, parameters, and expected hierarchy; hidden tests may access them directly. |
| L30 | 0 | For a repair task, trace the existing implementation and its dependencies before changing it. Make the smallest targeted fix rather than rewriting surrounding logic. |
| L31 | 19 | Use related, working designs as references for protocol conventions, but verify that their behavior matches the current specification. |
| L32 | 1 | Treat compile, lint, and synthesis failures as blockers. Resolve warnings or tool incompatibilities that indicate questionable RTL before submitting. |
| L33 | 1 | Build self-checks around protocol corner cases, not just typical transfers: independent handshakes, backpressure, reset, simultaneous events, and boundary conditions. |
| L34 | 9 | After the final edit, rerun the checks and testbench. A passing test from before the last change does not validate the submitted design. |
| L35 | 24 | Check timing and accounting carefully: verify when state updates occur and that events arriving together, or while output is blocked, are neither lost nor duplicated. |
| L36 | 4 | Treat compiler and linter failures as blockers: inspect the first diagnostic, make a focused correction, and rerun checks before attempting further RTL changes. |
| L37 | 36 | Turn the specification and any failure description into a precise cycle-by-cycle expectation; do not rely on a plausible diagnosis without checking the surrounding control logic. |
| L38 | 0 | Run a focused testbench for the reported behavior, then add cases for reset, stalls, boundary conditions, and competing transactions where relevant. |
| L39 | 21 | Check timing as well as values: verify when state and counters advance, especially around valid/ready handshakes and phase transitions. |
| L40 | 2 | After the final edit, rerun compilation and the relevant tests; earlier passing checks do not validate later changes. |


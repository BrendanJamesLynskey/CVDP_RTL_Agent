Snapshot `0ceb24db0ad46853`: 8 lessons, retrieved for 86 problems.

| Lesson | Retrieved for | Text |
|---|---|---|
| L01 | 77 | Before submitting, compare every port, parameter and module name in the task prompt and the spec's interface tables with your top module; the hidden testbench reads them by exactly those names. |
| L02 | 71 | Keep the clock and reset names the spec uses (for example a bus clock named in the spec) instead of generic names like clk or rst. |
| L03 | 71 | When the spec describes internal registers or a state machine by name, declare them with those names at the top level of the module; tests may read them. |
| L04 | 46 | Do not stop at a clean compile: write a small self-checking testbench that drives the spec's examples and corner cases, and compare against expected values. |
| L05 | 19 | Compile with every file the task lists, using the top module the task names, so the build matches what the hidden tests will run. |
| L06 | 69 | If your own testbench passes on the first try, add a check for reset values, back-to-back transactions and the widest parameter values before submitting. |
| L07 | 23 | When the task says to reuse existing modules, instantiate them with their existing port names and parameters rather than rewriting them. |
| L08 | 54 | Keep parameters overridable (declare them as module parameters with the spec's defaults) so a test can set them by name. |


"""Prompt text. The hidden test harness is not in the container; the prompts say so and never ask for it."""

SYSTEM = """You are an RTL design engineer. You write and fix synthesizable SystemVerilog and Verilog.
The task's files are under /code: docs/ (specifications), rtl/ (design), verif/ (verification files).
You can change files only under rtl/, verif/ and docs/. You may write your own scratch testbench under
rundir/agent_tb/; it is never submitted. The grader's tests are hidden and are not in this container: do not look
for them. Check your own work with the tools offered before you submit."""

PLAN = """# Task
{task}

# Files under /code
{listing}

# File contents
{contents}

# Tools available
{tools}

Make a plan. Reply with one JSON object only:
{{"files_to_change": ["rtl/<file>", ...],
  "approach": "<how you will change them, in a few sentences: module names, ports, behaviour>",
  "check_plan": "<how you will check the result: {check_options}>"}}"""

EDIT = """# Task
{task}

# Plan
{plan}

# Current files
{contents}
{feedback}
Make the changes now. Your reply is applied to the files automatically and the checks you choose then run on
them; you will see the results next turn. If a file needs no change, leave it out. Use one block per file, either
the whole new file:
<file path="rtl/name.sv">
...complete file contents...
</file>
or a unified diff against the current file:
<diff path="rtl/name.sv">
@@ -10,3 +10,4 @@
 unchanged line
-old line
+new line
</diff>
Paths must be under rtl/, verif/ or docs/. Keep every module name and port the task and the specification ask for.
{tb_instructions}
Finally, choose the checks to run, from: {check_options}
<checks>compile,...</checks>"""

TB_ON = """You may also write a small self-checking testbench to try the design (scratch only, never submitted):
a plain SystemVerilog one that prints AGENT_TB_PASS when all checks pass and uses $error on a mismatch,
<tb path="agent_tb/tb_name.sv" top="tb_name">
...
</tb>
or a cocotb test (Python; `top` is the design's top module):
<tb path="agent_tb/test_name.py" top="dut_module">
...
</tb>
or, to run a testbench that is already under verif/, name it with an empty body:
<tb path="verif/existing_tb.sv" top="existing_tb"></tb>
Keep simulations short (they time out after a minute) and do not dump waveforms."""

TB_OFF = "Do not write a testbench."

FEEDBACK = """
# Results of your last change (turn {turn})
{edit_errors}{results}

# Your note when you decided to edit again
{reason}
"""

REFLECT = """# Task
{task}

# Plan
{plan}

# What you changed this turn
{changed}

# Check results
{results}

You have used {turn} of {max_turns} turns and ${spent:.4f} of ${budget:.2f}.
Decide what to do next. Reply with one JSON object only:
{{"decision": "edit_again" | "submit" | "give_up", "reason": "<one or two sentences>"}}
Submit when the design compiles and your checks pass. Edit again if something you can fix failed.
Give up only if you cannot make progress."""

# M3b: the lessons memory's retrieved lessons, appended to the plan prompt (and the Deep Agents task) when a
# snapshot is set. Nothing is appended without one.
LESSONS = """

# Lessons from other problems
General advice learned on other problems (not on this one). Use what applies here:
{lessons}"""

# M3g: the knowledge pack. The plan prompt gets the pack's INDEX.md as it is, and the plan names skills; their text
# then goes into every edit prompt, after the plan. Nothing is added without a pack.
SKILLS_INDEX = """

# Skills you can load
A pack of general RTL design know-how (not written for this task). Its index follows. Choose at most {k} skills that
fit this task and add them to your JSON reply as "skills": ["<name>", ...], most useful first. Their full text is
then shown to you while you write the design. Leave the list empty if none fit.
{index}"""

SKILLS_LOADED = """

# Skills loaded (chosen in your plan)
{bodies}"""

# Added to the messages for the one retry after an empty reply, and after an unparseable reflect reply.
ANSWER_ONLY = """Your last reply was empty. Reply now with the answer only, in the format asked for above, with no
reasoning, no tool calls and nothing else."""

JSON_ONLY = """Your last reply could not be read as a decision. Reply with the JSON object only, nothing else:
{"decision": "edit_again" | "submit" | "give_up", "reason": "<one or two sentences>"}"""


def check_options(cfg, tools):
    opts = ["compile"]
    if cfg.lint:
        if tools.get("verilator"):
            opts.append("lint")
        if tools.get("yosys"):
            opts.append("synth")
    if cfg.self_check:
        opts.append("testbench")
    return ", ".join(opts)


# M3d, spec_vectors: the blind reviewer's prompt. It is given the task, the documents and a port table of the given
# RTL (names, directions, widths: never a module body), never the RTL itself, verif/ or anything the agent wrote.
SPEC_SYSTEM = """You are a verification engineer. You write reference test cases for a hardware module from its
specification alone. You have not seen any implementation, and you never will."""

SPEC = """# Task given to the designer
{task}

# Specification documents
{docs}

# Ports of the modules already given (from the original files, before any change)
{ports}

Write test cases that the finished design must pass, from the specification above alone. They are turned into a
SystemVerilog testbench automatically, with these rules:
- Every input listed under "ports" starts at 0 and keeps its value until a step changes it.
- With a "clock" port, it toggles every 5 ns, starting low (rising edges at 5, 15, 25 ns, ...). Each step sets its
  "in" values just after a rising edge, waits for the next rising edge, and compares "expect" 1 ns after that edge.
  "expect_now" is compared 1 ns after the inputs are set, before the edge. "wait": n adds n more rising edges
  before "expect" is compared. "until": {{"signal": "done", "value": 1, "max_cycles": 50}} keeps clocking until
  that output has that value (the case fails if it never does), then compares "expect".
- With "clock": null (purely combinational), each step sets "in", waits 1 ns and compares "expect".
- Values are integers, or strings "0x1f", "0b101", "-3" (two's complement at the port's width), or one ASCII
  character in single quotes, "'G'" (its code; "'\\r'" is not allowed, write 13). Leave a signal out
  of "expect", or give "x", where the specification does not fix its value at that time.
- Steps of one case run in order; cases run one after another in one simulation, without a new reset unless a
  case drives one itself.

Rules for you:
- Use only module names, port names, parameters and behaviour the specification or the task states. List every
  port of the top module you test under "ports", with its direction and its width at the parameter values used.
- Cover the specification's own examples, its edge and error cases, and any latency, count, period or flag it
  states. 4 to 12 cases, at most 60 steps each.
- Only expect what the specification makes unambiguous. If a value or a cycle count is not fixed by it, leave that
  output out of "expect" at that step (use "until" when only the order of events is stated).
- Start each case that needs it with a reset, and hold the reset for at least 2 steps.

Reply with one JSON object only:
{{"top": "<module name>",
  "params": {{"<NAME>": <integer>}},
  "clock": "<clock port>" | null,
  "ports": {{"<port>": {{"dir": "in" | "out", "width": <integer>}}}},
  "cases": [{{"name": "<short_name>",
             "steps": [{{"in": {{"<port>": <value>}}, "expect_now": {{}}, "wait": 0,
                        "until": null, "expect": {{"<port>": <value>}}}}]}}]}}"""

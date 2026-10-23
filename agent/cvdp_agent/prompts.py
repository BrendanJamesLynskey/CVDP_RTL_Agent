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

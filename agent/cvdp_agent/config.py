"""Run settings, all from environment variables so the harness can pass them through CVDP_AGENT_ENV."""
import os
from dataclasses import dataclass, field


def _flag(name, default):
    v = os.environ.get(name)
    if v is None or v.strip() == "":
        return default
    return v.strip().lower() not in ("0", "false", "no", "off")


def _num(name, default, cast):
    v = os.environ.get(name)
    if v is None or v.strip() == "":
        return default
    return cast(v)


@dataclass
class Config:
    root: str = "/code"                 # the mounted task tree
    provider: str = "openrouter"        # fake | openrouter
    model: str = ""                     # OpenRouter model ID
    max_turns: int = 10                 # edit -> check -> reflect cycles
    budget_usd: float = 0.10            # per problem, provider-reported cost
    wall_s: float = 480.0               # under the harness's default agent timeout (600 s)
    self_check: bool = True             # write and run a self-written testbench
    lint: bool = True                   # verilator --lint-only and the yosys read/synth check
    reasoning: str = "default"          # default | low | medium | high | off (OpenRouter's reasoning effort)
    seed: str = ""                      # repeat number from the sweep; a label only (sampling is not seeded)
    provider_order: list = field(default_factory=list)  # OpenRouter providers to use, in order, no fallbacks
    harness: str = "langgraph"          # langgraph (the M1-M3 agent) | deepagents (LangGraph's Deep Agents, M3b)
    max_rounds: int = 22                # deepagents: model calls (tool-call rounds); M2's worst case for 10 turns
    memory: str = ""                    # a lessons snapshot (JSON, tools/learn_lessons.py); blank = no memory
    memory_k: int = 5                   # lessons retrieved into the plan prompt
    mutation_gate: bool = False         # M3c: a mutation-score gate on the agent's own testbench before submit
    interface_check: bool = False       # M3c: the design's interface, by elaboration, against the given one
    gate_mutants: int = 12              # mutants per gate run (Yosys mutate -list N)
    gate_seed: int = 1                  # mutate -seed: the same mutants for the same design
    gate_threshold: float = 0.5         # kill rate the gate needs (equivalent mutants make 1.0 unreachable)
    gate_s: float = 60.0                # the gate's own wall time per run
    gate_max_failures: int = 2          # gate failures per problem; after that, the agent submits anyway
    out_dir: str = ""                   # default <root>/rundir/agent_out
    fake_script: str = ""               # fake provider: a JSON file or inline JSON list of responses
    ledger_dir: str = ""                # whole-run spend guard: shared directory of per-problem costs
    run_budget_usd: float | None = None # whole-run spend guard: stop starting work once the ledger passes this
    tool_timeout_s: float = 60.0        # per deterministic tool call
    finalize_s: float = 30.0            # finalize's own time after the wall cap (its compile)
    max_context_chars: int = 120_000    # files shown to the LLM, in total
    extra: dict = field(default_factory=dict)

    @property
    def agent_out(self):
        return self.out_dir or os.path.join(self.root, "rundir", "agent_out")

    def switches(self):
        return {
            "self_check": self.self_check,
            "lint": self.lint,
            "max_turns": self.max_turns,
            "budget_usd": self.budget_usd,
            "wall_s": self.wall_s,
            "reasoning": self.reasoning,
            "provider_order": ",".join(self.provider_order),
            # M3b settings appear only when set, so an M1-M3 agent's summary keeps exactly its old fields
            **({"harness": self.harness, "max_rounds": self.max_rounds} if self.harness != "langgraph" else {}),
            **({"memory": self.memory} if self.memory else {}),
            # M3c switches, likewise only when on
            **({"mutation_gate": True} if self.mutation_gate else {}),
            **({"interface_check": True} if self.interface_check else {}),
        }


def _reasoning(name):
    from .llm import REASONING

    v = (os.environ.get(name) or "default").strip().lower()
    if v not in REASONING:
        raise ValueError(f"{name} must be one of {', '.join(REASONING)}, got {v!r}")
    return v


def _harness(name):
    v = (os.environ.get(name) or "langgraph").strip().lower()
    if v not in ("langgraph", "deepagents"):
        raise ValueError(f"{name} must be langgraph or deepagents, got {v!r}")
    return v


def from_env():
    rb = os.environ.get("CVDP_RUN_BUDGET_USD", "").strip()
    return Config(
        root=os.environ.get("CVDP_ROOT", "/code"),
        provider=os.environ.get("CVDP_PROVIDER", "openrouter").strip().lower(),
        model=os.environ.get("CVDP_MODEL", "").strip(),
        max_turns=_num("CVDP_MAX_TURNS", 10, int),
        budget_usd=_num("CVDP_BUDGET_USD", 0.10, float),
        wall_s=_num("CVDP_WALL_S", 480.0, float),
        self_check=_flag("CVDP_SELF_CHECK", True),
        lint=_flag("CVDP_LINT", True),
        reasoning=_reasoning("CVDP_REASONING"),
        seed=os.environ.get("CVDP_SEED", "").strip(),
        provider_order=[p.strip() for p in os.environ.get("CVDP_PROVIDER_ORDER", "").split(",") if p.strip()],
        harness=_harness("CVDP_HARNESS"),
        max_rounds=_num("CVDP_MAX_ROUNDS", 22, int),
        memory=os.environ.get("CVDP_MEMORY", "").strip(),
        mutation_gate=_flag("CVDP_MUTATION_GATE", False),
        interface_check=_flag("CVDP_INTERFACE_CHECK", False),
        out_dir=os.environ.get("CVDP_OUT_DIR", ""),
        fake_script=os.environ.get("CVDP_FAKE_SCRIPT", ""),
        ledger_dir=os.environ.get("CVDP_LEDGER_DIR", ""),
        run_budget_usd=float(rb) if rb else None,
        tool_timeout_s=_num("CVDP_TOOL_TIMEOUT_S", 60.0, float),
    )

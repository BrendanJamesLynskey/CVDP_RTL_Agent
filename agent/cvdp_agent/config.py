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
    provider: str = "openrouter"        # fake | openrouter | claude_plan | claude_openrouter | claude_api (claudecode)
                                    # | anthropic (apiloop: the Anthropic API, an API key; M3j)
    model: str = ""                     # OpenRouter model ID
    max_turns: int = 10                 # edit -> check -> reflect cycles
    budget_usd: float = 0.10            # per problem, provider-reported cost
    wall_s: float = 480.0               # under the harness's default agent timeout (600 s)
    self_check: bool = True             # write and run a self-written testbench
    lint: bool = True                   # verilator --lint-only and the yosys read/synth check
    reasoning: str = "default"          # default | low | medium | high | off (OpenRouter's reasoning effort)
    seed: str = ""                      # repeat number from the sweep; a label only (sampling is not seeded)
    provider_order: list = field(default_factory=list)  # OpenRouter providers to use, in order, no fallbacks
    data_collection: str = ""           # F1B: "deny" = OpenRouter routes only to providers that collect no data
    harness: str = "langgraph"          # langgraph (the M1-M3 agent) | deepagents (LangGraph's Deep Agents, M3b)
                                        # | claudecode (Claude Code headless on the owner's plan, a comparison)
                                    # | apiloop (M3j: a plain Messages API tool loop, no Claude Code)
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
    verify_submit: bool = False         # M3d: a submit is refused until the current design passed a simulation
    spec_vectors: bool = False          # M3d: verify_submit plus reference cases written blind from the spec
    verify_max_refusals: int = 2        # refusals per problem; after that, the submit is let through
    skills: str = ""                    # M3g: a knowledge pack directory (INDEX.md, skills, MANIFEST.sha256); blank = none
    skills_max: int = 3                 # M3g: skills the plan may load
    skills_cap_bytes: int = 13_000      # M3g: loaded skill text per edit prompt, at most
    skill_pack: str = ""                # M3h: a tag of the private pack (native_skills.PINNED); blank = none
    skill_pack_dir: str = ""            # M3h: the pack's generic/ directory, mounted read-only (claudecode only)
    skill_hint: bool = False            # M3h S2c: a one-line user CLAUDE.md saying the skills are installed
    cc_profile: str = "default"         # M3i: "plain" = Claude Code with our system prompt and four tools (claudecode only)
                                    # M3j: "bare" = plain plus --bare (needs an API key: provider claude_api)
    presubmit_iface: bool = False       # M3k arm K (apiloop): one interface/file/compile check when the model finishes
    timing_claims: bool = False         # M3k arm T (apiloop): one extra first turn listing the task's cycle-level claims
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
            # M3d switches, likewise only when on
            **({"verify_submit": True} if self.verify_submit else {}),
            **({"spec_vectors": True} if self.spec_vectors else {}),
            # M3g, likewise only when set
            **({"skills": self.skills} if self.skills else {}),
            # M3h, likewise only when set
            **({"skill_pack": self.skill_pack} if self.skill_pack else {}),
            **({"skill_hint": True} if self.skill_hint else {}),
            # M3i, likewise only when set
            **({"cc_profile": self.cc_profile} if self.cc_profile != "default" else {}),
            # M3k, likewise only when on
            **({"presubmit_iface": True} if self.presubmit_iface else {}),
            **({"timing_claims": True} if self.timing_claims else {}),
            # F1B, likewise only when set
            **({"data_collection": self.data_collection} if self.data_collection else {}),
        }

    def __post_init__(self):
        if self.spec_vectors:  # S is V plus the spec cases: the spec testbench is applied by V's rule
            self.verify_submit = True
        if self.skills and self.harness != "langgraph":  # M3g: the pack is loaded by the LangGraph graph's nodes
            raise ValueError("CVDP_SKILLS is a step of the LangGraph graph: use CVDP_HARNESS=langgraph")
        if (self.skill_pack or self.skill_hint) and self.harness != "claudecode":  # M3h: Claude Code's own skills
            raise ValueError("CVDP_SKILL_PACK installs Claude Code skills: use CVDP_HARNESS=claudecode")
        if self.skill_hint and not self.skill_pack:
            raise ValueError("CVDP_SKILL_HINT needs CVDP_SKILL_PACK")
        if self.cc_profile not in ("default", "plain", "bare"):
            raise ValueError(f"CVDP_CC_PROFILE must be default, plain or bare, got {self.cc_profile!r}")
        if self.cc_profile != "default" and self.harness != "claudecode":
            raise ValueError("CVDP_CC_PROFILE=plain or bare is a Claude Code profile: use CVDP_HARNESS=claudecode")
        if self.cc_profile in ("plain", "bare") and (self.skill_pack or self.skill_hint):
            raise ValueError("CVDP_CC_PROFILE=plain or bare has no skills: it cannot take a skill pack")
        if self.cc_profile == "bare" and self.provider != "claude_api":  # --bare never reads the plan's OAuth token
            raise ValueError("CVDP_CC_PROFILE=bare needs an API key: use CVDP_PROVIDER=claude_api")
        if self.harness == "apiloop" and self.provider not in ("anthropic", "fake"):
            raise ValueError("CVDP_HARNESS=apiloop calls the Anthropic API: use CVDP_PROVIDER=anthropic")
        if (self.presubmit_iface or self.timing_claims) and self.harness != "apiloop":
            raise ValueError("CVDP_PRESUBMIT_IFACE and CVDP_TIMING_CLAIMS are steps of the apiloop harness")
        if self.presubmit_iface and self.timing_claims:
            raise ValueError("CVDP_PRESUBMIT_IFACE and CVDP_TIMING_CLAIMS are separate arms")


def _reasoning(name):
    from .llm import REASONING

    v = (os.environ.get(name) or "default").strip().lower()
    if v not in REASONING:
        raise ValueError(f"{name} must be one of {', '.join(REASONING)}, got {v!r}")
    return v


def _harness(name):
    v = (os.environ.get(name) or "langgraph").strip().lower()
    if v not in ("langgraph", "deepagents", "claudecode", "apiloop"):
        raise ValueError(f"{name} must be langgraph, deepagents, claudecode or apiloop, got {v!r}")
    return v


def _data_collection(name):
    v = (os.environ.get(name) or "").strip().lower()
    if v not in ("", "deny"):
        raise ValueError(f"{name} must be blank or deny, got {v!r}")
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
        data_collection=_data_collection("CVDP_DATA_COLLECTION"),
        harness=_harness("CVDP_HARNESS"),
        max_rounds=_num("CVDP_MAX_ROUNDS", 60 if _harness("CVDP_HARNESS") in ("claudecode", "apiloop") else 22, int),
        memory=os.environ.get("CVDP_MEMORY", "").strip(),
        mutation_gate=_flag("CVDP_MUTATION_GATE", False),
        interface_check=_flag("CVDP_INTERFACE_CHECK", False),
        verify_submit=_flag("CVDP_VERIFY_SUBMIT", False),
        spec_vectors=_flag("CVDP_SPEC_VECTORS", False),
        presubmit_iface=_flag("CVDP_PRESUBMIT_IFACE", False),
        timing_claims=_flag("CVDP_TIMING_CLAIMS", False),
        skills=os.environ.get("CVDP_SKILLS", "").strip(),
        skills_cap_bytes=_num("CVDP_SKILLS_CAP_BYTES", 13_000, int),
        skill_pack=os.environ.get("CVDP_SKILL_PACK", "").strip(),
        skill_pack_dir=os.environ.get("CVDP_SKILL_PACK_DIR", "").strip(),
        skill_hint=_flag("CVDP_SKILL_HINT", False),
        cc_profile=(os.environ.get("CVDP_CC_PROFILE") or "default").strip().lower(),
        out_dir=os.environ.get("CVDP_OUT_DIR", ""),
        fake_script=os.environ.get("CVDP_FAKE_SCRIPT", ""),
        ledger_dir=os.environ.get("CVDP_LEDGER_DIR", ""),
        run_budget_usd=float(rb) if rb else None,
        tool_timeout_s=_num("CVDP_TOOL_TIMEOUT_S", 60.0, float),
    )

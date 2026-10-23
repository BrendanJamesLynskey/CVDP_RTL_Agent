"""LLM providers. Each call returns its text and the usage the provider reported. Cost is never estimated: a call
whose provider reports no cost is recorded with cost None."""
import json
import os
import time
from dataclasses import dataclass

OPENROUTER_BASE = "https://openrouter.ai/api/v1"


@dataclass
class LLMResult:
    text: str
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    cost: float | None
    latency_s: float
    generation_id: str | None = None


class FakeLLM:
    """Scripted and deterministic, for tests and the CI smoke run. Each response is a dict
    {"text": ..., "cost": float|None, "prompt_tokens": int, "completion_tokens": int, "node": optional, "sleep": s}
    or a plain string. Responses are taken in order; when the script runs out, `default(node)` answers."""

    model = "fake"

    def __init__(self, script=None, clock=None):
        self.script = list(script or [])
        self.calls = []
        self.clock = clock

    @classmethod
    def from_spec(cls, spec):
        if not spec:
            return cls()
        if os.path.exists(spec):
            with open(spec) as f:
                spec = f.read()
        return cls(json.loads(spec))

    def invoke(self, node, messages, max_tokens=None, timeout=None):
        self.calls.append(node)
        item = self.script.pop(0) if self.script else {"text": default(node)}
        if isinstance(item, str):
            item = {"text": item}
        if item.get("raise"):
            raise RuntimeError(item["raise"])
        if item.get("sleep") and self.clock is not None:
            self.clock.advance(item["sleep"])
        text = item.get("text") or default(node)
        prompt_chars = sum(len(m["content"]) for m in messages)
        return LLMResult(
            text=text,
            model=self.model,
            prompt_tokens=item.get("prompt_tokens", prompt_chars // 4),
            completion_tokens=item.get("completion_tokens", len(text) // 4),
            cost=item.get("cost", 0.0),
            latency_s=0.0,
        )


SMOKE_TB = """module agent_smoke_tb;
  initial begin
    $display("AGENT_TB_PASS smoke");
    $finish;
  end
endmodule
"""


def default(node):
    """The fake provider's answers when unscripted: a plan, an edit that writes only a scratch testbench (so every
    check runs on the real tools, and nothing is submitted), then submit."""
    if node == "plan":
        return json.dumps({"files_to_change": [], "approach": "fake provider: no design change",
                           "check_plan": "compile, lint, a smoke testbench"})
    if node == "edit":
        return ("<checks>compile,lint,synth,testbench</checks>\n"
                f'<tb path="agent_tb/agent_smoke_tb.sv" top="agent_smoke_tb">\n{SMOKE_TB}</tb>\n')
    if node == "reflect":
        return json.dumps({"decision": "submit", "reason": "fake provider"})
    return ""


class OpenRouterLLM:
    def __init__(self, model, timeout_s=120.0):
        from langchain_openai import ChatOpenAI  # imported here so tests need no network client

        if not model:
            raise ValueError("CVDP_MODEL is not set")
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise ValueError("OPENROUTER_API_KEY is not set")
        self.model = model
        self._key = key
        self._chat = ChatOpenAI(model=model, api_key=key, base_url=OPENROUTER_BASE, timeout=timeout_s,
                                max_retries=1, temperature=0.2, extra_body={"usage": {"include": True}})

    def invoke(self, node, messages, max_tokens=None, timeout=None):
        from langchain_core.messages import HumanMessage, SystemMessage

        msgs = [SystemMessage(m["content"]) if m["role"] == "system" else HumanMessage(m["content"])
                for m in messages]
        t0 = time.monotonic()
        opts = {k: v for k, v in (("max_tokens", max_tokens), ("timeout", timeout)) if v}
        r = self._chat.bind(**opts).invoke(msgs)
        latency = time.monotonic() - t0
        usage = (r.response_metadata or {}).get("token_usage") or {}
        gen_id = (r.response_metadata or {}).get("id")
        cost = usage.get("cost")
        if cost is None and gen_id:
            cost = self._generation_cost(gen_id)
        text = r.content if isinstance(r.content, str) else "".join(
            c.get("text", "") for c in r.content if isinstance(c, dict))
        return LLMResult(
            text=text,
            model=(r.response_metadata or {}).get("model_name") or self.model,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            cost=float(cost) if cost is not None else None,
            latency_s=latency,
            generation_id=gen_id,
        )

    def _generation_cost(self, gen_id, budget_s=10.0):
        """Fallback: OpenRouter's generation endpoint, which can lag the response by a second or two. Never takes
        more than `budget_s` in all, so it cannot push the agent past its wall cap."""
        import httpx

        end = time.monotonic() + budget_s
        for wait in (1, 2, 4):
            if time.monotonic() + wait + 1 > end:
                break
            time.sleep(wait)
            try:
                r = httpx.get(f"{OPENROUTER_BASE}/generation", params={"id": gen_id},
                              timeout=max(1.0, min(5.0, end - time.monotonic())),
                              headers={"Authorization": f"Bearer {self._key}"})
                if r.status_code == 200:
                    cost = (r.json().get("data") or {}).get("total_cost")
                    if cost is not None:
                        return cost
            except httpx.HTTPError:
                pass
        return None


def make(cfg, clock=None):
    if cfg.provider == "fake":
        return FakeLLM.from_spec(cfg.fake_script)
    if cfg.provider == "openrouter":
        return OpenRouterLLM(cfg.model)
    raise ValueError(f"unknown CVDP_PROVIDER {cfg.provider!r}")

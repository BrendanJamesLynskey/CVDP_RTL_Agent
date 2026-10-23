"""LLM providers. Each call returns its text and the usage the provider reported. Cost is never estimated: a call
whose provider reports no cost is recorded with cost None."""
import json
import os
import time
from dataclasses import dataclass

OPENROUTER_BASE = "https://openrouter.ai/api/v1"

# CVDP_REASONING: how much the model may reason. "default" sends no `reasoning` field (the model's own default);
# the others send OpenRouter's `reasoning: {effort, exclude: true}`, so reasoning text never reaches the reply.
REASONING = ("default", "low", "medium", "high", "off")
# One step lower, for the retry after an empty reply. Low goes straight to off: not every model lists "minimal"
# (DeepSeek V4.1 Flash does not), and OpenRouter maps an unlisted effort to the nearest one, which can be low again.
LOWER = {"high": "medium", "medium": "low", "default": "low", "low": "off", "off": "off"}


def reasoning_body(level):
    """The request's `reasoning` field for a level, or None for "default" (field left out)."""
    if not level or level == "default":
        return None
    return {"effort": "none" if level == "off" else level, "exclude": True}


class ReasoningRejected(Exception):
    """The provider refused the request because of its `reasoning` field (HTTP 400). Nothing was generated."""


@dataclass
class LLMResult:
    text: str
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    cost: float | None
    latency_s: float
    generation_id: str | None = None
    reasoning_tokens: int | None = None   # usage.completion_tokens_details.reasoning_tokens, as reported
    finish_reason: str | None = None
    provider: str | None = None           # the provider OpenRouter routed the call to


class FakeLLM:
    """Scripted and deterministic, for tests and the CI smoke run. Each response is a dict
    {"text": ..., "cost": float|None, "prompt_tokens": int, "completion_tokens": int, "reasoning_tokens": int,
    "sleep": s (fake clock), "real_sleep": s, "provider": name} or a plain string ("text": "" is an empty reply). Responses are taken in order; when the script runs
    out, `default(node)` answers. With `rejects_reasoning`, any request that carries a `reasoning` field is refused
    the way OpenRouter refuses it (before generating anything), and the scripted response is kept for the next call.
    Every request body's `reasoning` field is recorded in `requests`."""

    model = "fake"

    def __init__(self, script=None, clock=None, rejects_reasoning=False):
        self.script = list(script or [])
        self.calls = []
        self.requests = []
        self.clock = clock
        self.rejects_reasoning = rejects_reasoning

    @classmethod
    def from_spec(cls, spec):
        if not spec:
            return cls()
        if os.path.exists(spec):
            with open(spec) as f:
                spec = f.read()
        return cls(json.loads(spec))

    def invoke(self, node, messages, max_tokens=None, timeout=None, reasoning="default", max_retries=None):
        body = {"reasoning": reasoning_body(reasoning)}
        self.requests.append({"node": node, "body": body, "messages": messages, "max_tokens": max_tokens,
                              "timeout": timeout, "max_retries": max_retries})
        if self.rejects_reasoning and body["reasoning"] is not None:
            raise ReasoningRejected("HTTP 400: this model does not support the reasoning parameter")
        self.calls.append(node)
        item = self.script.pop(0) if self.script else {"text": default(node)}
        if isinstance(item, str):
            item = {"text": item}
        if item.get("raise"):
            raise RuntimeError(item["raise"])
        if item.get("sleep") and self.clock is not None:
            self.clock.advance(item["sleep"])
        if item.get("real_sleep"):  # a provider that really does not answer in time
            time.sleep(item["real_sleep"])
        text = item["text"] if item.get("text") is not None else default(node)
        prompt_chars = sum(len(m["content"]) for m in messages)
        return LLMResult(
            text=text,
            model=self.model,
            prompt_tokens=item.get("prompt_tokens", prompt_chars // 4),
            completion_tokens=item.get("completion_tokens", len(text) // 4),
            cost=item.get("cost", 0.0),
            latency_s=item.get("latency_s", 0.0),
            reasoning_tokens=item.get("reasoning_tokens"),
            finish_reason=item.get("finish_reason", "stop"),
            provider=item.get("provider", "fake"),
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
    """OpenRouter's chat completions endpoint through the `openai` client, called directly (not through langchain)
    so the whole response is kept: the `provider` that served the call, `usage.cost` and the reasoning-token
    count. `provider_order` pins OpenRouter's routing (`provider: {order, allow_fallbacks: false}`)."""

    def __init__(self, model, timeout_s=120.0, http_client=None, provider_order=None):
        import openai  # imported here so tests need no network client

        if not model:
            raise ValueError("CVDP_MODEL is not set")
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise ValueError("OPENROUTER_API_KEY is not set")
        self.model = model
        self._key = key
        self.provider_order = [p for p in (provider_order or []) if p]
        extra = {"http_client": http_client} if http_client is not None else {}
        self._client = openai.OpenAI(api_key=key, base_url=OPENROUTER_BASE, timeout=timeout_s, max_retries=1,
                                     **extra)

    def request_body(self, reasoning):
        """The OpenRouter-specific part of the request body."""
        body = {"usage": {"include": True}}
        rb = reasoning_body(reasoning)
        if rb is not None:
            body["reasoning"] = rb
        if self.provider_order:
            body["provider"] = {"order": self.provider_order, "allow_fallbacks": False}
        return body

    def invoke(self, node, messages, max_tokens=None, timeout=None, reasoning="default", max_retries=None):
        import openai

        t0 = time.monotonic()
        body = self.request_body(reasoning)
        opts = {k: v for k, v in (("timeout", timeout), ("max_retries", max_retries)) if v is not None}
        try:
            r = self._client.with_options(**opts).chat.completions.create(
                model=self.model, messages=[{"role": m["role"], "content": m["content"]} for m in messages],
                temperature=0.2, extra_body=body, **({"max_tokens": max_tokens} if max_tokens else {}))
        except openai.BadRequestError as e:
            if "reasoning" in body:  # a 400 generates nothing; the caller retries without the field
                raise ReasoningRejected(f"HTTP 400: {e}") from e
            raise
        latency = time.monotonic() - t0
        usage = r.usage
        extra = (getattr(usage, "model_extra", None) or {}) if usage else {}
        details = getattr(usage, "completion_tokens_details", None) if usage else None
        cost = extra.get("cost")
        gen_id = r.id
        if cost is None and gen_id:
            cost = self._generation_cost(gen_id)
        choice = r.choices[0] if r.choices else None
        content = choice.message.content if choice and choice.message else None
        return LLMResult(
            text=content if isinstance(content, str) else "",
            model=r.model or self.model,
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            cost=float(cost) if cost is not None else None,
            latency_s=latency,
            generation_id=gen_id,
            reasoning_tokens=getattr(details, "reasoning_tokens", None),
            finish_reason=choice.finish_reason if choice else None,
            provider=(r.model_extra or {}).get("provider"),
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
        return OpenRouterLLM(cfg.model, provider_order=cfg.provider_order)
    raise ValueError(f"unknown CVDP_PROVIDER {cfg.provider!r}")

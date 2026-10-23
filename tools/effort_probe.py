"""How many reasoning tokens a model spends at each CVDP_REASONING level, on one small RTL prompt. Each line is one
OpenRouter call through the agent's own client (the same request body the agent sends); every number is
provider-reported usage. Costs a fraction of a cent per call.

Usage: OPENROUTER_API_KEY=... python3 tools/effort_probe.py <model id> [level ...]   (default: all levels)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agent"))

from cvdp_agent.llm import REASONING, OpenRouterLLM  # noqa: E402
from cvdp_agent.trace import redact  # noqa: E402

PROMPT = ("Write a synthesizable SystemVerilog module `updown` for a 4-bit up/down counter with synchronous "
          "active-high reset, enable and a `dir` input. Reply with the code only.")


def main(model, levels):
    llm = OpenRouterLLM(model)
    total = 0.0
    print(f"model {model}, max_tokens 4000, prompt: 4-bit up/down counter")
    for level in levels:
        try:
            r = llm.invoke("plan", [{"role": "user", "content": PROMPT}], max_tokens=4000, timeout=150,
                           reasoning=level)
            total += r.cost or 0.0
            print(f"{level:8s} completion {r.completion_tokens} reasoning {r.reasoning_tokens} cost {r.cost} "
                  f"finish {r.finish_reason} provider {r.provider} answer_chars {len(r.text.strip())}")
        except Exception as e:
            print(f"{level:8s} ERROR {redact(f'{type(e).__name__}: {e}')[:300]}")
    print(f"total cost {total:.6f}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:] or list(REASONING))

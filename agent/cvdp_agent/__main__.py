"""Entry point. Always exits 0: the harness scores whatever is on disk, and a crash must not lose the best edit."""
import json
import os
import sys
import traceback


def main(argv):
    if "--mermaid" in argv:
        from .graph import mermaid

        print(mermaid())
        return 0
    from .config import Config, from_env

    cfg = Config(root=os.environ.get("CVDP_ROOT", "/code"), out_dir=os.environ.get("CVDP_OUT_DIR", ""))
    try:
        cfg = from_env()  # inside the try: a bad input (e.g. CVDP_MAX_TURNS=10.0) must still exit 0
        from .graph import run

        summary = run(cfg)
        print(json.dumps({k: summary.get(k) for k in ("model", "turns", "cost_usd", "stop_reason", "kept")}))
    except Exception as e:  # never non-zero; record what happened
        from .trace import redact

        msg = redact(f"{type(e).__name__}: {e}\n{traceback.format_exc()}")
        print(msg, file=sys.stderr)
        try:
            os.makedirs(cfg.agent_out, exist_ok=True)
            path = os.path.join(cfg.agent_out, "summary.json")
            if not os.path.exists(path):
                summary = {"provider": cfg.provider, "model": cfg.model or None, "stop_reason": "error",
                           "error": msg[-2000:], "switches": cfg.switches(), "cost_usd": None,
                           "cost_unreported_calls": 0}
                with open(path, "w") as f:
                    json.dump(summary, f, indent=1)
                from .graph import write_ledger

                write_ledger(cfg, summary)
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

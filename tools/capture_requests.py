#!/usr/bin/env python3
"""M3j: what Claude Code sends, read from the request body, with no model call and no spend.

Starts a local server that records each POST body and answers every request with an error, then runs Claude Code
with M3i's plain profile (and, with --bare, M3j's bare one) against it, using a placeholder API key. Prints, for the
first request with tools: the system blocks (length and first words), the tools (name and size), the request
settings, the messages (role, block sizes, first words) and the init event's tools and credential source.
Nothing secret is used or written: the key is a placeholder and the server drops auth headers.

    python3 tools/capture_requests.py --claude path/to/claude [--bare] [--out capture.json]

Run with the pinned Claude Code (2.1.310: the agent image's CLAUDE_CODE_VERSION), e.g. from
`npm i @anthropic-ai/claude-code@2.1.310` in a scratch directory, and the agent's Python environment."""
import argparse
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agent"))
from cvdp_agent import claude_code  # noqa: E402

PLACEHOLDER = "sk-ant-api03-placeholder-capture-only"


def serve(records):
    class H(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("content-length") or 0))
            try:
                records.append({"path": self.path, "beta": self.headers.get("anthropic-beta"),
                                "body": json.loads(body)})
            except ValueError:
                records.append({"path": self.path, "raw_bytes": len(body)})
            self.send_response(400)
            self.send_header("content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"type":"error","error":{"type":"invalid_request_error","message":"capture only"}}')

        def do_GET(self):
            self.send_response(404)
            self.end_headers()

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def summarise(records, stream):
    main = next((r for r in records if (r.get("body") or {}).get("tools")), records[0] if records else {})
    b = main.get("body") or {}

    def head(t):
        return " ".join(str(t).split())[:70]
    msgs = []
    for m in b.get("messages", []):
        c = m["content"] if isinstance(m["content"], list) else [{"type": "text", "text": m["content"]}]
        msgs.append({"role": m["role"], "blocks": [{"chars": len(x.get("text", "")), "head": head(x.get("text", ""))}
                                                   for x in c]})
    init = {}
    for line in stream.splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") == "system" and e.get("subtype") == "init":
            init = {"tools": e.get("tools"), "apiKeySource": e.get("apiKeySource"),
                    "claude_code_version": e.get("claude_code_version"), "skills": len(e.get("skills") or []),
                    "mcp_servers": len(e.get("mcp_servers") or [])}
    return {"requests": len(records), "model": b.get("model"),
            "system": [{"chars": len(s.get("text", "")), "head": head(s.get("text", ""))} for s in b.get("system", [])],
            "tools": [{"name": t.get("name"), "bytes": len(json.dumps(t))} for t in b.get("tools", [])],
            "settings": {k: b.get(k) for k in ("thinking", "context_management", "output_config", "max_tokens")},
            "beta": main.get("beta"), "messages": msgs, "init": init}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--claude", required=True)
    ap.add_argument("--bare", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()
    records = []
    srv = serve(records)
    build = claude_code.bare_command if a.bare else claude_code.plain_command
    cmd = build(claude_code.PROMPT.format(task="Write rtl/x.sv: a 1-bit register."), 60, "claude-haiku-5-5")
    cmd[0] = os.path.abspath(a.claude)
    env = claude_code.plain_env({"PATH": os.environ.get("PATH", "")})
    env.update(ANTHROPIC_BASE_URL=f"http://127.0.0.1:{srv.server_port}", ANTHROPIC_API_KEY=PLACEHOLDER,
               CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1", DISABLE_TELEMETRY="1")
    with tempfile.TemporaryDirectory() as task:
        p = subprocess.run(cmd, cwd=task, capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL,
                           env=env)
    srv.shutdown()
    out = summarise(records, p.stdout)
    out["profile"] = "bare" if a.bare else "plain"
    text = json.dumps(out, indent=1)
    if a.out:
        open(a.out, "w").write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()

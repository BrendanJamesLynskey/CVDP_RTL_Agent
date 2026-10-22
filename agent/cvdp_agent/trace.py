"""trace.jsonl: one line per LLM call and per tool call. Every string is redacted before it is written."""
import json
import os
import re
import time

# Anything that looks like a key or an auth header. The key's own value is redacted too, whatever its shape.
_PATTERNS = [
    re.compile(r"sk-or-[A-Za-z0-9_\-]*"),
    re.compile(r"Bearer\s*\S*", re.IGNORECASE),
    re.compile(r"Authorization\S*(\s*[:=]\s*\S+)?", re.IGNORECASE),
]
_SECRET_ENV = ("OPENROUTER_API_KEY",)
REDACTED = "[REDACTED]"


def redact(value):
    if isinstance(value, str):
        for name in _SECRET_ENV:
            secret = os.environ.get(name)
            if secret and len(secret) >= 8:
                value = value.replace(secret, REDACTED)
        for p in _PATTERNS:
            value = p.sub(REDACTED, value)
        return value
    if isinstance(value, dict):
        return {redact(k): redact(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    return value


def truncate(text, limit=2000):
    if text is None:
        return None
    if len(text) <= limit:
        return text
    half = limit // 2
    return text[:half] + f"\n...[{len(text) - limit} chars cut]...\n" + text[-half:]


class Tracer:
    def __init__(self, out_dir):
        self.path = os.path.join(out_dir, "trace.jsonl") if out_dir else None
        if self.path:
            os.makedirs(out_dir, exist_ok=True)
            open(self.path, "w").close()
        self.events = []

    def log(self, kind, **fields):
        event = redact({"t": round(time.time(), 3), "kind": kind, **fields})
        self.events.append(event)
        if self.path:
            with open(self.path, "a") as f:
                f.write(json.dumps(event) + "\n")
        return event

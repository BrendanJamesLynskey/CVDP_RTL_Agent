"""The knowledge pack (M3g): a frozen directory of skills, loaded close to how Claude skills work.

A pack is a directory with INDEX.md (one "name: description" line per skill), one <name>.md per skill, and
MANIFEST.sha256 (`sha256sum` lines for every file, the manifest itself excepted). It is checked against its manifest
before use; any file that is missing or differs refuses the whole pack.

The plan prompt gets INDEX.md as it is; the plan names up to MAX_SKILLS skills; their bodies, in the order named, go
into every edit prompt, up to a byte cap. Names are matched exactly after trimming, lower-casing and dropping a
trailing ".md"; anything else is recorded as unknown and ignored."""
import hashlib
import os
import re

MAX_SKILLS = 3
# The largest three skills of rtl_pack (frozen in brief 18A) come to 12,554 bytes with their headers well under
# 13,000, so the cap binds only on a different pack. It is a cap on loaded text, not a target.
CAP_BYTES = 13_000
_LINE = re.compile(r"^([a-z0-9][a-z0-9-]*):\s+(.+)$")


class PackError(ValueError):
    """The pack does not match its manifest, or is not a pack."""


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def manifest_hash(path):
    return sha256(os.path.join(path, "MANIFEST.sha256"))


def verify(path):
    """{file: sha256} from the manifest, after checking every file against it."""
    mf = os.path.join(path, "MANIFEST.sha256")
    if not os.path.isfile(mf):
        raise PackError(f"{path}: no MANIFEST.sha256")
    want = {}
    for ln in open(mf):
        if not ln.strip():
            continue
        parts = ln.split()
        if len(parts) != 2 or not re.fullmatch(r"[0-9a-f]{64}", parts[0]):
            raise PackError(f"{path}: bad manifest line {ln.strip()!r}")
        want[parts[1].lstrip("*")] = parts[0]
    for name, h in want.items():
        full = os.path.join(path, name)
        if os.path.basename(name) != name or not os.path.isfile(full):
            raise PackError(f"{path}: {name} is in the manifest but not in the pack")
        if sha256(full) != h:
            raise PackError(f"{path}: {name} does not match the manifest")
    present = {f for f in os.listdir(path) if f.endswith(".md")}
    extra = present - set(want)
    if extra:
        raise PackError(f"{path}: not in the manifest: {', '.join(sorted(extra))}")
    return want


class Pack:
    def __init__(self, path):
        files = verify(path)
        if "INDEX.md" not in files:
            raise PackError(f"{path}: no INDEX.md in the manifest")
        self.path = path
        self.hash = manifest_hash(path)
        self.index = open(os.path.join(path, "INDEX.md")).read()
        self.names = []
        for ln in self.index.splitlines():
            m = _LINE.match(ln.strip())
            if m and f"{m.group(1)}.md" in files:
                self.names.append(m.group(1))
        if not self.names:
            raise PackError(f"{path}: INDEX.md names no skill in the pack")
        self.bodies = {n: open(os.path.join(path, f"{n}.md")).read() for n in self.names}

    def select(self, requested, k=MAX_SKILLS):
        """(names to load, unknown names): the plan's names in its order, known, without repeats, at most k."""
        if isinstance(requested, str):
            requested = [requested]
        if not isinstance(requested, list):
            return [], []
        chosen, unknown = [], []
        for x in requested:
            n = str(x).strip().lower()
            n = n[:-3] if n.endswith(".md") else n
            if n in self.bodies:
                if n not in chosen and len(chosen) < k:
                    chosen.append(n)
            else:
                unknown.append(str(x)[:80])
        return chosen, unknown[:20]

    def block(self, names, cap=CAP_BYTES):
        """(text, names loaded, bytes, truncated): the bodies in order, each under a header, cut at `cap` bytes of
        body text (at a line break). A skill that no longer fits at all is left out, and counted as truncated."""
        parts, loaded, used, truncated = [], [], 0, False
        for n in names:
            body = self.bodies[n]
            size = len(body.encode())
            if used + size > cap:
                room = cap - used
                cut = body.encode()[:room].decode(errors="ignore")
                cut = cut[:cut.rfind("\n") + 1] if "\n" in cut else ""
                truncated = True
                if not cut.strip():
                    break
                body, size = cut + "[... cut: the loaded skills' size cap]\n", len(cut.encode())
            parts.append(f"## Skill: {n}\n{body}")
            loaded.append(n)
            used += size
            if truncated:
                break
        return "\n".join(parts), loaded, used, truncated

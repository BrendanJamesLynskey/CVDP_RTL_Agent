"""The file tool. The LLM may change files only under rtl/, verif/ and docs/, and may write its own testbench only
under rundir/agent_tb/. Every other path is refused here, in code, whatever the LLM asks for."""
import os
import re

EDIT_ROOTS = ("rtl", "verif", "docs")
TB_ROOT = os.path.join("rundir", "agent_tb")
TEXT_EXT = {".sv", ".v", ".svh", ".vh", ".md", ".txt", ".py", ".json", ".yml", ".yaml", ".tcl", ".mk", ".f", ".c",
            ".h", ".cpp", ".xdc", ".sdc", ".rst", ".csv", ".hex", ".mem", ""}


class PathRefused(Exception):
    pass


class FileTool:
    def __init__(self, root):
        self.root = os.path.realpath(root)
        self.created = set()  # files the agent created (relative paths)

    # ---------- path policy ----------
    def _resolve(self, path, roots):
        if not isinstance(path, str) or not path.strip():
            raise PathRefused("empty path")
        p = path.strip()
        if p.startswith("/code/"):
            p = p[len("/code/"):]
        elif p.startswith(self.root + os.sep):
            p = p[len(self.root) + 1:]
        if os.path.isabs(p):
            raise PathRefused(f"{path}: absolute path outside /code")
        parts = p.replace("\\", "/").split("/")
        if any(x in ("..", "") for x in parts):
            raise PathRefused(f"{path}: '..' or empty path component")
        full = os.path.realpath(os.path.join(self.root, *parts))
        for r in roots:
            base = os.path.realpath(os.path.join(self.root, r))
            if full == base:
                continue
            if full.startswith(base + os.sep):
                return full, os.path.relpath(full, self.root)
        raise PathRefused(f"{path}: outside the allowed roots {', '.join(roots)}")

    def resolve_edit(self, path):
        return self._resolve(path, EDIT_ROOTS)

    def resolve_tb(self, path):
        p = path.strip()
        if p.startswith("/code/"):
            p = p[len("/code/"):]
        if p.startswith("agent_tb/"):
            p = os.path.join("rundir", p)
        return self._resolve(p, (TB_ROOT,))

    # ---------- reading ----------
    def list_files(self, exclude_prefixes=("rundir/agent_out", "rundir/agent_tb")):
        out = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
            for fn in sorted(filenames):
                rel = os.path.relpath(os.path.join(dirpath, fn), self.root)
                if any(rel.startswith(x) for x in exclude_prefixes):
                    continue
                out.append(rel)
        return out

    def read(self, rel):
        with open(os.path.join(self.root, rel), "r", errors="replace") as f:
            return f.read()

    def source_files(self, roots=("rtl",), exts=(".sv", ".v")):
        files = []
        for r in roots:
            base = os.path.join(self.root, r)
            for dirpath, _, filenames in os.walk(base):
                for fn in sorted(filenames):
                    if os.path.splitext(fn)[1] in exts:
                        files.append(os.path.join(dirpath, fn))
        return sorted(files)

    # ---------- writing ----------
    def _write(self, full, rel, content):
        existed = os.path.exists(full)
        parent = os.path.dirname(full)
        os.makedirs(parent, exist_ok=True)
        with open(full, "w") as f:
            f.write(content)
        if not existed:
            self.created.add(rel)
        _match_owner(full, self.root)

    def write(self, path, content):
        full, rel = self.resolve_edit(path)
        self._write(full, rel, content)
        return rel

    def write_tb(self, path, content):
        full, rel = self.resolve_tb(path)
        self._write(full, rel, content)
        return rel

    def apply_diff(self, path, diff):
        full, rel = self.resolve_edit(path)
        old = open(full).read() if os.path.exists(full) else ""
        new = apply_unified_diff(old, diff)
        self._write(full, rel, new)
        return rel

    # ---------- best-edit snapshots ----------
    def snapshot(self):
        snap = {}
        for r in EDIT_ROOTS:
            base = os.path.join(self.root, r)
            for dirpath, _, filenames in os.walk(base):
                for fn in filenames:
                    full = os.path.join(dirpath, fn)
                    try:  # a dangling symlink or an unreadable file is not part of the design
                        with open(full, "rb") as f:
                            snap[os.path.relpath(full, self.root)] = f.read()
                    except OSError:
                        continue
        return snap

    def restore(self, snap):
        current = self.snapshot()
        for rel in current:
            if rel not in snap:
                try:
                    os.remove(os.path.join(self.root, rel))
                except OSError:
                    pass
        for rel, data in snap.items():
            if current.get(rel) != data:
                full = os.path.join(self.root, rel)
                os.makedirs(os.path.dirname(full), exist_ok=True)
                with open(full, "wb") as f:
                    f.write(data)


def _match_owner(full, root):
    """Give files the owner of the mounted tree, so the host user (not root) can clean the work directory."""
    try:
        st = os.stat(root)
        if os.geteuid() == 0 and st.st_uid != 0:
            os.chown(full, st.st_uid, st.st_gid)
            d = os.path.dirname(full)
            while d.startswith(root) and d != root:
                os.chown(d, st.st_uid, st.st_gid)
                d = os.path.dirname(d)
    except OSError:
        pass


class DiffError(Exception):
    pass




def apply_unified_diff(old_text, diff):
    """Apply a unified diff by matching each hunk's context, not its line numbers (LLMs get those wrong)."""
    lines = old_text.splitlines()
    hunks, cur = [], None
    for raw in diff.splitlines():
        if raw.startswith(("---", "+++", "diff ", "index ")) and cur is None:
            continue
        if raw.startswith("@@"):
            cur = {"old": [], "new": []}
            hunks.append(cur)
            continue
        if cur is None:
            continue
        if raw.startswith("\\"):
            continue
        tag, body = (raw[:1], raw[1:]) if raw else (" ", "")
        if tag == " ":
            cur["old"].append(body)
            cur["new"].append(body)
        elif tag == "-":
            cur["old"].append(body)
        elif tag == "+":
            cur["new"].append(body)
        else:  # a context line that lost its leading space
            cur["old"].append(raw)
            cur["new"].append(raw)
    if not hunks:
        raise DiffError("no hunks in diff")
    pos = 0
    for h in hunks:
        old, new = h["old"], h["new"]
        if not old:  # pure insertion at the end
            lines.extend(new)
            continue
        idx = _find(lines, old, pos)
        if idx is None:
            idx = _find(lines, old, 0)
        if idx is None:
            stripped = [x.strip() for x in lines]
            idx = _find(stripped, [x.strip() for x in old], 0)
        if idx is None:
            raise DiffError("hunk context not found: " + " | ".join(old[:3])[:200])
        lines[idx:idx + len(old)] = new
        pos = idx + len(new)
    return "\n".join(lines) + ("\n" if old_text.endswith("\n") or not old_text else "")


def _find(lines, block, start):
    n = len(block)
    for i in range(start, len(lines) - n + 1):
        if lines[i:i + n] == block:
            return i
    return None

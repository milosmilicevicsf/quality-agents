"""File, Git and artifact primitives. No model-controlled shell commands."""

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


class QAError(Exception):
    pass


def stamp():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    data = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(data).hexdigest()


def load(path):
    path = Path(path)
    if path.stat().st_size > 5_000_000:
        raise QAError(f"JSON input too large: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def new_dir(path):
    path = Path(path).resolve()
    if path.exists():
        raise QAError(f"Output already exists; use a new directory: {path}")
    path.mkdir(parents=True)
    return path


def safe_relative(name):
    if (not isinstance(name, str) or not name or "\\" in name or ":" in name
            or any(ord(c) < 32 for c in name) or "\"" in name):
        raise QAError(f"Unsafe relative path: {name!r}")
    path = PurePosixPath(name)
    if name == "." or path.is_absolute() or any(p in ("..", ".git") for p in path.parts) or str(path) != name:
        raise QAError(f"Unsafe relative path: {name!r}")
    return path


def inside(root, name):
    rel = safe_relative(name)
    root = Path(root).resolve()
    dest = root.joinpath(*rel.parts)
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise QAError(f"Symlinks are not supported: {name}")
    if not dest.resolve().is_relative_to(root):
        raise QAError("Path escapes repository")
    return dest


def git(repo, *args, binary=False):
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("GIT_"):
            env.pop(key)
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_TERMINAL_PROMPT="0")
    result = subprocess.run(["git", "-c", "core.hooksPath=" + os.devnull,
                             "-c", "core.fsmonitor=false", "-C", str(repo), *args],
                            env=env, capture_output=True, timeout=45)
    if result.returncode:
        raise QAError("Git operation failed: " + result.stderr.decode(errors="replace")[:500])
    return result.stdout if binary else result.stdout.decode("utf-8").strip()


def revision(repo):
    repo = Path(repo).resolve()
    if git(repo, "rev-parse", "--show-toplevel") != str(repo):
        # Windows Git may print forward slashes.
        if Path(git(repo, "rev-parse", "--show-toplevel")).resolve() != repo:
            raise QAError("--repo must point at the Git repository root")
    head = git(repo, "rev-parse", "--verify", "HEAD")
    if git(repo, "status", "--porcelain", "--untracked-files=normal"):
        raise QAError("Commit/stash changes and untracked files before preparing a snapshot")
    return head


def secret_path(name):
    parts = PurePosixPath(name.lower()).parts
    return any(p == ".env" or p.startswith(".env.") or p in (
        ".ssh", ".aws", ".npmrc", ".pypirc", "secrets", "credentials", "id_rsa",
        "id_ed25519", "credentials.json", "service-account.json")
        or p.endswith((".pem", ".key", ".p12", ".pfx", ".jks", ".keystore")) for p in parts)


def redact(text):
    # Conservative heuristics; these are not a complete PII/secret detector.
    text = re.sub(r"-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?-----END [^-]*PRIVATE KEY-----",
                  "[REDACTED PRIVATE KEY]", text)
    text = re.sub(r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9_]{16,}|AKIA[A-Z0-9]{16})\b",
                  "[REDACTED TOKEN]", text)
    text = re.sub(r"(?im)((?:password|api[_-]?key|access[_-]?token|secret)\s*[:=]\s*)[^\n]+",
                  r"\1[REDACTED]", text)
    return re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[REDACTED EMAIL]", text)


def envelope(value):
    return {"data": value, "sha256": digest(value)}


def unwrap(path):
    box = load(path)
    if set(box) != {"data", "sha256"} or box["sha256"] != digest(box["data"]):
        raise QAError(f"Artifact integrity mismatch: {Path(path).name}")
    return box["data"]

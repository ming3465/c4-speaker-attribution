"""Run provenance: every result CSV gets a manifest.json saying exactly how it was made.

Records the git commit (and whether the tree was dirty), the dataset file
hashes, every CLI argument, the model and its Ollama digest, the hash seed and
Python version, timestamps (ISO 8601, UTC), row counts and the gate outcome.
Without it, a table cannot be traced back to the configuration that produced it.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

HASH_CHUNK = 1 << 20


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def git_state(root: Path) -> dict[str, Any]:
    def run(*cmd: str) -> str:
        try:
            return subprocess.run(cmd, cwd=root, capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return ""
    commit = run("git", "rev-parse", "HEAD")
    dirty = bool(run("git", "status", "--porcelain")) if commit else None
    return {"git_commit": commit or None, "git_dirty": dirty}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def portable_path(path: Path, root: Path) -> str:
    """Repo-relative when inside the repo, so manifests compare across machines."""
    try:
        return str(Path(path).resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def build_manifest(
    *,
    root: Path,
    args: dict[str, Any],
    dataset_files: Iterable[Path],
    model: str,
    model_digest: str,
    started_utc: str,
) -> dict[str, Any]:
    return {
        **git_state(root),
        "dataset": [{"path": portable_path(p, root), "sha256": file_sha256(p)} for p in dataset_files],
        "args": {k: (portable_path(v, root) if isinstance(v, Path) else v) for k, v in args.items()},
        "model": model,
        "model_digest": model_digest,
        "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
        "python": platform.python_version(),
        "started_utc": started_utc,
    }


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")


def read_manifest(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))

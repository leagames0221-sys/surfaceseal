"""Pinned-hash baseline for drift detection (the worm re-commit vector).

`surfaceseal init` records a SHA-256 of every in-scope control-surface file. Later,
`scan --baseline` re-hashes the current surface and flags any file whose hash has
changed or that is newly present — even when there is no git diff to read (e.g.
inspecting an already-cloned, already-trusted working tree). Unchanged files are
trusted and skipped, so the run stays quiet unless something actually moved.

The baseline stores hashes only, never file contents, so it leaks nothing sensitive
and stays small.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

BASELINE_FILENAME = ".surfaceseal-baseline.json"


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load(repo_root: str | Path) -> dict[str, str]:
    f = Path(repo_root) / BASELINE_FILENAME
    if not f.is_file():
        return {}
    data = json.loads(f.read_text(encoding="utf-8"))
    pinned = data.get("surfaces", {})
    return {str(k): str(v) for k, v in pinned.items()} if isinstance(pinned, dict) else {}


def write(repo_root: str | Path, surfaces: dict[str, str]) -> Path:
    f = Path(repo_root) / BASELINE_FILENAME
    payload = {"version": 1, "surfaces": dict(sorted(surfaces.items()))}
    f.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return f


def is_drifted(pinned: dict[str, str], path: str, text: str) -> bool:
    """True if ``path`` is new vs the baseline or its content hash has changed."""
    prior = pinned.get(path)
    return prior is None or prior != hash_text(text)

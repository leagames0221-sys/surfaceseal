"""Git access — the only module that shells out to ``git``.

Isolating subprocess use here keeps the rest of the codebase pure and trivially
testable (the engine and packs operate on in-memory text, never on a live repo).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

from .core.models import ChangeKind


@dataclass(frozen=True)
class DiffEntry:
    path: str
    change_kind: ChangeKind
    head_text: str
    base_text: str | None


def _git(args: list[str], cwd: str) -> str:
    proc = subprocess.run(  # noqa: S603 - fixed argv, no shell, trusted binary
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def _show(cwd: str, ref: str, path: str) -> str | None:
    """Return file content at ``ref:path`` or ``None`` if it does not exist there."""
    try:
        return _git(["show", f"{ref}:{path}"], cwd)
    except RuntimeError:
        return None


def tracked_files(cwd: str = ".") -> list[str]:
    """Return repo-tracked file paths (used by ``init`` to snapshot the surface)."""
    out = _git(["ls-files"], cwd)
    return [ln for ln in out.splitlines() if ln.strip()]


def read_head(path: str, cwd: str = ".") -> str | None:
    """Return the working-tree content of ``path`` at ``HEAD``."""
    return _show(cwd, "HEAD", path)


def changed_files(base: str, cwd: str = ".") -> list[DiffEntry]:
    """Return added/modified files between ``base`` and the working ``HEAD``.

    Deletions are ignored: a removed control surface cannot ship poison downstream.
    Renames are reported as their added (head) path.
    """
    out = _git(["diff", "--name-status", "-M", base, "HEAD"], cwd)
    entries: list[DiffEntry] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        code = status[0]
        if code == "A":
            path = parts[1]
            kind = ChangeKind.ADDED
            base_text = None
        elif code == "M":
            path = parts[1]
            kind = ChangeKind.MODIFIED
            base_text = _show(cwd, base, path)
        elif code == "R":
            path = parts[2]  # new path after rename
            kind = ChangeKind.MODIFIED
            base_text = _show(cwd, base, parts[1])
        else:
            continue  # D (delete), C (copy), T (type change) - out of scope here
        head_text = _show(cwd, "HEAD", path)
        if head_text is None:
            continue
        entries.append(
            DiffEntry(path=path, change_kind=kind, head_text=head_text, base_text=base_text)
        )
    return entries

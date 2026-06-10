"""Resolve which changed files are in-scope agent control surfaces.

The registry is data-driven (``surfaces.toml``, ADR-0004 / M3): bundled defaults
plus an optional repo-root ``surfaces.toml`` that extends them, so supporting a new
agent is a config edit, not a code change.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from fnmatch import fnmatch
from importlib import resources
from pathlib import Path

# Formats that carry executable commands (handled by packs.autorun).
EXECUTABLE_FORMATS = frozenset({"claude_settings", "vscode_tasks", "hooks_json", "mcp_json"})
# Formats inspected only by the advisory injection pack.
INSTRUCTION_FORMATS = frozenset({"instruction_md"})


@dataclass(frozen=True)
class SurfaceRule:
    match: str
    agent: str
    format: str


def _parse_rules(raw: bytes) -> list[SurfaceRule]:
    data = tomllib.loads(raw.decode("utf-8"))
    return [
        SurfaceRule(match=s["match"], agent=s["agent"], format=s["format"])
        for s in data.get("surface", [])
    ]


def load_rules(repo_root: str | Path | None = None) -> list[SurfaceRule]:
    """Load bundled rules, then append any repo-root ``surfaces.toml`` overrides."""
    bundled = resources.files("surfaceseal").joinpath("surfaces.toml").read_bytes()
    rules = _parse_rules(bundled)
    if repo_root is not None:
        override = Path(repo_root) / "surfaces.toml"
        if override.is_file():
            rules.extend(_parse_rules(override.read_bytes()))
    return rules


def _normalize(path: str) -> str:
    p = path.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p


def path_excluded(path: str, patterns: list[str]) -> bool:
    """True if ``path`` matches any exclude glob.

    Supports a trailing ``/**`` recursive prefix match (e.g. ``tests/fixtures/**``)
    in addition to plain :func:`fnmatch` patterns. Lets a repo keep poisoned test
    fixtures or vendored samples out of its own gate.
    """
    norm = _normalize(path)
    for pat in patterns:
        if pat.endswith("/**"):
            prefix = pat[:-3]
            if norm == prefix or norm.startswith(prefix + "/"):
                return True
        elif fnmatch(norm, pat):
            return True
    return False


def classify(path: str, rules: list[SurfaceRule]) -> SurfaceRule | None:
    """Return the first matching surface rule for ``path``, or ``None``.

    ``**/name`` matches by basename anywhere; other patterns match the full
    normalized path or an exact basename for root-level conventions.
    """
    norm = _normalize(path)
    base = norm.rsplit("/", 1)[-1]
    for rule in rules:
        pat = rule.match
        if pat.startswith("**/"):
            if fnmatch(base, pat[3:]) or fnmatch(norm, pat):
                return rule
        elif norm == pat or fnmatch(norm, pat) or norm.endswith("/" + pat):
            return rule
    return None

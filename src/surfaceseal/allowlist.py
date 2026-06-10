"""Maintainer-accepted control-surface entries.

`surfaceseal init` records the commands present in the current control surface so
that legitimate, pre-existing hooks/tasks/servers do not light up on every run
(the alert-fatigue failure mode of a full scan). Anything *not* on the allowlist is
treated fail-closed (R-09): new execution capability is surfaced by default.

Format (`.surfaceseal-allow.toml`):

    [[allow]]
    path = ".claude/settings.json"
    command = "npm run lint"
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ALLOWLIST_FILENAME = ".surfaceseal-allow.toml"


@dataclass
class Allowlist:
    scoped: set[tuple[str, str]] = field(default_factory=set)

    def permits(self, path: str, command: str) -> bool:
        return (path, command) in self.scoped

    def add(self, path: str, command: str) -> None:
        self.scoped.add((path, command))

    @classmethod
    def load(cls, repo_root: str | Path) -> Allowlist:
        f = Path(repo_root) / ALLOWLIST_FILENAME
        if not f.is_file():
            return cls()
        data = tomllib.loads(f.read_text(encoding="utf-8"))
        al = cls()
        for entry in data.get("allow", []):
            path = entry.get("path", "")
            command = entry.get("command", "")
            if path and command:
                al.add(path, command)
        return al

    def write(self, repo_root: str | Path) -> Path:
        f = Path(repo_root) / ALLOWLIST_FILENAME
        lines = [
            "# surfaceseal allowlist - maintainer-accepted control-surface commands.",
            "# Regenerate with `surfaceseal init`; review additions in code review.",
            "",
        ]
        for path, command in sorted(self.scoped):
            esc = command.replace("\\", "\\\\").replace('"', '\\"')
            lines.append("[[allow]]")
            lines.append(f'path = "{path}"')
            lines.append(f'command = "{esc}"')
            lines.append("")
        f.write_text("\n".join(lines), encoding="utf-8")
        return f

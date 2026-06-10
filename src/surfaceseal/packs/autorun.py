"""Primary pack: structural detection of execution capability in control surfaces.

This is the headline, high-confidence layer (ADR-0003). It extracts command-bearing
entries from each format, then reasons about *what the change introduced*:

- a command that runs **automatically** (a hook, a folder-open task, an MCP server
  launch) and is newly introduced by this change is treated as CRITICAL — it would
  execute on every downstream consumer with no review (the Miasma vector);
- any command matching a high-risk signature is CRITICAL regardless of trigger;
- a newly introduced **manual** command is WARNING.

Commands already present in the base revision are not re-flagged (diff reasoning);
the allowlist (applied in the engine) suppresses entries a maintainer has accepted.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.models import ChangeUnit, Finding, Severity
from ..parsers import jsonc
from ..rules.autorun_rules import match_high_risk


@dataclass(frozen=True)
class _Cmd:
    command: str
    line: int
    context: str
    autorun: bool


def _find_line(text: str, needle: str) -> int:
    if not needle:
        return 1
    idx = text.find(needle)
    if idx < 0:
        # fall back to the first distinctive token
        token = needle.strip().split()[0] if needle.strip() else needle
        idx = text.find(token)
    return text.count("\n", 0, idx) + 1 if idx >= 0 else 1


def _as_command(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(str(v) for v in value)
    return ""


def _extract_claude(data: object, text: str) -> list[_Cmd]:
    cmds: list[_Cmd] = []
    if not isinstance(data, dict):
        return cmds
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return cmds
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            continue
        for group in groups:
            inner = group.get("hooks", []) if isinstance(group, dict) else []
            for h in inner:
                if isinstance(h, dict) and h.get("type") == "command":
                    cmd = _as_command(h.get("command"))
                    if cmd:
                        cmds.append(_Cmd(cmd, _find_line(text, cmd), f"hook:{event}", autorun=True))
    return cmds


def _extract_vscode_tasks(data: object, text: str) -> list[_Cmd]:
    cmds: list[_Cmd] = []
    tasks = data.get("tasks") if isinstance(data, dict) else None
    if not isinstance(tasks, list):
        return cmds
    for task in tasks:
        if not isinstance(task, dict):
            continue
        cmd = _as_command(task.get("command"))
        if not cmd:
            continue
        args = _as_command(task.get("args"))
        full = f"{cmd} {args}".strip()
        run_options = task.get("runOptions")
        run_on = run_options.get("runOn") if isinstance(run_options, dict) else None
        autorun = run_on == "folderOpen"
        label = "task:folderOpen" if autorun else "task:manual"
        cmds.append(_Cmd(full, _find_line(text, cmd), label, autorun=autorun))
    return cmds


def _extract_hooks_json(data: object, text: str) -> list[_Cmd]:
    cmds: list[_Cmd] = []
    hooks = data.get("hooks") if isinstance(data, dict) else data
    items = hooks if isinstance(hooks, list) else []
    for h in items:
        if isinstance(h, dict):
            cmd = _as_command(h.get("command"))
            event = h.get("event", "hook")
            if cmd:
                cmds.append(_Cmd(cmd, _find_line(text, cmd), f"hook:{event}", autorun=True))
    return cmds


def _extract_mcp(data: object, text: str) -> list[_Cmd]:
    cmds: list[_Cmd] = []
    servers = data.get("mcpServers") if isinstance(data, dict) else None
    if not isinstance(servers, dict):
        return cmds
    for name, spec in servers.items():
        if not isinstance(spec, dict):
            continue
        cmd = _as_command(spec.get("command"))
        if not cmd:
            continue
        args = _as_command(spec.get("args"))
        full = f"{cmd} {args}".strip()
        cmds.append(_Cmd(full, _find_line(text, cmd), f"mcp:{name}", autorun=True))
    return cmds


_EXTRACTORS = {
    "claude_settings": _extract_claude,
    "vscode_tasks": _extract_vscode_tasks,
    "hooks_json": _extract_hooks_json,
    "mcp_json": _extract_mcp,
}


def scan(unit: ChangeUnit) -> list[Finding]:
    """Return findings for one in-scope executable surface."""
    extractor = _EXTRACTORS.get(unit.fmt)
    if extractor is None:
        return []

    try:
        head = jsonc.loads(unit.head_text)
    except ValueError:
        return [
            Finding(
                rule_id="SS-PARSE",
                severity=Severity.WARNING,
                surface=unit.surface,
                line=1,
                message=f"control surface could not be parsed as JSON ({unit.surface.path})",
            )
        ]

    head_cmds = extractor(head, unit.head_text)

    base_cmd_set: set[str] = set()
    if unit.base_text is not None:
        try:
            base = jsonc.loads(unit.base_text)
            base_cmd_set = {c.command for c in extractor(base, unit.base_text)}
        except ValueError:
            base_cmd_set = set()

    findings: list[Finding] = []
    for c in head_cmds:
        if c.command in base_cmd_set:
            continue  # unchanged since base - not introduced by this change
        sig = match_high_risk(c.command)
        if sig is not None:
            sev, rule_id, why = Severity.CRITICAL, sig.rule_id, sig.label
        elif c.autorun:
            sev, rule_id = Severity.CRITICAL, "SS-AUTORUN-NEW"
            why = "auto-executing command added"
        else:
            sev, rule_id, why = Severity.WARNING, "SS-CMD-NEW", "new command introduced"
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=sev,
                surface=unit.surface,
                line=c.line,
                message=f"{why} in {c.context}",
                evidence=c.command[:200],
            )
        )
    return findings

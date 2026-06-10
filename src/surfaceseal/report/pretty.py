"""Human-readable terminal report.

Colour via ANSI only (no dependency); disabled when stdout is not a TTY or when
``NO_COLOR`` is set, so CI logs stay clean.
"""

from __future__ import annotations

import os
import sys

from ..core.models import Severity, Verdict

_LABEL = {Severity.CRITICAL: "CRITICAL", Severity.WARNING: "WARNING", Severity.INFO: "INFO"}
_COLOR = {Severity.CRITICAL: "31", Severity.WARNING: "33", Severity.INFO: "36"}


def _use_color() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _use_color() else text


def render(verdict: Verdict) -> str:
    lines: list[str] = []
    if not verdict.findings:
        lines.append(_c("PASS", "32") + " surfaceseal: no poisoned control-surface changes found.")
        return "\n".join(lines)

    crit = sum(1 for f in verdict.findings if f.severity is Severity.CRITICAL)
    warn = sum(1 for f in verdict.findings if f.severity is Severity.WARNING)
    for f in sorted(verdict.findings, key=lambda x: (-int(x.severity), x.surface.path, x.line)):
        tag = _c(_LABEL[f.severity], _COLOR[f.severity])
        advisory = _c(" (advisory)", "90") if f.advisory else ""
        lines.append(f"{tag}{advisory}  {f.surface.path}:{f.line}  [{f.rule_id}] {f.message}")
        if f.evidence:
            lines.append(f"        -> {f.evidence}")
    verdict_word = _c("BLOCK", "31") if crit else _c("REVIEW", "33")
    lines.append("")
    lines.append(f"{verdict_word}  {crit} critical, {warn} warning  (exit {verdict.exit_code})")
    return "\n".join(lines)

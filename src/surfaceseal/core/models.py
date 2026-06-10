"""Core data contracts.

These types are the boundary between the diff/parse layer, the detection packs,
and the reporters. They are intentionally plain (stdlib ``dataclass`` / ``enum``)
so the core carries zero third-party dependencies (C-1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class Severity(IntEnum):
    """Ordered so the worst severity in a run maps directly to an exit code.

    INFO/WARNING/CRITICAL are ordered; ``max()`` over a finding set yields the
    run's verdict. Advisory packs (e.g. instruction-injection) are capped at
    WARNING so a lossy detector can never on its own fail a merge.
    """

    INFO = 0
    WARNING = 1
    CRITICAL = 2


class ChangeKind(IntEnum):
    """How a control-surface file entered this run."""

    ADDED = 0       # file/entry newly introduced by the diff
    MODIFIED = 1    # existing file/entry changed by the diff
    DRIFTED = 2     # changed vs a trusted baseline (no git diff context)


@dataclass(frozen=True)
class Surface:
    """A control-surface file selected for inspection.

    ``agent`` is the logical agent family (e.g. ``"claude-code"``, ``"cursor"``)
    resolved from ``surfaces.toml``; ``kind`` records why it is in scope.
    """

    path: str
    agent: str
    kind: ChangeKind


@dataclass(frozen=True)
class Finding:
    """One detected issue, addressable back to a file and line.

    ``rule_id`` references a signature in ``surfaceseal.rules.*``. ``advisory``
    marks findings from lossy detectors so reporters can label them honestly.
    """

    rule_id: str
    severity: Severity
    surface: Surface
    line: int
    message: str
    advisory: bool = False
    evidence: str = ""


@dataclass
class Verdict:
    """Aggregate result of a scan."""

    findings: list[Finding] = field(default_factory=list)

    @property
    def severity(self) -> Severity:
        """Worst severity across all findings (INFO when clean)."""
        if not self.findings:
            return Severity.INFO
        return max(f.severity for f in self.findings)

    @property
    def exit_code(self) -> int:
        """Map the verdict to a CI exit code: 0 clean / 1 warning / 2 critical."""
        sev = self.severity
        if sev is Severity.CRITICAL:
            return 2
        if sev is Severity.WARNING:
            return 1
        return 0

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

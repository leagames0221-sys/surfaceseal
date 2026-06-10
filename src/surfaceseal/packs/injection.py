"""Advisory pack: best-effort hidden-instruction detection in instruction files.

Operates line-by-line on the *added* lines of a change (or all lines for an added
file / drift). Every finding is advisory and capped at WARNING — a lossy detector
must never, on its own, fail a merge (ADR-0003). Its job is to draw a human's eye,
not to gate.
"""

from __future__ import annotations

from collections import Counter

from ..core.models import ChangeUnit, Finding, Severity
from ..rules.injection_rules import scan_line


def _added_lines(head_text: str, base_text: str | None) -> list[tuple[int, str]]:
    """Return (1-based line number, text) for lines newly introduced by the change.

    Uses a multiset diff rather than a plain set: if a payload line is re-injected,
    a single identical line already in the base must not mask the new copy. A head
    occurrence counts as "added" only once the base's occurrences are exhausted.
    """
    if base_text is None:
        return [(i + 1, ln) for i, ln in enumerate(head_text.splitlines()) if ln.strip()]
    remaining = Counter(base_text.splitlines())
    added: list[tuple[int, str]] = []
    for i, ln in enumerate(head_text.splitlines()):
        if not ln.strip():
            continue
        if remaining.get(ln, 0) > 0:
            remaining[ln] -= 1  # this head line is covered by a base occurrence
            continue
        added.append((i + 1, ln))
    return added


def scan(unit: ChangeUnit) -> list[Finding]:
    findings: list[Finding] = []
    for line_no, line in _added_lines(unit.head_text, unit.base_text):
        sig = scan_line(line)
        if sig is None:
            continue
        findings.append(
            Finding(
                rule_id=sig.rule_id,
                severity=Severity.WARNING,  # advisory cap
                surface=unit.surface,
                line=line_no,
                message=f"possible {sig.label}",
                advisory=True,
                evidence=line.strip()[:200],
            )
        )
    return findings

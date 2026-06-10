"""Core model contracts: severity ordering and exit-code mapping."""

from surfaceseal.core.models import (
    ChangeKind,
    Finding,
    Severity,
    Surface,
    Verdict,
)


def _surface() -> Surface:
    return Surface(path=".claude/settings.json", agent="claude-code", kind=ChangeKind.ADDED)


def _finding(sev: Severity, advisory: bool = False) -> Finding:
    return Finding(
        rule_id="TEST-001",
        severity=sev,
        surface=_surface(),
        line=1,
        message="test",
        advisory=advisory,
    )


def test_empty_verdict_is_clean():
    v = Verdict()
    assert v.severity is Severity.INFO
    assert v.exit_code == 0


def test_exit_code_maps_worst_severity():
    v = Verdict()
    v.add(_finding(Severity.INFO))
    v.add(_finding(Severity.WARNING))
    assert v.exit_code == 1
    v.add(_finding(Severity.CRITICAL))
    assert v.exit_code == 2


def test_severity_is_ordered():
    assert Severity.CRITICAL > Severity.WARNING > Severity.INFO


def test_advisory_flag_is_carried():
    f = _finding(Severity.WARNING, advisory=True)
    assert f.advisory is True

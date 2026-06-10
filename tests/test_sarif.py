"""SARIF 2.1.0 reporter: valid shape, level mapping, advisory downgrade."""

import json

from surfaceseal.core.models import ChangeKind, Finding, Severity, Surface, Verdict
from surfaceseal.report import sarif


def _f(rule_id, sev, advisory=False):
    surface = Surface(path=".claude/settings.json", agent="claude-code", kind=ChangeKind.ADDED)
    return Finding(
        rule_id=rule_id, severity=sev, surface=surface, line=3, message="m", advisory=advisory
    )


def test_empty_verdict_valid_sarif():
    doc = json.loads(sarif.render(Verdict()))
    assert doc["version"] == "2.1.0"
    assert doc["runs"][0]["tool"]["driver"]["name"] == "surfaceseal"
    assert doc["runs"][0]["results"] == []


def test_levels_mapped():
    v = Verdict()
    v.add(_f("SS-AUTORUN-NEW", Severity.CRITICAL))
    v.add(_f("SS-CMD-NEW", Severity.WARNING))
    v.add(_f("SS-INJ-EXFIL", Severity.WARNING, advisory=True))
    levels = [r["level"] for r in json.loads(sarif.render(v))["runs"][0]["results"]]
    assert levels == ["error", "warning", "note"]  # advisory downgraded to note


def test_location_carries_path_and_line():
    v = Verdict()
    v.add(_f("SS-AUTORUN-NEW", Severity.CRITICAL))
    loc = json.loads(sarif.render(v))["runs"][0]["results"][0]["locations"][0]["physicalLocation"]
    assert loc["artifactLocation"]["uri"] == ".claude/settings.json"
    assert loc["region"]["startLine"] == 3

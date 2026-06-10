"""Regression: pretty output chrome is ASCII; arbitrary evidence never crashes print.

Guards the Windows cp932 UnicodeEncodeError found during live testing: a scanned
file (e.g. an invisible-character injection payload) must not be able to crash the
reporter.
"""

from surfaceseal.core.models import ChangeKind, Finding, Severity, Surface, Verdict
from surfaceseal.report import pretty


def _verdict_with_evidence(evidence: str) -> Verdict:
    v = Verdict()
    surface = Surface(path=".claude/settings.json", agent="claude-code", kind=ChangeKind.ADDED)
    v.add(
        Finding(
            "SS-INJ-INVISIBLE", Severity.WARNING, surface, 1, "m", advisory=True, evidence=evidence
        )
    )
    return v


def test_chrome_is_ascii_for_clean_pass():
    # PASS line must survive any console encoding.
    pretty.render(Verdict()).encode("ascii")


def test_render_does_not_raise_on_nonascii_evidence():
    # zero-width / CJK bytes in evidence must not break rendering
    out = pretty.render(_verdict_with_evidence("payload​あ"))
    assert "SS-INJ-INVISIBLE" in out

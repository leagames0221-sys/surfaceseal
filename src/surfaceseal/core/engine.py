"""The detection pipeline: change units -> packs -> allowlist -> verdict.

Source-agnostic: it does not know whether units came from a git diff or a baseline
comparison. It only knows how to dispatch each unit to the right pack and apply the
allowlist. Keeping it here (in the core) is safe because it imports packs lazily, so
the core module graph stays acyclic at import time.
"""

from __future__ import annotations

from collections.abc import Iterable

from .models import ChangeUnit, Verdict


def run(units: Iterable[ChangeUnit], allow=None) -> Verdict:
    """Scan ``units`` and return a verdict, suppressing allowlisted findings."""
    from ..packs import autorun
    from ..surfaces import EXECUTABLE_FORMATS

    verdict = Verdict()
    for unit in units:
        # Only executable formats are scanned here; the instruction-injection
        # (advisory) pack lands in Phase 2.
        findings = autorun.scan(unit) if unit.fmt in EXECUTABLE_FORMATS else []
        for finding in findings:
            if allow is not None and allow.permits(finding.surface.path, finding.evidence):
                continue
            verdict.add(finding)
    return verdict

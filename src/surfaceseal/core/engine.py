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
    from ..packs import autorun, injection
    from ..surfaces import EXECUTABLE_FORMATS, INSTRUCTION_FORMATS

    verdict = Verdict()
    for unit in units:
        if unit.fmt in EXECUTABLE_FORMATS:
            findings = autorun.scan(unit)
        elif unit.fmt in INSTRUCTION_FORMATS:
            findings = injection.scan(unit)  # advisory, capped at WARNING
        else:
            findings = []
        for finding in findings:
            if allow is not None and allow.permits(finding.surface.path, finding.evidence):
                continue
            verdict.add(finding)
    return verdict

"""SARIF 2.1.0 output so findings drop into GitHub Code Scanning (R-11).

Hand-built JSON (no dependency). Severity maps to SARIF ``level``: CRITICAL/WARNING
-> ``error``/``warning``, advisory findings -> ``note`` regardless of severity so a
lossy detector never shows up as a hard error in the security tab.
"""

from __future__ import annotations

import json

from ..core.models import Finding, Severity, Verdict
from ..rules.autorun_rules import HIGH_RISK
from ..rules.injection_rules import ADVISORY

_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"


def _level(f: Finding) -> str:
    if f.advisory:
        return "note"
    return "error" if f.severity is Severity.CRITICAL else "warning"


def _rule_ids() -> list[str]:
    ids = ["SS-AUTORUN-NEW", "SS-CMD-NEW", "SS-PARSE"]
    ids += [s.rule_id for s in HIGH_RISK]
    ids += [s.rule_id for s in ADVISORY]
    return ids


def render(verdict: Verdict) -> str:
    results = []
    for f in verdict.findings:
        results.append(
            {
                "ruleId": f.rule_id,
                "level": _level(f),
                "message": {
                    "text": f.message + (f": {f.evidence[:200]}" if f.evidence else "")
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": f.surface.path},
                            "region": {"startLine": max(1, f.line)},
                        }
                    }
                ],
            }
        )
    doc = {
        "$schema": _SCHEMA,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "surfaceseal",
                        "informationUri": "https://github.com/leagames0221-sys/surfaceseal",
                        "rules": [{"id": rid} for rid in _rule_ids()],
                    }
                },
                "results": results,
            }
        ],
    }
    return json.dumps(doc, indent=2)

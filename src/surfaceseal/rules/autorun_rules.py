"""High-risk signatures for commands found in agent control surfaces.

Signatures are data, not prose: each is a compiled pattern with an id and a
human label. They classify *already-extracted* command strings; this module never
executes anything. Categories follow the techniques catalogued in the 2026 agent
supply-chain incident reporting (Snyk ToxicSkills, Miasma worm write-ups).
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Signature:
    rule_id: str
    pattern: re.Pattern[str]
    label: str


def _p(expr: str) -> re.Pattern[str]:
    return re.compile(expr, re.IGNORECASE)


# Each entry flags a command-string category that warrants CRITICAL on its own.
HIGH_RISK: tuple[Signature, ...] = (
    Signature("SS-EXEC-PIPE", _p(r"\b(curl|wget|iwr|invoke-webrequest)\b.*\|\s*(sh|bash|zsh|python|powershell|pwsh)\b"),
              "remote content piped into an interpreter"),
    Signature("SS-EXEC-DECODE", _p(r"\b(base64|atob|frombase64string)\b.*(-d|--decode|decode)?.*\|\s*(sh|bash|python|node|powershell|pwsh)\b"),
              "decoded blob piped into an interpreter"),
    Signature("SS-EXEC-EVAL", _p(r"\b(eval|iex|invoke-expression)\b"),
              "dynamic evaluation of a string as code"),
    Signature("SS-CRED-PATH", _p(r"(~|\$HOME|%USERPROFILE%)?[\\/]?\.(aws|ssh|gnupg|netrc|kube|npmrc|docker)\b|\.git-credentials|id_rsa"),
              "access to a credential / secret store path"),
    Signature("SS-CRED-ENV", _p(r"\b(printenv|env|set)\b.*(\||>|curl|wget|nc)\b|process\.env\b.*\b(fetch|http|post)\b"),
              "environment variables routed to output / network"),
    Signature("SS-NET-EXFIL", _p(r"\b(curl|wget|nc|ncat|invoke-webrequest|iwr)\b.*(\b\d{1,3}(\.\d{1,3}){3}\b|--data|-d\b|-F\b|post)"),
              "outbound network send of local data"),
)


def match_high_risk(command: str) -> Signature | None:
    """Return the first high-risk signature matching ``command``, else ``None``."""
    for sig in HIGH_RISK:
        if sig.pattern.search(command):
            return sig
    return None

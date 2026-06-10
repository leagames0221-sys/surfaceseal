"""Advisory signatures for hidden instructions in natural-language agent files.

These are deliberately conservative triage hints, not a reliable detector:
natural-language prompt injection cannot be caught completely by signatures
(published studies put automated recall low against obfuscation). Findings from
this module are always advisory and capped at WARNING (ADR-0003). Signatures are
data; this module never executes anything.
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


ADVISORY: tuple[Signature, ...] = (
    Signature("SS-INJ-OVERRIDE", _p(r"ignore (all |any |the )?(previous|prior|above) (instructions|rules|context)"),
              "instruction-override phrasing"),
    Signature("SS-INJ-CONCEAL", _p(r"\b(do not|don't|never)\b.{0,30}\b(tell|inform|mention|reveal|notify|show)\b.{0,20}\b(user|human|owner)\b|conceal|covertly|without (the )?user('s)? (knowledge|awareness)"),
              "instruction to hide activity from the user"),
    Signature("SS-INJ-EXFIL", _p(r"\b(send|post|upload|exfiltrate|forward|transmit)\b.{0,40}\b(token|secret|credential|api[_ -]?key|password|env|\.env)\b"),
              "instruction to send secrets outward"),
    Signature("SS-INJ-CREDREAD", _p(r"\b(read|open|cat|print|dump)\b.{0,30}(\.env|\.aws|\.ssh|id_rsa|credentials|secret)"),
              "instruction to read a credential store"),
    Signature("SS-INJ-INVISIBLE", _p(r"[​‌‍⁠﻿­]"),
              "zero-width / invisible characters (possible hidden payload)"),
)


def scan_line(line: str) -> Signature | None:
    for sig in ADVISORY:
        if sig.pattern.search(line):
            return sig
    return None

"""Parse JSON-with-comments (JSONC) using only the stdlib.

Agent config files (`.claude/settings.json`, `.vscode/tasks.json`, `hooks.json`,
`.mcp.json`) are routinely written as JSONC: ``//`` and ``/* */`` comments and
trailing commas. ``json.loads`` rejects those, so we strip them first — carefully,
without touching comment-like sequences that appear *inside* string values.

This is a tolerant reader for inspection, not a spec-strict validator.
"""

from __future__ import annotations

import json
from typing import Any


def strip_jsonc(text: str) -> str:
    """Return ``text`` with comments and trailing commas removed.

    A small state machine walks the text tracking whether we are inside a string
    (and escapes), a line comment, or a block comment, so that ``//`` or ``/*``
    embedded in a string literal is preserved verbatim.
    """
    out: list[str] = []
    i = 0
    n = len(text)
    in_string = False
    escaped = False
    in_line_comment = False
    in_block_comment = False

    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
                out.append(ch)
            i += 1
            continue

        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
            # keep newlines so line numbers downstream stay roughly aligned
            if ch == "\n":
                out.append(ch)
            i += 1
            continue

        if in_string:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            i += 1
            continue

        # not in string or comment
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue
        out.append(ch)
        i += 1

    return _strip_trailing_commas("".join(out))


def _strip_trailing_commas(text: str) -> str:
    """Remove commas that immediately precede a ``}`` or ``]`` (ignoring whitespace)."""
    out: list[str] = []
    i = 0
    n = len(text)
    in_string = False
    escaped = False
    while i < n:
        ch = text[i]
        if in_string:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        if ch == ",":
            j = i + 1
            while j < n and text[j] in " \t\r\n":
                j += 1
            if j < n and text[j] in "}]":
                # drop this comma; keep the whitespace for line alignment
                out.append(text[i + 1 : j])
                i = j
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def loads(text: str) -> Any:
    """Parse JSONC text into Python objects. Raises ``json.JSONDecodeError`` on failure."""
    return json.loads(strip_jsonc(text))

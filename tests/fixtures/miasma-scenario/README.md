# Miasma scenario fixture

Reproduces the shape of the **Miasma worm** (June 2026): a pull request that adds a
poisoned entry to an AI agent's control surface so that, when any downstream
developer opens the repo in their agent, an auto-running hook harvests credentials.

- `clean/.claude/settings.json` — the legitimate base: one formatter hook a
  maintainer has accepted (allowlisted in real use).
- `poisoned/.claude/settings.json` — the malicious PR: keeps the formatter, then
  adds a `SessionStart` hook that reads a credential store and sends it outbound.

Expected surfaceseal verdict on the diff (`clean` → `poisoned`):

- the formatter hook is **not** re-flagged (unchanged since base),
- the new `SessionStart` hook is **CRITICAL** (auto-executing + credential/network
  signature), so `scan --diff` exits `2` and a CI gate blocks the merge.

This is exercised end-to-end in `tests/test_miasma_integration.py` against a real
temporary git repository.

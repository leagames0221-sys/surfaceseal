# ADR-0002 — Two operating modes: diff gate and baseline drift

- **Status**: Accepted
- **Date**: 2026-06-10

## Context

The tool must answer two related but distinct questions, and conflating them makes
the product blurry:

1. *"Did this PR introduce poison?"* — the outbound CI gate.
2. *"Has an already-trusted environment been tampered with since I accepted it?"* —
   the worm re-commit / drift vector, where there may be no PR diff to read.

A naive "scan everything every time" approach fails question 1: a repo's legitimate,
long-standing hooks would re-alert on every run (alert fatigue), defeating an
outbound gate.

## Decision

Ship **two explicit modes**, sharing one detection core:

- `scan --diff [--base <ref>]` — analyse only files **added/modified** in the git
  diff. Reasons about the *change*. This is the merge-gate path.
- `scan --baseline` — compare the current control surface against a pinned hash
  snapshot (`surfaceseal init` creates it). Flags drift even without a diff context.

## Alternatives considered

- **Full-tree scan (snyk-style)** — rejected: produces alert fatigue as an outbound
  gate; cannot separate "always-been-here" from "introduced now".
- **Diff-only, no baseline** — rejected: misses the worm re-commit when scanning an
  installed environment with no PR.
- **Baseline-only** — rejected: heavier setup; the common CI case is a PR diff.

## Consequence

Both modes feed the same `core` engine and packs; only the *change source*
(`gitdiff` vs `baseline`) differs. `ChangeKind` (ADDED/MODIFIED/DRIFTED) records
provenance so reporters and rules can treat them appropriately.

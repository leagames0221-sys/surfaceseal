# ADR-0003 — Deterministic core, LLM as an optional explain layer

- **Status**: Accepted
- **Date**: 2026-06-10

## Context

Two detection problems with very different tractability sit under one roof:

- **Structural** (autorun commands, hooks, MCP server commands) — the format is
  fixed; detection is deterministic and high-confidence.
- **Natural-language instruction injection** (hidden directives in `CLAUDE.md` /
  `AGENTS.md`) — inherently lossy; published work shows signature/automated recall
  is low against obfuscation.

## Decision

- The **detection core is fully deterministic**. All gating decisions come from
  static rules; results are reproducible and CI-stable.
- **Structural detection is the headline** (`packs/autorun`), emits up to CRITICAL.
- **Instruction-injection is advisory** (`packs/injection`), capped at WARNING, so a
  lossy detector can never on its own fail a merge.
- **LLM is an optional explain-only layer** (`--explain`, Ollama). It annotates
  findings in plain language; it **does not** produce or change verdicts. If the LLM
  is unavailable the core completes every function (fail-soft).

## Alternatives considered

- **LLM-as-judge for verdicts** — rejected: non-reproducible, violates the free /
  local-first constraint, and makes CI flaky.

## Consequence

Provider access goes through an ABC (`explain/base.py`) with an Ollama implementation
and env swap; default behaviour requires no LLM at all.

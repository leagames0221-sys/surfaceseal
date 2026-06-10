# ADR-0004 — Domain-agnostic core + detection packs (2-layer)

- **Status**: Accepted
- **Date**: 2026-06-10

## Context

Agent control surfaces and threat signatures change monthly (new agents: windsurf,
kiro, antigravity, hermes…). Hardcoding formats and rules into one module would rot
and would not transfer to bespoke client engagements.

## Decision

Two layers with a one-way dependency:

- `core/` — domain-agnostic contracts (`Finding`, `Surface`, `Severity`, `Verdict`,
  the detection `engine`, `baseline`). Knows nothing about specific file formats.
- `packs/` — domain logic (`autorun`, `injection`) that produces `Finding`s, with
  signatures isolated as data in `rules/`.

`core` never imports a pack. Surfaces are config-driven via `surfaces.toml`
(bundled defaults + user extension), so adding an agent is data, not code.

## Alternatives considered

- **Single module** — rejected: rots as surfaces multiply; no clean reuse path for
  client-specific packs.

## Consequence

Reuse for a bespoke engagement = drop in a new pack + a `surfaces.toml` entry; the
core and CLI are untouched.

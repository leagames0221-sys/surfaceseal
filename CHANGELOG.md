# Changelog

All notable changes to this project are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); this project uses semantic versioning.

## [Unreleased]

### Added
- Phase 0 scaffold: project layout, zero-dependency `pyproject.toml`, domain-agnostic
  core model (`Finding` / `Surface` / `Severity` / `Verdict`).
- ADR-0001 (prior-art audit + scope), ADR-0002 (diff vs baseline two-mode split),
  ADR-0003 (deterministic core + optional LLM layer), ADR-0004 (core/packs 2-layer).
- Phase 1 (headline, R-04): diff-aware structural detection of autorun/hook/MCP
  command capability introduced by a change.
  - `gitdiff` (isolated git access), self-contained JSONC parser, config-driven
    surface registry (`surfaces.toml`), `packs/autorun` + high-risk signature rules.
  - `allowlist` + `surfaceseal init` (fail-closed bootstrap), `scan --diff` /
    `--baseline` modes, human-readable report, exit codes 0/1/2.
  - Miasma-scenario fixture + end-to-end git integration test (poisoned PR → exit 2).
  - 25 tests pass, ruff clean.

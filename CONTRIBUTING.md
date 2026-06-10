# Contributing

Thanks for looking. surfaceseal is a small, dependency-free CLI; contributions that
keep it that way are most welcome.

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest -q          # tests
python -m ruff check .       # lint
```

## Ground rules

- **Zero runtime dependencies.** The detection core must run on the standard library
  alone. A new runtime dependency requires an ADR justifying it (see `docs/adr/`).
- **Never execute inspected content.** No `eval`, `exec`, dynamic `import`, or
  subprocess execution of the files being scanned. Git access stays isolated in
  `gitdiff.py`.
- **Signatures are data.** Add detection patterns to `src/surfaceseal/rules/` and
  exercise them with fixtures under `tests/fixtures/` — never inline a working
  payload in prose.
- **Be honest about confidence.** Structural detection (autorun/hook/MCP) is the
  high-confidence headline; natural-language injection detection is advisory and
  capped at WARNING. Keep that boundary.

## Adding a new agent surface

Add an entry to `src/surfaceseal/surfaces.toml` (or ship a repo-root `surfaces.toml`)
mapping the path to an `agent` and a `format`. New formats need an extractor in the
relevant pack.

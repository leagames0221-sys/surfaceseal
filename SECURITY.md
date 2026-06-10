# Security Policy

## Reporting a vulnerability

Open a private security advisory via GitHub's "Report a vulnerability" flow on this
repository. Please do not file public issues for undisclosed vulnerabilities.

## Design stance

- **surfaceseal never executes the code it inspects.** All analysis is static: files
  are parsed, never imported, run, or evaluated. There is no `eval`, `exec`, dynamic
  `import`, or subprocess execution of inspected content anywhere in the codebase.
- **Dangerous patterns live in data, not prose.** Detection signatures are kept in
  `src/surfaceseal/rules/` and exercised only through fixtures under `tests/fixtures/`,
  never described inline in a way that could function as a payload recipe.
- **Zero runtime dependencies.** The tool does not widen the supply-chain surface it
  is meant to defend.

## Scope

surfaceseal detects *tampering / injection* in AI agent control-surface files. It is
not a general SAST tool, not a dependency scanner, and not a runtime sandbox.

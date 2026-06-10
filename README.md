# surfaceseal

**A security merge gate for the files your AI coding agent silently trusts.**

When you open a repository in Claude Code, Cursor, Codex, or Gemini CLI, the agent
auto-reads its *control surface* — hook definitions, instruction files, autorun
tasks, MCP server configs — and acts on them **before you review anything**. That
makes those files a supply-chain attack surface. The Miasma worm (June 2026) used
exactly this: a committed `.claude/` config that harvested credentials and then
re-committed itself into every repo the stolen tokens could write to, disabling
73 repositories across Microsoft orgs.

surfaceseal is the **outbound quarantine**: it reads a pull request's *diff*, looks
only at what that diff **adds or changes** in the agent control surface, and blocks
the merge if a commit introduces a poisoned hook, an autorun payload, or a hidden
instruction — so you never ship the worm downstream.

> **Scope is security, not quality.** surfaceseal answers *"has this agent config
> been poisoned?"* It is **not** a capability-governance gate (for *"is this tool
> well-built / approval-gated / idempotent?"* see
> [agents-shipgate](https://github.com/ThreeMoonsLab/agents-shipgate)). The two are
> complementary: shipgate reviews tool readiness; surfaceseal reviews tampering.

## Why diff-aware (and not a full scan)

Existing agent scanners walk the whole tree and flag every config they find. As an
*outbound* gate that produces alert fatigue — a repo's legitimate, long-standing
hooks light up on every run. surfaceseal compares **base vs head** and reasons about
*the change*: a brand-new autorun command in this PR is the signal; the hook that
has been there for six months and is on your allowlist is not.

## What it checks

- **Autorun / hook injection** (primary, deterministic) — new or modified shell
  commands in `.claude/settings.json`, `.vscode/tasks.json`, `hooks.json`,
  `.mcp.json` server commands. *(structural → high confidence)*
- **Trusted-surface drift** — `--baseline` mode pins a hash of the control surface
  and flags later tampering (the worm re-commit vector) outside a git-diff context.
- **Instruction injection** (advisory) — best-effort signatures for hidden directives
  in `CLAUDE.md` / `AGENTS.md` (credential-exfil phrasing, "conceal this" patterns,
  obfuscated payloads). *Capped at `warning`; natural-language detection is
  inherently lossy — see [Limitations](#limitations).*

## Constraints

Free · no credit card · runs fully local · **zero runtime dependencies** · never
executes the code it inspects (static analysis only).

## Quick start

```bash
# Gate a pull request's diff (exit 2 = critical → CI fails the merge)
surfaceseal scan --diff --base origin/main

# Accept the current control surface as a trusted baseline
surfaceseal init

# Re-check an already-installed environment against its baseline
surfaceseal scan --baseline
```

## Use as a GitHub Action

Gate every pull request — a poisoned control-surface change fails the check:

```yaml
# .github/workflows/surfaceseal.yml
name: surfaceseal
on: pull_request
jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: leagames0221-sys/surfaceseal@master
        # with:
        #   fail-on-warning: "true"   # also fail on advisory/warning findings
```

`surfaceseal init` first, commit `.surfaceseal-allow.toml` + `.surfaceseal-baseline.json`,
and the gate only flags what a PR *introduces* on top of that accepted baseline.

## Limitations

- **Instruction-injection detection is advisory and lossy.** Natural-language
  prompt injection cannot be caught reliably by deterministic signatures; published
  studies put automated recall low against obfuscation. surfaceseal's strength is the
  *structural* autorun/hook/MCP layer; treat injection findings as triage hints.
- Differentiation is a *combination* (diff-scoped × security-intent × control-surface),
  not a single novel check. A general scanner could add a diff mode.
- Covers a fixed (but config-extensible) set of agent surfaces; new agents need a
  `surfaces.toml` entry.

## License

MIT.

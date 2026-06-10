# ADR-0001 — Prior-art audit and scope

- **Status**: Accepted
- **Date**: 2026-06-10

## Context

AI coding agents auto-trust an in-repo *control surface* (hooks, instruction files,
autorun tasks, MCP configs). In 2026 this became an active supply-chain attack
surface: the Miasma worm (June 2026) shipped a poisoned `.claude/` config that
harvested credentials and re-committed itself downstream, disabling 73 Microsoft-org
repositories; Check Point disclosed pre-trust RCE in Claude Code via repo config
(CVE-2025-59536, CVSS 8.7). NVIDIA's mitigation guidance explicitly recommends
auditing AI-generated PRs but names no tool that does it.

Before building, the existing tools were audited (clone/metadata/source inspection,
read-only) to avoid duplicating prior art.

## Decision

Build a **security-intent, diff-aware merge gate** specialized to the agent control
surface. Adopt nothing; reuse only patterns. Own contribution = the diff-scoped
security detection of poisoned autorun/hook/MCP changes.

## Prior art (audited 2026-06-10)

| Tool | Position | Why not a fit |
|---|---|---|
| `snyk/agent-scan` (2548★, Apache-2.0) | Consumer-side: scans installed/home components + remote skills/MCP; has rug-pull (W005) | Full-tree, consumer-oriented; not a diff-scoped *outbound* gate |
| `cisco-ai-defense/skill-scanner` (2162★) | Skill-unit scanner (static/behavioral/LLM) | Skill-centric; autorun/instruction-injection in a repo diff not central |
| GoPlus / A386 `AgentGuard` | Runtime: blocks dangerous actions at tool-call time | Runtime sandbox, not commit-time |
| `microsoft/agent-governance-toolkit` | Pre-commit *governance* (naming, required fields, secrets) | Docs state it does **not** detect malicious/injected agent config |
| `ThreeMoonsLab/agents-shipgate` (Apache-2.0) | Static PR-diff merge gate for **tool-use readiness** (approval policy, idempotency, schema completeness) | Same *form*, different *intent*: quality governance, explicitly **not** malware/injection detection. **Complementary.** |

## Consequence

- Differentiation is a **combination** (diff-scoped × security-intent × control-surface),
  not a single novel check — recorded honestly in README Limitations.
- Multiple teams are independently converging on the static PR-diff agent-gate form
  (snyk = consumer, shipgate = quality, surfaceseal = security). This validates demand
  but means the durable niche is the **security** specialization.
- README positions surfaceseal as complementary to agents-shipgate, not competitive.

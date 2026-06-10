"""Command-line entry point.

Subcommands:
  scan --diff [--base REF]   gate a pull request's changes (default merge-gate path)
  scan --baseline            re-check an installed environment vs its pinned baseline
  init                       accept the current control surface as the allowlist

Exit codes: 0 clean / 1 warning / 2 critical (R-10), so CI fails the merge on 2.
"""

from __future__ import annotations

import argparse
import sys

from . import gitdiff
from .allowlist import Allowlist
from .core import engine
from .core.models import ChangeKind, ChangeUnit, Surface
from .report import pretty
from .surfaces import SurfaceRule, classify, load_rules


def _unit_from(
    path: str, head_text: str, base_text: str | None, kind: ChangeKind, rule: SurfaceRule
) -> ChangeUnit:
    surface = Surface(path=path, agent=rule.agent, kind=kind)
    return ChangeUnit(surface=surface, fmt=rule.format, head_text=head_text, base_text=base_text)


def _units_from_diff(base: str, cwd: str, rules: list[SurfaceRule]) -> list[ChangeUnit]:
    units: list[ChangeUnit] = []
    for entry in gitdiff.changed_files(base, cwd):
        rule = classify(entry.path, rules)
        if rule is None:
            continue
        units.append(
            _unit_from(entry.path, entry.head_text, entry.base_text, entry.change_kind, rule)
        )
    return units


def _units_from_disk(cwd: str, rules: list[SurfaceRule]) -> list[ChangeUnit]:
    units: list[ChangeUnit] = []
    for path in gitdiff.tracked_files(cwd):
        rule = classify(path, rules)
        if rule is None:
            continue
        text = gitdiff.read_head(path, cwd)
        if text is None:
            continue
        units.append(_unit_from(path, text, None, ChangeKind.ADDED, rule))
    return units


def _cmd_scan(args: argparse.Namespace) -> int:
    cwd = args.repo
    rules = load_rules(cwd)
    allow = Allowlist.load(cwd)

    if args.baseline:
        # Phase 2 wires the pinned-hash comparison; for now baseline re-scans the
        # current surface against the allowlist (drift surfaces as un-allowlisted).
        units = _units_from_disk(cwd, rules)
    else:
        units = _units_from_diff(args.base, cwd, rules)

    verdict = engine.run(units, allow)
    print(pretty.render(verdict))
    return verdict.exit_code


def _cmd_init(args: argparse.Namespace) -> int:
    cwd = args.repo
    rules = load_rules(cwd)
    units = _units_from_disk(cwd, rules)
    verdict = engine.run(units, allow=None)  # no allowlist: capture everything present
    allow = Allowlist()
    for f in verdict.findings:
        if f.evidence:
            allow.add(f.surface.path, f.evidence)
    out = allow.write(cwd)
    print(f"surfaceseal: wrote {len(allow.scoped)} accepted entries to {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="surfaceseal", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="scan control-surface changes")
    mode = scan.add_mutually_exclusive_group()
    mode.add_argument("--diff", action="store_true", help="gate the git diff (default)")
    mode.add_argument("--baseline", action="store_true", help="re-check vs the pinned baseline")
    scan.add_argument("--base", default="HEAD~1", help="base ref for --diff (default: HEAD~1)")
    scan.add_argument("--repo", default=".", help="repository path (default: .)")
    scan.set_defaults(func=_cmd_scan)

    init = sub.add_parser("init", help="accept the current control surface as the allowlist")
    init.add_argument("--repo", default=".", help="repository path (default: .)")
    init.set_defaults(func=_cmd_init)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except RuntimeError as exc:
        print(f"surfaceseal: error: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())

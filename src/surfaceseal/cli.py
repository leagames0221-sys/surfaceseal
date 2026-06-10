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
from .core import baseline, engine
from .core.models import ChangeKind, ChangeUnit, Surface
from .report import pretty, sarif
from .surfaces import SurfaceRule, classify, load_rules, path_excluded


def _unit_from(
    path: str, head_text: str, base_text: str | None, kind: ChangeKind, rule: SurfaceRule
) -> ChangeUnit:
    surface = Surface(path=path, agent=rule.agent, kind=kind)
    return ChangeUnit(surface=surface, fmt=rule.format, head_text=head_text, base_text=base_text)


def _units_from_diff(
    base: str, cwd: str, rules: list[SurfaceRule], excludes: list[str]
) -> list[ChangeUnit]:
    units: list[ChangeUnit] = []
    for entry in gitdiff.changed_files(base, cwd):
        if path_excluded(entry.path, excludes):
            continue
        rule = classify(entry.path, rules)
        if rule is None:
            continue
        units.append(
            _unit_from(entry.path, entry.head_text, entry.base_text, entry.change_kind, rule)
        )
    return units


def _units_from_disk(cwd: str, rules: list[SurfaceRule], excludes: list[str]) -> list[ChangeUnit]:
    units: list[ChangeUnit] = []
    for path in gitdiff.tracked_files(cwd):
        if path_excluded(path, excludes):
            continue
        rule = classify(path, rules)
        if rule is None:
            continue
        text = gitdiff.read_head(path, cwd)
        if text is None:
            continue
        units.append(_unit_from(path, text, None, ChangeKind.ADDED, rule))
    return units


def _units_from_baseline(
    cwd: str, rules: list[SurfaceRule], excludes: list[str]
) -> list[ChangeUnit]:
    """Build DRIFTED units for in-scope files new or changed vs the pinned baseline."""
    pinned = baseline.load(cwd)
    units: list[ChangeUnit] = []
    for path in gitdiff.tracked_files(cwd):
        if path_excluded(path, excludes):
            continue
        rule = classify(path, rules)
        if rule is None:
            continue
        text = gitdiff.read_head(path, cwd)
        if text is None:
            continue
        if pinned and not baseline.is_drifted(pinned, path, text):
            continue  # trusted and unchanged since the baseline was pinned
        units.append(_unit_from(path, text, None, ChangeKind.DRIFTED, rule))
    return units


def _emit(verdict, fmt: str) -> None:
    print(sarif.render(verdict) if fmt == "sarif" else pretty.render(verdict))


def _cmd_scan(args: argparse.Namespace) -> int:
    cwd = args.repo
    rules = load_rules(cwd)
    allow = Allowlist.load(cwd)

    excludes = args.exclude or []
    if args.baseline:
        units = _units_from_baseline(cwd, rules, excludes)
    else:
        units = _units_from_diff(args.base, cwd, rules, excludes)

    verdict = engine.run(units, allow)
    _emit(verdict, args.format)
    return verdict.exit_code


def _cmd_init(args: argparse.Namespace) -> int:
    cwd = args.repo
    rules = load_rules(cwd)
    units = _units_from_disk(cwd, rules, args.exclude or [])

    # 1) allowlist: accept the commands currently present so they do not re-alert
    verdict = engine.run(units, allow=None)
    allow = Allowlist()
    for f in verdict.findings:
        # Only allowlist gating (structural) findings; advisory injection hints are
        # WARNING-only and must keep surfacing, so they are not silenced here.
        if f.evidence and not f.advisory:
            allow.add(f.surface.path, f.evidence)
    allow_path = allow.write(cwd)

    # 2) baseline: pin a content hash of every in-scope surface for drift detection
    pinned = {u.surface.path: baseline.hash_text(u.head_text) for u in units}
    base_path = baseline.write(cwd, pinned)

    print(
        f"surfaceseal: accepted {len(allow.scoped)} commands ({allow_path.name}); "
        f"pinned {len(pinned)} surfaces ({base_path.name})"
    )
    if allow.scoped:
        # Trust-on-first-use: init endorses whatever executes today. If the repo is
        # already compromised, that poison is being accepted — review before committing.
        print(
            "  note: this accepts the control surface AS-IS. Review "
            f"{allow_path.name} before committing — anything already poisoned is now allowlisted.",
            file=sys.stderr,
        )
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
    scan.add_argument(
        "--format", choices=["pretty", "sarif"], default="pretty", help="output format"
    )
    scan.add_argument(
        "--exclude", action="append", metavar="GLOB",
        help="skip paths matching this glob (repeatable; supports trailing /**)",
    )
    scan.set_defaults(func=_cmd_scan)

    init = sub.add_parser("init", help="accept the current control surface as the allowlist")
    init.add_argument("--repo", default=".", help="repository path (default: .)")
    init.add_argument(
        "--exclude", action="append", metavar="GLOB",
        help="skip paths matching this glob (repeatable; supports trailing /**)",
    )
    init.set_defaults(func=_cmd_init)
    return p


def _make_output_robust() -> None:
    """Best-effort: scanned files may contain arbitrary (even invisible) characters.

    On a non-UTF-8 console (e.g. Windows cp932) printing that evidence would raise
    UnicodeEncodeError, so re-encode stdout/stderr as UTF-8 with replacement. Guarded
    because some streams (test capture) do not support reconfigure.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001 - never let output setup break the run
            pass


def main(argv: list[str] | None = None) -> int:
    _make_output_robust()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except RuntimeError as exc:
        print(f"surfaceseal: error: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())

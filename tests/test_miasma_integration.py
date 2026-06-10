"""End-to-end gate test against a real temporary git repository (the killer demo).

Builds a repo, commits a clean control surface, then commits a Miasma-style
poisoned PR, and asserts that `surfaceseal scan --diff` blocks it with exit 2.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from surfaceseal.cli import main

FIXTURES = Path(__file__).parent / "fixtures" / "miasma-scenario"


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "-c", "commit.gpgsign=false", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _place(repo: Path, variant: str) -> None:
    src = FIXTURES / variant / ".claude" / "settings.json"
    dst = repo / ".claude" / "settings.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def _make_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _place(repo, "clean")
    _git(repo, "add", "-f", "-A")
    _git(repo, "commit", "-q", "-m", "clean base")
    base = _git(repo, "rev-parse", "HEAD")
    return repo, base


def test_poisoned_pr_is_blocked(tmp_path, capsys):
    repo, base = _make_repo(tmp_path)
    _place(repo, "poisoned")
    _git(repo, "add", "-f", "-A")
    _git(repo, "commit", "-q", "-m", "innocent-looking PR")

    code = main(["scan", "--diff", "--base", base, "--repo", str(repo)])
    out = capsys.readouterr().out

    assert code == 2, f"expected merge to be blocked, got exit {code}\n{out}"
    assert "CRITICAL" in out
    assert "npm run format" not in out  # pre-existing hook must not be re-flagged


def test_no_op_change_passes(tmp_path, capsys):
    repo, base = _make_repo(tmp_path)
    # commit an unrelated, non-surface file
    (repo / "src.py").write_text("print('hi')\n", encoding="utf-8")
    _git(repo, "add", "-f", "-A")
    _git(repo, "commit", "-q", "-m", "unrelated change")

    code = main(["scan", "--diff", "--base", base, "--repo", str(repo)])
    out = capsys.readouterr().out
    assert code == 0, out
    assert "PASS" in out


def test_init_then_clean_diff_passes(tmp_path, capsys):
    repo, base = _make_repo(tmp_path)
    # accept the current surface, then re-add the same file in a new commit
    main(["init", "--repo", str(repo)])
    capsys.readouterr()
    # baseline mode should now find nothing un-allowlisted
    code = main(["scan", "--baseline", "--repo", str(repo)])
    out = capsys.readouterr().out
    assert code == 0, out

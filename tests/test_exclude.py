"""Exclude globs: keep test fixtures / vendored samples out of a repo's own gate."""

from surfaceseal.surfaces import path_excluded


def test_recursive_prefix_match():
    assert path_excluded("tests/fixtures/miasma/.claude/settings.json", ["tests/fixtures/**"])
    assert path_excluded("tests/fixtures", ["tests/fixtures/**"])


def test_non_match_passes_through():
    assert not path_excluded(".claude/settings.json", ["tests/fixtures/**"])


def test_plain_fnmatch():
    assert path_excluded("vendor/x.json", ["vendor/*.json"])
    assert not path_excluded("src/x.json", ["vendor/*.json"])


def test_empty_patterns():
    assert not path_excluded(".claude/settings.json", [])

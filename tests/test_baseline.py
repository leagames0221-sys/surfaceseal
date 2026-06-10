"""Baseline drift: hashing, drift detection, write/load roundtrip."""

from surfaceseal.core import baseline


def test_hash_is_deterministic():
    assert baseline.hash_text("abc") == baseline.hash_text("abc")
    assert baseline.hash_text("abc") != baseline.hash_text("abd")


def test_drift_detection():
    pinned = {".claude/settings.json": baseline.hash_text("v1")}
    assert baseline.is_drifted(pinned, ".claude/settings.json", "v1") is False
    assert baseline.is_drifted(pinned, ".claude/settings.json", "v2") is True  # changed
    assert baseline.is_drifted(pinned, "new.json", "x") is True  # new path


def test_write_load_roundtrip(tmp_path):
    surfaces = {".claude/settings.json": "deadbeef", ".mcp.json": "cafe"}
    baseline.write(tmp_path, surfaces)
    loaded = baseline.load(tmp_path)
    assert loaded == surfaces


def test_load_missing_returns_empty(tmp_path):
    assert baseline.load(tmp_path) == {}

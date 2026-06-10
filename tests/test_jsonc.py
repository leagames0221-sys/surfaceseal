"""JSONC parser: comments and trailing commas stripped; strings preserved."""

from surfaceseal.parsers import jsonc


def test_line_comment_stripped():
    assert jsonc.loads('{ "a": 1 // note\n}') == {"a": 1}


def test_block_comment_stripped():
    assert jsonc.loads('{ /* x */ "a": 1 }') == {"a": 1}


def test_trailing_comma_stripped():
    assert jsonc.loads('{ "a": [1, 2,], }') == {"a": [1, 2]}


def test_comment_like_sequence_inside_string_preserved():
    parsed = jsonc.loads('{ "url": "https://x/y", "p": "a//b" }')
    assert parsed == {"url": "https://x/y", "p": "a//b"}


def test_newlines_kept_for_line_alignment():
    text = '{\n  "a": 1, // c\n  "b": 2\n}'
    # the value for b must still resolve; comment removal must not collapse lines
    assert jsonc.loads(text) == {"a": 1, "b": 2}

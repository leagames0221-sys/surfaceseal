"""Surface classification from the bundled registry."""

from surfaceseal.surfaces import classify, load_rules

RULES = load_rules()


def test_claude_settings_classified():
    r = classify(".claude/settings.json", RULES)
    assert r is not None and r.agent == "claude-code" and r.format == "claude_settings"


def test_nested_mcp_json_classified_by_basename():
    r = classify("packages/api/.mcp.json", RULES)
    assert r is not None and r.format == "mcp_json"


def test_vscode_tasks_classified():
    r = classify(".vscode/tasks.json", RULES)
    assert r is not None and r.format == "vscode_tasks"


def test_instruction_file_classified():
    r = classify("AGENTS.md", RULES)
    assert r is not None and r.format == "instruction_md"


def test_unrelated_file_not_classified():
    assert classify("src/app/main.py", RULES) is None
    assert classify("README.md", RULES) is None

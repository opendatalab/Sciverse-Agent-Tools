"""Regression checks for the checked-in Claude plugin bundle."""
import json
from pathlib import Path

from generators.to_claude_skill import (
    generate_marketplace_json,
    generate_mcp_json,
    generate_plugin_json,
    generate_skill_md,
)

ROOT = Path(__file__).resolve().parents[1]
OPENAPI = ROOT / "openapi.yaml"


def test_checked_in_plugin_artifacts_match_generator_bytes():
    artifacts = {
        "skill-claude-code/skills/sciverse/SKILL.md": generate_skill_md(OPENAPI),
    }
    for path, content in {
        "skill-claude-code/.claude-plugin/plugin.json": generate_plugin_json(OPENAPI),
        "skill-claude-code/.mcp.json": generate_mcp_json(),
        ".claude-plugin/marketplace.json": generate_marketplace_json(OPENAPI),
    }.items():
        artifacts[path] = json.dumps(content, ensure_ascii=False, indent=2) + "\n"
    for path, expected in artifacts.items():
        assert (ROOT / path).read_bytes() == expected.encode("utf-8"), path


def test_project_mcp_example_preserves_file_credential_fallback():
    skill = generate_skill_md(OPENAPI)
    block = skill.split("   ```json\n", 1)[1].split("   ```", 1)[0]
    example = json.loads(block)
    assert example == generate_mcp_json()
    assert "env" not in example["mcpServers"]["sciverse"]

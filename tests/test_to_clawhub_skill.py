from pathlib import Path

from generators.to_clawhub_skill import generate_manifest, generate_skill_md

FIXTURE = Path(__file__).parent / "fixtures" / "minimal_openapi.yaml"


def test_manifest_basic_fields():
    m = generate_manifest(FIXTURE)
    assert m["name"] == "sciverse-agent-tools"
    assert m["version"] == "1.0.0"  # fixture 中是 1.0.0
    assert m["runtime"] == "node>=18"
    assert "do_foo" in {t["name"] for t in m["tools"]}


def test_manifest_tool_entry_points():
    m = generate_manifest(FIXTURE)
    do_foo = next(t for t in m["tools"] if t["name"] == "do_foo")
    assert do_foo["script"] == "scripts/do_foo.mjs"
    assert "input_schema" in do_foo


def test_skill_md_has_frontmatter():
    md = generate_skill_md(FIXTURE)
    assert md.startswith("---\n")
    assert "name: sciverse-agent-tools" in md
    assert "version: 1.0.0" in md


def test_skill_md_lists_all_tools():
    md = generate_skill_md(FIXTURE)
    assert "## do_foo" in md
    assert "测试 tool。" in md

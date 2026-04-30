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
    assert "### do_foo" in md
    # Fixture 没有 x-en-description，fallback 到 description（中文）。
    assert "测试 tool。" in md


def test_skill_md_prefers_english_extension_when_present():
    fixture = Path(__file__).parent / "fixtures" / "with_en_openapi.yaml"
    md = generate_skill_md(fixture)
    assert "Run a foo" in md  # x-en-description 文本
    assert "测试 tool。" not in md  # 中文 description 不应出现


def test_manifest_uses_english_description_for_tools():
    fixture = Path(__file__).parent / "fixtures" / "with_en_openapi.yaml"
    m = generate_manifest(fixture)
    do_foo = next(t for t in m["tools"] if t["name"] == "do_foo")
    assert "Run a foo" in do_foo["description"]


def test_skill_md_uses_english_static_sections():
    md = generate_skill_md(FIXTURE)
    # 静态段落必须为英文（与 ClawHub 社区惯例对齐）
    assert "## When to use" in md
    assert "## Authentication" in md
    assert "## Tools" in md
    assert "## Composition patterns" in md
    assert "## Exit codes" in md

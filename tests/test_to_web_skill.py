from pathlib import Path

from generators.to_web_skill import generate

FIXTURE = Path(__file__).parent / "fixtures" / "minimal_openapi.yaml"


def test_generate_creates_expected_directory_tree(tmp_path):
    out = tmp_path / "web-skill"
    generate(FIXTURE, out)
    skill_root = out / ".well-known" / "agent-skills" / "sciverse"
    assert skill_root.is_dir()
    assert (skill_root / "SKILL.md").is_file()
    # index.json 在 .well-known/agent-skills/ 这一级（与 platform-console 现状一致），不在 sciverse/ 内
    assert (out / ".well-known" / "agent-skills" / "index.json").is_file()
    assert (skill_root / "references" / "workflows.md").is_file()
    assert (skill_root / "references" / "rag-and-content.md").is_file()
    assert (skill_root / "references" / "search-tools.md").is_file()
    assert (skill_root / "references" / "runtime.md").is_file()
    assert (skill_root / "agents" / "openai.yaml").is_file()


def test_skill_md_frontmatter_has_name(tmp_path):
    out = tmp_path / "web-skill"
    generate(FIXTURE, out)
    content = (out / ".well-known" / "agent-skills" / "sciverse" / "SKILL.md").read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert "name: sciverse" in content


def test_references_copied_byte_for_byte(tmp_path):
    """references/*.md 是 narrative 文档，generator 不做 template 渲染。"""
    out = tmp_path / "web-skill"
    generate(FIXTURE, out)
    src = Path(__file__).parent.parent / "generators" / "web_skill_assets" / "references" / "workflows.md"
    dst = out / ".well-known" / "agent-skills" / "sciverse" / "references" / "workflows.md"
    assert dst.read_bytes() == src.read_bytes()


def test_index_json_lists_all_skill_files_sorted(tmp_path):
    """index.json 的 files 数组列出 sciverse/ 内全部文件，按字符串排序稳定。"""
    import json
    out = tmp_path / "web-skill"
    generate(FIXTURE, out)
    index = json.loads((out / ".well-known" / "agent-skills" / "index.json").read_text(encoding="utf-8"))
    skills = index["skills"]
    assert len(skills) == 1
    sciverse = skills[0]
    assert sciverse["name"] == "sciverse"
    assert isinstance(sciverse["description"], str) and sciverse["description"]
    files = sciverse["files"]
    # 应有 SKILL.md / agents/openai.yaml / references/*.md 4 个（scripts 由 Task A3 加，本 task 测试不假设）
    assert "SKILL.md" in files
    assert "agents/openai.yaml" in files
    assert "references/workflows.md" in files
    # 必须排序：调用 sorted(files) == files
    assert files == sorted(files), f"files not sorted: {files}"

import json
from pathlib import Path

import pytest

from generators.to_web_skill import SKILL_DESCRIPTION, generate

FIXTURE = Path(__file__).parent / "fixtures" / "minimal_openapi.yaml"

# platform-console fork（dev branch）保留期内可用的真值 source。
# Phase B 完成后该路径会被删除，届时本测试会 skip 而不是 fail。
LEGACY_SOURCE_INDEX = Path(
    "/Users/shlab/development/sciverse-console/platform-console"
    "/frontend/public/.well-known/agent-skills/index.json"
)


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


def test_skill_description_matches_legacy_source():
    """C1 regression：SKILL_DESCRIPTION 必须与 platform-console source 真值字符串相等。

    Phase B 完成后 platform-console fork 会被删除，本测试随之 skip。
    """
    if not LEGACY_SOURCE_INDEX.exists():
        pytest.skip("legacy source removed after Phase B")
    source = json.loads(LEGACY_SOURCE_INDEX.read_text(encoding="utf-8"))
    expected = source["skills"][0]["description"]
    assert SKILL_DESCRIPTION == expected, (
        "SKILL_DESCRIPTION drifted from platform-console source; "
        "若 source 真的改了，请同步更新 to_web_skill.SKILL_DESCRIPTION。"
    )


def test_generate_is_idempotent_with_stale_files(tmp_path):
    """I2 regression：二次运行不应让旧残留文件混进 index.json files 数组。

    通过在 sciverse/ 子树下预创建一个 stale 文件，跑 generate() 后断言：
      1) stale 文件已被清理（_copy_static 入口 shutil.rmtree skill_root）
      2) index.json 的 files 数组不含该 stale 文件
    """
    out = tmp_path / "web-skill"
    skill_root = out / ".well-known" / "agent-skills" / "sciverse"
    skill_root.mkdir(parents=True)
    stale = skill_root / "stale-file.txt"
    stale.write_text("leftover from previous run", encoding="utf-8")

    generate(FIXTURE, out)

    assert not stale.exists(), "stale 文件应被 _copy_static 入口清理"
    index = json.loads((out / ".well-known" / "agent-skills" / "index.json").read_text(encoding="utf-8"))
    files = index["skills"][0]["files"]
    assert "stale-file.txt" not in files, f"stale 文件不该进 index.json: {files}"

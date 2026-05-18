"""派生器：OpenAPI + web_skill_assets/ → 站点级 .well-known/agent-skills/sciverse/ bundle。

与 to_clawhub_skill.py / to_claude_skill.py 不同，本 generator 用外部静态资源
（generators/web_skill_assets/）作为 source，因为 references/*.md 是长 narrative
文档，写在 Python 三引号字符串里会很丑且难维护。SKILL.md / openai.yaml / scripts
也走 byte-copy（这些都没有动态变量需要 render），index.json 由本模块 json.dumps
程式化生成（避免 template 引擎与程式化生成并存的歧义）。

输出形态与 platform-console/frontend/public/.well-known/agent-skills/ 完全一致：
- index.json（站点级 skill 发现入口）
- sciverse/SKILL.md（拆章节式，引用 references/*.md）
- sciverse/references/*.md（直接 copy）
- sciverse/agents/openai.yaml（host 适配，直接 copy）
- sciverse/scripts/*.mjs（由 Task A3 加入，本骨架不处理）
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from ._common import load_openapi

ASSETS = Path(__file__).parent / "web_skill_assets"
SKILL_DIR_RELATIVE = Path(".well-known/agent-skills/sciverse")
SKILL_DESCRIPTION = (
    "Retrieve citation-grade academic literature from Sciverse. "
    "Use when an agent needs structured paper metadata search, semantic paper chunk retrieval "
    "for RAG, source text expansion around a paper offset, or figure/table image fetching."
)


def _copy_static(out_root: Path) -> None:
    """copy SKILL.md / references/* / agents/* 到 out_root 的对应位置。"""
    skill_root = out_root / SKILL_DIR_RELATIVE
    skill_root.mkdir(parents=True, exist_ok=True)

    # SKILL.md template（当前无动态变量，直接 copy 去掉 .template 后缀）
    shutil.copy(ASSETS / "SKILL.md.template", skill_root / "SKILL.md")

    # references/ 字节级 copy（narrative 文档，不做 render）
    references_dst = skill_root / "references"
    references_dst.mkdir(exist_ok=True)
    for md in sorted((ASSETS / "references").glob("*.md")):
        shutil.copy(md, references_dst / md.name)

    # agents/*.template 去掉 .template 后缀（当前 openai.yaml 无 {{ base_url }} 等占位符，
    # 但保留 .template 后缀约定为未来插入占位符留通路）
    agents_dst = skill_root / "agents"
    agents_dst.mkdir(exist_ok=True)
    for tmpl in sorted((ASSETS / "agents").glob("*.template")):
        shutil.copy(tmpl, agents_dst / tmpl.name.removesuffix(".template"))


def _write_index(out_root: Path) -> None:
    """根据 skill_root 实际文件列表生成 index.json（在 .well-known/agent-skills/ 一层）。

    程式化生成而非 template render，理由：files 列表必须是动态扫描产物，
    且本字段是 JSON 数组，混在 string template 里需要小心引号 / 转义，
    不如直接 json.dumps 干净。
    """
    skill_root = out_root / SKILL_DIR_RELATIVE
    files = sorted(
        str(p.relative_to(skill_root)).replace("\\", "/")
        for p in skill_root.rglob("*")
        if p.is_file()
    )
    index = {
        "skills": [
            {
                "name": "sciverse",
                "description": SKILL_DESCRIPTION,
                "files": files,
            }
        ]
    }
    (skill_root.parent / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def generate(openapi_path: Path, out_root: Path) -> None:
    """主入口：根据 openapi + web_skill_assets 渲染整个 bundle 到 out_root。

    openapi_path 当前没用到（SKILL.md 无动态字段），但保留参数为后续插入
    OpenAPI version / endpoint 时不破坏 API 留通路。
    """
    _ = load_openapi(openapi_path)  # 验证 openapi.yaml 可读，且为 A2 后续插入预留
    _copy_static(out_root)
    _write_index(out_root)


if __name__ == "__main__":
    root = Path(__file__).parent.parent
    generate(root / "openapi.yaml", root / "dist" / "web-skill")
    print(f"wrote {root / 'dist' / 'web-skill'}")

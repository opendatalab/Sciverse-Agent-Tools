"""派生器：OpenAPI → ClawHub skill bundle (SKILL.md + manifest.json)。"""
from __future__ import annotations

import json
from pathlib import Path

from ._common import get_request_schema, iter_operations, load_openapi


SKILL_NAME = "sciverse-agent-tools"
SKILL_DESCRIPTION = (
    "SciVerse 学术文献检索：按结构化条件查元数据、自然语言语义检索片段、按字节读取原文。"
    "适合需要权威学术文献支撑的 RAG 与 agent 工作流。"
)


def generate_manifest(openapi_path: Path) -> dict:
    spec = load_openapi(openapi_path)
    version = spec["info"].get("x-sciverse-tools-version", spec["info"]["version"])

    tools = []
    for _path, _method, op in iter_operations(spec):
        op_id = op["operationId"]
        tools.append({
            "name": op_id,
            "description": op.get("description", op.get("summary", "")).strip(),
            "script": f"scripts/{op_id}.mjs",
            "input_schema": get_request_schema(op, spec),
        })

    return {
        "name": SKILL_NAME,
        "version": version,
        "description": SKILL_DESCRIPTION,
        "runtime": "node>=18",
        "license": "Apache-2.0",
        "homepage": "https://sciverse.space",
        "env": [
            {
                "name": "SCIVERSE_API_TOKEN",
                "required": True,
                "description": "SciVerse API Token（从 https://sciverse.space 控制台申请）",
            },
            {
                "name": "SCIVERSE_BASE_URL",
                "required": False,
                "default": "https://sciverse.space/api",
                "description": "覆盖默认 API base URL（用于 dev / 自建网关）",
            },
        ],
        "tools": tools,
    }


def generate_skill_md(openapi_path: Path) -> str:
    spec = load_openapi(openapi_path)
    version = spec["info"].get("x-sciverse-tools-version", spec["info"]["version"])

    lines = [
        "---",
        f"name: {SKILL_NAME}",
        f"version: {version}",
        f"description: {SKILL_DESCRIPTION}",
        "license: Apache-2.0",
        "homepage: https://sciverse.space",
        "---",
        "",
        f"# {SKILL_NAME}",
        "",
        SKILL_DESCRIPTION,
        "",
        "## 触发条件",
        "",
        "当用户问题涉及以下任一情形时启用本 skill：",
        "",
        "- 需要查找学术文献（按作者、年份、期刊、学科等结构化条件）",
        "- 需要文献片段支撑回答（RAG / 引用）",
        "- 需要扩展某一文献的原文上下文（已有 doc_id，要更多字节）",
        "",
        "## 鉴权",
        "",
        "本 skill 需要环境变量 `SCIVERSE_API_TOKEN`（从 https://sciverse.space 控制台申请）。",
        "可选 `SCIVERSE_BASE_URL` 覆盖默认 API base URL。",
        "",
        "## 工具列表",
        "",
    ]

    for _path, _method, op in iter_operations(spec):
        op_id = op["operationId"]
        desc = op.get("description", op.get("summary", "")).strip()
        lines.extend([
            f"### {op_id}",
            "",
            desc,
            "",
            f"**调用**：`node scripts/{op_id}.mjs '<JSON 入参>'`",
            "",
        ])

    lines.extend([
        "## 协同链路",
        "",
        "典型 RAG 链路：",
        "",
        "```",
        "semantic_search(query=...)",
        "    └─▶ hits[i].doc_id, hits[i].offset",
        "            └─▶ read_content(doc_id, offset)",
        "```",
        "",
        "结构化筛选 + 元数据查询：",
        "",
        "```",
        "search_papers(authors=[...], year_from=2020)",
        "    └─▶ hits[].doc_id 列表",
        "```",
        "",
        "## 错误处理",
        "",
        "- 退出码 0：成功，stdout 为 JSON 响应",
        "- 退出码 1：HTTP 4xx/5xx，stderr 含 status 与响应体",
        "- 退出码 2：参数错误（缺少 token、JSON 不合法、必填字段缺失）",
        "",
    ])

    return "\n".join(lines)


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    openapi = root / "openapi.yaml"

    manifest = generate_manifest(openapi)
    manifest_path = root / "skill" / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {manifest_path.relative_to(root)}")

    skill_md = generate_skill_md(openapi)
    skill_md_path = root / "skill" / "SKILL.md"
    skill_md_path.write_text(skill_md, encoding="utf-8")
    print(f"wrote {skill_md_path.relative_to(root)}")


if __name__ == "__main__":
    main()

"""派生器：OpenAPI → ClawHub skill bundle (SKILL.md + manifest.json)。

SKILL.md 输出**英文**给 OpenClaw agent（与 ClawHub 社区惯例对齐），
其内容优先取自 OpenAPI 中的 `x-en-summary` / `x-en-description` 扩展字段，
fallback 到 `summary` / `description`（中文，给开发者用的 OpenAPI 文档）。
"""
from __future__ import annotations

import json
from pathlib import Path

from ._common import get_request_schema, iter_operations, load_openapi


# ClawHub 命名约定（2026-05 迁到 @sciverse 组织后）：
#   - `name` = 组织 namespace + slug，作为唯一全局 ID（如 `sciverse-academic-retrieval`）
#   - `slug` = 公开 URL slug，用户安装时填的名字（`openclaw skills install <slug>`）
# 这两个字段都写进 manifest.json + SKILL.md frontmatter。
# 注：与 npm/PyPI 包名 `sciverse` 不同；ClawHub 已 publish 过此 skill name，
# 不能跟着 SDK 包改名（会断裂已有用户的安装链路）。
SKILL_NAME = "sciverse-academic-retrieval"
SKILL_SLUG = "academic-retrieval"
SKILL_DESCRIPTION_EN = (
    "Sciverse academic paper retrieval: structured metadata search, semantic "
    "chunk retrieval for RAG, and byte-range content reading. For agent "
    "workflows that need citation-grade scientific literature."
)


def _en_description(node: dict) -> str:
    """优先英文描述。fallback 顺序：x-en-description → x-en-summary → description → summary。"""
    return (
        node.get("x-en-description")
        or node.get("x-en-summary")
        or node.get("description")
        or node.get("summary")
        or ""
    ).strip()


def _read_existing_version(manifest_path: Path) -> str | None:
    """读 manifest.json 现有 version。允许 skill 独立 bump（与 SDK/MCP 版本号脱钩）。
    首次生成（manifest 不存在）则返回 None，由调用方 fallback 到 openapi 版本。"""
    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8")).get("version")
    except json.JSONDecodeError:
        return None


def generate_manifest(openapi_path: Path, *, existing_version: str | None = None) -> dict:
    spec = load_openapi(openapi_path)
    version = existing_version or spec["info"].get("x-sciverse-tools-version", spec["info"]["version"])

    tools = []
    for _path, _method, op in iter_operations(spec):
        op_id = op["operationId"]
        tools.append({
            "name": op_id,
            "description": _en_description(op),
            "script": f"scripts/{op_id}.mjs",
            "input_schema": get_request_schema(op, spec),
        })

    return {
        "name": SKILL_NAME,
        "version": version,
        "slug": SKILL_SLUG,
        "description": SKILL_DESCRIPTION_EN,
        "runtime": "node>=18",
        "license": "Apache-2.0",
        "homepage": "https://sciverse.space",
        "env": [
            {
                "name": "SCIVERSE_API_TOKEN",
                "required": True,
                "description": "Sciverse API Token (obtain from https://sciverse.space).",
            },
            {
                "name": "SCIVERSE_BASE_URL",
                "required": False,
                "default": "https://api.sciverse.space",
                "description": "Override the default API base URL (for dev / self-hosted gateways).",
            },
        ],
        "tools": tools,
    }


def generate_skill_md(openapi_path: Path, *, existing_version: str | None = None) -> str:
    spec = load_openapi(openapi_path)
    version = existing_version or spec["info"].get("x-sciverse-tools-version", spec["info"]["version"])

    lines = [
        "---",
        f"name: {SKILL_NAME}",
        f"slug: {SKILL_SLUG}",
        f"version: {version}",
        f"description: {SKILL_DESCRIPTION_EN}",
        "license: Apache-2.0",
        "homepage: https://sciverse.space",
        "---",
        "",
        f"# {SKILL_SLUG}",
        "",
        SKILL_DESCRIPTION_EN,
        "",
        "## When to use",
        "",
        "Trigger this skill when the user's request involves any of:",
        "",
        "- Locating academic papers by structured criteria (authors, year, journal, subjects)",
        "- Grounding answers in paper excerpts (RAG / citations)",
        "- Expanding the original text around a known doc_id (more bytes before/after a chunk)",
        "",
        "## Authentication",
        "",
        "This skill requires the `SCIVERSE_API_TOKEN` environment variable",
        "(obtain from https://sciverse.space). Optionally set `SCIVERSE_BASE_URL`",
        "to override the default API base URL.",
        "",
        "## Tools",
        "",
    ]

    for _path, _method, op in iter_operations(spec):
        op_id = op["operationId"]
        desc = _en_description(op)
        lines.extend([
            f"### {op_id}",
            "",
            desc,
            "",
            f"**Invoke**: `node scripts/{op_id}.mjs '<JSON args>'`",
            "",
        ])

    lines.extend([
        "## Bootstrap: learn the schema first",
        "",
        "If you're unsure which fields exist or what values an enum takes",
        "(e.g. `metadata_type`, `language`, `access_oa_status`), call",
        "`list_catalog` once at the start. Sample values are returned for",
        "low-cardinality fields. Use it instead of guessing field names —",
        "guessing wastes turns.",
        "",
        "```",
        "list_catalog(include_sample_values=true)",
        "    └─▶ fields[].name + sample_values  →  precise filter construction",
        "```",
        "",
        "## Recipes",
        "",
        "**RAG flow (natural-language Q&A):**",
        "",
        "```",
        "semantic_search(query=...) → hits[i].doc_id, hits[i].offset",
        "    └─▶ read_content(doc_id, offset)",
        "```",
        "",
        "**Lookup by DOI:**",
        "",
        "```",
        "search_papers(filters_advanced=[{field: \"doi\", value: \"10.1038/...\"}])",
        "```",
        "",
        "**OA + year filter:**",
        "",
        "```",
        "search_papers(",
        "    year_from=2024,",
        "    filters_advanced=[{field: \"access_is_oa\", value: \"true\"}]",
        ")",
        "```",
        "",
        "**Structured + semantic hybrid:**",
        "",
        "```",
        "search_papers(authors=[...], year_from=2020) → doc_ids",
        "semantic_search(query=...) → filter hits client-side by doc_ids",
        "```",
        "",
        "**Bias fuzzy search toward recent work (freshness boost):**",
        "",
        "Set `freshness_boost` to weight results by publication date with",
        "gauss decay. Only effective when `query` is non-empty; mutually",
        "exclusive with `sort_by_year`.",
        "",
        "```",
        "search_papers(query=\"large language model\", freshness_boost=\"STRONG\")",
        "    # STRONG: 3-year decay, for tracking research directions",
        "search_papers(query=\"protein folding\", freshness_boost=\"MILD\")",
        "    # MILD:   10-year decay, for everyday literature search",
        "```",
        "",
        "**Fetch a paper figure / image:**",
        "",
        "When read_content Markdown contains `![alt](file_name)`, call",
        "`get_resource` with the file_name to fetch image binary.",
        "",
        "```",
        "read_content(doc_id, offset) → markdown ![Figure 3](dt=xxx/p/f3.png)",
        "    └─▶ get_resource(file_name=\"dt=xxx/p/f3.png\")",
        "```",
        "",
        "## Exit codes",
        "",
        "- `0` — success; stdout is the JSON response",
        "- `1` — HTTP 4xx/5xx; stderr contains status code and response body",
        "- `2` — argument error (missing token, malformed JSON, required field absent)",
        "",
    ])

    return "\n".join(lines)


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    openapi = root / "openapi.yaml"
    manifest_path = root / "clawhub" / "manifest.json"
    skill_md_path = root / "clawhub" / "SKILL.md"

    # 优先保留 manifest.json 已有 version（人工/ClawHub 上传时 bump 过），
    # 避免每次跑 build 把 version 拽回 openapi.yaml。
    existing_version = _read_existing_version(manifest_path)

    manifest = generate_manifest(openapi, existing_version=existing_version)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {manifest_path.relative_to(root)} (version {manifest['version']})")

    skill_md = generate_skill_md(openapi, existing_version=existing_version)
    skill_md_path.write_text(skill_md, encoding="utf-8")
    print(f"wrote {skill_md_path.relative_to(root)}")


if __name__ == "__main__":
    main()

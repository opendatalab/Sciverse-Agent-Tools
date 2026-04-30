"""派生器：OpenAPI → ClawHub skill bundle (SKILL.md + manifest.json)。

SKILL.md 输出**英文**给 OpenClaw agent（与 ClawHub 社区惯例对齐），
其内容优先取自 OpenAPI 中的 `x-en-summary` / `x-en-description` 扩展字段，
fallback 到 `summary` / `description`（中文，给开发者用的 OpenAPI 文档）。
"""
from __future__ import annotations

import json
from pathlib import Path

from ._common import get_request_schema, iter_operations, load_openapi


SKILL_NAME = "sciverse-agent-tools"
SKILL_DESCRIPTION_EN = (
    "SciVerse academic paper retrieval: structured metadata search, semantic "
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


def generate_manifest(openapi_path: Path) -> dict:
    spec = load_openapi(openapi_path)
    version = spec["info"].get("x-sciverse-tools-version", spec["info"]["version"])

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
        "description": SKILL_DESCRIPTION_EN,
        "runtime": "node>=18",
        "license": "Apache-2.0",
        "homepage": "https://sciverse.space",
        "env": [
            {
                "name": "SCIVERSE_API_TOKEN",
                "required": True,
                "description": "SciVerse API Token (obtain from https://sciverse.space).",
            },
            {
                "name": "SCIVERSE_BASE_URL",
                "required": False,
                "default": "https://sciverse.space/api",
                "description": "Override the default API base URL (for dev / self-hosted gateways).",
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
        f"description: {SKILL_DESCRIPTION_EN}",
        "license: Apache-2.0",
        "homepage: https://sciverse.space",
        "---",
        "",
        f"# {SKILL_NAME}",
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
        "## Composition patterns",
        "",
        "Typical RAG flow:",
        "",
        "```",
        "semantic_search(query=...)",
        "    └─▶ hits[i].doc_id, hits[i].offset",
        "            └─▶ read_content(doc_id, offset)",
        "```",
        "",
        "Structured filter + metadata lookup:",
        "",
        "```",
        "search_papers(authors=[...], year_from=2020)",
        "    └─▶ list of hits[].doc_id",
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

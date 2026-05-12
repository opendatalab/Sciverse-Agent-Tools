"""派生器：OpenAPI → Claude Code 官方 Agent Skill 格式。

与 `to_clawhub_skill.py` 平行的另一种 skill 形态：

- 输出目录：`agent-tools/skill-claude-code/`（与 ClawHub 的 `agent-tools/skill/` 区分开）
- frontmatter 严格只含 `name` 和 `description` 两个字段（Claude Code 官方 spec）
- description 是 model-facing trigger，须明确何时该调用此 skill
- 正文为 markdown，描述前置条件、能力、典型 composition pattern
- 同时输出 Plugin Marketplace 入口：`agent-tools/.claude-plugin/marketplace.json`
- 依赖另一个并行 agent 维护的 `@sciverse/mcp-server` npm 包

Claude Code 官方 spec 参考：
- 路径：`~/.claude/skills/<skill-name>/SKILL.md`（用户级）/ `.claude/skills/...`（项目级）
- 通过 Plugin Marketplace 也可分发（`claude /plugin install`）
"""
from __future__ import annotations

import json
from pathlib import Path

from ._common import iter_operations, load_openapi


SKILL_NAME = "sciverse"
# Model-facing trigger description——Claude Code 用这个文本判断何时触发 skill。
# 关键词 "academic paper" / "paper retrieval" / "scientific literature" 用来匹配用户请求。
SKILL_DESCRIPTION = (
    "Use when the user needs academic paper retrieval — searching scientific "
    "literature by author/year/journal, finding paper chunks for RAG-style "
    "citations, or expanding original text around a known paper offset. "
    "Provides three SciVerse tools (search_papers, semantic_search, read_content) "
    "via the @sciverse/mcp-server MCP server."
)

PLUGIN_CATEGORY = "research"
PLUGIN_HOMEPAGE = "https://sciverse.space"
PLUGIN_OWNER_NAME = "SciVerse Platform Team"


def _en_description(node: dict) -> str:
    """优先英文描述，与 to_clawhub_skill 保持一致的 fallback 策略。"""
    return (
        node.get("x-en-description")
        or node.get("x-en-summary")
        or node.get("description")
        or node.get("summary")
        or ""
    ).strip()


def generate_skill_md(openapi_path: Path) -> str:
    spec = load_openapi(openapi_path)

    lines = [
        "---",
        f"name: {SKILL_NAME}",
        f"description: {SKILL_DESCRIPTION}",
        "---",
        "",
        "# SciVerse — Academic Paper Retrieval",
        "",
        "Retrieval skill for the SciVerse open platform. Exposes three tools",
        "for working with scientific literature: structured metadata search,",
        "semantic chunk retrieval for RAG, and byte-range content reading.",
        "",
        "## When to use",
        "",
        "Trigger this skill when the user's request involves any of:",
        "",
        "- Locating academic papers by structured criteria (authors, year, journal, subjects)",
        "- Grounding an answer in paper excerpts (RAG / citations)",
        "- Expanding the original text around a known doc_id (more bytes before/after a chunk)",
        "",
        "Do NOT use this skill for general web search, news, or non-scientific content —",
        "the underlying index only covers peer-reviewed and preprint scientific literature.",
        "",
        "## Prerequisites",
        "",
        "This skill is a thin wrapper around the `@sciverse/mcp-server` MCP server.",
        "Before invoking any tool, ensure the server is reachable:",
        "",
        "1. Install the MCP server:",
        "",
        "   ```bash",
        "   npm install -g @sciverse/mcp-server",
        "   ```",
        "",
        "   Or add it to your project `.mcp.json`:",
        "",
        "   ```json",
        "   {",
        '     "mcpServers": {',
        '       "sciverse": {',
        '         "command": "npx",',
        '         "args": ["-y", "@sciverse/mcp-server"],',
        '         "env": { "SCIVERSE_API_TOKEN": "${SCIVERSE_API_TOKEN}" }',
        "       }",
        "     }",
        "   }",
        "   ```",
        "",
        "2. Obtain an API token from https://sciverse.space and export it:",
        "",
        "   ```bash",
        "   export SCIVERSE_API_TOKEN=sv-...",
        "   ```",
        "",
        "Optional: set `SCIVERSE_BASE_URL` to override the default API base URL",
        "(for dev / self-hosted gateways; must remain on `*.sciverse.space`).",
        "",
        "## Tools",
        "",
        "All three tools are exposed by the MCP server. Claude Code will surface",
        "them automatically when this skill is active.",
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
        ])

    lines.extend([
        "## Composition patterns",
        "",
        "Typical RAG flow (semantic chunk → expand original text):",
        "",
        "```",
        "semantic_search(query=...)",
        "    └─▶ hits[i].doc_id, hits[i].offset",
        "            └─▶ read_content(doc_id, offset)",
        "```",
        "",
        "Structured filter (narrow down by author/year/journal):",
        "",
        "```",
        "search_papers(authors=[...], year_from=2020, journals=[...])",
        "    └─▶ list of hits[].doc_id, hits[].abstract",
        "```",
        "",
        "Combined (structured pre-filter then semantic refine):",
        "",
        "```",
        "search_papers(authors=[...], year_from=2020)   # narrow universe",
        "    └─▶ doc_ids → user-side filter on semantic_search hits",
        "```",
        "",
        "## Notes for Claude",
        "",
        "- Always cite `doc_id` and `title` when surfacing paper-based facts to the user.",
        "- Prefer `semantic_search` for natural-language questions; only fall back to",
        "  `search_papers` when the user provides structured criteria (specific author,",
        "  year range, journal).",
        "- When a `semantic_search` hit looks promising but the chunk is truncated,",
        "  use `read_content(doc_id, offset)` to expand context before answering.",
        "- The platform returns at most 30 hits per `semantic_search` and 50 per",
        "  `search_papers` page; paginate via `page` if the user wants more.",
        "",
    ])

    return "\n".join(lines)


def generate_marketplace_json(openapi_path: Path) -> dict:
    """生成 Plugin Marketplace 入口 (`.claude-plugin/marketplace.json`)。

    Marketplace schema 目前为社区惯例，最小可用字段：
    - name / owner / plugins[]
    - 每个 plugin: name / description / version / source / category
    """
    spec = load_openapi(openapi_path)
    version = spec["info"].get("x-sciverse-tools-version", spec["info"]["version"])

    return {
        "name": SKILL_NAME,
        "owner": {
            "name": PLUGIN_OWNER_NAME,
            "homepage": PLUGIN_HOMEPAGE,
        },
        "plugins": [
            {
                "name": SKILL_NAME,
                "description": SKILL_DESCRIPTION,
                "version": version,
                "source": "./skill-claude-code",
                "category": PLUGIN_CATEGORY,
                "homepage": PLUGIN_HOMEPAGE,
            }
        ],
    }


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    openapi = root / "openapi.yaml"

    # 1. 生成 SKILL.md
    skill_dir = root / "skill-claude-code"
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = generate_skill_md(openapi)
    skill_md_path = skill_dir / "SKILL.md"
    skill_md_path.write_text(skill_md, encoding="utf-8")
    print(f"wrote {skill_md_path.relative_to(root)}")

    # 2. 生成 plugin marketplace 入口
    marketplace_dir = root / ".claude-plugin"
    marketplace_dir.mkdir(parents=True, exist_ok=True)
    marketplace = generate_marketplace_json(openapi)
    marketplace_path = marketplace_dir / "marketplace.json"
    marketplace_path.write_text(
        json.dumps(marketplace, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {marketplace_path.relative_to(root)}")


if __name__ == "__main__":
    main()

"""派生器：OpenAPI → Claude Code 官方 Agent Skill 格式。

与 `to_clawhub_skill.py` 平行的另一种 skill 形态：

- 输出目录：`skill-claude-code/`（与 ClawHub 的 `clawhub/` 区分开）
- frontmatter 严格只含 `name` 和 `description` 两个字段（Claude Code 官方 spec）
- description 是 model-facing trigger，须明确何时该调用此 skill
- 正文为 markdown，描述前置条件、能力、典型 composition pattern
- 同时输出 Plugin Marketplace 入口：`.claude-plugin/marketplace.json`
- 依赖另一个并行 agent 维护的 `sciverse-mcp-server` npm 包

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
    "Provides six Sciverse tools (search_papers, semantic_search, list_catalog, "
    "list_paper_relations, read_content, get_resource) via the sciverse-mcp-server MCP server."
)

PLUGIN_CATEGORY = "research"
PLUGIN_HOMEPAGE = "https://sciverse.space"
PLUGIN_OWNER_NAME = "Sciverse Platform Team"


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
        "# Sciverse — Academic Paper Retrieval",
        "",
        "Retrieval skill for the Sciverse open platform. Exposes six tools",
        "for working with scientific literature: field introspection,",
        "structured metadata search, semantic chunk retrieval for RAG,",
        "citation / reference pagination, byte-range content reading, and",
        "figure / table image fetching.",
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
        "This skill is a thin wrapper around the `sciverse-mcp-server` MCP server.",
        "Before invoking any tool, ensure the server is reachable:",
        "",
        "1. Install the MCP server:",
        "",
        "   ```bash",
        "   npm install -g sciverse-mcp-server",
        "   ```",
        "",
        "   Or add it to your project `.mcp.json`:",
        "",
        "   ```json",
        "   {",
        '     "mcpServers": {',
        '       "sciverse": {',
        '         "command": "npx",',
        '         "args": ["-y", "sciverse-mcp-server"],',
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
        "All six tools are exposed by the MCP server. Claude Code will surface",
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
        "## Bootstrap: learn the schema first",
        "",
        "If you don't yet know which fields exist or what values they take",
        "(e.g. \"is `oa_status` a field?\", \"what does `metadata_type` accept?\"),",
        "call `list_catalog` once at the start of the conversation. The result",
        "includes every field name, type, filterability, default-return status,",
        "and — for enum-like fields — sample values. Cache the catalog in your",
        "working memory; subsequent `search_papers` filters become precise",
        "instead of guessed.",
        "",
        "```",
        "list_catalog(include_sample_values=true)",
        "    └─▶ fields[].name + sample_values  →  pick the right filter field",
        "```",
        "",
        "## Recipes",
        "",
        "**1. Natural-language RAG (most common):**",
        "",
        "```",
        "semantic_search(query=\"How does Transformer attention work?\", top_k=5)",
        "    └─▶ for each hit: read_content(doc_id, offset, limit=8192)",
        "    └─▶ cite doc_id + title in the answer",
        "```",
        "",
        "**2. Look up a paper by DOI / doc_id:**",
        "",
        "```",
        "search_papers(filters_advanced=[",
        "    {field: \"doi\", operator: \"FILTER_OP_EQ\", value: \"10.1038/...\"}",
        "])",
        "```",
        "",
        "**3. Find OA papers in a year range:**",
        "",
        "```",
        "search_papers(",
        "    filters_advanced=[",
        "        {field: \"access_is_oa\", value: \"true\"},",
        "        {field: \"access_oa_status\", operator: \"FILTER_OP_IN\",",
        "         value: [\"gold\", \"green\", \"hybrid\"]}",
        "    ],",
        "    year_from=2024",
        ")",
        "```",
        "",
        "**4. Filter by language / metadata_type (enum fields):**",
        "",
        "```",
        "# First check the enum: list_catalog(include_sample_values=true)",
        "# Then filter precisely:",
        "search_papers(",
        "    query=\"transformer\",",
        "    filters_advanced=[",
        "        {field: \"language\", value: \"en\"},",
        "        {field: \"metadata_type\", value: \"paper\"}",
        "    ]",
        ")",
        "```",
        "",
        "**5. Structured pre-filter + semantic refine (hybrid):**",
        "",
        "```",
        "search_papers(authors=[\"Hinton\"], year_from=2020, page_size=50)",
        "    └─▶ collect hits[].doc_id list",
        "semantic_search(query=\"attention\", top_k=20)",
        "    └─▶ filter hits to those whose doc_id appears in step-1 list",
        "```",
        "",
        "**6. Bias fuzzy search toward recent work (freshness boost):**",
        "",
        "Set `freshness_boost` to weight results by publication date with gauss",
        "decay over `publication_published_date`. Only effective when `query`",
        "is non-empty; mutually exclusive with `sort_by_year`.",
        "",
        "```",
        "search_papers(query=\"large language model\", freshness_boost=\"STRONG\")",
        "    # STRONG: 3-year decay, for tracking research directions",
        "search_papers(query=\"protein folding\", freshness_boost=\"MILD\")",
        "    # MILD:   10-year decay, for everyday literature search",
        "```",
        "",
        "**7. Show a figure / image from the paper:**",
        "",
        "When `read_content` Markdown contains `![alt](file_name)` placeholders",
        "and the user wants to see the figure (e.g. \"show me Figure 3\"),",
        "fetch the binary with `get_resource`. The MCP server wraps the bytes",
        "as a base64 image content block so Claude can read it directly.",
        "",
        "```",
        "read_content(doc_id, offset) → markdown with ![Figure 3](dt=xxx/p_yyy/f3.png)",
        "    └─▶ get_resource(file_name=\"dt=xxx/p_yyy/f3.png\")",
        "    └─▶ Claude sees the image inline",
        "```",
        "",
        "**8. Search authors or journals (collection):**",
        "",
        "Set `collection` to `authors` or `sources` (default `papers`) to search",
        "those entities instead of papers. Each collection has its own fields —",
        "call `list_catalog(collection=\"authors\")` first. Use `filters_advanced` +",
        "`sort_advanced`; the papers convenience fields (`authors`/`year_from`/...) ",
        "apply to papers only.",
        "",
        "```",
        "# Top authors by h-index, sorted by citations",
        "search_papers(",
        "    collection=\"authors\",",
        "    filters_advanced=[{field: \"summary_stats.h_index\", operator: \"FILTER_OP_GTE\", value: 50}],",
        "    sort_advanced=[{field: \"cited_by_count\", order: \"SORT_ORDER_DESC\"}]",
        ")",
        "# Enrich a paper result: take an author orcid / venue issn, then look up the entity",
        "search_papers(collection=\"authors\", filters_advanced=[{field: \"orcid\", value: \"https://orcid.org/...\"}])",
        "```",
        "",
        "## Notes for Claude",
        "",
        "- **Always cite** `doc_id` and `title` when surfacing paper-based facts.",
        "- **Prefer `semantic_search`** for natural-language questions; only fall back",
        "  to `search_papers` when the user provides structured criteria.",
        "- **When stuck on a field name**: call `list_catalog` instead of guessing.",
        "  Field name typos return 400 with a clear message, but waste a turn.",
        "- **Before reading a paper's fulltext**: check `is_content_accessible` on the",
        "  `search_papers` hit — `true` means the paper has fulltext AND you're authorized,",
        "  so `read_content(doc_id, ...)` will work; `false` means no fulltext or no permission.",
        "- **When a chunk looks promising but truncated**: `read_content(doc_id, offset)`",
        "  to expand. `read_content` returns `more: true` when more bytes are available.",
        "- **Pagination**: max 30 hits per `semantic_search`, max 50 per `search_papers`",
        "  page; use `page` to paginate.",
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

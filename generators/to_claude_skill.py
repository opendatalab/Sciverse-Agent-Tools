"""派生器：OpenAPI → Claude Code 官方 Agent Skill 格式。

与 `to_clawhub_skill.py` 平行的另一种 skill 形态：

- 输出目录：`skill-claude-code/`（与 ClawHub 的 `clawhub/` 区分开）
- 该目录是一个完整 Claude Code 插件：
  - `skills/sciverse/SKILL.md` —— 标准布局的 skill
  - `.claude-plugin/plugin.json` —— 插件清单
  - `.mcp.json` —— 插件自带的 MCP server
- frontmatter 严格只含 `name` 和 `description` 两个字段（Claude Code 官方 spec）
- description 是 model-facing trigger，须明确何时该调用此 skill
- 正文为 markdown，描述前置条件、能力、典型 composition pattern
- 同时输出 Marketplace 入口 `.claude-plugin/marketplace.json`
- 依赖另一个并行 agent 维护的 `sciverse-mcp-server` npm 包

Claude Code 官方 spec 参考（插件形态）：
- skill 放 `skills/<name>/SKILL.md`；`SKILL.md` 在插件根目录也能加载，但那是
  较新版本才支持的行为，标准位置兼容性最好
- 插件根目录的 `.mcp.json` 会被自动发现并在 plugin 启用时启动 server
- `.claude-plugin/marketplace.json` 只描述 marketplace 与插件条目；
  plugin 自身的组件（skills / mcpServers）必须在插件目录里，不能只写进条目
"""
from __future__ import annotations

import json
from pathlib import Path

from ._common import iter_operations, load_openapi
from .to_web_skill import copy_scripts


SKILL_NAME = "sciverse"
# Model-facing trigger description——Claude Code 用这个文本判断何时触发 skill。
# 关键词 "academic paper" / "paper retrieval" / "scientific literature" 用来匹配用户请求。
SKILL_DESCRIPTION = (
    "Use when the user needs academic paper retrieval — searching scientific "
    "literature and patent/author/source metadata, finding paper chunks for RAG-style "
    "citations, or expanding original text around a known paper offset. "
    "Provides six Sciverse tools (search_metadata, semantic_search, list_catalog, "
    "list_paper_relations, read_content, get_resource) via the sciverse-mcp-server MCP server."
)

PLUGIN_CATEGORY = "research"
PLUGIN_HOMEPAGE = "https://sciverse.space"
PLUGIN_OWNER_NAME = "Sciverse Platform Team"
PLUGIN_REPOSITORY = "https://github.com/opendatalab/Sciverse-Agent-Tools"
PLUGIN_LICENSE = "Apache-2.0"
PLUGIN_KEYWORDS = ["research", "academic", "papers", "literature", "retrieval", "mcp"]
MARKETPLACE_DESCRIPTION = (
    "Sciverse academic retrieval tools for Claude Code: a retrieval skill plus "
    "the sciverse-mcp-server MCP server, installed together."
)


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
        "metadata search across papers, authors, sources and patents, semantic chunk retrieval for RAG,",
        "citation / reference pagination, character-range content reading, and",
        "figure / table image fetching.",
        "",
        "## When to use",
        "",
        "Trigger this skill when the user's request involves any of:",
        "",
        "- Locating academic papers by structured criteria (authors, year, journal, subjects)",
        "- Grounding an answer in paper excerpts (RAG / citations)",
        "- Expanding the original text around a known doc_id (more text before/after a chunk)",
        "",
        "Do NOT use this skill for general web search, news, or non-scientific content —",
        "the supported collections are papers, authors, sources, and patents.",
        "",
        "## Prerequisites",
        "",
        "This skill is a thin wrapper around the `sciverse-mcp-server` MCP server.",
        "Before invoking any tool, ensure the server is reachable:",
        "",
        "1. Obtain an API token from https://sciverse.space and export it",
        "   (or run `sciverse auth login`, which saves it to",
        "   `~/.sciverse/credentials.json`):",
        "",
        "   ```bash",
        "   export SCIVERSE_API_TOKEN=sv-...",
        "   ```",
        "",
        "2. Install the MCP server:",
        "",
        "   ```bash",
        "   npm install -g sciverse-mcp-server",
        "   ```",
        "",
        "   When installed as a Claude Code plugin, the bundle already ships",
        "   `.mcp.json`, so the server starts with the plugin and step 2 is",
        "   optional — only the token has to be provided.",
        "",
        "   Or add it to your project `.mcp.json`:",
        "",
        "   ```json",
        "   {",
        '     "mcpServers": {',
        '       "sciverse": {',
        '         "command": "npx",',
        '         "args": ["-y", "sciverse-mcp-server"]',
        "       }",
        "     }",
        "   }",
        "   ```",
        "",
        "Optional: set `SCIVERSE_BASE_URL` to override the default API base URL",
        "(for dev / self-hosted gateways; must remain on `*.sciverse.space`).",
        "",
        "Portable fallback: run `node scripts/search_metadata.mjs '<JSON args>'` from this skill directory.",
        "The bundled scripts require SCIVERSE_API_TOKEN and Node.js 18 or newer.",
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
        "working memory; subsequent `search_metadata` filters become precise",
        "instead of guessed.",
        "",
        "```",
        "list_catalog(include_sample_values=true)",
        "    └─▶ fields[].name + sample_values  →  pick the right filter field",
        "```",
        "",
        "`search_metadata` uses canonical `filters` / `sort`; no convenience parameters.",
        "`semantic_search` remains paper-only. `read_content` supports papers/patents",
        "(default papers), offset=0 and limit=4096. Pass patents explicitly for patent text.",
        "`get_resource` primarily fetches paper images; ZIP downloads are not supported.",
        "MCP: set SCIVERSE_ENABLE_LEGACY_TOOLS=true and restart to restore the legacy tool list.",
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
        "search_metadata(filters=[",
        "    {field: \"doi\", operator: \"FILTER_OP_EQ\", value: \"10.1038/...\"}",
        "])",
        "```",
        "",
        "**3. Find OA papers in a year range:**",
        "",
        "```",
        "search_metadata(",
        "    filters=[",
        "        {field: \"publication_published_year\", operator: \"FILTER_OP_GTE\", value: 2024},",
        "        {field: \"access_is_oa\", operator: \"FILTER_OP_EQ\", value: true},",
        "        {field: \"access_oa_status\", operator: \"FILTER_OP_IN\",",
        "         value: [\"gold\", \"green\", \"hybrid\"]}",
        "    ]",
        ")",
        "```",
        "",
        "**4. Filter by language / metadata_type (enum fields):**",
        "",
        "```",
        "# First check the enum: list_catalog(include_sample_values=true)",
        "# Then filter precisely:",
        "search_metadata(",
        "    query=\"transformer\",",
        "    filters=[",
        "        {field: \"language\", operator: \"FILTER_OP_EQ\", value: \"en\"},",
        "        {field: \"metadata_type\", operator: \"FILTER_OP_EQ\", value: \"paper\"}",
        "    ]",
        ")",
        "```",
        "",
        "**5. Scoped semantic search (constrained corpus):**",
        "",
        "```",
        "semantic_search(",
        "    query=\"attention\",",
        "    filters={\"author\": [\"Hinton\"],",
        "             \"publication_published_year\": {\"gte\": 2020}}",
        ")",
        "    # filters apply at recall time (server-side), AND across fields;",
        "    # soft semantics: chunks missing that metadata are NOT excluded",
        "```",
        "",
        "For a hard guarantee, or meta-only constraints (fwci, citation graph,",
        "complex hit-sets), scope by doc_id — a HARD recall-time filter:",
        "",
        "```",
        "search_metadata(..., fields=[\"doc_id\",\"title\"])",
        "    └─▶ collect hits[].doc_id (only fulltext papers carry one)",
        "semantic_search(query=\"attention\", filters={\"doc_id\": [...]})",
        "    # hits never leave the set; empty list → empty hits (never global);",
        "    # up to 1000 deduped ids (400 SCOPE_TOO_LARGE beyond)",
        "```",
        "",
        "**6. Bias fuzzy search ranking (soft boosts — stackable):**",
        "",
        "Three multiplicative boosts reorder fuzzy-search results while keeping",
        "relevance. Only effective when `query` is non-empty; ignored when any",
        "sort is set; shallow paging while active (no `next_cursor`).",
        "No implicit year sort is added. Explicit sort disables soft boosts.",
        "",
        "```",
        "search_metadata(query=\"large language model\", freshness_boost=\"STRONG\")",
        "    # recent first: STRONG=3-year decay, MILD=10-year",
        "search_metadata(query=\"protein folding\", impact_boost=\"MILD\")",
        "    # highly-cited float up (bounded; zero-citation stays neutral)",
        "search_metadata(query=\"深度学习\", language_affinity=\"MILD\")",
        "    # demote (never exclude) results not in the query's language;",
        "    # target detected from query text (kana→ja/hangul→ko/Han→zh/Latin→en);",
        "    # unknown-language papers stay neutral. Hard-exclude instead:",
        "    # filters=[{\"field\":\"language\",\"operator\":\"FILTER_OP_EQ\",\"value\":\"zh\"}]",
        "search_metadata(query=\"...\", freshness_boost=\"MILD\", impact_boost=\"MILD\",",
        "              language_affinity=\"MILD\")   # stack: relevant+recent+cited+same-lang",
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
        "Set `collection` to `authors`, `sources`, or `patents` (default `papers`) to search",
        "those entities instead of papers. Each collection has its own fields —",
        "call `list_catalog(collection=\"authors\")` first. Use `filters` +",
        "`sort` with the selected collection fields.",
        "",
        "```",
        "# Top authors by h-index, sorted by citations",
        "search_metadata(",
        "    collection=\"authors\",",
        "    filters=[{field: \"summary_stats.h_index\", operator: \"FILTER_OP_GTE\", value: 50}],",
        "    sort=[{field: \"cited_by_count\", order: \"SORT_ORDER_DESC\"}]",
        ")",
        "# Enrich a paper result: take an author orcid / venue issn, then look up the entity",
        "search_metadata(collection=\"authors\", filters=[{field: \"orcid\", operator: \"FILTER_OP_EQ\", value: \"https://orcid.org/...\"}])",
        "```",
        "",
        "## Notes for Claude",
        "",
        "- **Always cite** `doc_id` and `title` when surfacing paper-based facts.",
        "- **Prefer `semantic_search`** for natural-language questions; only fall back",
        "  to `search_metadata` when the user provides structured criteria.",
        "- **When stuck on a field name**: call `list_catalog` instead of guessing.",
        "  Field name typos return 400 with a clear message, but waste a turn.",
        "- **Before reading a paper's fulltext**: check `is_content_accessible` on the",
        "  `search_metadata` hit — `true` means the paper has fulltext AND you're authorized,",
        "  so `read_content(doc_id, ...)` will work; `false` means no fulltext or no permission.",
        "- **When a chunk looks promising but truncated**: `read_content(doc_id, offset)`",
        "  to expand. `read_content` returns `more: true` when more text is available;",
        "  offset/limit are Unicode code points (not bytes) — page with `next_offset`.",
        "- **Pagination**: `semantic_search` top_k allows up to 100, but `balanced`",
        "  truncates to ~50 server-side — use `quality` (or `fast`) when you need more.",
        "  At most ~3 chunks come back per paper, so a high top_k needs many distinct",
        "  papers to be matched. `search_metadata` returns max 50 per page; use `page`.",
        "",
    ])

    return "\n".join(lines)


def generate_plugin_json(openapi_path: Path) -> dict:
    """生成插件清单 (`skill-claude-code/.claude-plugin/plugin.json`)。

    Claude Code 以插件目录里的这份清单为准来发现组件；marketplace 条目
    只负责"从哪里取"，不承载 skills / mcpServers。
    """
    spec = load_openapi(openapi_path)
    version = spec["info"].get("x-sciverse-tools-version", spec["info"]["version"])

    return {
        "name": SKILL_NAME,
        "displayName": "Sciverse",
        "version": version,
        "description": SKILL_DESCRIPTION,
        "author": {
            "name": PLUGIN_OWNER_NAME,
            "url": PLUGIN_HOMEPAGE,
        },
        "homepage": PLUGIN_HOMEPAGE,
        "repository": PLUGIN_REPOSITORY,
        "license": PLUGIN_LICENSE,
        "keywords": PLUGIN_KEYWORDS,
    }


def generate_mcp_json() -> dict:
    """生成插件自带的 MCP server 定义 (`skill-claude-code/.mcp.json`)。

    不写 `env`：Claude Code 启动 plugin MCP server 时会继承父进程环境，
    `SCIVERSE_API_TOKEN` / `SCIVERSE_BASE_URL` 直接透传；未设置时 server
    回落到 `~/.sciverse/credentials.json`。写空 env 反而会覆盖掉继承值。
    """
    return {
        "mcpServers": {
            SKILL_NAME: {
                "command": "npx",
                "args": ["-y", "sciverse-mcp-server"],
            }
        }
    }


def generate_marketplace_json(openapi_path: Path) -> dict:
    """生成 Plugin Marketplace 入口 (`.claude-plugin/marketplace.json`)。

    字段以 Claude Code marketplace schema 为准：
    - name / owner{name,url} / description / plugins[]
    - 每个 plugin: name / description / version / source / category / homepage
    """
    spec = load_openapi(openapi_path)
    version = spec["info"].get("x-sciverse-tools-version", spec["info"]["version"])

    return {
        "name": SKILL_NAME,
        "owner": {
            "name": PLUGIN_OWNER_NAME,
            "url": PLUGIN_HOMEPAGE,
        },
        "description": MARKETPLACE_DESCRIPTION,
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

    # 1. 生成 SKILL.md（标准布局 skills/<name>/SKILL.md）
    plugin_root = root / "skill-claude-code"
    skill_dir = plugin_root / "skills" / SKILL_NAME
    skill_dir.mkdir(parents=True, exist_ok=True)
    copy_scripts(skill_dir / "scripts")
    skill_md = generate_skill_md(openapi)
    skill_md_path = skill_dir / "SKILL.md"
    skill_md_path.write_text(skill_md, encoding="utf-8", newline="\n")
    print(f"wrote {skill_md_path.relative_to(root)}")

    # 2. 生成插件清单 + 自带 MCP server 定义
    plugin_dir = plugin_root / ".claude-plugin"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    plugin_path = plugin_dir / "plugin.json"
    plugin_path.write_text(
        json.dumps(generate_plugin_json(openapi), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {plugin_path.relative_to(root)}")

    mcp_path = plugin_root / ".mcp.json"
    mcp_path.write_text(
        json.dumps(generate_mcp_json(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {mcp_path.relative_to(root)}")

    # 3. 生成 plugin marketplace 入口
    marketplace_dir = root / ".claude-plugin"
    marketplace_dir.mkdir(parents=True, exist_ok=True)
    marketplace = generate_marketplace_json(openapi)
    marketplace_path = marketplace_dir / "marketplace.json"
    marketplace_path.write_text(
        json.dumps(marketplace, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {marketplace_path.relative_to(root)}")


if __name__ == "__main__":
    main()

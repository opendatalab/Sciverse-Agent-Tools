# Coding agent 接入指南

> SciVerse 通过 MCP server [`sciverse-mcp-server`](../../packages/mcp/) 或 Agent Skill [`skills/sciverse`](../../skills/sciverse/) 给主流 coding agent 提供学术文献检索能力。本目录是各 agent 的 5 分钟接入指南。

## 选择你的 agent

| Agent | 指南 | 配置文件 |
|---|---|---|
| Claude Code (`claude` CLI / VS Code) | [claude-code.md](./claude-code.md) | `.mcp.json` |
| Cursor | [cursor.md](./cursor.md) | `.cursor/mcp.json` |
| Codex CLI (OpenAI) | [codex-cli.md](./codex-cli.md) | `~/.codex/config.toml` |
| Windsurf (Codeium) | [windsurf.md](./windsurf.md) | `~/.codeium/windsurf/mcp_config.json` |

## Agent Skill 安装方式

如果你的 agent 支持 [skills.sh](https://skills.sh/) / `npx skills`，可以不配置 MCP，直接安装 Sciverse Agent Skill：

```bash
npx skills add https://sciverse.space
```

也可以从 GitHub 安装：

```bash
npx skills add https://github.com/opendatalab/Sciverse-Agent-Tools --skill sciverse
```

如需指定安装范围，可按 `skills` CLI 支持追加 `-a <agent>`、`-g` 或 `--all`；安装后仍需设置 `SCIVERSE_API_TOKEN`。

## MCP 路径

如果选择 [MCP (Model Context Protocol)](https://modelcontextprotocol.io) 接入，`sciverse-mcp-server` 是 stdio 形态的 MCP server，包装 SciVerse 五个 API：

- `list_catalog` — 字段 introspection（agent 第一次碰到不确定的字段先调此接口）
- `search_papers` — 结构化元数据检索
- `semantic_search` — 自然语言语义检索（RAG）
- `read_content` — 按字节区间读取文献原文
- `get_resource` — 取 `read_content` Markdown 中引用的图片字节流（多模态 RAG）

## 通用前置条件

1. SciVerse API Token：从 https://sciverse.space 控制台申请，形如 `sv-xxx`
2. Node.js 18+（`sciverse-mcp-server` 用 `npx` 运行）

## 不在列表里的 agent？

只要支持 MCP stdio，都能用同样模式接入。把以下 JSON 翻译到对应 agent 的配置语法即可：

```json
{
  "command": "npx",
  "args": ["-y", "sciverse-mcp-server"],
  "env": { "SCIVERSE_API_TOKEN": "sv-xxx" }
}
```

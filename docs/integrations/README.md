# Coding agent 接入指南

> SciVerse 通过 MCP server [`@sciverse/mcp-server`](../../packages/mcp/) 给主流 coding agent 提供学术文献检索能力。本目录是各 agent 的 5 分钟接入指南。

## 选择你的 agent

| Agent | 指南 | 配置文件 |
|---|---|---|
| Claude Code (`claude` CLI / VS Code) | [claude-code.md](./claude-code.md) | `.mcp.json` |
| Cursor | [cursor.md](./cursor.md) | `.cursor/mcp.json` |
| Codex CLI (OpenAI) | [codex-cli.md](./codex-cli.md) | `~/.codex/config.toml` |
| Windsurf (Codeium) | [windsurf.md](./windsurf.md) | `~/.codeium/windsurf/mcp_config.json` |

## 底层协议

所有 agent 都通过 [MCP (Model Context Protocol)](https://modelcontextprotocol.io) 接入。`@sciverse/mcp-server` 是 stdio 形态的 MCP server，包装 SciVerse 三个 API：

- `search_papers` — 结构化元数据检索
- `semantic_search` — 自然语言语义检索（RAG）
- `read_content` — 按字节区间读取文献原文

## 通用前置条件

1. SciVerse API Token：从 https://sciverse.space 控制台申请，形如 `sv-xxx`
2. Node.js 18+（`@sciverse/mcp-server` 用 `npx` 运行）

## 不在列表里的 agent？

只要支持 MCP stdio，都能用同样模式接入。把以下 JSON 翻译到对应 agent 的配置语法即可：

```json
{
  "command": "npx",
  "args": ["-y", "@sciverse/mcp-server"],
  "env": { "SCIVERSE_API_TOKEN": "sv-xxx" }
}
```

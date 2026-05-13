# sciverse-mcp-server

[![npm](https://img.shields.io/npm/v/sciverse-mcp-server.svg)](https://www.npmjs.com/package/sciverse-mcp-server)

SciVerse 开放平台官方 MCP (Model Context Protocol) server。把三个学术文献检索工具暴露给任何 MCP 兼容的 coding agent —— Claude Code、Cursor、Codex CLI、Windsurf、Continue 等。

> Official MCP server for the SciVerse open platform. Exposes academic paper retrieval (`search_papers` / `semantic_search` / `read_content`) to any MCP-compatible coding agent.

## Quick start

```bash
export SCIVERSE_API_TOKEN=sv-xxx   # 从 https://sciverse.space 控制台申请
npx -y sciverse-mcp-server        # stdio 启动；coding agent 通常会代你 spawn
```

## 在 coding agent 里接入

### Claude Code

项目级 `.mcp.json`（也可以用 `claude mcp add sciverse npx -- -y sciverse-mcp-server`）：

```json
{
  "mcpServers": {
    "sciverse": {
      "command": "npx",
      "args": ["-y", "sciverse-mcp-server"],
      "env": { "SCIVERSE_API_TOKEN": "sv-xxx" }
    }
  }
}
```

### Cursor

`.cursor/mcp.json` 或 Settings → MCP Servers，配置同上。

### Codex CLI

`~/.codex/config.toml`：

```toml
[mcp_servers.sciverse]
command = "npx"
args = ["-y", "sciverse-mcp-server"]
env = { SCIVERSE_API_TOKEN = "sv-xxx" }
```

更详细的接入示例见仓库 `docs/integrations/`。

## 环境变量

| 变量 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `SCIVERSE_API_TOKEN` | ✓ | — | Bearer Token（控制台申请） |
| `SCIVERSE_BASE_URL` | | `https://api.sciverse.space` | API 入口，仅允许 `*.sciverse.space` 域名（防 token 泄漏） |

## 暴露的 tool

| 名称 | 用途 |
|---|---|
| `search_papers` | 结构化元数据检索（作者/年份/期刊/学科） |
| `semantic_search` | 自然语言语义检索（RAG 用） |
| `read_content` | 按字节区间读取文献原文 |

Input schema 与描述均从 `agent-tools/openapi.yaml` 派生（构建期跑 `npm run gen`），与 ClawHub skill、OpenAI/Anthropic tool 定义保持一致。

## 开发

```bash
npm install
npm run gen       # 从 ../../openapi.yaml 派生 src/generated/tools.ts
npm run build     # tsc → dist/
npm test          # vitest
```

如 `npm install` 因网络源问题失败，可换源：

```bash
npm install --registry https://registry.npmmirror.com
```

## 协议

Apache-2.0

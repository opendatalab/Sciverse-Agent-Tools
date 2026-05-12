# Claude Code 接入 SciVerse

> 给 Claude Code 用户（`claude` CLI / VS Code 扩展）的 5 分钟接入指南。

## 前置条件

- SciVerse API Token：从 https://sciverse.space 控制台申请
- Node.js 18+
- Claude Code 已安装

## 接入方式 A：MCP server（推荐，三个 tool 全开）

### 用 `claude mcp add` 一行命令

```bash
claude mcp add sciverse --env SCIVERSE_API_TOKEN=sv-xxx -- npx -y @sciverse/mcp-server
```

### 或手动写 `.mcp.json`

在项目根创建 `.mcp.json`：

```json
{
  "mcpServers": {
    "sciverse": {
      "command": "npx",
      "args": ["-y", "@sciverse/mcp-server"],
      "env": {
        "SCIVERSE_API_TOKEN": "sv-xxx"
      }
    }
  }
}
```

如要自定义 base URL（必须是 `*.sciverse.space` 子域名，否则 server 拒绝启动，以防 token 泄漏到任意域名）：

```json
"env": {
  "SCIVERSE_API_TOKEN": "sv-xxx",
  "SCIVERSE_BASE_URL": "https://api.sciverse.space"
}
```

## 接入方式 B：官方 Agent Skill（额外提供 prompt 编排）

仓库已派生 Claude Code 官方 skill 形态（[`skill-claude-code/`](../../skill-claude-code/)），它假设 MCP server 已通过方式 A 安装。

```bash
# 用户级
cp -r path/to/agent-tools/skill-claude-code ~/.claude/skills/sciverse

# 或 Plugin Marketplace 一键安装
claude /plugin marketplace add <repo-url>
claude /plugin install sciverse
```

## 验证

启动 Claude Code 后，运行：

```
/mcp
```

应能看到 `sciverse` 列出三个 tool：`search_papers`、`semantic_search`、`read_content`。

Hello-world prompt：

```
找 3 篇关于 Transformer 注意力机制的论文，引用具体段落。
```

Claude 会依次调用 `semantic_search` → `read_content` 完成 RAG 回答。

## 常见问题

| 现象 | 排查 |
|---|---|
| `/mcp` 看不到 sciverse | 确认 `.mcp.json` 路径在 cwd；用 `claude mcp list` 查；重启 Claude Code |
| HTTP 401 / `INVALID_API_KEY` | Token 错或已撤销，去 https://sciverse.space 重新生成 |
| HTTP 429 | 当前 Tier 配额已耗尽，看控制台或升级 Tier |
| `SCIVERSE_BASE_URL must point to *.sciverse.space` | 自定义 URL 必须是 `*.sciverse.space` 子域名（防 token 泄漏） |
| `npx` 拉包慢 | 加 `--registry https://registry.npmmirror.com`，或预装 `npm install -g @sciverse/mcp-server` 后把 `command` 改为 `sciverse-mcp` |

## 进阶

- 多环境 token：用 shell 直接 `SCIVERSE_API_TOKEN=$(security find-generic-password ...)` 注入 env，不要明文写进版本控制
- 与其他 MCP server 并存：`mcpServers` 是对象，可以并列多个 server
- 仅启用部分 tool：Claude Code 支持 `/permissions` 限制；或在 prompt 里明确告诉 Claude 只用 `semantic_search`

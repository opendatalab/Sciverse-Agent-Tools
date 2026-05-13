# Windsurf 接入 SciVerse

> 给 Codeium Windsurf 用户的 5 分钟接入指南。

## 前置条件

- SciVerse API Token：从 https://sciverse.space 控制台申请
- Node.js 18+
- Windsurf 已登录（Cascade 可用）

## 配置

编辑 `~/.codeium/windsurf/mcp_config.json`：

```json
{
  "mcpServers": {
    "sciverse": {
      "command": "npx",
      "args": ["-y", "sciverse-mcp-server"],
      "env": {
        "SCIVERSE_API_TOKEN": "sv-xxx"
      }
    }
  }
}
```

或通过 GUI：`Settings` → `Cascade` → `Plugins / MCP` → `Add custom server`。

> 配置路径在不同操作系统/Windsurf 版本可能不同，权威路径以 Windsurf docs 为准：https://docs.windsurf.com/windsurf/cascade/mcp

## 验证

打开 Cascade 面板，应看到 `sciverse` plugin 已加载（三个 tool）。

Hello-world prompt：

```
帮我找 3 篇关于 Transformer 注意力机制的论文，附原文片段引用。
```

Cascade 会调用 `semantic_search` → `read_content` 完成 RAG 回答。

## 常见问题

| 现象 | 排查 |
|---|---|
| Cascade 看不到 sciverse | 检查 `mcp_config.json` 路径，重启 Windsurf；查看 `Cascade Logs` |
| 配置文件路径找不到 | macOS 通常是 `~/.codeium/windsurf/`；Windows 是 `%USERPROFILE%\.codeium\windsurf\`；以官方 docs 为准 |
| 401 / `INVALID_API_KEY` | Token 失效，回控制台生成新的 |
| HTTP 429 | 配额耗尽 |
| `npx` 拉包失败 | 改成 `"command": "sciverse-mcp"`，先全局装 `npm install -g sciverse-mcp-server` |

## 进阶

- **企业代理**：在 `env` 里加 `HTTPS_PROXY` 让 `npx` / fetch 走公司代理
- **自定义 base URL**：在 `env` 加 `SCIVERSE_BASE_URL=https://api.sciverse.space`（仅 `*.sciverse.space` 子域名被接受，防 token 泄漏）
- **降级到 SDK**：若 Windsurf 版本不支持 MCP，可在 Codeium Chat 里用 [`sciverse-agent-tools`](../../packages/typescript/) npm 包做 function calling

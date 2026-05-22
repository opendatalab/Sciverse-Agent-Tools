# Cursor 接入 Sciverse

> 给 Cursor 用户的 5 分钟接入指南。

## 前置条件

- Sciverse API Token：从 https://sciverse.space 控制台申请
- Node.js 18+
- Cursor ≥ 0.40（支持 MCP）

## 配置

### 项目级 `.cursor/mcp.json`

在项目根创建：

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

### 或全局 Settings

`Cursor Settings` → `Features` → `MCP Servers` → `+ Add new MCP server`：

- Name: `sciverse`
- Type: `command`
- Command: `npx -y sciverse-mcp-server`
- Env: `SCIVERSE_API_TOKEN=sv-xxx`

> 如果你的 Cursor 版本菜单位置不同，参阅官方文档：https://docs.cursor.com/context/model-context-protocol

## 验证

打开 Cursor Composer (Cmd/Ctrl+I)，确认右上角 MCP 图标显示 `sciverse: 4 tools`。

Hello-world prompt（Composer agent mode）：

```
帮我找 3 篇关于 Transformer 注意力机制的论文，附原文片段引用。
```

也可以先让 agent 学习 schema 再做精确查询：

```
先列出 Sciverse 有哪些字段、access_oa_status 有哪些可能值，然后帮我找 2024 年以来 gold OA 状态的 Nature 期刊论文。
```

agent 会先调 `list_catalog(include_sample_values=true)` 拿到字段表 + 枚举值样本，再用 `search_papers` 精确构造 filter。

Cursor 应当连续调用 `semantic_search` → `read_content`，把结果整合成答复。

## 常见问题

| 现象 | 排查 |
|---|---|
| MCP 图标显示 `0 tools` | 重启 Cursor；用 `Reload Window` 命令；查看 `Output > MCP Logs` |
| `Authentication failed` / 401 | Token 失效，回控制台生成新的；env 是否有多余引号/空格 |
| 配置改完不生效 | Cursor 缓存 MCP server，必须 `Reload MCP Servers` 或重启 |
| `npx` 拉包慢 | 配置改为 `"command": "sciverse-mcp"`，先全局装 `npm install -g sciverse-mcp-server` |
| HTTP 429 | 配额超限，看控制台 |

## 进阶

- **限定 tool 调用**：Cursor 没有 fine-grained tool permission；如果只想让它用 `semantic_search`，请在 prompt 里明示
- **多项目复用**：把 `.cursor/mcp.json` 放进 dotfiles，或放到全局 Settings 避免每个项目重复
- **dev 环境 token**：用 `env` 字段而不是 shell 全局 export，避免 token 泄漏到无关进程

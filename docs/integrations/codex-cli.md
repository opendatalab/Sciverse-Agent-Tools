# Codex CLI 接入 SciVerse

> 给 OpenAI Codex CLI 用户的 5 分钟接入指南。

## 前置条件

- SciVerse API Token：从 https://sciverse.space 控制台申请
- Node.js 18+
- Codex CLI 已安装并配置了 OpenAI key（参见 https://github.com/openai/codex）

## 配置

编辑 `~/.codex/config.toml`，新增：

```toml
[mcp_servers.sciverse]
command = "npx"
args = ["-y", "sciverse-mcp-server"]
env = { SCIVERSE_API_TOKEN = "sv-xxx" }
```

如要自定义 base URL（必须 `*.sciverse.space` 子域名，否则启动失败 —— 防 token 泄漏）：

```toml
[mcp_servers.sciverse]
command = "npx"
args = ["-y", "sciverse-mcp-server"]
env = { SCIVERSE_API_TOKEN = "sv-xxx", SCIVERSE_BASE_URL = "https://api.sciverse.space" }
```

> 如果你的 Codex CLI 版本配置格式有差异（早期版本曾用 JSON），参阅官方 docs：https://github.com/openai/codex/blob/main/docs/config.md

## 验证

```bash
codex
```

进入交互后输入：

```
搜索 Hinton 在 2020-2023 年发表的论文，按年份倒序。
```

Codex 应当调用 `search_papers` 完成结构化检索。

或测试 RAG 链路：

```
找 3 篇关于 Transformer 注意力机制的论文，引用具体段落。
```

应触发 `semantic_search` → `read_content`。

## 常见问题

| 现象 | 排查 |
|---|---|
| Codex 启动报错说找不到 MCP server | 检查 `command` 路径，确认本机 `node`/`npx` 已在 PATH |
| 第一次启动卡很久 | `npx -y` 在拉包，正常；之后会走缓存，或预装 `npm install -g sciverse-mcp-server` 改 command 为 `sciverse-mcp` |
| 401 / `INVALID_API_KEY` | Token 失效或没正确传到 env |
| TOML 解析报错 | TOML 对引号敏感，env 必须是 `{ KEY = "value" }`，不是 JSON 风格的 `{"KEY":"value"}` |
| 看不到 sciverse 工具被调 | 把 prompt 写明确："use the sciverse search_papers tool to ..." |

## 进阶

- **环境隔离**：用 `~/.codex/profiles/*.toml`（若版本支持）把 dev/prod token 分开
- **多 server 并存**：`[mcp_servers.<name>]` 段可以加多个，每段一个 server
- **CI 集成**：把 `SCIVERSE_API_TOKEN` 走 GitHub Actions secrets，避免明文写进 `config.toml`

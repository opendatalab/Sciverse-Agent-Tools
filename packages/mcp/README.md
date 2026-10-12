# sciverse-mcp-server

[![npm](https://img.shields.io/npm/v/sciverse-mcp-server.svg)](https://www.npmjs.com/package/sciverse-mcp-server)

[English](#english) | [中文](#中文)

Official MCP (Model Context Protocol) server for the Sciverse open platform.
Exposes five academic-paper retrieval tools to any MCP-compatible coding agent
— Claude Code, Cursor, Codex CLI, Windsurf, Continue, and more.

> Tools: `search_papers` / `semantic_search` / `read_content` / `list_catalog` / `get_resource`
>
> 工具：`search_papers`（结构化元数据）/ `semantic_search`（语义检索）/ `read_content`（原文切片）/ `list_catalog`（字段 introspection）/ `get_resource`（论文图片二进制）

---

## English

### Quick start

```bash
export SCIVERSE_API_TOKEN=sv-xxx   # get one from https://sciverse.space
npx -y sciverse-mcp-server         # stdio mode; coding agents will spawn this for you
```

Or skip the env var entirely by running the Python CLI once:

```bash
pip install sciverse && sciverse auth login
# saves token to ~/.sciverse/credentials.json (file mode 0600)
# the MCP server will pick it up automatically next time it starts
```

### Connect from coding agents

#### Claude Code

Project-level `.mcp.json` (or run `claude mcp add sciverse npx -- -y sciverse-mcp-server`):

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

If you ran `sciverse auth login`, the `env` block can be omitted entirely.

#### Cursor

`.cursor/mcp.json` (or Settings → MCP Servers), same shape as above.

#### Codex CLI

`~/.codex/config.toml`:

```toml
[mcp_servers.sciverse]
command = "npx"
args = ["-y", "sciverse-mcp-server"]
env = { SCIVERSE_API_TOKEN = "sv-xxx" }
```

#### Windsurf

`~/.codeium/windsurf/mcp_config.json`, same JSON shape as Claude Code.

See [`docs/integrations/`](https://github.com/opendatalab/Sciverse-Agent-Tools/tree/main/docs/integrations)
for full per-agent guides.

### Configuration

Token / endpoint resolution order: explicit `env` in MCP config →
`SCIVERSE_API_TOKEN` / `SCIVERSE_BASE_URL` environment → `~/.sciverse/credentials.json` →
default (`https://api.sciverse.space`).

| Var | Required | Default | Notes |
|---|---|---|---|
| `SCIVERSE_API_TOKEN` | ✓ (or via login) | — | Bearer token |
| `SCIVERSE_BASE_URL` | | `https://api.sciverse.space` | Must be a `*.sciverse.space` domain (anti-leak guard) |

### Exposed tools

| Tool | Purpose |
|---|---|
| `search_papers` | Structured metadata search over papers / authors / sources (set `collection`) |
| `semantic_search` | Natural-language semantic chunk retrieval (RAG) |
| `read_content` | Character-range read of original paper text (offset/limit in Unicode code points) |
| `list_catalog` | Field introspection (returns all field names + enum sample values, agents should call this first to learn the schema) |
| `get_resource` | Fetch a paper figure / table image; the server wraps the bytes as an MCP `image` content block (base64 + mimeType) so multimodal models (e.g. Claude) can read the figure inline |

Tool descriptions + input schemas are derived from `openapi.yaml` at build time
(`npm run gen`), kept in sync with the SDK / ClawHub skill / OpenAI / Anthropic
tool exports.

### Hello-world prompt

After wiring up the MCP server, try:

```
帮我找 3 篇关于 Transformer 注意力机制的论文，附原文片段引用。
Find 3 papers on Transformer attention mechanism with quoted excerpts.
```

Or let the agent learn the schema first:

```
List the Sciverse fields and the values access_oa_status can take, then find
2024+ gold-OA Nature papers.
```

### Development

```bash
npm install
npm run gen       # derive src/generated/tools.ts from ../../openapi.yaml
npm run build     # tsc → dist/
npm test          # vitest (27 tests)
```

If `npm install` is slow / blocked, switch registry:

```bash
npm install --registry https://registry.npmmirror.com
```

### Links

- Source repo: <https://github.com/opendatalab/Sciverse-Agent-Tools>
- Python SDK + CLI: <https://pypi.org/project/sciverse>
- TypeScript SDK: <https://www.npmjs.com/package/sciverse>
- License: Apache-2.0

---

## 中文

Sciverse 开放平台官方 MCP (Model Context Protocol) server。把 5 个学术文献检索
工具暴露给任何 MCP 兼容的 coding agent —— Claude Code、Cursor、Codex CLI、
Windsurf、Continue 等。

### 快速开始

```bash
export SCIVERSE_API_TOKEN=sv-xxx   # 从 https://sciverse.space 控制台申请
npx -y sciverse-mcp-server         # stdio 启动；coding agent 通常会代你 spawn
```

也可以跑一次 Python CLI 把 token 持久化，之后 env 都不用配：

```bash
pip install sciverse && sciverse auth login
# 保存到 ~/.sciverse/credentials.json（文件权限 0600）
# MCP server 启动时自动 fallback 读取
```

### 在 coding agent 里接入

#### Claude Code

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

跑过 `sciverse auth login` 后 `env` 整段可省略。

#### Cursor

`.cursor/mcp.json` 或 Settings → MCP Servers，格式同上。

#### Codex CLI

`~/.codex/config.toml`：

```toml
[mcp_servers.sciverse]
command = "npx"
args = ["-y", "sciverse-mcp-server"]
env = { SCIVERSE_API_TOKEN = "sv-xxx" }
```

#### Windsurf

`~/.codeium/windsurf/mcp_config.json`，JSON 格式同 Claude Code。

完整接入指南见 [`docs/integrations/`](https://github.com/opendatalab/Sciverse-Agent-Tools/tree/main/docs/integrations)。

### 配置

Token / endpoint 解析顺序：MCP 配置里显式 `env` → `SCIVERSE_API_TOKEN` /
`SCIVERSE_BASE_URL` 环境变量 → `~/.sciverse/credentials.json` →
默认值（`https://api.sciverse.space`）。

| 变量 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `SCIVERSE_API_TOKEN` | ✓（或通过 login） | — | Bearer Token |
| `SCIVERSE_BASE_URL` | | `https://api.sciverse.space` | 必须是 `*.sciverse.space` 子域名（防 token 泄漏） |

### 暴露的 tool

| 名称 | 用途 |
|---|---|
| `search_papers` | 结构化元数据检索（作者 / 年份 / 期刊 / 学科） |
| `semantic_search` | 自然语言语义检索（RAG 用） |
| `read_content` | 按 Unicode 码点区间读文献原文 |
| `list_catalog` | 字段 introspection（返回所有字段名 + 枚举值样本，agent 接入时建议先调一次学 schema） |
| `get_resource` | 取文献附属图片字节流；MCP server 包装为 `image` content block + base64 + mimeType，多模态模型（如 Claude）可直接读图 |

Tool 描述和 input schema 均从 `openapi.yaml` 派生（构建期 `npm run gen`），与
Python/TS SDK、ClawHub skill、OpenAI / Anthropic tool 保持一致。

### Hello-world prompt

接入完成后试：

```
帮我找 3 篇关于 Transformer 注意力机制的论文，附原文片段引用。
```

或让 agent 先学 schema 再发查询：

```
列出 Sciverse 有哪些字段、access_oa_status 取值，然后找 2024 年以来 gold OA
状态的 Nature 期刊论文。
```

### 开发

```bash
npm install
npm run gen       # 从 ../../openapi.yaml 派生 src/generated/tools.ts
npm run build     # tsc → dist/
npm test          # vitest（27 测试）
```

如 `npm install` 因网络源问题失败，换源：

```bash
npm install --registry https://registry.npmmirror.com
```

### 链接

- 源码仓库：<https://github.com/opendatalab/Sciverse-Agent-Tools>
- Python SDK + CLI：<https://pypi.org/project/sciverse>
- TypeScript SDK：<https://www.npmjs.com/package/sciverse>
- 协议：Apache-2.0

### SCP Hub 逐用户 JWT 入口（默认关闭）

新增 `POST /mcp/scp`：每次请求必须带 Hub 用户 JWT，无状态、JSON 响应，不发送 `Mcp-Session-Id`；不要求用户先登录 SciVerse。新入口校验 Hub 凭证后签发短期内部委托，由 SciVerse 后端查询权威 SSO 资料并自动建账。无效 JWT 不会回退旧 IP 白名单。`/mcp` 和 stdio 保留原行为。

部署使用 Node 22。开启需配置 `SCIVERSE_MCP_HUB_JWT_ENABLED=true`、`SCIVERSE_MCP_HUB_JWT_ISSUER=scp-hub`、精确 `SCIVERSE_MCP_HUB_JWT_AUDIENCE`、`SCIVERSE_MCP_HUB_JWT_ALGORITHM`（RS256/ES256/EdDSA之一），并挂载 `SCIVERSE_MCP_HUB_JWT_PUBLIC_KEYS_FILE`（JSON：kid→SPKI PEM）。无 kid 仅可显式启用 `SCIVERSE_MCP_HUB_JWT_ALLOW_MISSING_KID=true` 且只配置一个公钥。拒绝对称算法、远端 key URL、多 aud 数组和超过 900 秒的有效期。

MCP 自己的委托私钥使用独立 RS256 PKCS8 PEM：`SCIVERSE_MCP_DELEGATION_PRIVATE_KEY_FILE`、`SCIVERSE_MCP_DELEGATION_KEY_ID`。后端只持对应公钥；MCP 不需要 Hub 私钥。Hub 公钥与委托私钥加载于进程启动，轮换后滚动重启。不同环境独立密钥。

`SCIVERSE_MCP_HUB_SYNC_SUBJECTS` 为逗号分隔的探活 UID，必须与后端相同；只能 initialize/list，不能业务调用。新通道仅开放五个原计划工具，不含 `list_paper_relations`。用户身份 `sub` 保留前导零，按可信 SSO UID 匹配。

HTTP 服务仅使用显式环境变量，不会从运行用户的个人凭据文件取默认 token。仅 Hub/Bearer 模式不需要 `SCIVERSE_API_TOKEN`；保留旧 `SCIVERSE_MCP_TRUSTED_IPS` 时则仍需显式设置该 token。

Hub 必须识别两类失败：入口 HTTP 401；以及业务工具 `isError=true`、文本 JSON `{status:401,body:{code:"HUB_CREDENTIAL_REVOKED"}}`。后者需重新签发并最多重试一次；解封时撤销边界覆盖 30 秒时钟偏差，新凭证可能需等待最多约 31 秒。403 封禁和 503 身份服务故障不得循环刷新。生产上线还需确认无状态协议、SSO状态/邮箱契约、数据库迁移、内部建账路径公网拒绝和三组密钥分发。

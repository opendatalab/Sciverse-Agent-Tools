# SciVerse Agent Tools

[English](./README.md) | **简体中文**

为 LLM Agent 提供 [SciVerse 开放平台](https://sciverse.space)学术检索能力的标准化 tool schema 与 SDK。

| 工具 | 适用场景 |
|---|---|
| `list_catalog` | 字段 introspection：返回可用字段、过滤算子、enum 字段取值样本 |
| `search_papers` | 按结构化条件查文献元数据（作者/年份/期刊/学科） |
| `semantic_search` | 自然语言语义检索片段（RAG 用） |
| `read_content` | 取原文字节切片（扩展 RAG 上下文） |
| `get_resource` | 取 `read_content` Markdown 中引用的图片/表格字节流 |

五个工具共用同一套 Bearer Token 鉴权，并在 Python SDK / TypeScript SDK / MCP server / Claude Code skill / ClawHub skill 中以一致接口暴露。canonical schema 见 [`openapi.yaml`](./openapi.yaml)。

## 接入方式选择

| 路径 | 适合谁 | 安装 |
|---|---|---|
| **Claude Code skill** | Claude Code / VS Code 用户 | 通过 Plugin Marketplace 一行装（见下） |
| **MCP server** | 任意 MCP-capable coding agent（Cursor / Codex CLI / Windsurf...） | 写到 `.mcp.json` —— [接入指南](./docs/integrations/) |
| **Python / TypeScript SDK** | 自定义 agent（OpenAI / Anthropic / LangChain / LlamaIndex...） | `pip install sciverse` 或 `npm install sciverse` |
| **CLI** | shell 脚本 / 快速试用 / 无 agent loop | 随 Python SDK 一起装 —— `sciverse auth login` |
| **Web well-known URL** | 通过 well-known URI 约定自动发现 skill 的 agent host | 把 agent host 指向 <https://sciverse.space/.well-known/agent-skills/> |

## 5 分钟接入 —— Claude Code

```bash
claude /plugin marketplace add https://github.com/opendatalab/Sciverse-Agent-Tools
claude /plugin install sciverse
```

skill 依赖 `sciverse-mcp-server`，装一次即可：

```bash
npm install -g sciverse-mcp-server
export SCIVERSE_API_TOKEN=sv-...     # 从 https://sciverse.space 控制台申请
```

或在项目 `.mcp.json` 里声明 MCP server —— 详见 [`skill-claude-code/SKILL.md`](./skill-claude-code/SKILL.md)。

## 5 分钟接入 —— 其他 MCP-capable agent

把下面这段贴进 agent 的 MCP 配置文件（Claude Code / Cursor 的 `.mcp.json`、Codex CLI 的 `~/.codex/config.toml` 等）：

```json
{
  "mcpServers": {
    "sciverse": {
      "command": "npx",
      "args": ["-y", "sciverse-mcp-server"],
      "env": { "SCIVERSE_API_TOKEN": "${SCIVERSE_API_TOKEN}" }
    }
  }
}
```

各 agent 详细步骤：

| Agent | 指南 |
|---|---|
| Claude Code | [docs/integrations/claude-code.md](./docs/integrations/claude-code.md) |
| Cursor | [docs/integrations/cursor.md](./docs/integrations/cursor.md) |
| Codex CLI | [docs/integrations/codex-cli.md](./docs/integrations/codex-cli.md) |
| Windsurf | [docs/integrations/windsurf.md](./docs/integrations/windsurf.md) |

## 5 分钟接入 —— agent host 走 well-known URL

如果你的 agent host 支持
[well-known URI 约定](https://en.wikipedia.org/wiki/Well-known_URI)
自动发现 skill，SciVerse 在以下地址提供 skill bundle：

```
https://sciverse.space/.well-known/agent-skills/index.json
```

接口返回 manifest，列出 `sciverse` skill 及其文件（`SKILL.md`、references、
agent 适配配置、可运行脚本）。遵循该约定的 host 会先拉 manifest，再把 skill
materialise 到本地供模型调用。

适用场景：

- 你的 agent host 已支持 `.well-known/agent-skills/` 自动发现
- 你想自动跟进最新 skill 版本（消费侧无需锁版本）
- 你不想为了拿 skill 单独 clone 一个 git repo

需要 host 特定的安装命令（Claude Code / MCP / OpenClaw / ClawHub），见上方
其他 Quickstart 段。

## 5 分钟接入 —— SDK

### 1. 获取 Bearer Token

登录 [SciVerse 开发者控制台](https://sciverse.space) 申请 API Token。

### 2. 安装 SDK

```bash
# Python
pip install sciverse

# TypeScript / Node.js
npm install sciverse
```

### 3. 配置凭据（三种方式任选）

```bash
# A. 环境变量（推荐 server / CI 场景）
export SCIVERSE_API_TOKEN=sv-...

# B. 凭据文件（推荐本地开发 —— ~/.sciverse/credentials.json，权限 0600）
sciverse auth login

# C. 显式传给 client（仅推荐密钥从 vault 取的场景）
```

读取顺序：显式参数 → `SCIVERSE_API_TOKEN` 环境变量 → `~/.sciverse/credentials.json`。

### 4. 调 SDK

**Python：**

```python
import asyncio
from sciverse import AgentToolsClient

async def main():
    # token / base_url 省略 —— 自动从环境变量或凭据文件读
    async with AgentToolsClient() as c:
        r = await c.semantic_search(query="Transformer 注意力机制")
        for hit in r["hits"][:3]:
            print(hit["title"], hit["score"])

asyncio.run(main())
```

**TypeScript：**

```ts
import { AgentToolsClient } from "sciverse";

const c = new AgentToolsClient();  // 自动读 SCIVERSE_API_TOKEN
const r: any = await c.semanticSearch({ query: "Transformer 注意力机制" });
r.hits.slice(0, 3).forEach((h: any) => console.log(h.title, h.score));
```

### 5. 接入 Agent 框架

**Anthropic Claude（Python）：**

```python
from anthropic import Anthropic
from sciverse import ANTHROPIC_TOOLS

client = Anthropic()
msg = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=2048,
    tools=ANTHROPIC_TOOLS,   # 5 个 tool schema 全包含
    messages=[{"role": "user", "content": "找几篇关于 Transformer 的论文"}]
)
```

**OpenAI（TypeScript）：**

```ts
import OpenAI from "openai";
import { OPENAI_TOOLS } from "sciverse";

const openai = new OpenAI();
const resp = await openai.chat.completions.create({
  model: "gpt-4o",
  tools: OPENAI_TOOLS as any,
  messages: [{ role: "user", content: "找几篇 Transformer 论文" }],
});
```

完整端到端示例（含 tool 调用回环）见 [`examples/`](./examples/)：

**SDK 直接调用（自己写 tool calling 回环）：**

- `python_anthropic_rag.py` — Anthropic + 5 tool RAG agent
- `python_openai_function_call.py` — OpenAI function calling
- `ts_openai.ts` — TypeScript + OpenAI
- `ts_langchain_agent.ts` — TypeScript + LangChain

**Agent SDK（agent loop 由 SDK 处理，更贴近 coding-agent 风格）：**

- `python_claude_agent_sdk.py` — Claude Agent SDK + `sciverse-mcp-server`
- `ts_openai_agents.ts` — `@openai/agents` + `sciverse-mcp-server`

## CLI

`sciverse` Python 包自带 CLI：

```bash
sciverse auth login                                  # 粘 token，保存到 ~/.sciverse/credentials.json
sciverse auth status                                 # 显示当前 token 来源和 endpoint
sciverse auth logout                                 # 删凭据文件

sciverse catalog --samples                           # list_catalog 带 enum 样本
sciverse search --author Hinton --year-from 2020     # search_papers
sciverse semantic-search "注意力机制"                  # semantic_search
sciverse content <doc_id> --offset 0 --limit 4096    # read_content
sciverse resource <file_name> -o figure.png          # get_resource（二进制 → 文件）
```

JSON 输出到 stdout（可 `| jq` 加工），错误到 stderr。

## API 速览

### Python SDK

```python
async with AgentToolsClient() as c:           # token 从 env / 凭据文件读
    # 1. 字段 introspection —— 首次接入调一次
    await c.list_catalog(include_sample_values=True)
    # 2. 结构化检索
    await c.search_papers(query=..., authors=[...], year_from=2020, page_size=10)
    # 3. 语义检索（mode: fast / balanced / quality）
    await c.semantic_search(query=..., top_k=10, mode="balanced")
    # 4. 读原文字节区间
    await c.read_content(doc_id=..., offset=0, limit=4096)
    # 5. 取图片字节流（多模态 RAG）
    img_bytes, mime = await c.get_resource(file_name="dt=.../p_.../f3.png")
```

返回值类型为 `dict[str, Any]`，**响应 schema 详见 [`openapi.yaml`](./openapi.yaml)**。
高级用户可用 `from sciverse.types import SearchPapersRequest, ...` 做类型化构造与校验。

**长生命周期 client**（web server / agent runtime，client 不随单次 request 起灭）：

```python
client = AgentToolsClient()
try:
    while serving:
        r = await client.semantic_search(query=...)
        ...
finally:
    await client.aclose()   # 显式关闭底层 httpx 连接池
```

### TypeScript SDK

```ts
const c = new AgentToolsClient();   // 自动读 SCIVERSE_API_TOKEN
await c.listCatalog({ include_sample_values: true });
await c.searchPapers({ query, authors, year_from, page_size });
await c.semanticSearch({ query, top_k, mode });
await c.readContent({ doc_id, offset, limit });
const { bytes, mimeType } = await c.getResource({ file_name });
```

返回值类型为 `unknown`，需用户自行 cast：

```ts
import type { components } from "sciverse";
type SemanticSearchResp = components["schemas"]["SemanticSearchResponse"];
const r = await c.semanticSearch({ query: "x" }) as SemanticSearchResp;
```

## 错误处理

**Python：** 非 2xx 响应抛 `httpx.HTTPStatusError`：

```python
import httpx
try:
    await c.search_papers(query="x")
except httpx.HTTPStatusError as e:
    print(e.response.status_code, e.response.text)
```

**TypeScript：** 非 2xx 响应抛 `Error("SciVerse API <status>: <body>")`：

```ts
try {
  await c.searchPapers({ query: "x" });
} catch (e) {
  console.error(e);  // "SciVerse API 401: {...}"
}
```

| HTTP 状态 | 含义 |
|---|---|
| 401 | Token 缺失或无效 |
| 400 | 请求参数错误（如字段名未知 —— 调 `list_catalog` 查可用字段） |
| 429 | 配额 / 限流超限（仅生产网关） |
| 502 / 503 | 上游服务不可用 |

## 五个工具的协同链路

**1. 自然语言 RAG（最常见）：**

```
semantic_search(query="...")
    └─▶ 对每个 hit：read_content(doc_id, offset, limit=8192)
            └─▶ 回答里引用 doc_id + title
```

**2. 先查 schema 再精确过滤：**

```
list_catalog(include_sample_values=true)         # 首次接入调一次 —— 学习字段名和 enum 取值
    └─▶ search_papers(filters_advanced=[...])    # 构造精确过滤条件
```

**3. 结构化预筛 + 语义精化（hybrid）：**

```
search_papers(authors=[...], year_from=2020)     # 先按结构化条件缩窄
    └─▶ hits[].doc_id 列表
            └─▶ semantic_search(query="...")     # 在缩窄结果里语义检索
                                                 # （需自行二次过滤 ——
                                                 #  semantic_search 不支持 doc_id 白名单）
```

**4. 多模态 RAG（含图片）：**

```
semantic_search(query="...")
    └─▶ read_content(doc_id, offset) 返回 Markdown，含 ![图 3](dt=xxx/p_yyy/f3.png)
            └─▶ get_resource(file_name="dt=xxx/p_yyy/f3.png")
                    └─▶ 图片字节流 + mime type —— 直接喂多模态模型
```

## 版本与变更

参见 [CHANGELOG.md](./CHANGELOG.md)。版本号由 [semantic-release](https://semantic-release.gitbook.io/) 根据 [Conventional Commits](https://www.conventionalcommits.org/) 自动管理（详见 [CONTRIBUTING.md](./CONTRIBUTING.md)）。

## 开发

```bash
uv sync
bash scripts/build.sh   # 重新派生 dist/ 与 packages/*/src/{tools,types}.{py,ts}
uv run pytest tests/    # 派生器单测
```

## OpenClaw 用户

通过 [ClawHub](https://clawhub.ai) 一键安装：

```bash
clawhub install sciverse
```

详见 [`clawhub/README.md`](./clawhub/README.md)。

## License

Apache-2.0

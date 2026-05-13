# SciVerse Agent Tools

为 LLM Agent 提供 SciVerse 开放平台检索能力的标准化 tool schema 与 SDK。

| 工具 | 适用场景 |
|---|---|
| `search_papers` | 按结构化条件查文献元数据（作者/年份/期刊/学科） |
| `semantic_search` | 自然语言语义检索片段（RAG 用） |
| `read_content` | 取原文字节切片（扩展 RAG 上下文） |

## 5 分钟接入

### 1. 获取 Bearer Token

登录 [SciVerse 开发者控制台](https://sciverse.space) 申请 API Token。

### 2. 安装 SDK

```bash
# Python
pip install sciverse-agent-tools

# TypeScript / Node.js
npm install sciverse-agent-tools
```

### 3. 直接调用

**Python：**

```python
import asyncio
from sciverse_agent_tools import AgentToolsClient

async def main():
    async with AgentToolsClient(
        base_url="https://api.sciverse.space",
        token="<TOKEN>",
    ) as c:
        r = await c.semantic_search(query="Transformer 注意力机制")
        for hit in r["hits"][:3]:
            print(hit["title"], hit["score"])

asyncio.run(main())
```

**TypeScript：**

```ts
import { AgentToolsClient } from "sciverse-agent-tools";

const c = new AgentToolsClient({
  baseUrl: "https://api.sciverse.space",
  token: process.env.SCIVERSE_API_TOKEN!,
});

const r: any = await c.semanticSearch({ query: "Transformer 注意力机制" });
r.hits.slice(0, 3).forEach((h: any) => console.log(h.title, h.score));
```

### 4. 接入 Agent 框架

**Anthropic Claude（Python）：**

```python
from anthropic import Anthropic
from sciverse_agent_tools import ANTHROPIC_TOOLS

client = Anthropic()
msg = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=2048,
    tools=ANTHROPIC_TOOLS,
    messages=[{"role": "user", "content": "找几篇关于 Transformer 的论文"}]
)
```

**OpenAI（TypeScript）：**

```ts
import OpenAI from "openai";
import { OPENAI_TOOLS } from "sciverse-agent-tools";

const openai = new OpenAI();
const resp = await openai.chat.completions.create({
  model: "gpt-4o",
  tools: OPENAI_TOOLS as any,
  messages: [{ role: "user", content: "找几篇 Transformer 论文" }],
});
```

完整端到端示例（含 tool 调用回环）见 [`examples/`](./examples/)：

**SDK 直接调用（自己写 tool calling 回环）：**

- `python_anthropic_rag.py` — Anthropic + 三个 tool 的 RAG agent
- `python_openai_function_call.py` — OpenAI function calling
- `ts_openai.ts` — TypeScript + OpenAI
- `ts_langchain_agent.ts` — TypeScript + LangChain

**Agent SDK（agent loop 由 SDK 处理，更贴近 coding-agent 风格）：**

- `python_claude_agent_sdk.py` — Claude Agent SDK + `sciverse-mcp-server` MCP server
- `ts_openai_agents.ts` — `@openai/agents` + `sciverse-mcp-server` MCP server

## API 速览

### Python SDK

```python
async with AgentToolsClient(base_url=..., token=...) as c:
    # 1. 结构化检索
    await c.search_papers(query=..., authors=[...], year_from=2020, page_size=10)
    # 2. 语义检索（mode: fast / balanced / quality）
    await c.semantic_search(query=..., top_k=10, mode="balanced")
    # 3. 读原文字节区间
    await c.read_content(doc_id=..., offset=0, limit=4096)
```

返回值类型为 `dict[str, Any]`，**响应 schema 详见 [`openapi.yaml`](./openapi.yaml)**。  
高级用户可用 `from sciverse_agent_tools.types import SearchPapersRequest, ...` 做类型化构造与校验。

**长生命周期 client**（如 web server / agent runtime，client 不随单次 request 起灭）：

```python
client = AgentToolsClient(base_url="https://api.sciverse.space", token=TOKEN)
try:
    # 复用 client 处理多请求
    while serving:
        r = await client.semantic_search(query=...)
        ...
finally:
    await client.aclose()  # 显式关闭底层 httpx 连接池
```

### TypeScript SDK

```ts
const c = new AgentToolsClient({ baseUrl, token });
await c.searchPapers({ query, authors, year_from, page_size });
await c.semanticSearch({ query, top_k, mode });
await c.readContent({ doc_id, offset, limit });
```

返回值类型为 `unknown`，需用户自行 cast：

```ts
import type { components } from "sciverse-agent-tools";
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
| 400 | 请求参数错误 |
| 429 | 配额超限（仅生产网关） |
| 502 / 503 | 上游服务不可用 |

## 三个工具的协同链路

典型 RAG 流：

```
semantic_search(query="...")
    └─▶ hits[i].doc_id, hits[i].offset
            └─▶ read_content(doc_id, offset)  # 取扩展上下文
```

筛选 + 语义混合：

```
search_papers(authors=[...], year_from=2020)  # 先按结构化条件缩窄
    └─▶ hits[].doc_id 列表
            └─▶ semantic_search(query="...")  # 在缩窄结果里语义检索（受限于 SDK，需自行二次筛选）
```

## 版本与变更

参见 [CHANGELOG.md](./CHANGELOG.md)。当前版本 **v0.1.0** (pre-stable)，前几个版本会根据真实 Agent 调用反馈调整 description，可能小幅 breaking。

## 开发

```bash
cd agent-tools
uv sync
bash scripts/build.sh   # 重新派生 dist/ 与 packages/*/src/{tools,types}.{py,ts}
uv run pytest tests/    # 派生器单测
```

## OpenClaw 用户

通过 [ClawHub](https://clawhub.ai) 一键安装：

```bash
clawhub install sciverse-agent-tools
```

详见 [`skill/README.md`](./skill/README.md)。

## Claude Code 用户

SciVerse 提供 Claude Code 官方 Agent Skill 形态（与 OpenClaw 平行的另一种 skill）。

**方式 1：通过 Plugin Marketplace（推荐）**

```bash
claude /plugin marketplace add https://github.com/opendatalab/SciVerse-agent-tools
claude /plugin install sciverse
```

**方式 2：手动安装**

把 `skill-claude-code/` 整目录复制到 Claude Code skill 加载路径之一：

```bash
# 用户级
cp -r agent-tools/skill-claude-code ~/.claude/skills/sciverse

# 或项目级
cp -r agent-tools/skill-claude-code .claude/skills/sciverse
```

**配合 MCP server**

Claude Code skill 形态依赖 `sciverse-mcp-server`（由另一个并行 agent 维护），先安装：

```bash
npm install -g sciverse-mcp-server
export SCIVERSE_API_TOKEN=sv-...
```

或在项目 `.mcp.json` 里声明（详见 `skill-claude-code/SKILL.md`）。

## 其他 coding agent

通过 MCP server [`sciverse-mcp-server`](./packages/mcp/) 接入主流 coding agent：

| Agent | 接入指南 |
|---|---|
| Claude Code | [docs/integrations/claude-code.md](./docs/integrations/claude-code.md) |
| Cursor | [docs/integrations/cursor.md](./docs/integrations/cursor.md) |
| Codex CLI | [docs/integrations/codex-cli.md](./docs/integrations/codex-cli.md) |
| Windsurf | [docs/integrations/windsurf.md](./docs/integrations/windsurf.md) |

## TODO / 路线图

> v0.2.0（2026-05-13）已落地：MCP server 包、Claude Code Skill 派生、4 篇接入指南、GitHub 公开 mirror（含 author 脱敏 sync）、ClawHub 组织迁移（`@sciverse/academic-retrieval`）、Agent SDK 示例、LICENSE、包 metadata。明细见 [CHANGELOG.md](./CHANGELOG.md)。
>
> 下面是**剩余未完成项**，已完成项不再列出。

### 功能增强（P1/P2）

- [ ] **Token 体验：`sciverse auth login` device-code flow**（P1）— 写 `~/.sciverse/credentials.json`，MCP server / SDK 自动 fallback 读取；省掉用户每次手动复制 token 进 env
- [ ] **MCP `progress` 通知** — `semantic_search` quality 模式 2-4s，借 MCP progress notifications 输出"正在 LLM 改写 query / 召回 X 篇"，避免 agent UI 静默等待
- [ ] **eval baseline** — `evals/`：一批 query → 期望 tool 调用 → recall@k，CI 跑；当前 description 调优靠"真实 Agent 反馈"但没基线
- [ ] **MCP server 接 SLS `app_logs`** — 当前出错只写 stderr，没结构化日志
- [ ] **更多框架适配** — Vercel AI SDK（TS 圈最热）、LlamaIndex（README 提了但 examples 没有）、Dify / Coze（国内工具市场上架）
- [ ] **Offline mock** — SDK 加 `MOCK=1` 模式返回 fixture，方便 agent 开发者无 token 本地调试
- [ ] **`read_full_content` 高阶 wrapper** — `read_content` 上限 16KB，agent 经常循环 offset 浪费 turn，封装一次拿完

### v0.2.0 发布后验证（合 main 触发）

合 dev → main 时这些 job 才跑，需关注：

- [ ] **`agent-tools:drift-check`**（MR-only）— 验证派生产物 idempotent，特别是这次 ClawHub skill name/slug 改动后
- [ ] **`agent-tools:release-mcp`** — 首次发 `sciverse-mcp-server@0.2.0` 到 npmjs.org，去 https://www.npmjs.com/package/sciverse-mcp-server 验证；如缺 npm 身份需 GitLab CI variable 补 `NPM_TOKEN`
- [ ] **`agent-tools:release`** — PyPI + TS SDK 0.2.0 发布
- [ ] **`agent-tools:publish-skill`** — ClawHub 发 `sciverse-academic-retrieval` 0.1.5（独立版本）
- [ ] **`agent-tools:mirror-sync`** — `git subtree split` + filter-branch 脱敏 + 推到 GitHub mirror（已手动跑过一次，CI 形态待验）

### 运维 / 手动操作（你来做）

- [ ] **GitHub mirror 切换为 public** — Settings → Danger Zone → Change visibility → Public。public 后 `claude /plugin marketplace add` 才能匿名 clone
- [ ] **GitLab runner IP 加 dev 网关白名单** — 当前 `agent-tools:contract` job 因 dev 网关返 403（鉴权前拦截）暂设 `allow_failure: true`；白名单生效后移除该 flag 恢复 strict 契约校验
- [ ] **mirror repo 补 `CONTRIBUTING.md`** — 说明这是单向 mirror，issue 欢迎，PR 会被 cherry-pick 回主仓
- [ ] **mirror repo About 段** — 描述 + topics（`mcp`、`agent-tools`、`claude-code`、`sciverse`）提升 discoverability

### 公告 / 链路稳定后细化

- [ ] **用户安装命令公告** — `openclaw skills install academic-retrieval`（README 已改，待对外发布说明同步）
- [ ] **`agent-tools:publish-skill` 改用 `--source-repo` 直发** — mirror public 后移除 `/tmp` workaround，加 `--source-repo opendatalab/SciVerse-agent-tools --source-commit ${MIRROR_SHA}`，让 ClawHub 详情页有可审计 source 链接
- [ ] **ClawHub 详情页 Source repo 填 `opendatalab/SciVerse-agent-tools`** — mirror public + publish-skill 切到 `--source-repo` 后自动生效

### ClawHub `CLAWHUB_TOKEN` 维护

- [x] 当前用 owner 个人 token 代表 `@sciverse` 组织 publish（ClawHub 无组织级 token 概念）
- [ ] **owner 变更时需同步替换** GitLab CI variable `CLAWHUB_TOKEN`

**回滚预案**：保留旧个人账号 + 旧 GitLab publish job 至少一个 release cycle 作为热备，确认新链路无问题后再下线。

## License

Apache-2.0

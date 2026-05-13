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

- `python_anthropic_rag.py` — Anthropic + 三个 tool 的 RAG agent
- `python_openai_function_call.py` — OpenAI function calling
- `ts_openai.ts` — TypeScript + OpenAI
- `ts_langchain_agent.ts` — TypeScript + LangChain

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

### 立即可做（P1 剩余）

- [ ] **Claude Agent SDK / OpenAI Agents SDK 示例** — `examples/` 当前是 `messages.create` 风格的 tool-calling 回环；补 `claude-agent-sdk` / `@openai/agents` 的 `mcpServers` 注入示例（coding-agent 风格应用主流走 Agent SDK）
- [ ] **Token 体验：`sciverse auth login` device-code flow** — 写 `~/.sciverse/credentials.json`，MCP server / SDK 自动 fallback 读取；省掉用户每次手动复制 token 进 env

### P2（可缓但有价值）

- [ ] **MCP `progress` 通知** — `semantic_search` quality 模式 2-4s，借 MCP progress notifications 输出"正在 LLM 改写 query / 召回 X 篇"，避免 agent UI 静默等待
- [ ] **eval baseline** — `evals/`：一批 query → 期望 tool 调用 → recall@k，CI 跑；当前 description 调优靠"真实 Agent 反馈"但没基线
- [ ] **MCP server 接 SLS `app_logs`** — 当前出错只写 stderr，没结构化日志
- [ ] **更多框架适配** — Vercel AI SDK（TS 圈最热）、LlamaIndex（README 提了但 examples 没有）、Dify / Coze（国内工具市场上架）
- [ ] **Offline mock** — SDK 加 `MOCK=1` 模式返回 fixture，方便 agent 开发者无 token 本地调试
- [ ] **`read_full_content` 高阶 wrapper** — `read_content` 上限 16KB，agent 经常循环 offset 浪费 turn，封装一次拿完

### 今天落地后的 follow-up

- [x] ~~**npm 发布前置**~~ — 已采用无 scope 名 `sciverse-mcp-server`（避免 `@sciverse` org 注册成本）；GitLab CI 新增 `agent-tools:release-mcp` job，main + packages/mcp/** 变更时 `npm publish` 到 npmjs.org，version 独立维护、tag 前缀 `sciverse-mcp-v` 避免与 SDK 冲突
- [ ] **首次 npm publish 验证** — 第一次 main 合并触发 `release-mcp` 后，去 https://www.npmjs.com/package/sciverse-mcp-server 验证发包成功；如需 npm 用户身份配置可在 GitLab CI variable 补 `NPM_TOKEN`（与 SDK release job 共用）
- [x] ~~**Plugin Marketplace `<repo-url>` 占位符**~~ — 已替换为 `https://github.com/opendatalab/SciVerse-agent-tools`
- [ ] **mirror 切换为 public** — 当前 GitHub mirror 是 private。`claude /plugin marketplace add` 需要 public repo 才能匿名 clone。手动操作：mirror Settings → Danger Zone → Change visibility → Public
- [ ] **派生漂移 CI 验证** — 这次顺手把 ClawHub `skill/*` 重生成后的版本也提交了，需要跑一次 CI 确认"派生产物漂移检测"job 还能正常报警
- [ ] **CHANGELOG 版本号** — `[Unreleased]` 累积了多条 Added（MCP / Claude skill / 接入文档 / mirror sync），下次发布前 bump 到 `0.2.0` 并定型 `[Unreleased]`
- [ ] **完善 PyPI / npm 包 metadata**：repository / homepage / documentation / changelog / bugs URLs（含新 `sciverse-mcp-server`）
- [ ] **根级 LICENSE 文件**（Apache-2.0）
- [ ] **examples 中 Anthropic model id 用 alias**（替换 `claude-opus-4-7` 或注明可替换）
- [ ] **README 加 `await c.aclose()` 长生命周期 client 示例**

### ClawHub skill：迁移到组织账号 + GitHub 公开 mirror

旧形态：ClawHub 上 `sciverse-agent-tools` skill 由个人账号 publish。
新形态：`@sciverse` 组织名下 `academic-retrieval` slug，全局唯一 ID 为 `sciverse-academic-retrieval`。

**Phase 1 — ClawHub 组织账号**

- [x] 在 https://clawhub.ai 创建 `sciverse` 组织，owner 已就位
- [x] 在 ClawHub web 上把 skill 迁到 `@sciverse` 组织，发布为 `sciverse-academic-retrieval`（slug `academic-retrieval`）
- [x] 派生器 `generators/to_clawhub_skill.py` 同步：`SKILL_NAME = "sciverse-academic-retrieval"` + `SKILL_SLUG = "academic-retrieval"`，manifest 加 `slug` 字段，SKILL.md frontmatter 加 `slug` 字段，标题用 slug。
- [x] 版本号独立 bump：派生器读 `skill/manifest.json` 已有 `version`，不再被 openapi.yaml 拽回（manifest 现 `0.1.5`，openapi `0.1.2`，二者解耦）
- [x] CI variable `CLAWHUB_TOKEN`：保留 owner 个人 token（ClawHub 无组织级 token 概念，由 owner 个人身份代表组织 publish，与 GitHub PAT 模式一致）。owner 变更时需同步替换。
- [ ] 用户安装命令更新：`openclaw skills install academic-retrieval`（README 已改，待发布说明同步）

**Phase 2 — GitHub 公开 mirror**（基础设施已就位）

- [x] 创建 `github.com/opendatalab/SciVerse-agent-tools` mirror repo（含 agent-tools/ 子目录完整 history，首次手动 `git subtree split` 推送）
- [x] GitLab CI sync job `agent-tools:mirror-sync`：main 分支 + agent-tools/ 变更触发，`git subtree split` 后 `--force` 推到 mirror，`allow_failure: true`（不阻塞 release）
- [ ] **mirror 切到 public**（同上一节 TODO）
- [ ] 在 mirror repo 加 `CONTRIBUTING.md`：说明本仓库是单向 mirror，issue 欢迎，PR 会被 cherry-pick 回主仓
- [ ] 更新 `agent-tools:publish-skill` job：mirror 稳定后改为从仓库目录直发并加 `--source-repo opendatalab/SciVerse-agent-tools` flag（参见 publish-skill job 内的 v0.2 TODO 注释）
- [ ] ClawHub 详情页 Source repo 填 `opendatalab/SciVerse-agent-tools`

**回滚预案**：保留旧个人账号 + 旧 GitLab publish job 至少一个 release cycle 作为热备，确认新链路无问题后再下线。

## License

Apache-2.0

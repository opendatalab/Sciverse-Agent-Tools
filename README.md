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
        base_url="https://sciverse.space/api",
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
  baseUrl: "https://sciverse.space/api",
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
import type { components } from "sciverse-agent-tools/dist/types";
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

## License

Apache-2.0

# sciverse

[English](#english) | [中文](#中文)

Sciverse open-platform TypeScript SDK for academic paper retrieval. Wraps five
retrieval tools (`searchPapers`, `semanticSearch`, `readContent`, `listCatalog`,
`getResource`) behind one fetch-based client + ready-to-use `OPENAI_TOOLS` /
`ANTHROPIC_TOOLS` constants for direct tool-calling.

> Tools: `searchPapers` (structured metadata) / `semanticSearch` (semantic retrieval) / `readContent` (text byte-range) / `listCatalog` (field introspection) / `getResource` (paper figure binary).
>
> 工具：`searchPapers`（结构化元数据）/ `semanticSearch`（语义检索）/ `readContent`（原文切片）/ `listCatalog`（字段 introspection）/ `getResource`（论文图片二进制）

---

## English

### Install

```bash
npm install sciverse           # or pnpm add / yarn add
```

Node.js ≥ 18 (uses native `fetch`).

### Configure once via Python CLI (optional but recommended)

```bash
pip install sciverse && sciverse auth login
# - opens https://sciverse.space/tokens in your browser
# - paste the token you create
# - saved to ~/.sciverse/credentials.json (file mode 0600)
```

After this any `new AgentToolsClient()` without explicit args picks it up
automatically. Override hierarchy: explicit arg → `SCIVERSE_API_TOKEN` env →
credentials file → default. Pure Node.js shops can skip the CLI and use env
vars / explicit constructor args.

### Quick start

```ts
import { AgentToolsClient } from "sciverse";

const c = new AgentToolsClient();  // token + baseUrl auto-resolved

const r: any = await c.semanticSearch({ query: "Transformer attention mechanism", top_k: 3 });
for (const hit of r.hits) {
  console.log(hit.doc_id, hit.score, hit.title);
}
```

### Explicit construction

```ts
const c = new AgentToolsClient({
  baseUrl: "https://api.sciverse.space",
  token: process.env.MY_TOKEN!,
});
```

### Five retrieval tools

```ts
// 1. Structured metadata search (Boolean filters + sort + pagination)
await c.searchPapers({
  query: "transformer",          // full-text BM25 (optional)
  authors: ["Hinton"],
  year_from: 2020, year_to: 2024,
  journals: ["Nature", "Science"],
  sort_by_year: "desc",          // "desc" / "asc" / "none"
  page_size: 10,
});

// 1b. Entity collections — search authors / journals (set collection)
await c.searchPapers({
  collection: "authors",         // papers (default) / authors / sources
  filters_advanced: [{ field: "summary_stats.h_index", operator: "FILTER_OP_GTE", value: 50 }],
  sort_advanced: [{ field: "cited_by_count", order: "SORT_ORDER_DESC" }],
});
// Call listCatalog({ collection: "authors" }) to discover each collection's fields.

// 2. Natural-language semantic search (vector + BM25 hybrid, returns chunks)
await c.semanticSearch({ query: "How does attention work?", top_k: 10, mode: "balanced" });

// 3. Byte-range read of original paper text
await c.readContent({ doc_id: "p_xxx", offset: 0, limit: 8192 });

// 4. Schema introspection — call once to discover field names + enum values
await c.listCatalog({ include_sample_values: true });

// 5. Fetch a paper figure / table image
const { bytes, mimeType } = await c.getResource({ file_name: "dt=xxx/p_yyy/f3.png" });
// `bytes` is a Uint8Array; `mimeType` is e.g. "image/png"
```

### Response typing

Responses are returned as `unknown`. Cast with the generated OpenAPI types:

```ts
import type { components } from "sciverse";
type SemanticSearchResp = components["schemas"]["SemanticSearchResponse"];
const r = (await c.semanticSearch({ query: "x" })) as SemanticSearchResp;
```

### Use with OpenAI / Anthropic tool-calling

```ts
import OpenAI from "openai";
import { AgentToolsClient, OPENAI_TOOLS } from "sciverse";

const openai = new OpenAI();
const sv = new AgentToolsClient();

const resp = await openai.chat.completions.create({
  model: "gpt-4o",
  tools: OPENAI_TOOLS as any,
  messages: [{ role: "user", content: "Find 3 transformer papers" }],
});
// ... dispatch tool_calls to sv.searchPapers / sv.semanticSearch / ...
```

`ANTHROPIC_TOOLS` is exported the same way for `@anthropic-ai/sdk`.

For Claude Agent SDK / OpenAI Agents SDK (agent loop handled by framework),
see [`sciverse-mcp-server`](https://www.npmjs.com/package/sciverse-mcp-server).

### Error handling

Non-2xx responses throw `new Error("Sciverse API <status>: <body>")`:

```ts
try {
  await c.searchPapers({ query: "x" });
} catch (e) {
  console.error(e);  // "Sciverse API 401: {...}"
}
```

| HTTP | Meaning |
|---|---|
| 400 | Bad request (unknown field, conflicting query+sort, ...) |
| 401 | Token missing / invalid / user disabled |
| 403 | Field permission denied |
| 429 | Rate limit (60 req / 60s per user, shared across protected endpoints) |
| 502 | Upstream metadata-service unavailable |

### Links

- Source repo: <https://github.com/opendatalab/Sciverse-Agent-Tools>
- Changelog: <https://github.com/opendatalab/Sciverse-Agent-Tools/blob/main/CHANGELOG.md>
- Console (get a token): <https://sciverse.space>
- License: Apache-2.0

---

## 中文

Sciverse 开放平台 TypeScript SDK，5 个学术文献检索 tool（结构化元数据、
语义检索、原文切片、字段 introspection、论文图片）。

### 安装

```bash
npm install sciverse           # 或 pnpm add / yarn add
```

要求 Node.js ≥ 18（使用 native fetch）。

### 通过 Python CLI 登录一次（推荐）

```bash
pip install sciverse && sciverse auth login
# - 浏览器打开 https://sciverse.space/tokens
# - 复制控制台生成的 token，粘贴回 CLI
# - 保存到 ~/.sciverse/credentials.json（文件权限 0600）
```

之后任何 `new AgentToolsClient()` 不传 token 都自动 fallback 读取。优先级：
显式参数 → `SCIVERSE_API_TOKEN` 环境变量 → 凭据文件 → 默认值。纯 Node 用户
不想装 Python 也可以直接通过环境变量或构造参数传 token。

### 快速开始

```ts
import { AgentToolsClient } from "sciverse";

const c = new AgentToolsClient();  // token + baseUrl 自动解析

const r: any = await c.semanticSearch({ query: "Transformer 注意力机制", top_k: 3 });
for (const hit of r.hits) {
  console.log(hit.doc_id, hit.score, hit.title);
}
```

### 显式构造

```ts
const c = new AgentToolsClient({
  baseUrl: "https://api.sciverse.space",
  token: process.env.MY_TOKEN!,
});
```

### 5 个检索 tool

```ts
// 1. 结构化元数据查询（布尔过滤 + 排序 + 分页）
await c.searchPapers({
  query: "transformer",          // 全文 BM25（可选）
  authors: ["Hinton"],
  year_from: 2020, year_to: 2024,
  journals: ["Nature", "Science"],
  sort_by_year: "desc",          // "desc" / "asc" / "none"
  page_size: 10,
});

// 2. 自然语言语义检索（向量 + BM25 混合，返回 chunk）
await c.semanticSearch({ query: "注意力机制如何工作？", top_k: 10, mode: "balanced" });

// 3. 按字节区间读原文
await c.readContent({ doc_id: "p_xxx", offset: 0, limit: 8192 });

// 4. 字段 introspection —— Agent 接入第一步
await c.listCatalog({ include_sample_values: true });

// 5. 取文献附属图片（read_content Markdown 中 ![alt](file_name) 占位时）
const { bytes, mimeType } = await c.getResource({ file_name: "dt=xxx/p_yyy/f3.png" });
// `bytes` 是 Uint8Array；`mimeType` 形如 "image/png"
```

### 响应类型化

响应默认 `unknown`，用派生自 OpenAPI 的类型 cast：

```ts
import type { components } from "sciverse";
type SemanticSearchResp = components["schemas"]["SemanticSearchResponse"];
const r = (await c.semanticSearch({ query: "x" })) as SemanticSearchResp;
```

### 接入 OpenAI / Anthropic tool calling

```ts
import OpenAI from "openai";
import { AgentToolsClient, OPENAI_TOOLS } from "sciverse";

const openai = new OpenAI();
const sv = new AgentToolsClient();

const resp = await openai.chat.completions.create({
  model: "gpt-4o",
  tools: OPENAI_TOOLS as any,
  messages: [{ role: "user", content: "找 3 篇 Transformer 论文" }],
});
// ... 同理 dispatch tool_calls 到 sv.searchPapers / sv.semanticSearch / ...
```

`ANTHROPIC_TOOLS` 同样导出，用于 `@anthropic-ai/sdk`。

Claude Agent SDK / OpenAI Agents SDK 写法更简洁（agent loop 由框架处理），
详见 [`sciverse-mcp-server`](https://www.npmjs.com/package/sciverse-mcp-server)。

### 错误处理

非 2xx 响应抛 `new Error("Sciverse API <status>: <body>")`：

```ts
try {
  await c.searchPapers({ query: "x" });
} catch (e) {
  console.error(e);  // "Sciverse API 401: {...}"
}
```

| HTTP | 含义 |
|---|---|
| 400 | 请求参数错误（未知字段 / query 与 sort 冲突等） |
| 401 | Token 缺失 / 无效 / 用户被禁用 |
| 403 | 字段权限不足 |
| 429 | 用户级限流（60 请求 / 60 秒，受保护接口共享额度） |
| 502 | 上游 metadata-service 不可用 |

### 链接

- 源码仓库：<https://github.com/opendatalab/Sciverse-Agent-Tools>
- 变更日志：<https://github.com/opendatalab/Sciverse-Agent-Tools/blob/main/CHANGELOG.md>
- 控制台申请 Token：<https://sciverse.space>
- 协议：Apache-2.0

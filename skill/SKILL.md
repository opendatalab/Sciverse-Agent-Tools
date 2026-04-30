---
name: sciverse-agent-tools
version: 0.1.0
description: SciVerse 学术文献检索：按结构化条件查元数据、自然语言语义检索片段、按字节读取原文。适合需要权威学术文献支撑的 RAG 与 agent 工作流。
license: Apache-2.0
homepage: https://sciverse.space
---

# sciverse-agent-tools

SciVerse 学术文献检索：按结构化条件查元数据、自然语言语义检索片段、按字节读取原文。适合需要权威学术文献支撑的 RAG 与 agent 工作流。

## 触发条件

当用户问题涉及以下任一情形时启用本 skill：

- 需要查找学术文献（按作者、年份、期刊、学科等结构化条件）
- 需要文献片段支撑回答（RAG / 引用）
- 需要扩展某一文献的原文上下文（已有 doc_id，要更多字节）

## 鉴权

本 skill 需要环境变量 `SCIVERSE_API_TOKEN`（从 https://sciverse.space 控制台申请）。
可选 `SCIVERSE_BASE_URL` 覆盖默认 API base URL。

## 工具列表

### search_papers

按结构化条件检索学术文献元数据（标题、作者、期刊、年份、摘要等）。
适用：「查找 Hinton 在 2020-2023 年发表的论文」「找 Nature 上关于 CRISPR 的近期文献」。
不适用：自然语言问答检索 → 用 semantic_search；查全文片段 → 用 read_content。
返回：论文元数据列表，每条含 doc_id、title、authors、abstract、journal、year 等。

**调用**：`node scripts/search_papers.mjs '<JSON 入参>'`

### semantic_search

自然语言语义检索，返回相关文献片段（chunk）用于 RAG 回答。
适用：「Transformer 注意力机制如何工作？」「最新的蛋白质折叠预测方法有哪些？」
不适用：精确字段过滤 → search_papers；取完整原文 → read_content。
返回：相关 chunk 列表，每条含 chunk_id/doc_id/abstract/chunk/score/title/offset。
典型链路：semantic_search → 选取 chunk → read_content(doc_id, offset)。

**调用**：`node scripts/semantic_search.mjs '<JSON 入参>'`

### read_content

按字节区间读取文献原文片段。通常配合 semantic_search 返回的 doc_id/offset 使用，
用于扩展上下文（往前/往后读更多字节）。
返回：UTF-8 文本片段、bytes_returned、next_offset、是否还有后续。

**调用**：`node scripts/read_content.mjs '<JSON 入参>'`

## 协同链路

典型 RAG 链路：

```
semantic_search(query=...)
    └─▶ hits[i].doc_id, hits[i].offset
            └─▶ read_content(doc_id, offset)
```

结构化筛选 + 元数据查询：

```
search_papers(authors=[...], year_from=2020)
    └─▶ hits[].doc_id 列表
```

## 错误处理

- 退出码 0：成功，stdout 为 JSON 响应
- 退出码 1：HTTP 4xx/5xx，stderr 含 status 与响应体
- 退出码 2：参数错误（缺少 token、JSON 不合法、必填字段缺失）

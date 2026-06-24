# academic-retrieval — ClawHub skill bundle

[![ClawHub](https://img.shields.io/badge/clawhub-academic--retrieval-brightgreen)](https://clawhub.ai/academic-retrieval)

ClawHub skill that gives any OpenClaw agent Sciverse academic-paper retrieval
capabilities (English | [中文](#中文说明)).

Published by **@sciverse** (slug `academic-retrieval`).

## Install

```bash
openclaw skills install academic-retrieval
```

## Configure

```bash
export SCIVERSE_API_TOKEN=sv-xxx       # obtain from https://sciverse.space
```

## Tools at a glance

| Tool | Purpose |
|---|---|
| `list_catalog` | Field introspection (call once to learn available fields + enum values) |
| `search_papers` | Structured metadata search over papers / authors / sources (set `collection`) |
| `semantic_search` | Natural-language semantic chunk retrieval (for RAG) |
| `read_content` | Byte-range read of a paper's original text |
| `get_resource` | Fetch figure / table image bytes referenced inside `read_content` Markdown |

See `SKILL.md` for full agent-facing documentation.

## Direct invocation (bypass OpenClaw)

```bash
node scripts/semantic_search.mjs '{"query":"Transformer attention mechanism","top_k":3}'
```

## Relationship to the SDK

This skill is **complementary** to the `sciverse` packages on PyPI / npm:

- **This skill** — OpenClaw users only. Zero external deps (Node 18+ native fetch).
- **PyPI / npm SDK** — Any LLM agent framework (OpenAI, Anthropic, LangChain, LlamaIndex…).

## License

Apache-2.0

---

## 中文说明

OpenClaw 用户专用：通过 ClawHub 一键给 agent 加上 Sciverse 学术文献检索能力。

发布者 **@sciverse**，slug `academic-retrieval`。

### 安装

```bash
openclaw skills install academic-retrieval
```

### 配置

```bash
export SCIVERSE_API_TOKEN=sv-xxx   # 从 https://sciverse.space 控制台申请
# 可选：export SCIVERSE_BASE_URL=https://api-custom.sciverse.space
```

### 工具速览

| Tool | 用途 |
|---|---|
| `list_catalog` | 字段 introspection（首次接入调一次，学习可用字段和 enum 取值） |
| `search_papers` | 按结构化条件查 papers / authors / sources（用 `collection` 切换实体集合） |
| `semantic_search` | 自然语言语义检索文献片段（RAG 用） |
| `read_content` | 按字节区间读取文献原文片段 |
| `get_resource` | 取 `read_content` Markdown 中引用的图片字节流（多模态 RAG） |

agent 视角的完整文档见 `SKILL.md`（英文）。

### 直接调用（不通过 OpenClaw）

```bash
node scripts/semantic_search.mjs '{"query":"Transformer 注意力机制","top_k":3}'
```

### 与 SDK 的关系

本 skill 与 PyPI/npm 上的 `sciverse` 包是**互补**的：

- **本 skill**：OpenClaw 用户专用，零外部依赖（仅 Node 18+ native fetch）
- **PyPI/npm SDK**：任意 LLM Agent 框架（OpenAI / Anthropic / LangChain / LlamaIndex...）

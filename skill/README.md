# sciverse-agent-tools — ClawHub skill bundle

OpenClaw 用户专用：通过 ClawHub 一键给 agent 加上 SciVerse 学术文献检索能力。

## 安装

```bash
clawhub install sciverse-agent-tools
```

## 配置

```bash
export SCIVERSE_API_TOKEN=sv-xxx   # 从 https://sciverse.space 控制台申请
# 可选：export SCIVERSE_BASE_URL=https://sciverse-dev.opendatalab.org.cn/api
```

## 工具速览

| Tool | 用途 |
|---|---|
| `search_papers` | 按作者/年份/期刊/学科结构化检索文献元数据 |
| `semantic_search` | 自然语言语义检索文献片段（RAG 用） |
| `read_content` | 按字节区间读取文献原文片段 |

详见 `SKILL.md`。

## 直接调用（不通过 OpenClaw）

```bash
node scripts/semantic_search.mjs '{"query":"Transformer 注意力机制","top_k":3}'
```

## 与 SDK 的关系

本 skill 与 PyPI/npm 上的 `sciverse-agent-tools` 包是**互补**的：
- **本 skill**：OpenClaw 用户专用，零外部依赖（仅 Node 18+ native fetch）
- **PyPI/npm SDK**：任意 LLM Agent 框架（OpenAI / Anthropic / LangChain / LlamaIndex...）


## License

Apache-2.0

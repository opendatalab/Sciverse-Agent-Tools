# sciverse

[English](#english) | [中文](#中文)

SciVerse open-platform Python SDK + CLI for academic paper retrieval. Wraps
five retrieval tools (`search_papers`, `semantic_search`, `read_content`,
`list_catalog`, `get_resource`) behind one async client + ready-to-use
`OPENAI_TOOLS` / `ANTHROPIC_TOOLS` constants for direct tool-calling.

> 工具：`search_papers`（结构化元数据）/ `semantic_search`（语义检索）/ `read_content`（原文切片）/ `list_catalog`（字段 introspection）/ `get_resource`（论文图片二进制）

---

## English

### Install

```bash
pip install sciverse
# or, if you only want the CLI:
pipx install sciverse
```

### Configure once (no env vars needed afterwards)

```bash
sciverse auth login
# - opens https://sciverse.space/tokens in your browser
# - paste the token you create
# - saved to ~/.sciverse/credentials.json (file mode 0600)
```

After this any `AgentToolsClient()` without explicit args picks it up
automatically. Override hierarchy: explicit arg → `SCIVERSE_API_TOKEN` env →
credentials file → default.

### CLI

The `sciverse` command exposes both auth management and direct retrieval —
useful for shell pipelines and quick verification without writing Python.

```bash
# Auth
sciverse auth login [--token <t>] [--endpoint <url>] [--no-browser]
sciverse auth status                       # masked token / endpoint / saved_at
sciverse auth logout

# Retrieval (all output JSON to stdout, errors to stderr — pipe to jq freely)
sciverse search [QUERY] [--author NAME] [--year-from 2020] [--year-to 2024] \
                [--journal "Nature"] [--subject biology] [--title-contains attention] \
                [--sort-by-year desc|asc|none] [--page 1] [--page-size 10]
sciverse semantic-search QUERY [--top-k 10] [--mode fast|balanced|quality]
sciverse content DOC_ID [--offset 0] [--limit 4096]
sciverse catalog [--samples]               # field introspection
sciverse resource FILE_NAME [-o out.png]   # paper figure binary; omit -o → stdout
```

Examples:

```bash
# Find 3 Hinton papers from 2020+, pipe to jq for titles
sciverse search --author Hinton --year-from 2020 --page-size 3 | jq '.hits[].title'

# Semantic search, output top 5 hits
sciverse semantic-search "How does attention work?" --top-k 5

# Read 8KB from a specific paper
sciverse content p_xxx --offset 0 --limit 8192 | jq -r '.text'

# Discover field names + enum values
sciverse catalog --samples | jq '.fields[] | select(.sample_values | length > 0)'

# Save a figure
sciverse resource "dt=xxx/p_yyy/f3.png" -o /tmp/figure.png
```

### Quick start

```python
import asyncio
from sciverse import AgentToolsClient

async def main():
    async with AgentToolsClient() as c:  # token + endpoint auto-resolved
        r = await c.semantic_search(query="Transformer attention mechanism", top_k=3)
        for hit in r["hits"]:
            print(hit["doc_id"], hit["score"], hit["title"])

asyncio.run(main())
```

### Long-lived client (web server / agent runtime)

```python
client = AgentToolsClient()  # construct once at startup
try:
    while serving:
        r = await client.semantic_search(query=...)
        ...
finally:
    await client.aclose()    # release the underlying httpx connection pool
```

### Five retrieval tools

```python
# 1. Structured metadata search (Boolean filters + sort + pagination)
await c.search_papers(
    query="transformer",                # full-text BM25 (optional)
    authors=["Hinton"],
    year_from=2020, year_to=2024,
    journals=["Nature", "Science"],
    sort_by_year="desc",                # "desc" / "asc" / "none"
    page_size=10,
)

# 2. Natural-language semantic search (vector + BM25 hybrid, returns chunks)
await c.semantic_search(query="How does attention work?", top_k=10, mode="balanced")

# 3. Byte-range read of original paper text
#    (use doc_id + offset from semantic_search hits)
await c.read_content(doc_id="p_xxx", offset=0, limit=8192)

# 4. Schema introspection — call once to discover field names + enum values
await c.list_catalog(include_sample_values=True)

# 5. Fetch a paper figure / table image (when read_content Markdown contains
#    ![alt](file_name) placeholders)
bytes_, mime_type = await c.get_resource(file_name="dt=xxx/p_yyy/f3.png")
```

### Use with Anthropic / OpenAI tool-calling

The SDK exports ready-to-use tool schemas matching each provider's spec —
drop straight into `messages.create(tools=...)` or
`chat.completions.create(tools=...)`.

```python
from anthropic import Anthropic
from sciverse import ANTHROPIC_TOOLS, AgentToolsClient

anthropic = Anthropic()
async with AgentToolsClient() as sv:
    messages = [{"role": "user", "content": "Find 3 transformer papers"}]
    resp = anthropic.messages.create(
        model="claude-opus-4-7",
        max_tokens=4096,
        tools=ANTHROPIC_TOOLS,
        messages=messages,
    )
    # ... handle tool_use blocks by dispatching to sv.search_papers / ...
```

```python
from openai import OpenAI
from sciverse import OPENAI_TOOLS, AgentToolsClient

openai = OpenAI()
async with AgentToolsClient() as sv:
    resp = openai.chat.completions.create(
        model="gpt-4o",
        tools=OPENAI_TOOLS,
        messages=[{"role": "user", "content": "Find 3 transformer papers"}],
    )
    # ... handle tool_calls similarly
```

For Claude Agent SDK / OpenAI Agents SDK (agent loop handled by framework),
see [`sciverse-mcp-server`](https://www.npmjs.com/package/sciverse-mcp-server).

### Error handling

Non-2xx responses raise `httpx.HTTPStatusError`. Platform error body:
`{code, message, request_id}`.

```python
import httpx
try:
    await c.search_papers(query="x")
except httpx.HTTPStatusError as e:
    print(e.response.status_code, e.response.text)
```

| HTTP | Meaning |
|---|---|
| 400 | Bad request (unknown field, conflicting query+sort, ...) |
| 401 | Token missing / invalid / user disabled |
| 403 | Field permission denied |
| 429 | Rate limit (60 req / 60s per user, shared across protected endpoints) |
| 502 | Upstream metadata-service unavailable |

### Typed request models (optional)

```python
from sciverse.types import SearchPapersRequest, SemanticSearchRequest
# Pydantic v2 models — for explicit validation when constructing requests.
```

### Links

- Source repo: <https://github.com/opendatalab/Sciverse-Agent-Tools>
- Changelog: <https://github.com/opendatalab/Sciverse-Agent-Tools/blob/main/CHANGELOG.md>
- Console (get a token): <https://sciverse.space>
- License: Apache-2.0

---

## 中文

SciVerse 开放平台 Python SDK + CLI，提供 5 个学术文献检索 tool（结构化元数据、
语义检索、原文切片、字段 introspection、论文图片）。

### 安装

```bash
pip install sciverse
# 只想用 CLI 时：
pipx install sciverse
```

### 登录（只跑一次，后续 SDK 无需再传 token）

```bash
sciverse auth login
# - 浏览器打开 https://sciverse.space/tokens
# - 复制控制台生成的 token，粘贴回 CLI
# - 保存到 ~/.sciverse/credentials.json（文件权限 0600）
```

之后任何 `AgentToolsClient()` 不传 token 自动 fallback 读取。优先级：
显式参数 → `SCIVERSE_API_TOKEN` 环境变量 → 凭据文件 → 默认值。

### CLI

`sciverse` 命令既管理凭据，也直接调五个检索 API —— 适合 shell pipeline
和不写 Python 的快速验证。

```bash
# 凭据管理
sciverse auth login [--token <t>] [--endpoint <url>] [--no-browser]
sciverse auth status                       # 打码后的 token / endpoint / 保存时间
sciverse auth logout

# 直接调检索 API（JSON 到 stdout，错误到 stderr，可直接 | jq）
sciverse search [QUERY] [--author NAME] [--year-from 2020] [--year-to 2024] \
                [--journal "Nature"] [--subject biology] [--title-contains 注意力] \
                [--sort-by-year desc|asc|none] [--page 1] [--page-size 10]
sciverse semantic-search QUERY [--top-k 10] [--mode fast|balanced|quality]
sciverse content DOC_ID [--offset 0] [--limit 4096]
sciverse catalog [--samples]               # 字段 introspection
sciverse resource FILE_NAME [-o out.png]   # 论文图片二进制；不传 -o 写 stdout
```

例子：

```bash
# 找 Hinton 2020 年起的论文，提取标题
sciverse search --author Hinton --year-from 2020 --page-size 3 | jq '.hits[].title'

# 语义检索，取前 5 个 chunk
sciverse semantic-search "注意力机制如何工作?" --top-k 5

# 读 8KB 原文
sciverse content p_xxx --offset 0 --limit 8192 | jq -r '.text'

# 学 schema + 枚举字段
sciverse catalog --samples | jq '.fields[] | select(.sample_values | length > 0)'

# 保存图片到文件
sciverse resource "dt=xxx/p_yyy/f3.png" -o /tmp/figure.png
```

`--token` 用于 CI 脚本场景（跳过交互式粘贴）。`--no-browser` 适合远程 / 无桌面环境。

### 快速开始

```python
import asyncio
from sciverse import AgentToolsClient

async def main():
    async with AgentToolsClient() as c:  # token + endpoint 自动解析
        r = await c.semantic_search(query="Transformer 注意力机制", top_k=3)
        for hit in r["hits"]:
            print(hit["doc_id"], hit["score"], hit["title"])

asyncio.run(main())
```

### 长生命周期 client（web server / agent runtime 场景）

```python
client = AgentToolsClient()  # 启动时构造一次
try:
    while serving:
        r = await client.semantic_search(query=...)
        ...
finally:
    await client.aclose()    # 显式关闭底层 httpx 连接池
```

### 5 个检索 tool

```python
# 1. 结构化元数据查询（布尔过滤 + 排序 + 分页）
await c.search_papers(
    query="transformer",                # 全文 BM25（可选）
    authors=["Hinton"],
    year_from=2020, year_to=2024,
    journals=["Nature", "Science"],
    sort_by_year="desc",                # "desc" / "asc" / "none"
    page_size=10,
)

# 2. 自然语言语义检索（向量 + BM25 混合，返回 chunk）
await c.semantic_search(query="注意力机制如何工作？", top_k=10, mode="balanced")

# 3. 按字节区间读原文（配合 semantic_search 返回的 doc_id + offset 用）
await c.read_content(doc_id="p_xxx", offset=0, limit=8192)

# 4. 字段 introspection —— Agent 接入第一步先调一次拿 schema + 枚举值
await c.list_catalog(include_sample_values=True)

# 5. 取文献附属图片（当 read_content 的 Markdown 含 ![alt](file_name) 占位时）
bytes_, mime_type = await c.get_resource(file_name="dt=xxx/p_yyy/f3.png")
```

### 接入 Anthropic / OpenAI tool calling

SDK 内嵌了对应 provider 格式的 tool schema 常量，可直接喂给
`messages.create(tools=...)` / `chat.completions.create(tools=...)`：

```python
from anthropic import Anthropic
from sciverse import ANTHROPIC_TOOLS, AgentToolsClient

anthropic = Anthropic()
async with AgentToolsClient() as sv:
    messages = [{"role": "user", "content": "找 3 篇 Transformer 论文"}]
    resp = anthropic.messages.create(
        model="claude-opus-4-7",
        max_tokens=4096,
        tools=ANTHROPIC_TOOLS,
        messages=messages,
    )
    # ... 在 tool_use block 里分发到 sv.search_papers / sv.semantic_search / ...
```

```python
from openai import OpenAI
from sciverse import OPENAI_TOOLS, AgentToolsClient

openai = OpenAI()
async with AgentToolsClient() as sv:
    resp = openai.chat.completions.create(
        model="gpt-4o",
        tools=OPENAI_TOOLS,
        messages=[{"role": "user", "content": "找 3 篇 Transformer 论文"}],
    )
    # ... 同理 dispatch tool_calls
```

Claude Agent SDK / OpenAI Agents SDK 写起来更简单 —— 它们接受 MCP server 配置，
agent loop 全权处理。详见 [`sciverse-mcp-server`](https://www.npmjs.com/package/sciverse-mcp-server)。

### 错误处理

非 2xx 响应抛 `httpx.HTTPStatusError`。平台错误体格式 `{code, message, request_id}`：

```python
import httpx
try:
    await c.search_papers(query="x")
except httpx.HTTPStatusError as e:
    print(e.response.status_code, e.response.text)
```

| HTTP | 含义 |
|---|---|
| 400 | 请求参数错误（未知字段 / query 与 sort 冲突等） |
| 401 | Token 缺失 / 无效 / 用户被禁用 |
| 403 | 字段权限不足 |
| 429 | 用户级限流（60 请求 / 60 秒，受保护接口共享额度） |
| 502 | 上游 metadata-service 不可用 |

### 类型化请求构造（可选）

```python
from sciverse.types import SearchPapersRequest, SemanticSearchRequest
# Pydantic v2 模型，需要显式校验构造时用。
```

### 链接

- 源码仓库：<https://github.com/opendatalab/Sciverse-Agent-Tools>
- 变更日志：<https://github.com/opendatalab/Sciverse-Agent-Tools/blob/main/CHANGELOG.md>
- 控制台申请 Token：<https://sciverse.space>
- 协议：Apache-2.0

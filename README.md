# SciVerse Agent Tools

**English** | [简体中文](./README.zh-CN.md)

Standardized tool schemas and SDKs that expose SciVerse Open Platform retrieval capabilities to LLM agents.

| Tool | Use case |
|---|---|
| `search_papers` | Structured metadata search (author / year / journal / discipline) |
| `semantic_search` | Natural-language semantic search over passages (RAG) |
| `read_content` | Fetch a byte-range slice of the source document (extend RAG context) |

## 5-minute quickstart

### 1. Get a Bearer token

Sign in to the [SciVerse Developer Console](https://sciverse.space) and request an API token.

### 2. Install the SDK

```bash
# Python
pip install sciverse

# TypeScript / Node.js
npm install sciverse
```

### 3. Direct calls

**Python:**

```python
import asyncio
from sciverse import AgentToolsClient

async def main():
    async with AgentToolsClient(
        base_url="https://api.sciverse.space",
        token="<TOKEN>",
    ) as c:
        r = await c.semantic_search(query="Transformer attention mechanism")
        for hit in r["hits"][:3]:
            print(hit["title"], hit["score"])

asyncio.run(main())
```

**TypeScript:**

```ts
import { AgentToolsClient } from "sciverse";

const c = new AgentToolsClient({
  baseUrl: "https://api.sciverse.space",
  token: process.env.SCIVERSE_API_TOKEN!,
});

const r: any = await c.semanticSearch({ query: "Transformer attention mechanism" });
r.hits.slice(0, 3).forEach((h: any) => console.log(h.title, h.score));
```

### 4. Plug into an agent framework

**Anthropic Claude (Python):**

```python
from anthropic import Anthropic
from sciverse import ANTHROPIC_TOOLS

client = Anthropic()
msg = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=2048,
    tools=ANTHROPIC_TOOLS,
    messages=[{"role": "user", "content": "Find a few papers on Transformers"}]
)
```

**OpenAI (TypeScript):**

```ts
import OpenAI from "openai";
import { OPENAI_TOOLS } from "sciverse";

const openai = new OpenAI();
const resp = await openai.chat.completions.create({
  model: "gpt-4o",
  tools: OPENAI_TOOLS as any,
  messages: [{ role: "user", content: "Find a few Transformer papers" }],
});
```

End-to-end examples (including the tool-calling loop) live in [`examples/`](./examples/):

**Direct SDK use (you own the tool-calling loop):**

- `python_anthropic_rag.py` — Anthropic + a 3-tool RAG agent
- `python_openai_function_call.py` — OpenAI function calling
- `ts_openai.ts` — TypeScript + OpenAI
- `ts_langchain_agent.ts` — TypeScript + LangChain

**Agent SDKs (the SDK drives the agent loop, closer to coding-agent style):**

- `python_claude_agent_sdk.py` — Claude Agent SDK + the `sciverse-mcp-server` MCP server
- `ts_openai_agents.ts` — `@openai/agents` + the `sciverse-mcp-server` MCP server

## API at a glance

### Python SDK

```python
async with AgentToolsClient(base_url=..., token=...) as c:
    # 1. Structured search
    await c.search_papers(query=..., authors=[...], year_from=2020, page_size=10)
    # 2. Semantic search (mode: fast / balanced / quality)
    await c.semantic_search(query=..., top_k=10, mode="balanced")
    # 3. Read a byte range of the source content
    await c.read_content(doc_id=..., offset=0, limit=4096)
```

Return values are typed as `dict[str, Any]`. **The full response schema lives in [`openapi.yaml`](./openapi.yaml).**  
Advanced users can `from sciverse.types import SearchPapersRequest, ...` for typed construction and validation.

**Long-lived client** (e.g. a web server or agent runtime where the client outlives a single request):

```python
client = AgentToolsClient(base_url="https://api.sciverse.space", token=TOKEN)
try:
    # Reuse the client across many requests
    while serving:
        r = await client.semantic_search(query=...)
        ...
finally:
    await client.aclose()  # Explicitly close the underlying httpx connection pool
```

### TypeScript SDK

```ts
const c = new AgentToolsClient({ baseUrl, token });
await c.searchPapers({ query, authors, year_from, page_size });
await c.semanticSearch({ query, top_k, mode });
await c.readContent({ doc_id, offset, limit });
```

Return values are typed as `unknown` — cast them yourself:

```ts
import type { components } from "sciverse";
type SemanticSearchResp = components["schemas"]["SemanticSearchResponse"];
const r = await c.semanticSearch({ query: "x" }) as SemanticSearchResp;
```

## Error handling

**Python:** non-2xx responses raise `httpx.HTTPStatusError`:

```python
import httpx
try:
    await c.search_papers(query="x")
except httpx.HTTPStatusError as e:
    print(e.response.status_code, e.response.text)
```

**TypeScript:** non-2xx responses raise `Error("SciVerse API <status>: <body>")`:

```ts
try {
  await c.searchPapers({ query: "x" });
} catch (e) {
  console.error(e);  // "SciVerse API 401: {...}"
}
```

| HTTP status | Meaning |
|---|---|
| 401 | Token missing or invalid |
| 400 | Bad request parameters |
| 429 | Quota exceeded (production gateway only) |
| 502 / 503 | Upstream service unavailable |

## How the three tools compose

A typical RAG flow:

```
semantic_search(query="...")
    └─▶ hits[i].doc_id, hits[i].offset
            └─▶ read_content(doc_id, offset)  # fetch extended context
```

Filter + semantic hybrid:

```
search_papers(authors=[...], year_from=2020)  # narrow by structured filters first
    └─▶ list of hits[].doc_id
            └─▶ semantic_search(query="...")  # semantic search within the narrowed set
                                              # (SDK limitation: filter the second pass yourself)
```

## Versioning & changelog

See [CHANGELOG.md](./CHANGELOG.md). Versions are managed automatically by [semantic-release](https://semantic-release.gitbook.io/) based on [Conventional Commits](https://www.conventionalcommits.org/) — see [CONTRIBUTING.md](./CONTRIBUTING.md) for details.

## Development

```bash
uv sync
bash scripts/build.sh   # regenerate dist/ and packages/*/src/{tools,types}.{py,ts}
uv run pytest tests/    # generator unit tests
```

## OpenClaw users

One-line install via [ClawHub](https://clawhub.ai):

```bash
clawhub install sciverse
```

See [`clawhub/README.md`](./clawhub/README.md) for details.

## Claude Code users

SciVerse ships an official Claude Code Agent Skill (a parallel skill format to OpenClaw).

**Option 1: via the Plugin Marketplace (recommended)**

```bash
claude /plugin marketplace add https://github.com/opendatalab/Sciverse-Agent-Tools
claude /plugin install sciverse
```

**Option 2: manual install**

Copy the entire `skill-claude-code/` directory into one of Claude Code's skill load paths:

```bash
# User-level
cp -r skill-claude-code ~/.claude/skills/sciverse

# Or project-level
cp -r skill-claude-code .claude/skills/sciverse
```

**Pair with the MCP server**

The Claude Code skill depends on `sciverse-mcp-server` (maintained by a sibling agent). Install it first:

```bash
npm install -g sciverse-mcp-server
export SCIVERSE_API_TOKEN=sv-...
```

Or declare it in your project's `.mcp.json` — see `skill-claude-code/SKILL.md`.

## Other coding agents

Plug into mainstream coding agents through the [`sciverse-mcp-server`](./packages/mcp/) MCP server:

| Agent | Integration guide |
|---|---|
| Claude Code | [docs/integrations/claude-code.md](./docs/integrations/claude-code.md) |
| Cursor | [docs/integrations/cursor.md](./docs/integrations/cursor.md) |
| Codex CLI | [docs/integrations/codex-cli.md](./docs/integrations/codex-cli.md) |
| Windsurf | [docs/integrations/windsurf.md](./docs/integrations/windsurf.md) |

## License

Apache-2.0

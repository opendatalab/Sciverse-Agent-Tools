# Sciverse Agent Tools

**English** | [简体中文](./README.zh-CN.md)

**Sciverse Agent Tools** provides standardized tool schemas and SDKs that expose the [Sciverse Open Platform](https://sciverse.space) academic retrieval capabilities to LLM agents. 

With these tools, you can easily empower your AI agents to search for academic papers, perform natural language semantic retrieval (RAG), and fetch original literature contents and multimodal resources (like figures and tables).

| Tool | Use case |
|---|---|
| `list_catalog` | Discover available fields, filter operators, and enum sample values (per `collection`) |
| `search_papers` | Structured metadata search over papers / authors / sources (set `collection`) |
| `semantic_search` | Natural-language semantic search over passages (RAG) |
| `list_paper_relations` | Paginate a paper's full citations / references / related works (by `unique_id`) |
| `read_content` | Fetch a byte-range slice of the source document (extend RAG context) |
| `get_resource` | Fetch figure / table image bytes referenced inside `read_content` Markdown |

All six tools share the same Bearer-Token authentication and are exposed identically through the Python SDK, the TypeScript SDK, the MCP server, the Claude Code skill, and the ClawHub skill. The canonical schema is [`openapi.yaml`](./openapi.yaml).

## Pick your integration path

| Path | Best for | Setup |
|---|---|---|
| **Skills CLI** | Projects using the generic Skills CLI | `npx skills add https://sciverse.space` |
| **Claude Code skill** | Anyone using Claude Code / VS Code | One-line install via Plugin Marketplace (below) |
| **MCP server** | Any MCP-capable coding agent (Cursor, Codex CLI, Windsurf, …) | Add to `.mcp.json` — [integration guides](./docs/integrations/) |
| **Python / TypeScript SDK** | Custom agents (OpenAI / Anthropic / LangChain / LlamaIndex / …) | `pip install sciverse` or `npm install sciverse` |
| **CLI** | Shell scripts, quick exploration, no agent loop | Comes with the Python SDK — `sciverse auth login` |
| **Web well-known URL** | Agent hosts that auto-discover skills via the well-known URI convention | Point your agent host at <https://sciverse.space/.well-known/agent-skills/> |

## Quickstart — Skills CLI

The easiest way to install the skill for projects supporting the Skills CLI is via the `npx skills` command:

```bash
npx skills add https://sciverse.space
```

This command automatically fetches the skill manifest and registers the tool for your project. Don't forget to configure your API token via the `SCIVERSE_API_TOKEN` environment variable.

## Quickstart — Claude Code

```bash
claude /plugin marketplace add https://github.com/opendatalab/Sciverse-Agent-Tools
claude /plugin install sciverse
```

The skill depends on `sciverse-mcp-server`; install it once:

```bash
npm install -g sciverse-mcp-server
export SCIVERSE_API_TOKEN=sv-...     # get one from https://sciverse.space
```

Or declare the MCP server per-project — see [`skill-claude-code/SKILL.md`](./skill-claude-code/SKILL.md).

## Quickstart — other MCP-capable agents

Drop this snippet into your agent's MCP config (`.mcp.json` for Claude Code / Cursor, `~/.codex/config.toml` for Codex CLI, etc.):

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

Per-agent step-by-step guides:

| Agent | Guide |
|---|---|
| Claude Code | [docs/integrations/claude-code.md](./docs/integrations/claude-code.md) |
| Cursor | [docs/integrations/cursor.md](./docs/integrations/cursor.md) |
| Codex CLI | [docs/integrations/codex-cli.md](./docs/integrations/codex-cli.md) |
| Windsurf | [docs/integrations/windsurf.md](./docs/integrations/windsurf.md) |

## Quickstart — agent host via well-known URL

For agent hosts that auto-discover skills via the
[well-known URI convention](https://en.wikipedia.org/wiki/Well-known_URI),
Sciverse serves the skill bundle at:

```
https://sciverse.space/.well-known/agent-skills/index.json
```

The endpoint returns a manifest listing the `sciverse` skill and its files
(`SKILL.md`, references, agent adapter configs, runnable scripts). Hosts that
follow the convention fetch the manifest, then materialise the skill locally
for the model to invoke.

Use this channel when:

- Your agent host already supports `.well-known/agent-skills/` discovery
- You want the latest skill version automatically (no version pinning on the consumer side)
- You don't want to clone a git repo just to obtain the skill

For host-specific install commands (Claude Code, MCP, OpenClaw, ClawHub), see
the other Quickstart sections above.

## Quickstart — SDK

### 1. Get a Bearer token

Sign in to the [Sciverse Developer Console](https://sciverse.space) and create an API token.

### 2. Install the SDK

The official and correct package name for both pip and npm is **`sciverse`**.

```bash
# Python
pip install sciverse

# TypeScript / Node.js
npm install sciverse
```

### 3. Configure credentials (any one of the three)

```bash
# A. Environment variable (recommended for servers / CI)
export SCIVERSE_API_TOKEN=sv-...

# B. Persisted credentials file (recommended for local dev — ~/.sciverse/credentials.json, 0600)
sciverse auth login

# C. Pass token explicitly to the client (recommended only when secrets come from a vault)
```

Resolution order: explicit argument → `SCIVERSE_API_TOKEN` env → `~/.sciverse/credentials.json`.

### 4. Call the SDK

**Python:**

```python
import asyncio
from sciverse import AgentToolsClient

async def main():
    # token / base_url omitted — resolved from env or credentials file
    async with AgentToolsClient() as c:
        r = await c.semantic_search(query="Transformer attention mechanism")
        for hit in r["hits"][:3]:
            print(hit["title"], hit["score"])

asyncio.run(main())
```

**TypeScript:**

```ts
import { AgentToolsClient } from "sciverse";

const c = new AgentToolsClient();  // reads SCIVERSE_API_TOKEN from env
const r: any = await c.semanticSearch({ query: "Transformer attention mechanism" });
r.hits.slice(0, 3).forEach((h: any) => console.log(h.title, h.score));
```

### 5. Plug into an agent framework

**Anthropic Claude (Python):**

```python
from anthropic import Anthropic
from sciverse import ANTHROPIC_TOOLS

client = Anthropic()
msg = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=2048,
    tools=ANTHROPIC_TOOLS,   # all 6 tool schemas
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

**LangChain (Python):**

`dist/langchain_tools.py` ships `BaseTool` subclasses generated from the same OpenAPI
spec. Bind them to an `AgentToolsClient` with `build_tools` — the client carries the
credentials and translates arguments the raw endpoints do not accept (`mode`, for one,
is ignored upstream, so a hand-rolled HTTP call makes `quality` behave like `balanced`).

```python
from langchain_tools import build_tools   # from dist/langchain_tools.py
from sciverse import AgentToolsClient

async with AgentToolsClient() as client:
    tools = build_tools(client)           # all 6 tools, bound
    hits = await tools[1].ainvoke({"query": "Transformer attention", "mode": "quality"})
```

The tools are async-only: drive them with `ainvoke()` or an async agent executor.

End-to-end examples (full tool-calling loop) live in [`examples/`](./examples/):

**Direct SDK use (you own the tool-calling loop):**

- `python_anthropic_rag.py` — Anthropic + 5-tool RAG agent
- `python_openai_function_call.py` — OpenAI function calling
- `ts_openai.ts` — TypeScript + OpenAI
- `ts_langchain_agent.ts` — TypeScript + LangChain

**Agent SDKs (the SDK drives the agent loop, closer to coding-agent style):**

- `python_claude_agent_sdk.py` — Claude Agent SDK + `sciverse-mcp-server`
- `ts_openai_agents.ts` — `@openai/agents` + `sciverse-mcp-server`

## CLI

The `sciverse` Python package ships with a CLI:

```bash
sciverse auth login                                  # paste token, saved to ~/.sciverse/credentials.json
sciverse auth status                                 # show resolved token source + endpoint
sciverse auth logout                                 # delete credentials file

sciverse catalog --samples                           # list_catalog with enum samples
sciverse search --author Hinton --year-from 2020     # search_papers
sciverse semantic-search "attention mechanism"       # semantic_search
sciverse paper-relations <unique_id> --relation CITATIONS   # list_paper_relations
sciverse content <doc_id> --offset 0 --limit 4096    # read_content
sciverse resource <file_name> -o figure.png          # get_resource (binary → file)
```

JSON goes to stdout (pipe through `| jq`), errors to stderr.

## API at a glance

### Python SDK

```python
async with AgentToolsClient() as c:           # token from env / credentials file
    # 1. Field discovery — call once when first integrating
    await c.list_catalog(include_sample_values=True)
    # 2. Structured search
    await c.search_papers(query=..., authors=[...], year_from=2020, page_size=10)
    # 3. Semantic search (mode: fast / balanced / quality)
    await c.semantic_search(query=..., top_k=10, mode="balanced")
    # 4. A paper's full citations / references / related works
    await c.list_paper_relations(unique_id=..., relation="CITATIONS", page_size=25)
    # 5. Byte-range read of original content
    await c.read_content(doc_id=..., offset=0, limit=4096)
    # 6. Figure / table image bytes (multimodal RAG)
    img_bytes, mime = await c.get_resource(file_name="dt=.../p_.../f3.png")
```

Return values are typed as `dict[str, Any]`. **The full response schema lives in [`openapi.yaml`](./openapi.yaml).**
Advanced users can `from sciverse.types import SearchPapersRequest, ...` for typed construction and validation.

**Long-lived client** (web server, agent runtime — outlives a single request):

```python
client = AgentToolsClient()
try:
    while serving:
        r = await client.semantic_search(query=...)
        ...
finally:
    await client.aclose()   # close underlying httpx connection pool
```

### TypeScript SDK

```ts
const c = new AgentToolsClient();   // token from env
await c.listCatalog({ include_sample_values: true });
await c.searchPapers({ query, authors, year_from, page_size });
await c.semanticSearch({ query, top_k, mode });
await c.listPaperRelations({ unique_id, relation: "CITATIONS", page_size: 25 });
await c.readContent({ doc_id, offset, limit });
const { bytes, mimeType } = await c.getResource({ file_name });
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

**TypeScript:** non-2xx responses raise `Error("Sciverse API <status>: <body>")`:

```ts
try {
  await c.searchPapers({ query: "x" });
} catch (e) {
  console.error(e);  // "Sciverse API 401: {...}"
}
```

| HTTP status | Meaning |
|---|---|
| 401 | Token missing or invalid |
| 400 | Bad request parameters (e.g. unknown filter field — call `list_catalog` to discover valid fields) |
| 429 | Quota / rate limit exceeded (production gateway only) |
| 502 / 503 | Upstream service unavailable |

## How the six tools compose

**1. Natural-language RAG (the common case):**

```
semantic_search(query="...")
    └─▶ for each hit: read_content(doc_id, offset, limit=8192)
            └─▶ cite doc_id + title in the answer
```

**2. Bootstrap then filter precisely:**

```
list_catalog(include_sample_values=true)         # first time only — learn fields + enum values
    └─▶ search_papers(filters_advanced=[...])    # construct precise filters
```

> Each `search_papers` hit carries **`is_content_accessible`** (bool): `true` only when the paper has fulltext **and** you're authorized — check it before `read_content(doc_id, …)`. Filterable fields keep growing (topic hierarchy, MeSH, identifier lookups, …); call `list_catalog` for the authoritative field list instead of hardcoding.

**3. Structured pre-filter + semantic refine (hybrid):**

```
search_papers(authors=[...], year_from=2020)     # narrow by structured filters first
    └─▶ list of hits[].doc_id
            └─▶ semantic_search(query="...")     # semantic search within the narrowed set
                                                 # (filter the second pass yourself —
                                                 #  semantic_search has no doc_id whitelist)
```

**4. Multimodal RAG with figures:**

```
semantic_search(query="...")
    └─▶ read_content(doc_id, offset) returns Markdown containing ![Fig 3](dt=xxx/p_yyy/f3.png)
            └─▶ get_resource(file_name="dt=xxx/p_yyy/f3.png")
                    └─▶ image bytes + mime type — feed directly to a multimodal model
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

## License

Apache-2.0

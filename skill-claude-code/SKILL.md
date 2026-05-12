---
name: sciverse
description: Use when the user needs academic paper retrieval — searching scientific literature by author/year/journal, finding paper chunks for RAG-style citations, or expanding original text around a known paper offset. Provides three SciVerse tools (search_papers, semantic_search, read_content) via the @sciverse/mcp-server MCP server.
---

# SciVerse — Academic Paper Retrieval

Retrieval skill for the SciVerse open platform. Exposes three tools
for working with scientific literature: structured metadata search,
semantic chunk retrieval for RAG, and byte-range content reading.

## When to use

Trigger this skill when the user's request involves any of:

- Locating academic papers by structured criteria (authors, year, journal, subjects)
- Grounding an answer in paper excerpts (RAG / citations)
- Expanding the original text around a known doc_id (more bytes before/after a chunk)

Do NOT use this skill for general web search, news, or non-scientific content —
the underlying index only covers peer-reviewed and preprint scientific literature.

## Prerequisites

This skill is a thin wrapper around the `@sciverse/mcp-server` MCP server.
Before invoking any tool, ensure the server is reachable:

1. Install the MCP server:

   ```bash
   npm install -g @sciverse/mcp-server
   ```

   Or add it to your project `.mcp.json`:

   ```json
   {
     "mcpServers": {
       "sciverse": {
         "command": "npx",
         "args": ["-y", "@sciverse/mcp-server"],
         "env": { "SCIVERSE_API_TOKEN": "${SCIVERSE_API_TOKEN}" }
       }
     }
   }
   ```

2. Obtain an API token from https://sciverse.space and export it:

   ```bash
   export SCIVERSE_API_TOKEN=sv-...
   ```

Optional: set `SCIVERSE_BASE_URL` to override the default API base URL
(for dev / self-hosted gateways; must remain on `*.sciverse.space`).

## Tools

All three tools are exposed by the MCP server. Claude Code will surface
them automatically when this skill is active.

### search_papers

Search academic papers by structured filters (title, authors, journal,
year, subjects, etc.).
Use when: "find Hinton's papers from 2020-2023", "Nature papers on
CRISPR".
Not for: natural-language Q&A retrieval (use semantic_search) or
full-text snippets (use read_content).
Returns: list of papers; each entry has doc_id, title, author, abstract,
publication_venue_name, publication_published_year.

### semantic_search

Natural-language semantic search returning relevant paper chunks for
RAG-style answering.
Use when: "How does Transformer attention work?", "What are recent
methods for protein structure prediction?".
Not for: precise field filtering (use search_papers) or fetching full
original text (use read_content).
Returns: list of chunks; each entry has chunk_id, doc_id, abstract,
chunk, score, title, offset.
Typical chain: semantic_search → pick chunk → read_content(doc_id,
offset).

### read_content

Read a UTF-8 byte range of a paper's original text. Typically used with
a doc_id/offset returned by semantic_search to expand context (read
more bytes before or after a chunk).
Returns: text fragment, bytes_returned, next_offset, more (boolean).

## Composition patterns

Typical RAG flow (semantic chunk → expand original text):

```
semantic_search(query=...)
    └─▶ hits[i].doc_id, hits[i].offset
            └─▶ read_content(doc_id, offset)
```

Structured filter (narrow down by author/year/journal):

```
search_papers(authors=[...], year_from=2020, journals=[...])
    └─▶ list of hits[].doc_id, hits[].abstract
```

Combined (structured pre-filter then semantic refine):

```
search_papers(authors=[...], year_from=2020)   # narrow universe
    └─▶ doc_ids → user-side filter on semantic_search hits
```

## Notes for Claude

- Always cite `doc_id` and `title` when surfacing paper-based facts to the user.
- Prefer `semantic_search` for natural-language questions; only fall back to
  `search_papers` when the user provides structured criteria (specific author,
  year range, journal).
- When a `semantic_search` hit looks promising but the chunk is truncated,
  use `read_content(doc_id, offset)` to expand context before answering.
- The platform returns at most 30 hits per `semantic_search` and 50 per
  `search_papers` page; paginate via `page` if the user wants more.

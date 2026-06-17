---
name: sciverse
description: Use when the user needs academic paper retrieval — searching scientific literature by author/year/journal, finding paper chunks for RAG-style citations, or expanding original text around a known paper offset. Provides three Sciverse tools (search_papers, semantic_search, read_content) via the sciverse-mcp-server MCP server.
---

# Sciverse — Academic Paper Retrieval

Retrieval skill for the Sciverse open platform. Exposes five tools
for working with scientific literature: field introspection,
structured metadata search, semantic chunk retrieval for RAG,
byte-range content reading, and figure / table image fetching.

## When to use

Trigger this skill when the user's request involves any of:

- Locating academic papers by structured criteria (authors, year, journal, subjects)
- Grounding an answer in paper excerpts (RAG / citations)
- Expanding the original text around a known doc_id (more bytes before/after a chunk)

Do NOT use this skill for general web search, news, or non-scientific content —
the underlying index only covers peer-reviewed and preprint scientific literature.

## Prerequisites

This skill is a thin wrapper around the `sciverse-mcp-server` MCP server.
Before invoking any tool, ensure the server is reachable:

1. Install the MCP server:

   ```bash
   npm install -g sciverse-mcp-server
   ```

   Or add it to your project `.mcp.json`:

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

2. Obtain an API token from https://sciverse.space and export it:

   ```bash
   export SCIVERSE_API_TOKEN=sv-...
   ```

Optional: set `SCIVERSE_BASE_URL` to override the default API base URL
(for dev / self-hosted gateways; must remain on `*.sciverse.space`).

## Tools

All five tools are exposed by the MCP server. Claude Code will surface
them automatically when this skill is active.

### search_papers

Search academic papers by structured filters (title, authors, journal,
year, subjects, etc.).
Use when: "find Hinton's papers from 2020-2023", "Nature papers on
CRISPR".
Not for: natural-language Q&A retrieval (use semantic_search) or
full-text snippets (use read_content).
Returns: list of papers; each entry has unique_id (always present),
doc_id (only when full text exists), title, author, abstract,
publication_venue_name_unified, publication_published_year.

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

### list_catalog

Returns the schema catalog for search_papers: every field name, type,
whether it's filterable / sortable, default-return status, human
description, and applicable FilterOperators.
Use when: "Which field do I filter by DOI?", "What values can
access_oa_status take?", "What's the right enum for metadata_type?".
Not for: actually searching papers (use search_papers / semantic_search).
Typical pattern: call once when first encountering Sciverse or facing
an ambiguous field need, then construct precise search_papers filters
from the returned schema.
Pass include_sample_values=true to also fetch top-20 values for
enum-like fields (OpenSearch terms aggregation, 24h cached).

### list_paper_relations

Paginate the full relation list of a paper. citations/references/related_works
are unbounded arrays (a highly-cited paper can have thousands); search_papers
only inlines a truncated few, so use this endpoint for the full list.
Use when: "What does paper X cite?" (relation=REFERENCES), "Which papers cite
paper X?" (relation=CITATIONS), "Works related to paper X" (relation=RELATED_WORKS).
Note: CITATIONS (incoming: who cites me) and REFERENCES (outgoing: who I cite)
are opposite directions.
Typical chain: get unique_id from search_papers / semantic_search, then paginate
here by relation.

### read_content

Read a UTF-8 byte range of a paper's original text. Typically used with
a doc_id/offset returned by semantic_search to expand context (read
more bytes before or after a chunk).
Returns: text fragment, bytes_returned, next_offset, more (boolean).

### get_resource

Returns the binary bytes of a paper figure / table image referenced
inside read_content's Markdown via `![alt](file_name)` placeholders.
Use when the user asks to see / display / describe a figure and
read_content output contains an image reference.
Input file_name comes from the Markdown URL part (relative path,
no `\\` or `..`).
Returns: raw image stream + image/* Content-Type. The SDK / MCP
server wraps the bytes as base64 + mimeType so Claude (multimodal)
can read the image directly.

## Bootstrap: learn the schema first

If you don't yet know which fields exist or what values they take
(e.g. "is `oa_status` a field?", "what does `metadata_type` accept?"),
call `list_catalog` once at the start of the conversation. The result
includes every field name, type, filterability, default-return status,
and — for enum-like fields — sample values. Cache the catalog in your
working memory; subsequent `search_papers` filters become precise
instead of guessed.

```
list_catalog(include_sample_values=true)
    └─▶ fields[].name + sample_values  →  pick the right filter field
```

## Recipes

**1. Natural-language RAG (most common):**

```
semantic_search(query="How does Transformer attention work?", top_k=5)
    └─▶ for each hit: read_content(doc_id, offset, limit=8192)
    └─▶ cite doc_id + title in the answer
```

**2. Look up a paper by DOI / doc_id:**

```
search_papers(filters_advanced=[
    {field: "doi", operator: "FILTER_OP_EQ", value: "10.1038/..."}
])
```

**3. Find OA papers in a year range:**

```
search_papers(
    filters_advanced=[
        {field: "access_is_oa", value: "true"},
        {field: "access_oa_status", operator: "FILTER_OP_IN",
         value: ["gold", "green", "hybrid"]}
    ],
    year_from=2024
)
```

**4. Filter by language / metadata_type (enum fields):**

```
# First check the enum: list_catalog(include_sample_values=true)
# Then filter precisely:
search_papers(
    query="transformer",
    filters_advanced=[
        {field: "language", value: "en"},
        {field: "metadata_type", value: "paper"}
    ]
)
```

**5. Structured pre-filter + semantic refine (hybrid):**

```
search_papers(authors=["Hinton"], year_from=2020, page_size=50)
    └─▶ collect hits[].doc_id list
semantic_search(query="attention", top_k=20)
    └─▶ filter hits to those whose doc_id appears in step-1 list
```

**6. Bias fuzzy search toward recent work (freshness boost):**

Set `freshness_boost` to weight results by publication date with gauss
decay over `publication_published_date`. Only effective when `query`
is non-empty; mutually exclusive with `sort_by_year`.

```
search_papers(query="large language model", freshness_boost="STRONG")
    # STRONG: 3-year decay, for tracking research directions
search_papers(query="protein folding", freshness_boost="MILD")
    # MILD:   10-year decay, for everyday literature search
```

**7. Show a figure / image from the paper:**

When `read_content` Markdown contains `![alt](file_name)` placeholders
and the user wants to see the figure (e.g. "show me Figure 3"),
fetch the binary with `get_resource`. The MCP server wraps the bytes
as a base64 image content block so Claude can read it directly.

```
read_content(doc_id, offset) → markdown with ![Figure 3](dt=xxx/p_yyy/f3.png)
    └─▶ get_resource(file_name="dt=xxx/p_yyy/f3.png")
    └─▶ Claude sees the image inline
```

## Notes for Claude

- **Always cite** `doc_id` and `title` when surfacing paper-based facts.
- **Prefer `semantic_search`** for natural-language questions; only fall back
  to `search_papers` when the user provides structured criteria.
- **When stuck on a field name**: call `list_catalog` instead of guessing.
  Field name typos return 400 with a clear message, but waste a turn.
- **When a chunk looks promising but truncated**: `read_content(doc_id, offset)`
  to expand. `read_content` returns `more: true` when more bytes are available.
- **Pagination**: max 30 hits per `semantic_search`, max 50 per `search_papers`
  page; use `page` to paginate.

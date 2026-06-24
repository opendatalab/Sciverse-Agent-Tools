---
name: sciverse-academic-retrieval
slug: academic-retrieval
version: 0.8.1
description: Sciverse academic paper retrieval: structured metadata search, semantic chunk retrieval for RAG, and byte-range content reading. For agent workflows that need citation-grade scientific literature.
license: Apache-2.0
homepage: https://sciverse.space
---

# academic-retrieval

Sciverse academic paper retrieval: structured metadata search, semantic chunk retrieval for RAG, and byte-range content reading. For agent workflows that need citation-grade scientific literature.

## When to use

Trigger this skill when the user's request involves any of:

- Locating academic papers by structured criteria (authors, year, journal, subjects)
- Grounding answers in paper excerpts (RAG / citations)
- Expanding the original text around a known doc_id (more bytes before/after a chunk)

## Authentication

This skill requires the `SCIVERSE_API_TOKEN` environment variable
(obtain from https://sciverse.space). Optionally set `SCIVERSE_BASE_URL`
to override the default API base URL.

## Tools

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

**Invoke**: `node scripts/search_papers.mjs '<JSON args>'`

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

**Invoke**: `node scripts/semantic_search.mjs '<JSON args>'`

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

**Invoke**: `node scripts/list_catalog.mjs '<JSON args>'`

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

**Invoke**: `node scripts/list_paper_relations.mjs '<JSON args>'`

### read_content

Read a UTF-8 byte range of a paper's original text. Typically used with
a doc_id/offset returned by semantic_search to expand context (read
more bytes before or after a chunk).
Returns: text fragment, bytes_returned, next_offset, more (boolean).

**Invoke**: `node scripts/read_content.mjs '<JSON args>'`

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

**Invoke**: `node scripts/get_resource.mjs '<JSON args>'`

## Bootstrap: learn the schema first

If you're unsure which fields exist or what values an enum takes
(e.g. `metadata_type`, `language`, `access_oa_status`), call
`list_catalog` once at the start. Sample values are returned for
low-cardinality fields. Use it instead of guessing field names —
guessing wastes turns.

```
list_catalog(include_sample_values=true)
    └─▶ fields[].name + sample_values  →  precise filter construction
```

## Recipes

**RAG flow (natural-language Q&A):**

```
semantic_search(query=...) → hits[i].doc_id, hits[i].offset
    └─▶ read_content(doc_id, offset)
```

**Lookup by DOI:**

```
search_papers(filters_advanced=[{field: "doi", value: "10.1038/..."}])
```

**OA + year filter:**

```
search_papers(
    year_from=2024,
    filters_advanced=[{field: "access_is_oa", value: "true"}]
)
```

**Structured + semantic hybrid:**

```
search_papers(authors=[...], year_from=2020) → doc_ids
semantic_search(query=...) → filter hits client-side by doc_ids
```

**Bias fuzzy search toward recent work (freshness boost):**

Set `freshness_boost` to weight results by publication date with
gauss decay. Only effective when `query` is non-empty; mutually
exclusive with `sort_by_year`.

```
search_papers(query="large language model", freshness_boost="STRONG")
    # STRONG: 3-year decay, for tracking research directions
search_papers(query="protein folding", freshness_boost="MILD")
    # MILD:   10-year decay, for everyday literature search
```

**Search authors or journals (collection):**

Set `collection` to `authors` or `sources` (default `papers`) to search
those entities. Each has its own fields — call
list_catalog(collection="authors") first; use filters_advanced +
sort_advanced (papers convenience fields apply to papers only).

```
search_papers(collection="authors",
    filters_advanced=[{field: "summary_stats.h_index", operator: "FILTER_OP_GTE", value: 50}],
    sort_advanced=[{field: "cited_by_count", order: "SORT_ORDER_DESC"}])
```

**Fetch a paper figure / image:**

When read_content Markdown contains `![alt](file_name)`, call
`get_resource` with the file_name to fetch image binary.

```
read_content(doc_id, offset) → markdown ![Figure 3](dt=xxx/p/f3.png)
    └─▶ get_resource(file_name="dt=xxx/p/f3.png")
```

## Exit codes

- `0` — success; stdout is the JSON response
- `1` — HTTP 4xx/5xx; stderr contains status code and response body
- `2` — argument error (missing token, malformed JSON, required field absent)

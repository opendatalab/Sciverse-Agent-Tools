---
name: sciverse-academic-retrieval
slug: academic-retrieval
version: 1.0.0
description: Sciverse academic paper retrieval: metadata search across papers, authors, sources and patents, semantic chunk retrieval for RAG, and character-range content reading (offsets in Unicode code points). For agent workflows that need citation-grade scientific literature.
license: Apache-2.0
homepage: https://sciverse.space
---

# academic-retrieval

Sciverse academic paper retrieval: metadata search across papers, authors, sources and patents, semantic chunk retrieval for RAG, and character-range content reading (offsets in Unicode code points). For agent workflows that need citation-grade scientific literature.

## When to use

Trigger this skill when the user's request involves any of:

- Locating academic papers by structured criteria (authors, year, journal, subjects)
- Grounding answers in paper excerpts (RAG / citations)
- Expanding the original text around a known doc_id (more text before/after a chunk)

## Authentication

This skill requires the `SCIVERSE_API_TOKEN` environment variable
(obtain from https://sciverse.space). Optionally set `SCIVERSE_BASE_URL`
to override the default API base URL.

## Tools

### search_metadata

Search metadata in one collection: papers, patents, authors or sources. Use list_catalog to discover authorized fields before choosing filters, sort and fields. Supports keywords, cursor pagination and facets; no implicit field sorting. Returns results, total_count and next_cursor with collection-specific fields. Use read_content for paper/patent text and semantic_search for paper semantic retrieval. Author/source IDs cannot be used to read content.

**Invoke**: `node scripts/search_metadata.mjs '<JSON args>'`

### semantic_search

Natural-language semantic search returning relevant paper chunks for
RAG-style answering.
Use when: "How does Transformer attention work?", "What are recent
methods for protein structure prediction?".
Not for: precise field filtering (use search_metadata) or fetching full
original text (use read_content).
Returns: list of chunks; each entry has chunk_id, doc_id, abstract,
chunk, score, title, offset.
Typical chain: semantic_search → pick chunk → read_content(doc_id,
offset).

**Invoke**: `node scripts/semantic_search.mjs '<JSON args>'`

### list_catalog

Returns the schema catalog for search_metadata: every field name, type,
whether it's filterable / sortable, default-return status, human
description, and applicable FilterOperators.
Use when: "Which field do I filter by DOI?", "What values can
access_oa_status take?", "What's the right enum for metadata_type?".
Not for: actually searching papers (use search_metadata / semantic_search).
Typical pattern: call once when first encountering Sciverse or facing
an ambiguous field need, then construct precise search_metadata filters
from the returned schema.
Pass include_sample_values=true to also fetch top-20 values for
enum-like fields (OpenSearch terms aggregation, 24h cached).

**Invoke**: `node scripts/list_catalog.mjs '<JSON args>'`

### list_paper_relations

Paginate the full relation list of a paper. citations/references/related_works
are unbounded arrays (up to 340k entries for a single paper) and are NOT
projectable in search_metadata, so this endpoint is the only way to read them.
Use when: "What does paper X cite?" (relation=REFERENCES), "Which papers cite
paper X?" (relation=CITATIONS), "Works related to paper X" (relation=RELATED_WORKS).
Note: CITATIONS (incoming: who cites me) and REFERENCES (outgoing: who I cite)
are opposite directions.
Typical chain: get unique_id from search_metadata / semantic_search, then paginate
here by relation.
Two limits (CITATIONS only; REFERENCES/RELATED_WORKS max out at 11833/20 in practice):
more than 10000 relations returns 429; page*page_size above 10000 returns 400.
In both cases switch to search_metadata with filters on
references_unique_id — it supports deep paging and arbitrary sorting.
total_count counts in-corpus matches only, so it can differ from the paper's own
citation_count by about 1%.

**Invoke**: `node scripts/list_paper_relations.mjs '<JSON args>'`

### read_content

Read a range of a paper or patent’s original text addressed in Unicode code
points (offset/limit count characters like Python len(), not bytes).
Typically used with a doc_id/offset returned by semantic_search to
expand context (read more text before or after a chunk).
Returns: text fragment, bytes_returned (UTF-8 byte length of text, for
reference only), next_offset (code-point offset of the next fragment —
page with it, never with bytes_returned), more (boolean).
Server behaviour: limit above 524288 is silently clamped; omitting
offset returns the whole document ignoring limit — the SDKs / MCP
server send offset=0 and limit=4096 by default, so pass offset
explicitly when calling the HTTP API directly.

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

`search_metadata` uses canonical `filters` / `sort`; no convenience parameters.
`semantic_search` remains paper-only. `read_content` supports papers/patents
(default papers), offset=0 and limit=4096. Pass patents explicitly for patent text.
`get_resource` primarily fetches paper images; ZIP downloads are not supported.
MCP: set SCIVERSE_ENABLE_LEGACY_TOOLS=true and restart to restore the legacy tool list.

## Recipes

**RAG flow (natural-language Q&A):**

```
semantic_search(query=...) → hits[i].doc_id, hits[i].offset
    └─▶ read_content(doc_id, offset)
```

**Lookup by DOI:**

```
search_metadata(filters=[{field: "doi", operator: "FILTER_OP_EQ", value: "10.1038/..."}])
```

**OA + year filter:**

```
search_metadata(
    filters=[{field: "publication_published_year", operator: "FILTER_OP_GTE", value: 2024}, {field: "access_is_oa", operator: "FILTER_OP_EQ", value: true}]
)
```

**Scoped semantic search (constrained corpus):**

```
semantic_search(
    query="...",
    filters={"author": ["Hinton"],
             "publication_published_year": {"gte": 2020}}
)   # applied at recall time, server-side; AND across fields
```

Soft semantics: chunks missing that metadata are NOT excluded.
For a hard guarantee, or meta-only constraints (fwci, citation graph,
complex hit-sets), scope by doc_id — a HARD recall-time filter:

```
search_metadata(..., fields=["doc_id","title"]) → collect doc_id
semantic_search(query=..., filters={"doc_id": [...]})
    # hits never leave the set; empty list → empty hits (never global);
    # up to 1000 deduped ids (400 SCOPE_TOO_LARGE beyond)
```

**Bias fuzzy search ranking (soft boosts — stackable):**

Three multiplicative boosts (`freshness_boost` / `impact_boost` /
`language_affinity`, each NONE/MILD/STRONG) reorder fuzzy-search
results while keeping relevance. Only effective when `query` is
non-empty; ignored when any sort is set; shallow paging while active.
No implicit year sort is added. Explicit sort disables soft boosts.

```
search_metadata(query="large language model", freshness_boost="STRONG")
    # recent first: STRONG=3-year decay, MILD=10-year
search_metadata(query="protein folding", impact_boost="MILD")
    # highly-cited float up (bounded; zero-citation stays neutral)
search_metadata(query="深度学习", language_affinity="MILD")
    # demote (never exclude) results not in the query's language;
    # unknown-language papers stay neutral; hard-exclude via
    # filters=[{"field":"language","operator":"FILTER_OP_EQ","value":"zh"}]
```

**Search authors or journals (collection):**

Set `collection` to `authors`, `sources`, or `patents` (default `papers`) to search
those entities. Each has its own fields — call
list_catalog(collection="authors") first; use filters +
sort with the selected collection fields.

```
search_metadata(collection="authors",
    filters=[{field: "summary_stats.h_index", operator: "FILTER_OP_GTE", value: 50}],
    sort=[{field: "cited_by_count", order: "SORT_ORDER_DESC"}])
```

**Fetch a paper figure / image:**

When read_content Markdown contains `![alt](file_name)`, call
`get_resource` with the file_name to fetch image binary.

```
read_content(doc_id, offset) → markdown ![Figure 3](dt=xxx/p/f3.png)
    └─▶ get_resource(file_name="dt=xxx/p/f3.png")
```

**Reading fulltext (check first):**

Each papers result from search_metadata carries `is_content_accessible` (bool): `true` only when
the paper has fulltext AND the caller is authorized. Check it before
`read_content(doc_id, ...)` — `false` means no fulltext or no read permission.

## Exit codes

- `0` — success; stdout is the JSON response
- `1` — HTTP 4xx/5xx; stderr contains status code and response body
- `2` — argument error (missing token, malformed JSON, required field absent)

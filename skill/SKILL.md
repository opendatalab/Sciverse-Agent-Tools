---
name: sciverse-academic-retrieval
slug: academic-retrieval
version: 0.1.5
description: SciVerse academic paper retrieval: structured metadata search, semantic chunk retrieval for RAG, and byte-range content reading. For agent workflows that need citation-grade scientific literature.
license: Apache-2.0
homepage: https://sciverse.space
---

# academic-retrieval

SciVerse academic paper retrieval: structured metadata search, semantic chunk retrieval for RAG, and byte-range content reading. For agent workflows that need citation-grade scientific literature.

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
Returns: list of papers; each entry has doc_id, title, author, abstract,
publication_venue_name, publication_published_year.

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

### read_content

Read a UTF-8 byte range of a paper's original text. Typically used with
a doc_id/offset returned by semantic_search to expand context (read
more bytes before or after a chunk).
Returns: text fragment, bytes_returned, next_offset, more (boolean).

**Invoke**: `node scripts/read_content.mjs '<JSON args>'`

## Composition patterns

Typical RAG flow:

```
semantic_search(query=...)
    └─▶ hits[i].doc_id, hits[i].offset
            └─▶ read_content(doc_id, offset)
```

Structured filter + metadata lookup:

```
search_papers(authors=[...], year_from=2020)
    └─▶ list of hits[].doc_id
```

## Exit codes

- `0` — success; stdout is the JSON response
- `1` — HTTP 4xx/5xx; stderr contains status code and response body
- `2` — argument error (missing token, malformed JSON, required field absent)

# Workflows

## Natural-Language Research Question

1. Run `semantic_search` with the user's question.
2. Select the most relevant chunks by score and title fit.
3. Run `read_content` for promising `doc_id` and `offset` pairs.
4. Answer with citations containing `doc_id` and title.

## Structured Literature Search

1. If fields or enum values are uncertain, run `list_catalog`.
2. Build a `search_papers` request with structured criteria.
3. Return a concise table or bullets with titles, years, venues, authors, and
   `doc_id`.
4. If the user asks for evidence from full text, continue with
   `semantic_search` or `read_content`.

## DOI Or Exact Identifier Lookup

1. Use `list_catalog` if the exact identifier field is uncertain.
2. Use `search_papers` with `filters_advanced`.
3. Return the matched paper metadata and note if no exact match is found.

## Hybrid Search (Scoped Semantic Search)

Use this when the user asks for a concept within a constrained corpus, such as a
specific author, journal, year range, or topic.

Preferred path — one call, server-side scoping:

1. Run `semantic_search` with `filters` (author, publication year/date, venue,
   topics, citation counts, language, ...). Constraints are applied at recall
   time inside both retrieval engines, not by post-filtering results.
2. Use `read_content` for final evidence.

Note the soft semantics: chunks missing that metadata are NOT excluded (e.g. a
chunk without year information still passes a year filter). Treat `filters` as
a broad constraint, not a hard guarantee — say so when precision matters.

Hard scope — when the constraint must be a hard guarantee, or needs meta-only
fields that `semantic_search.filters` does not support (fwci, citation-graph
queries, complex `search_papers` hit-sets):

1. Run `search_papers` to establish the candidate corpus. Project
   `fields: ["doc_id", "title"]`; only papers with full text carry a `doc_id`,
   so the scope naturally narrows to fulltext-available candidates.
2. Run `semantic_search` with `filters: {"doc_id": [...]}`. This is a HARD
   constraint applied at recall time: hits never leave the candidate set, and
   an explicitly empty list returns empty hits (never falls back to global
   search). Up to 1000 deduped ids per request — beyond that the server
   returns 400 `SCOPE_TOO_LARGE`; narrow the meta criteria instead of paging
   endlessly (each `search_papers` page also spends rate-limit budget).
3. Use `read_content` for final evidence.

Do not intersect global `semantic_search` results with candidate `doc_id`
client-side — that loses recall to global top-k truncation. `filters.doc_id`
replaces that pattern.

## Author / Journal Entity Profiles

`search_papers` and `list_catalog` accept `collection`: `papers` (default), `authors`,
`sources` (journals). Use this to discover or profile entities, and to enrich paper results.

Discovery (find entities directly):

1. `list_catalog '{"collection":"authors"}'` (or `sources`) to learn the fields.
2. `search_papers` with `collection` + `filters_advanced` + `sort_advanced`, e.g. top
   authors by `summary_stats.h_index` sorted by `cited_by_count`, or open-access core
   journals by `is_oa` / `is_core` / `topics.field.display_name`.

Enrichment (paper result → entity profile), two steps:

1. From a `search_papers` / `semantic_search` result, take an author's `orcid` or the
   venue's `publication_venue_issn`.
2. `search_papers '{"collection":"authors","filters_advanced":[{"field":"orcid", ...}]}'`
   (or `collection":"sources"` filtered by `issn`) to fetch the full entity profile
   (h-index, affiliations, topics / OA status, impact).

## Figures And Tables

1. Use `semantic_search` or `search_papers` to find the paper.
2. Use `read_content` to locate Markdown image placeholders.
3. Use `get_resource` with the exact `file_name`.
4. Cite the originating `doc_id` and title when describing the visual.

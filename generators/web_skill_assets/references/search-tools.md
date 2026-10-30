# Search Tools

Use these tools for catalog discovery and structured paper metadata search.

## list_catalog

Use when field names, filterability, sortability, operators, or enum-like values
are unclear.

```bash
node scripts/list_catalog.mjs '{"include_sample_values":true}'
# authors / sources collections have their own fields:
node scripts/list_catalog.mjs '{"collection":"authors","include_sample_values":true}'
```

Typical uses:

- Find the right field for DOI, OA status, language, metadata type, venue, or
  subject filtering.
- Inspect available `FilterOperators`.
- Avoid guessing field names before `search_metadata`.
- Pass `collection` (`papers` / `authors` / `sources` / `patents`) to inspect a specific entity's schema.

## search_metadata

Use when the user gives structured criteria such as title keywords, authors,
years, journals, subjects, DOI, OA status, or metadata fields.

```bash
node scripts/search_metadata.mjs '{
  "query": "transformer",
  "filters": [
    {"field":"author","operator":"FILTER_OP_IN","value":["Hinton"]},
    {"field":"publication_published_year","operator":"FILTER_OP_GTE","value":2020}
  ],
  "page_size": 10
}'
```

Common arguments:

- `collection`: `papers` (default), `authors`, `sources`, or `patents`.
  Call `list_catalog` for the selected collection before building filters.
- `query`: BM25-style keyword query over title/abstract/venue/keywords. Plain keywords
  match loosely (any word, ranked by relevance). Boolean syntax is supported: UPPERCASE
  `AND` / `OR` / `NOT`, `( )` grouping, `"quoted phrases"` (precedence NOT > AND > OR;
  adjacent words are implicitly AND). In boolean mode every term is required and nothing
  is relaxed — put only search terms in `query`, never labels or instructions. Lowercase
  `and`/`or` are ordinary words; quote `"OR"` for the literal. Max 64 terms.
- `filters`: explicit `[{field, operator, value}]` using `FILTER_OP_*` operators.
- No implicit year sorting. For newest papers first, explicitly use
  `sort: [{"field":"publication_published_year","order":"SORT_ORDER_DESC"}]`.
  Explicit sorting disables relevance boosts; use `freshness_boost` for relevant
  and recent papers instead.
- `sort`: `[{field, order}]` — sort by any sortable field (e.g. authors by
  `cited_by_count`, sources by `works_count`). `order` is `SORT_ORDER_DESC` / `SORT_ORDER_ASC`.
- `freshness_boost` / `impact_boost` / `language_affinity`: soft ranking boosts
  (`NONE`/`MILD`/`STRONG`, stackable multiplicative factors). Freshness biases toward
  recent papers (MILD=10-year decay, STRONG=3-year); impact floats highly-cited papers
  (bounded, zero-citation neutral); language affinity demotes (never excludes) results
  not in the query's language — target language detected from the query text,
  unknown-language papers stay neutral; to hard-exclude a language use
  `filters` on `language` instead. All three: only effective when `query` is
  non-empty; ignored when any sort is set; shallow paging while active (no `next_cursor`).
- `page`, `page_size`: pagination; `page_size` is capped at 50.

## list_paper_relations

Paginate a paper's full citations / references / related works. These are unbounded
arrays (up to 340k entries) and are **not projectable** in `search_metadata`, so this
endpoint is the only way to read them.

**Limits (CITATIONS only)**: over 10000 relations returns 429; `page * page_size`
above 10000 returns 400. In both cases switch to reverse lookup via `search_metadata`:

```bash
node scripts/search_metadata.mjs '{
  "filters": [
    {"field": "references_unique_id", "operator": "FILTER_OP_EQ", "value": "paper:10.1109/cvpr.2016.90"}
  ],
  "sort": [{"field": "citation_count", "order": "SORT_ORDER_DESC"}],
  "page_size": 50
}'
```

`total_count` counts in-corpus matches only, so it can differ from the paper's own
`citation_count` by about 1%.

```bash
node scripts/list_paper_relations.mjs '{
  "unique_id": "paper:10.1038/...",
  "relation": "CITATIONS",
  "page": 1,
  "page_size": 25
}'
```

- `unique_id` (required): from a `search_metadata` / `semantic_search` result (not `doc_id`).
- `relation` (required): `CITATIONS` (who cites this paper) / `REFERENCES` (what this paper
  cites — opposite direction) / `RELATED_WORKS`.
- `page`, `page_size`: pagination.

## Advanced Filter Example

```bash
node scripts/search_metadata.mjs '{
  "filters": [
    { "field": "doi", "operator": "FILTER_OP_EQ", "value": "10.1038/..." }
  ],
  "page_size": 5
}'
```

## Collections: authors / sources / patents

`search_metadata` and `list_catalog` accept `collection`: `papers` (default), `authors`,
`sources`, `patents`. Each collection has its own field schema — call
`list_catalog '{"collection":"authors"}'` first. Use canonical `filters` and `sort` with that collection's fields.
The new script rejects unknown parameters and paper convenience arguments.

- **authors**: filter by `summary_stats.h_index`, `works_count`, `cited_by_count`, `orcid`,
  `last_known_institutions.country_code`, `topics.field.display_name`, `source_issns`
  (authors who published in a given journal's ISSN).
- **sources** (journals): filter by `issn` / `issn_l`, `is_oa`, `is_in_doaj`, `is_core`,
  `type`, `country_code`, `topics.field.display_name`.
- **Linking from papers**: a paper result's `author[].orcid` joins to authors `orcid`; its
  `publication_venue_issn` joins to sources `issn`. So "semantic/meta search → entity
  profile" is two steps: get orcid/issn from a paper, then query the entity collection.

```bash
# Top authors by h-index, sorted by citations
node scripts/search_metadata.mjs '{
  "collection": "authors",
  "filters": [
    { "field": "summary_stats.h_index", "operator": "FILTER_OP_GTE", "value": 50 }
  ],
  "sort": [{ "field": "cited_by_count", "order": "SORT_ORDER_DESC" }]
}'

# Open-access core journals in a field
node scripts/search_metadata.mjs '{
  "collection": "sources",
  "filters": [
    { "field": "is_oa", "operator": "FILTER_OP_EQ", "value": true },
    { "field": "is_core", "operator": "FILTER_OP_EQ", "value": true },
    { "field": "topics.field.display_name", "operator": "FILTER_OP_EQ", "value": "Environmental Science" }
  ]
}'
```

## Result Handling

Return concise paper lists unless the user asks for exhaustive output. Preserve
`doc_id`, title, authors, venue, year, DOI when present, and explain which
filters were used.

### Patents

```bash
node scripts/list_catalog.mjs '{"collection":"patents"}'
node scripts/search_metadata.mjs '{"collection":"patents","query":"CRISPR","page_size":5}'
node scripts/read_content.mjs '{"collection":"patents","doc_id":"<doc_id from result>"}'
```

Use the returned identifier, never construct a patent doc_id. `semantic_search`
continues to search papers only. `get_resource` primarily fetches paper images.

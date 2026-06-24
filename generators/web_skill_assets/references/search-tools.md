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
- Avoid guessing field names before `search_papers`.
- Pass `collection` (`papers` / `authors` / `sources`) to inspect a specific entity's schema.

## search_papers

Use when the user gives structured criteria such as title keywords, authors,
years, journals, subjects, DOI, OA status, or metadata fields.

```bash
node scripts/search_papers.mjs '{
  "query": "transformer",
  "authors": ["Hinton"],
  "year_from": 2020,
  "page_size": 10
}'
```

Common arguments:

- `collection`: entity set — `papers` (default) / `authors` / `sources`. The convenience
  fields below apply to papers only; for `authors` / `sources` use `filters_advanced` (and
  `sort_advanced`) with that collection's field names. See `## Collections: authors / sources`.
- `query`: BM25-style keyword query over title/abstract/venue/keywords.
- `title_contains`, `abstract_contains`: targeted text matching.
- `authors`, `journals`, `subjects`: structured list filters.
- `year_from`, `year_to`: inclusive publication year bounds.
- `filters_advanced`: explicit field/operator/value filters after consulting
  `list_catalog`.
- `sort_by_year`: `desc`, `asc`, or `none`.
- `sort_advanced`: `[{field, order}]` — sort by any sortable field (e.g. authors by
  `cited_by_count`, sources by `works_count`). `order` is `SORT_ORDER_DESC` / `SORT_ORDER_ASC`.
- `page`, `page_size`: pagination; `page_size` is capped at 50.

## list_paper_relations

Paginate a paper's full citations / references / related works. `search_papers` only
inlines a truncated few of these unbounded arrays, so use this for the complete list.

```bash
node scripts/list_paper_relations.mjs '{
  "unique_id": "paper:10.1038/...",
  "relation": "CITATIONS",
  "page": 1,
  "page_size": 25
}'
```

- `unique_id` (required): from a `search_papers` / `semantic_search` result (not `doc_id`).
- `relation` (required): `CITATIONS` (who cites this paper) / `REFERENCES` (what this paper
  cites — opposite direction) / `RELATED_WORKS`.
- `page`, `page_size`: pagination.

## Advanced Filter Example

```bash
node scripts/search_papers.mjs '{
  "filters_advanced": [
    { "field": "doi", "operator": "FILTER_OP_EQ", "value": "10.1038/..." }
  ],
  "page_size": 5
}'
```

## Collections: authors / sources

`search_papers` and `list_catalog` accept `collection`: `papers` (default), `authors`,
`sources`. Each collection has its own field schema — call
`list_catalog '{"collection":"authors"}'` first. The papers convenience fields
(`authors` / `journals` / `year_from` / `subjects`) do **not** apply to other collections;
use `filters_advanced` + `sort_advanced` with that collection's field names.

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
node scripts/search_papers.mjs '{
  "collection": "authors",
  "filters_advanced": [
    { "field": "summary_stats.h_index", "operator": "FILTER_OP_GTE", "value": 50 }
  ],
  "sort_advanced": [{ "field": "cited_by_count", "order": "SORT_ORDER_DESC" }]
}'

# Open-access core journals in a field
node scripts/search_papers.mjs '{
  "collection": "sources",
  "filters_advanced": [
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

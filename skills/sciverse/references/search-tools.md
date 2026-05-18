# Search Tools

Use these tools for catalog discovery and structured paper metadata search.

## list_catalog

Use when field names, filterability, sortability, operators, or enum-like values
are unclear.

```bash
node scripts/list_catalog.mjs '{"include_sample_values":true}'
```

Typical uses:

- Find the right field for DOI, OA status, language, metadata type, venue, or
  subject filtering.
- Inspect available `FilterOperators`.
- Avoid guessing field names before `search_papers`.

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

- `query`: BM25-style keyword query over title/abstract/venue/keywords.
- `title_contains`, `abstract_contains`: targeted text matching.
- `authors`, `journals`, `subjects`: structured list filters.
- `year_from`, `year_to`: inclusive publication year bounds.
- `filters_advanced`: explicit field/operator/value filters after consulting
  `list_catalog`.
- `sort_by_year`: `desc`, `asc`, or `none`.
- `page`, `page_size`: pagination; `page_size` is capped at 50.

## Advanced Filter Example

```bash
node scripts/search_papers.mjs '{
  "filters_advanced": [
    { "field": "doi", "operator": "FILTER_OP_EQ", "value": "10.1038/..." }
  ],
  "page_size": 5
}'
```

## Result Handling

Return concise paper lists unless the user asks for exhaustive output. Preserve
`doc_id`, title, authors, venue, year, DOI when present, and explain which
filters were used.

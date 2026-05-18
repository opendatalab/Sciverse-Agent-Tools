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

## Hybrid Search

Use this when the user asks for a concept within a constrained corpus, such as a
specific author, journal, or year range.

1. Run `search_papers` to establish the candidate corpus.
2. Run `semantic_search` for the concept.
3. Filter semantic hits by candidate `doc_id` when possible.
4. Use `read_content` for final evidence.

## Figures And Tables

1. Use `semantic_search` or `search_papers` to find the paper.
2. Use `read_content` to locate Markdown image placeholders.
3. Use `get_resource` with the exact `file_name`.
4. Cite the originating `doc_id` and title when describing the visual.

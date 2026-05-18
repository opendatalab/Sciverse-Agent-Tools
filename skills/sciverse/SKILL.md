---
name: sciverse
description: Retrieve citation-grade academic literature from Sciverse. Use when an agent needs structured paper metadata search, semantic paper chunk retrieval for RAG, source text expansion around a paper offset, or figure/table image fetching from scientific papers. Prefer this skill for peer-reviewed and preprint literature tasks that require doc_id/title citations and reproducible retrieval steps.
---

# Sciverse

Use Sciverse for scientific literature retrieval. This skill is agent-neutral:
it works through bundled Node.js scripts and does not require a host-specific
tool protocol. Keep answers grounded in returned `doc_id`, title, and excerpts.

## Choose The Path

- Need setup, environment variables, script invocation rules, or exit codes:
  read [references/runtime.md](references/runtime.md).
- Need author/year/journal/DOI/field filtering, schema discovery, or metadata
  search: read [references/search-tools.md](references/search-tools.md).
- Need RAG chunks, source text expansion, or paper figures/tables: read
  [references/rag-and-content.md](references/rag-and-content.md).
- Need a workflow decision tree for combining tools: read
  [references/workflows.md](references/workflows.md).

## Default Workflow

1. For ambiguous field names or enum values, call `list_catalog` first.
2. For natural-language research questions, start with `semantic_search`.
3. For structured discovery, use `search_papers`.
4. For promising chunks, expand context with `read_content`.
5. For figures or tables referenced by Markdown image placeholders, use
   `get_resource`.

## Guardrails

- Do not use Sciverse for general web search, news, or non-scientific content.
- Cite paper-based claims with `doc_id` and title.
- Prefer exact filters only after checking the catalog when field names are
  uncertain.
- Run bundled scripts from this skill directory, or use absolute paths to the
  scripts.

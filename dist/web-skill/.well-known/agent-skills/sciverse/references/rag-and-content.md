# RAG And Content Tools

Use these tools for natural-language retrieval, source text expansion, and
paper figure/table fetching.

## semantic_search

Use for natural-language research questions and RAG-style grounding.

```bash
node scripts/semantic_search.mjs '{
  "query": "How does Transformer attention work?",
  "top_k": 5,
  "mode": "balanced"
}'
```

Common arguments:

- `query`: required natural-language query.
- `top_k`: number of chunks; maximum 30.
- `source_types`: optional `["web"]`, `["pdf"]`, or both.
- `mode`: `fast`, `balanced`, or `quality`.

Use returned `doc_id`, title, chunk text, score, and offset to decide whether to
expand the original source text.

## read_content

Use to read source text around a `doc_id` and byte `offset`, usually from a
`semantic_search` hit.

```bash
node scripts/read_content.mjs '{
  "doc_id": "...",
  "offset": 12000,
  "limit": 8192
}'
```

Common arguments:

- `doc_id`: required.
- `offset`: byte offset; default 0.
- `limit`: byte count; maximum 16384.

When `more` is true, continue with `next_offset` only if the user needs more
surrounding context.

## get_resource

Use when `read_content` returns Markdown image placeholders such as
`![Figure 3](dt=xxx/paper/f3.png)` and the user asks to inspect the figure or
table.

```bash
node scripts/get_resource.mjs '{
  "file_name": "dt=xxx/paper/f3.png"
}'
```

`file_name` must come from `read_content` output. Do not invent paths.

The script returns base64 image data. If the host agent can display images,
decode and show it; otherwise summarize the returned MIME type and file source.

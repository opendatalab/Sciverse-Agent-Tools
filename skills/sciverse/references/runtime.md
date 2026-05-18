# Runtime

## Requirements

- Node.js 18 or newer.
- `SCIVERSE_API_TOKEN` set in the environment.
- Optional `SCIVERSE_BASE_URL`; when set, it must point to `sciverse.space` or a
  `*.sciverse.space` subdomain.

## Invocation

Run scripts from the skill directory:

```bash
node scripts/list_catalog.mjs '{"include_sample_values":true}'
node scripts/search_papers.mjs '{"authors":["Hinton"],"year_from":2020}'
node scripts/semantic_search.mjs '{"query":"Transformer attention","top_k":5}'
node scripts/read_content.mjs '{"doc_id":"...","offset":0,"limit":4096}'
node scripts/get_resource.mjs '{"file_name":"dt=xxx/paper/figure.png"}'
```

If the current working directory is not the skill directory, use an absolute
script path.

## Inputs And Outputs

- Each script accepts one JSON object as its first argument.
- Successful calls write a JSON response to stdout.
- `get_resource` writes `{ "mime_type": "...", "base64": "..." }` because the
  endpoint returns binary image bytes.

## Exit Codes

- `0`: success.
- `1`: Sciverse API returned HTTP 4xx/5xx; stderr includes status and body.
- `2`: local argument, token, or URL validation error.

## Optional MCP Runtime

Some agents may already expose `sciverse-mcp-server` through MCP. If those tools
are available, using the host MCP tools is fine. Otherwise, use the bundled
scripts in this skill; they are the portable fallback for agents that support
skills but not MCP.

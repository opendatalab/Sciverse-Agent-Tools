# Sciverse retriever plugin for GPT Researcher

An independently versioned plugin maintained in Sciverse-Agent-Tools. It searches
scientific literature via Sciverse and returns citable passages. It does not
modify GPT Researcher's built-in retriever registry.

## Local installation (not published)

Python 3.12+ is required. From the Sciverse-Agent-Tools repository root:

```bash
python -m pip install ./packages/gpt-researcher
export RETRIEVER=sciverse
export SCIVERSE_API_TOKEN="your-token"
```

Install into the **same environment** that runs GPT Researcher. The minimum
supported PyPI version is `gpt-researcher==0.16.1`: its wheel includes plugin
entry-point discovery; the 0.16.0 wheel does not. GitHub release/tag numbers
(e.g. v3.7.0) are different from PyPI package versions.

Optional configuration:

- `SCIVERSE_BASE_URL`: defaults to `https://api.sciverse.space`.
- `SCIVERSE_MODE`: `fast` (keyword), `balanced` (hybrid, default), or `quality`
  (hybrid with three query-rewrite subqueries). Invalid environment values fall
  back to `balanced`; an invalid explicit `mode` raises `ValueError`.
- Combine providers using e.g. `RETRIEVER=sciverse,duckduckgo`.

```python
from gpt_researcher.actions.retriever import get_retriever

retriever = get_retriever("sciverse")
results = retriever("vision transformers", mode="quality").search(max_results=5)
```

Get a token at https://sciverse.space/. Missing/blank tokens raise a configuration
error. Runtime HTTP/JSON failures yield no results; metadata lookup failures
retain only hits with usable web source URLs. HTTP calls have a 30-second timeout.

## Content and filtering semantics

`raw_content` contains the title, available abstract and **retrieved passage**,
not the complete paper. `requires_scraping=False` tells GPT Researcher to use
this already-retrieved evidence instead of scraping a DOI/publisher page. An
integration test verifies the real upstream consumer preserves short passages
and citation URLs without scheduling a scrape. This is passage-level evidence;
reports must not treat it as proof that the entire paper has been read.

`query_domains` is accepted as the second positional argument for upstream
compatibility but is **not applied**: Sciverse searches its literature corpus.
Do not use this plugin when a strict domain allowlist is required.

Search defaults to seven passages and caps requests at 100. Results with no
usable content or HTTP(S) citation URL are skipped. Nonpositive limits return
an empty list. Citation URLs prefer an open-access URL, then DOI, then a hit's
web source URL. Direct calls may select `mode` as a keyword-only argument.

## Build and verify without publishing

From this directory, with `uv` installed:

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python build pytest ruff
.venv/bin/python -m build
uv pip install --python .venv/bin/python dist/gpt_researcher_sciverse-0.1.0-py3-none-any.whl
.venv/bin/python -m pytest tests -q
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
```

Tests mock only Sciverse HTTP requests; discovery, configuration and upstream
content routing use the installed GPT Researcher. No API token or LLM call is
needed for tests. This package is not connected to the repository's automatic main-branch
publishing workflow; building and installing it locally does not publish it.

## Manual release

The **Release GPT Researcher plugin** GitHub Actions workflow reuses the existing
`PYPI_API_TOKEN` repository secret and the `sciverse` package's build/twine upload
approach. It does not publish the SDK, MCP server or ClawHub package.

1. Update this package's version and merge the reviewed changes.
2. Run the workflow on `main`, enter the exact package version, and leave
   `publish=false` for a build/test-only run with downloadable distributions.
3. When ready to release, run with `publish=true`. This uploads only after lint,
   distribution checks and installed-wheel tests pass. No tag is created.

The PyPI token must permit creating/uploading `gpt-researcher-sciverse`; a token
scoped only to the existing `sciverse` project cannot publish this new project.
The workflow reuses the secret, but its project scope cannot be verified without
PyPI account access. `SCIVERSE_API_TOKEN` is a separate, local Sciverse API token
used for optional live acceptance testing; it is not used for PyPI uploads and
is not required by the offline CI suite.

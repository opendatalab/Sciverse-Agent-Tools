import pytest
import respx
from httpx import Response
from sciverse import AgentToolsClient


@pytest.mark.asyncio
@respx.mock
async def test_search_papers_happy_path():
    respx.post("https://api.example/meta-search").mock(
        return_value=Response(200, json={"hits": [{"doc_id": "p_1", "title": "Test"}], "total": 1, "page": 1, "page_size": 10})
    )
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        result = await c.search_papers(query="x")
    assert result["hits"][0]["doc_id"] == "p_1"


@pytest.mark.asyncio
@respx.mock
async def test_semantic_search_passes_mode():
    route = respx.post("https://api.example/agentic-search").mock(
        return_value=Response(200, json={"hits": []})
    )
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        await c.semantic_search(query="hello", mode="quality", top_k=5)
    body = route.calls.last.request.read()
    assert b'"mode":"quality"' in body
    assert b'"top_k":5' in body


@pytest.mark.asyncio
@respx.mock
async def test_read_content_uses_query_params():
    route = respx.get("https://api.example/content").mock(
        return_value=Response(200, json={"text": "x", "bytes_returned": 1, "next_offset": 1, "more": False})
    )
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        await c.read_content(doc_id="p_1", offset=100, limit=512)
    qs = dict(route.calls.last.request.url.params)
    assert qs == {"doc_id": "p_1", "offset": "100", "limit": "512"}


@pytest.mark.asyncio
@respx.mock
async def test_sends_bearer_token():
    route = respx.post("https://api.example/meta-search").mock(return_value=Response(200, json={"hits": [], "total": 0, "page": 1, "page_size": 10}))
    async with AgentToolsClient(base_url="https://api.example", token="abc") as c:
        await c.search_papers()
    assert route.calls.last.request.headers["authorization"] == "Bearer abc"


@pytest.mark.asyncio
@respx.mock
async def test_raises_on_4xx_with_httpx_error():
    """非 2xx 响应应抛 httpx.HTTPStatusError（用户应捕获该类型）。"""
    import httpx

    respx.post("https://api.example/meta-search").mock(
        return_value=Response(401, json={"code": "TOKEN_INVALID", "message": "无效 token"})
    )
    async with AgentToolsClient(base_url="https://api.example", token="bad") as c:
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await c.search_papers(query="x")
    assert exc_info.value.response.status_code == 401


@pytest.mark.asyncio
@respx.mock
async def test_search_papers_maps_authors_to_filter():
    route = respx.post("https://api.example/meta-search").mock(
        return_value=Response(200, json={"hits": [], "total": 0, "page": 1, "page_size": 10})
    )
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        await c.search_papers(authors=["Hinton", "LeCun"])
    body = route.calls.last.request.read()
    import json as _json
    parsed = _json.loads(body)
    assert "authors" not in parsed  # 不能透传给后端
    assert parsed["filters"] == [{
        "field": "author",
        "operator": "FILTER_OP_IN",
        "value": ["Hinton", "LeCun"],
    }]


@pytest.mark.asyncio
@respx.mock
async def test_search_papers_maps_year_range():
    route = respx.post("https://api.example/meta-search").mock(
        return_value=Response(200, json={"hits": [], "total": 0, "page": 1, "page_size": 10})
    )
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        await c.search_papers(year_from=2020, year_to=2023)
    import json as _json
    parsed = _json.loads(route.calls.last.request.read())
    fields = [f["field"] for f in parsed["filters"]]
    ops = [f["operator"] for f in parsed["filters"]]
    assert all(f == "publication_published_year" for f in fields)
    assert "FILTER_OP_GTE" in ops and "FILTER_OP_LTE" in ops


@pytest.mark.asyncio
@respx.mock
async def test_search_papers_maps_sort_by_year():
    route = respx.post("https://api.example/meta-search").mock(
        return_value=Response(200, json={"hits": [], "total": 0, "page": 1, "page_size": 10})
    )
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        await c.search_papers(sort_by_year="desc")
    import json as _json
    parsed = _json.loads(route.calls.last.request.read())
    assert parsed["sort"] == [{
        "field": "publication_published_year",
        "order": "SORT_ORDER_DESC",
    }]


@pytest.mark.asyncio
@respx.mock
async def test_search_papers_maps_journals_and_subjects():
    route = respx.post("https://api.example/meta-search").mock(
        return_value=Response(200, json={"hits": [], "total": 0, "page": 1, "page_size": 10})
    )
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        await c.search_papers(journals=["Nature"], subjects=["biology"])
    import json as _json
    parsed = _json.loads(route.calls.last.request.read())
    fields = {f["field"] for f in parsed["filters"]}
    assert fields == {"publication_venue_name_unified", "subjects"}


@pytest.mark.asyncio
@respx.mock
async def test_search_papers_maps_filters_advanced():
    route = respx.post("https://api.example/meta-search").mock(
        return_value=Response(200, json={"hits": [], "total": 0, "page": 1, "page_size": 10})
    )
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        await c.search_papers(filters_advanced=[
            {"field": "doi", "value": "10.1/x"},
            {"field": "language", "operator": "FILTER_OP_NE", "value": "zh"},
        ])
    import json as _json
    parsed = _json.loads(route.calls.last.request.read())
    assert parsed["filters"] == [
        {"field": "doi", "value": "10.1/x", "operator": "FILTER_OP_EQ"},
        {"field": "language", "operator": "FILTER_OP_NE", "value": "zh"},
    ]


@pytest.mark.asyncio
@respx.mock
async def test_search_papers_passthrough_keeps_only_canonical_fields():
    route = respx.post("https://api.example/meta-search").mock(
        return_value=Response(200, json={"hits": [], "total": 0, "page": 1, "page_size": 10})
    )
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        await c.search_papers(query="x", page=2, page_size=20, fields=["title"])
    import json as _json
    parsed = _json.loads(route.calls.last.request.read())
    assert set(parsed.keys()) == {"query", "page", "page_size", "fields"}

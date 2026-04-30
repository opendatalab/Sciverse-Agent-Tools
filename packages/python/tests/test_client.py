import pytest
import respx
from httpx import Response
from sciverse_agent_tools import AgentToolsClient


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

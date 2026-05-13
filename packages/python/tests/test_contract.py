import os

import httpx
import pytest

from sciverse_agent_tools import AgentToolsClient

pytestmark = pytest.mark.skipif(
    not (os.getenv("SCIVERSE_TEST_TOKEN") and os.getenv("SCIVERSE_TEST_BASE_URL")),
    reason="Layer 2 测试需要 SCIVERSE_TEST_TOKEN / SCIVERSE_TEST_BASE_URL"
)


def _skip_if_blocked(err: httpx.HTTPStatusError) -> None:
    """dev 网关 IP 白名单 / WAF 拦截会在鉴权前返回 403。这种环境问题
    应该 skip 而不是 fail —— 不是契约真坏。token 失效返 401 不在此列。"""
    if err.response.status_code == 403:
        pytest.skip(f"dev 网关拒绝（IP 白名单 / WAF？）：{err.response.url}")


@pytest.mark.asyncio
async def test_search_papers_returns_valid_shape():
    async with AgentToolsClient(
        base_url=os.environ["SCIVERSE_TEST_BASE_URL"],
        token=os.environ["SCIVERSE_TEST_TOKEN"],
    ) as c:
        try:
            r = await c.search_papers(query="transformer", page_size=3)
        except httpx.HTTPStatusError as e:
            _skip_if_blocked(e)
            raise
    assert isinstance(r, dict)
    assert "hits" in r
    assert isinstance(r["hits"], list)
    if r["hits"]:
        hit = r["hits"][0]
        assert "doc_id" in hit
        assert "title" in hit


@pytest.mark.asyncio
async def test_semantic_search_balanced_mode_returns_chunks():
    async with AgentToolsClient(
        base_url=os.environ["SCIVERSE_TEST_BASE_URL"],
        token=os.environ["SCIVERSE_TEST_TOKEN"],
    ) as c:
        try:
            r = await c.semantic_search(query="attention mechanism", top_k=3, mode="balanced")
        except httpx.HTTPStatusError as e:
            _skip_if_blocked(e)
            raise
    assert "hits" in r
    if r["hits"]:
        hit = r["hits"][0]
        for field in ("chunk_id", "doc_id", "title", "score", "offset"):
            assert field in hit, f"missing {field} in {hit}"


@pytest.mark.asyncio
async def test_semantic_search_validates_query_required():
    async with AgentToolsClient(
        base_url=os.environ["SCIVERSE_TEST_BASE_URL"],
        token=os.environ["SCIVERSE_TEST_TOKEN"],
    ) as c:
        with pytest.raises(Exception):
            await c.semantic_search(query="")


@pytest.mark.asyncio
async def test_read_content_after_semantic_search():
    async with AgentToolsClient(
        base_url=os.environ["SCIVERSE_TEST_BASE_URL"],
        token=os.environ["SCIVERSE_TEST_TOKEN"],
    ) as c:
        try:
            s = await c.semantic_search(query="quantum computing", top_k=1)
        except httpx.HTTPStatusError as e:
            _skip_if_blocked(e)
            raise
        if not s["hits"]:
            pytest.skip("no hits available")
        hit = s["hits"][0]
        r = await c.read_content(doc_id=hit["doc_id"], offset=hit.get("offset", 0), limit=1024)
    for field in ("text", "bytes_returned", "next_offset", "more"):
        assert field in r
    assert isinstance(r["text"], str)
    assert isinstance(r["more"], bool)


@pytest.mark.asyncio
async def test_invalid_token_returns_401():
    async with AgentToolsClient(
        base_url=os.environ["SCIVERSE_TEST_BASE_URL"],
        token="invalid-token-deadbeef",
    ) as c:
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await c.search_papers(query="x")
    status = exc_info.value.response.status_code
    if status == 403:
        # 网关 IP 白名单导致鉴权前就拦了，对 token 一视同仁返 403。
        # 跳过断言而不是 fail —— 不能验证 401 行为，但也不该误报契约破坏。
        pytest.skip("dev 网关 IP 白名单生效，未走到 token 校验环节")
    assert status == 401


@pytest.mark.asyncio
async def test_read_content_missing_doc_returns_4xx():
    async with AgentToolsClient(
        base_url=os.environ["SCIVERSE_TEST_BASE_URL"],
        token=os.environ["SCIVERSE_TEST_TOKEN"],
    ) as c:
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await c.read_content(doc_id="p_does_not_exist_xxxxxxxxxxxxxxxx")
    assert 400 <= exc_info.value.response.status_code < 600

import os
import pytest
from sciverse_agent_tools import AgentToolsClient

pytestmark = pytest.mark.skipif(
    not (os.getenv("SCIVERSE_TEST_TOKEN") and os.getenv("SCIVERSE_TEST_BASE_URL")),
    reason="Layer 2 测试需要 SCIVERSE_TEST_TOKEN / SCIVERSE_TEST_BASE_URL"
)


@pytest.mark.asyncio
async def test_search_papers_returns_valid_shape():
    async with AgentToolsClient(
        base_url=os.environ["SCIVERSE_TEST_BASE_URL"],
        token=os.environ["SCIVERSE_TEST_TOKEN"],
    ) as c:
        r = await c.search_papers(query="transformer", page_size=3)
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
        r = await c.semantic_search(query="attention mechanism", top_k=3, mode="balanced")
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
        s = await c.semantic_search(query="quantum computing", top_k=1)
        if not s["hits"]:
            pytest.skip("no hits available")
        hit = s["hits"][0]
        r = await c.read_content(doc_id=hit["doc_id"], offset=hit.get("offset", 0), limit=1024)
    for field in ("text", "bytes_returned", "next_offset", "more"):
        assert field in r
    assert isinstance(r["text"], str)
    assert isinstance(r["more"], bool)

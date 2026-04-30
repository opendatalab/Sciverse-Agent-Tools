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

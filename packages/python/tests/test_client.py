import json

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
@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("fast", {"retrieval": "es"}),
        ("balanced", {"retrieval": "hybrid"}),
        ("quality", {"retrieval": "hybrid", "sub_queries": 3}),
    ],
)
async def test_semantic_search_maps_mode_to_upstream_params(mode, expected):
    """mode 不透传（上游无此字段会静默丢弃），翻译为 retrieval / sub_queries。"""
    route = respx.post("https://api.example/agentic-search").mock(
        return_value=Response(200, json={"hits": []})
    )
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        await c.semantic_search(query="hello", mode=mode, top_k=5)
    import json as _json
    parsed = _json.loads(route.calls.last.request.read())
    assert "mode" not in parsed
    assert parsed == {"query": "hello", "top_k": 5, **expected}


@pytest.mark.asyncio
@respx.mock
async def test_semantic_search_without_mode_adds_nothing():
    """不传 mode 时不注入 retrieval/sub_queries（上游默认即 hybrid）。"""
    route = respx.post("https://api.example/agentic-search").mock(
        return_value=Response(200, json={"hits": []})
    )
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        await c.semantic_search(query="hello")
    import json as _json
    assert _json.loads(route.calls.last.request.read()) == {"query": "hello"}


@pytest.mark.asyncio
@respx.mock
async def test_semantic_search_explicit_params_override_mode():
    """显式 retrieval / sub_queries 优先于 mode 映射。"""
    route = respx.post("https://api.example/agentic-search").mock(
        return_value=Response(200, json={"hits": []})
    )
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        await c.semantic_search(query="hello", mode="quality", sub_queries=1)
    import json as _json
    parsed = _json.loads(route.calls.last.request.read())
    assert parsed == {"query": "hello", "retrieval": "hybrid", "sub_queries": 1}


@pytest.mark.asyncio
async def test_semantic_search_invalid_mode_rejected():
    """非法 mode 值在 SDK 层校验阶段就被拒（不打到后端）。"""
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        with pytest.raises(ValueError, match="mode"):
            await c.semantic_search(query="x", mode="turbo")


@pytest.mark.asyncio
@respx.mock
async def test_read_content_uses_query_params():
    route = respx.get("https://api.example/content").mock(
        return_value=Response(200, json={"text": "x", "bytes_returned": 1, "next_offset": 1, "more": False})
    )
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        await c.read_content(doc_id="p_1", offset=100, limit=512)
    qs = dict(route.calls.last.request.url.params)
    assert qs == {"doc_id": "p_1", "offset": "100", "limit": "512", "collection": "papers"}


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
async def test_sort_by_year_auto_with_query_keeps_relevance():
    """auto（默认）+ query：不加年份排序——保 BM25 相关性，软加权可用。
    显式排序会让 query 退化为命中过滤（后端 sort+query 语义），auto 必须避开。"""
    route = respx.post("https://api.example/meta-search").mock(
        return_value=Response(200, json={"hits": [], "total": 0, "page": 1, "page_size": 10})
    )
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        await c.search_papers(query="transformer")
    import json as _json
    parsed = _json.loads(route.calls.last.request.read())
    assert "sort" not in parsed


@pytest.mark.asyncio
@respx.mock
async def test_sort_by_year_auto_without_query_defaults_to_desc():
    """auto（默认）+ 纯结构化筛选：按年份降序——后端无排序时是 unique_id 序（实质乱序）。"""
    route = respx.post("https://api.example/meta-search").mock(
        return_value=Response(200, json={"hits": [], "total": 0, "page": 1, "page_size": 10})
    )
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        await c.search_papers(authors=["Hinton"])
    import json as _json
    parsed = _json.loads(route.calls.last.request.read())
    assert parsed["sort"] == [{
        "field": "publication_published_year",
        "order": "SORT_ORDER_DESC",
    }]


@pytest.mark.asyncio
@respx.mock
async def test_sort_by_year_auto_yields_to_sort_advanced():
    """auto + sort_advanced：显式排序优先，不叠加年份排序。"""
    route = respx.post("https://api.example/meta-search").mock(
        return_value=Response(200, json={"hits": [], "total": 0, "page": 1, "page_size": 10})
    )
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        await c.search_papers(sort_advanced=[{"field": "citation_count", "order": "SORT_ORDER_DESC"}])
    import json as _json
    parsed = _json.loads(route.calls.last.request.read())
    assert parsed["sort"] == [{"field": "citation_count", "order": "SORT_ORDER_DESC"}]


@pytest.mark.asyncio
async def test_sort_by_year_invalid_value_raises():
    """非法枚举值在 SDK 层直接报错（此前任意脏值会被静默当成 asc）。"""
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        with pytest.raises(ValueError, match="sort_by_year"):
            await c.search_papers(query="x", sort_by_year="descending")


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


@pytest.mark.asyncio
@respx.mock
async def test_search_papers_freshness_boost_passthrough():
    """freshness_boost 直接透传到 /meta-search payload。"""
    route = respx.post("https://api.example/meta-search").mock(
        return_value=Response(200, json={"hits": [], "total": 0, "page": 1, "page_size": 10})
    )
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        await c.search_papers(query="transformer", freshness_boost="STRONG")
    import json as _json
    parsed = _json.loads(route.calls.last.request.read())
    assert parsed["freshness_boost"] == "STRONG"


@pytest.mark.asyncio
async def test_search_papers_freshness_boost_invalid_value_rejected():
    """非法 freshness_boost 值在 SDK 层校验阶段就被拒（不打到后端）。"""
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        with pytest.raises(ValueError, match="freshness_boost"):
            await c.search_papers(query="x", freshness_boost="EXTREME")


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("collection", ["papers", "authors", "sources", "patents"])
async def test_search_metadata_canonical_payload(collection):
    route = respx.post("https://api.example/meta-search").respond(200, json={"hits": []})
    payload = {
        "query": "x", "collection": collection,
        "filters": [{"field": "unique_id", "operator": "FILTER_OP_EQ", "value": "x"}],
        "sort": [], "fields": ["unique_id"], "page": 1, "page_size": 5,
        "cursor": "opaque", "facets": [{"field": "language", "size": 50}],
        "freshness_boost": "MILD", "impact_boost": "STRONG", "language_affinity": "NONE",
    }
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        assert await c.search_metadata(**payload) == {"hits": []}
    assert json.loads(route.calls.last.request.content) == payload


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("kwargs", [{}, {"collection": "authors"}, {"collection": "sources"}, {"collection": "patents"}, {"filters": []}])
async def test_search_metadata_never_adds_sort(kwargs):
    route = respx.post("https://api.example/meta-search").respond(200, json={})
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        await c.search_metadata(**kwargs)
    assert json.loads(route.calls.last.request.content) == {"collection": "papers", **kwargs}


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("kwargs, field", [
    ({"typo": None}, "typo"), ({"year_from": 2020}, "year_from"),
    ({"collection": "invalid"}, "collection"),
    *[({field: "INVALID"}, field) for field in ("freshness_boost", "impact_boost", "language_affinity")],
])
async def test_search_metadata_rejects_invalid_parameters(kwargs, field):
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        with pytest.raises(ValueError, match=field):
            await c.search_metadata(**kwargs)
    assert not respx.calls


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("collection", ["authors", "sources", "patents"])
@pytest.mark.parametrize("sort_by_year", [None, "auto", "none"])
async def test_legacy_nonpapers_keeps_advanced_filters_without_year_sort(collection, sort_by_year):
    route = respx.post("https://api.example/meta-search").respond(200, json={})
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        await c.search_papers(collection=collection, sort_by_year=sort_by_year,
                              filters_advanced=[{"field": "unique_id", "value": "x"}])
    assert json.loads(route.calls.last.request.content) == {
        "collection": collection,
        "filters": [{"field": "unique_id", "value": "x", "operator": "FILTER_OP_EQ"}],
    }


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("collection", ["authors", "sources", "patents"])
@pytest.mark.parametrize("kwargs", [
    {"title_contains": ""}, {"abstract_contains": "x"}, {"authors": []},
    {"year_from": 0}, {"year_to": 2020}, {"journals": []}, {"subjects": []},
    {"sort_by_year": "asc"}, {"sort_by_year": "desc"},
])
async def test_legacy_nonpapers_rejects_paper_conveniences(collection, kwargs):
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        with pytest.raises(ValueError, match=next(iter(kwargs))):
            await c.search_papers(collection=collection, **kwargs)
    assert not respx.calls


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("kwargs, collection", [({}, "papers"), ({"collection": "patents"}, "patents")])
async def test_content_collection_and_default_window(kwargs, collection):
    route = respx.get("https://api.example/content").respond(200, json={"text": "x"})
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        await c.read_content(doc_id="x", **kwargs)
    assert dict(route.calls.last.request.url.params) == {
        "doc_id": "x", "collection": collection, "offset": "0", "limit": "4096",
    }


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("collection", ["authors", "sources", "invalid"])
async def test_content_rejects_unsupported_collection(collection):
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        with pytest.raises(ValueError, match="collection"):
            await c.read_content(doc_id="x", collection=collection)
    assert not respx.calls


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("size", [0, 51, True, "10"])
async def test_metadata_rejects_invalid_facet_size(size):
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        with pytest.raises(ValueError, match="facets"):
            await c.search_metadata(facets=[{"field": "language", "size": size}])
    assert not respx.calls


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("collection", ["authors", "sources", "patents"])
async def test_legacy_nonpapers_preserves_explicit_advanced_sort(collection):
    route = respx.post("https://api.example/meta-search").respond(200, json={})
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        await c.search_papers(collection=collection, sort_advanced=[{"field": "unique_id"}])
    assert json.loads(route.calls.last.request.content) == {
        "collection": collection,
        "sort": [{"field": "unique_id", "order": "SORT_ORDER_DESC"}],
    }


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("field", ["filters", "sort", "facets"])
@pytest.mark.parametrize("value", ["language", {}, 1, True, (), ["language"], [None], [[]], [1]])
async def test_metadata_rejects_malformed_entries_without_http(field, value):
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        with pytest.raises(ValueError, match=field):
            await c.search_metadata(**{field: value})
    assert not respx.calls


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("field, entry, unknown", [
    ("filters", {"field": "language", "operator": "FILTER_OP_EQ", "value": "en", "typo": None}, "typo"),
    ("sort", {"field": "unique_id", "order": "SORT_ORDER_ASC", "operator": "FILTER_OP_EQ"}, "operator"),
    ("facets", {"field": "language", "size": 10, "value": "en"}, "value"),
])
async def test_metadata_rejects_unknown_entry_keys_without_http(field, entry, unknown):
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        with pytest.raises(ValueError, match=unknown):
            await c.search_metadata(**{field: [entry]})
    assert not respx.calls


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("collection", ["invalid", "", 0, False, [], {}, None])
async def test_legacy_rejects_invalid_collection_without_http(collection):
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        with pytest.raises(ValueError, match="collection"):
            await c.search_papers(collection=collection)
    assert not respx.calls


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("facets", [[], [{"field": "language"}], [{"field": "language", "size": 1}]])
async def test_metadata_preserves_valid_entries_and_optional_facet_size(facets):
    route = respx.post("https://api.example/meta-search").respond(200, json={"results": []})
    payload = {
        "filters": [{"field": "language", "operator": "FILTER_OP_IN", "value": ["en", "zh"]}],
        "sort": [{"field": "unique_id", "order": "SORT_ORDER_ASC"}],
        "facets": facets,
    }
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        await c.search_metadata(**payload)
    assert json.loads(route.calls.last.request.content) == {"collection": "papers", **payload}


@pytest.mark.asyncio
@respx.mock
async def test_metadata_accepts_generated_model_default_serialization():
    from sciverse.types import SearchMetadataRequest

    payload = SearchMetadataRequest(query="x").model_dump(mode="json")
    assert all(payload[field] is None for field in ("filters", "sort", "facets"))
    route = respx.post("https://api.example/meta-search").respond(200, json={"results": []})
    async with AgentToolsClient(base_url="https://api.example", token="t") as c:
        result = await c.search_metadata(**payload)
    assert result == {"results": []}
    assert len(route.calls) == 1
    assert json.loads(route.calls.last.request.content) == {
        "query": "x", "collection": "papers", "page": 1, "page_size": 25,
        "freshness_boost": "NONE", "impact_boost": "NONE", "language_affinity": "NONE",
    }

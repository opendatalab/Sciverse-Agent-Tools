"""SciVerse Agent Tools 异步 HTTP client。"""
from __future__ import annotations

from types import TracebackType
from typing import Any

import httpx


_PASSTHROUGH = ("query", "page", "page_size", "fields")


def _to_backend_payload(kwargs: dict[str, Any]) -> dict[str, Any]:
    """把 search_papers 高级参数映射为 platform-console MetaSearchBody 接受的
    canonical 格式（query/filters/sort/fields/page/page_size）。"""
    out: dict[str, Any] = {}
    filters: list[dict[str, Any]] = []
    sort: list[dict[str, str]] = []

    for k in _PASSTHROUGH:
        if k in kwargs and kwargs[k] is not None:
            out[k] = kwargs[k]

    def _filter(field: str, op: str, value: Any) -> None:
        filters.append({"field": field, "operator": op, "value": value})

    if (v := kwargs.get("title_contains")) is not None:
        _filter("title", "FILTER_OP_CONTAINS", v)
    if (v := kwargs.get("abstract_contains")) is not None:
        _filter("abstract", "FILTER_OP_CONTAINS", v)
    if (v := kwargs.get("authors")) is not None and len(v) > 0:
        _filter("author", "FILTER_OP_IN", list(v))
    if (v := kwargs.get("year_from")) is not None:
        _filter("publication_published_year", "FILTER_OP_GTE", v)
    if (v := kwargs.get("year_to")) is not None:
        _filter("publication_published_year", "FILTER_OP_LTE", v)
    if (v := kwargs.get("journals")) is not None and len(v) > 0:
        _filter("publication_venue_name", "FILTER_OP_IN", list(v))
    if (v := kwargs.get("subjects")) is not None and len(v) > 0:
        _filter("subjects", "FILTER_OP_IN", list(v))
    if (v := kwargs.get("filters_advanced")) is not None:
        for item in v:
            entry = dict(item)
            entry.setdefault("operator", "FILTER_OP_EQ")
            filters.append(entry)

    sort_by_year = kwargs.get("sort_by_year")
    if sort_by_year and sort_by_year != "none":
        sort.append({
            "field": "publication_published_year",
            "order": "SORT_ORDER_DESC" if sort_by_year == "desc" else "SORT_ORDER_ASC",
        })

    if filters:
        out["filters"] = filters
    if sort:
        out["sort"] = sort
    return out


class AgentToolsClient:
    """封装 SciVerse 三个对外检索接口的 Bearer-authenticated 异步 client。

    用法：
        async with AgentToolsClient(base_url=..., token=...) as c:
            r = await c.semantic_search(query="...")
    """

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            headers={"Authorization": f"Bearer {token}"},
        )

    async def __aenter__(self) -> "AgentToolsClient":
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def search_papers(self, **kwargs: Any) -> dict[str, Any]:
        """对应 POST /meta-search。

        参数会被转换为后端 canonical 格式。Agent 友好参数：
        - query, page, page_size, fields  （透传）
        - title_contains, abstract_contains  → filter CONTAINS
        - authors  → filter author IN
        - year_from, year_to  → filter publication_published_year GTE/LTE
        - journals  → filter publication_venue_name IN
        - subjects  → filter subjects IN
        - filters_advanced  → 直接拼到 filters 列表
        - sort_by_year  → sort publication_published_year DESC/ASC
        """
        body = _to_backend_payload(kwargs)
        resp = await self._client.post("/meta-search", json=body)
        resp.raise_for_status()
        return resp.json()

    async def semantic_search(self, *, query: str, **kwargs: Any) -> dict[str, Any]:
        """对应 POST /agentic-search。"""
        body = {"query": query, **{k: v for k, v in kwargs.items() if v is not None}}
        resp = await self._client.post("/agentic-search", json=body)
        resp.raise_for_status()
        return resp.json()

    async def read_content(self, *, doc_id: str, offset: int = 0, limit: int = 4096) -> dict[str, Any]:
        """对应 GET /content。"""
        params = {"doc_id": doc_id, "offset": offset, "limit": limit}
        resp = await self._client.get("/content", params=params)
        resp.raise_for_status()
        return resp.json()

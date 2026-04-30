"""SciVerse Agent Tools 异步 HTTP client。"""
from __future__ import annotations

from types import TracebackType
from typing import Any

import httpx


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
        """对应 POST /meta-search。参数见 SearchPapersRequest。"""
        body = {k: v for k, v in kwargs.items() if v is not None}
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

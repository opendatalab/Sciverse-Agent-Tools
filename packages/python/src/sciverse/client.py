"""Sciverse Agent Tools 异步 HTTP client。"""
from __future__ import annotations

import platform
import uuid
from types import TracebackType
from typing import Any

import httpx

_CHANNEL = "python-sdk"
_PLATFORM = platform.system().lower()  # "linux" | "darwin" | "windows"
_SOURCE = f"{_PLATFORM}-{_CHANNEL}"


_PASSTHROUGH = (
    "query", "page", "page_size", "fields", "collection",
    "freshness_boost", "impact_boost", "language_affinity",
)
# 三个软加权档位共用同一枚举值域（NONE/MILD/STRONG）。
_BOOST_FIELDS = ("freshness_boost", "impact_boost", "language_affinity")
_BOOST_VALUES = frozenset({"NONE", "MILD", "STRONG"})
_SORT_BY_YEAR_VALUES = frozenset({"auto", "desc", "asc", "none"})

# 上游 agentic-search（Go 服务）没有 mode 字段，未知字段会被静默丢弃，
# 所以 mode 必须在 SDK 层翻译为上游真实参数 retrieval / sub_queries。
_SEMANTIC_MODE_MAP: dict[str, dict[str, Any]] = {
    "fast": {"retrieval": "es"},
    "balanced": {"retrieval": "hybrid"},
    "quality": {"retrieval": "hybrid", "sub_queries": 3},
}


def _to_backend_payload(kwargs: dict[str, Any]) -> dict[str, Any]:
    """把 search_papers 高级参数映射为 platform-console MetaSearchBody 接受的
    canonical 格式（query/filters/sort/fields/page/page_size）。"""
    out: dict[str, Any] = {}
    filters: list[dict[str, Any]] = []
    sort: list[dict[str, str]] = []

    for k in _PASSTHROUGH:
        if k in kwargs and kwargs[k] is not None:
            out[k] = kwargs[k]

    # 软加权枚举校验：枚举值不合法直接报错（在打到后端前）。
    for boost_field in _BOOST_FIELDS:
        if (boost := out.get(boost_field)) is not None:
            if not isinstance(boost, str) or boost not in _BOOST_VALUES:
                raise ValueError(
                    f"{boost_field} must be one of {sorted(_BOOST_VALUES)}, got {boost!r}"
                )

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
        _filter("publication_venue_name_unified", "FILTER_OP_IN", list(v))
    if (v := kwargs.get("subjects")) is not None and len(v) > 0:
        _filter("subjects", "FILTER_OP_IN", list(v))
    if (v := kwargs.get("filters_advanced")) is not None:
        for item in v:
            entry = dict(item)
            entry.setdefault("operator", "FILTER_OP_EQ")
            filters.append(entry)

    # sort_by_year 默认 auto：有 query（或 sort_advanced）时不加年份排序——保 BM25
    # 相关性且软加权可用（显式排序会让 query 退化为命中过滤、boost 全失效）；
    # 纯结构化筛选时按年份降序（后端默认序是 unique_id，实质乱序）。
    sort_by_year = kwargs.get("sort_by_year") or "auto"
    if sort_by_year not in _SORT_BY_YEAR_VALUES:
        raise ValueError(
            f"sort_by_year must be one of {sorted(_SORT_BY_YEAR_VALUES)}, got {sort_by_year!r}"
        )
    if sort_by_year == "auto":
        sort_by_year = "none" if (out.get("query") or kwargs.get("sort_advanced")) else "desc"
    if sort_by_year != "none":
        sort.append({
            "field": "publication_published_year",
            "order": "SORT_ORDER_DESC" if sort_by_year == "desc" else "SORT_ORDER_ASC",
        })

    if (sa := kwargs.get("sort_advanced")) is not None:
        for item in sa:
            if item and item.get("field"):
                sort.append({"field": item["field"], "order": item.get("order", "SORT_ORDER_DESC")})

    if filters:
        out["filters"] = filters
    if sort:
        out["sort"] = sort
    return out


class AgentToolsClient:
    """封装 Sciverse 三个对外检索接口的 Bearer-authenticated 异步 client。

    用法：
        async with AgentToolsClient(base_url=..., token=...) as c:
            r = await c.semantic_search(query="...")

    token / base_url 都可省略 —— 省略时按以下顺序 fallback：
        1. 显式参数
        2. 环境变量 SCIVERSE_API_TOKEN / SCIVERSE_BASE_URL
        3. ~/.sciverse/credentials.json（由 `sciverse auth login` 写入）
        4. base_url 默认值 https://api.sciverse.space；token 找不到则抛 ValueError
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        from sciverse.credentials import resolve_endpoint, resolve_token
        resolved_token = resolve_token(token)
        if not resolved_token:
            raise ValueError(
                "未找到 Sciverse API Token。请显式传 token、或设 SCIVERSE_API_TOKEN 环境变量、"
                "或运行 `sciverse auth login` 保存凭据到 ~/.sciverse/credentials.json。"
            )
        self._base_url = resolve_endpoint(base_url).rstrip("/")
        self._token = resolved_token
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            headers={"Authorization": f"Bearer {resolved_token}"},
            event_hooks={"request": [self._inject_request_id]},
        )

    @staticmethod
    async def _inject_request_id(request: httpx.Request) -> None:
        request.headers["X-Request-Id"] = str(uuid.uuid4())
        request.headers["X-Sciverse-Source"] = _SOURCE

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
        - journals  → filter publication_venue_name_unified IN
        - subjects  → filter subjects IN
        - filters_advanced  → 直接拼到 filters 列表
        - sort_by_year  → 按年份排序（auto/desc/asc/none，默认 auto）。auto = 有 query
          时不排序（保 BM25 相关性与软加权）、纯结构化筛选时年份降序。
          勿用 query+desc 求「相关且新」——那会退化为命中过滤，应改用 freshness_boost。
        - freshness_boost  → 模糊搜索新鲜度加权（NONE/MILD/STRONG，默认 NONE）。
          仅 query 非空时生效；传排序时被忽略（硬排优先）。
          MILD: 近 10 年加权，适合日常查文献；STRONG: 近 3 年，适合跟踪研究方向。
        - impact_boost  → 模糊搜索影响力加权（NONE/MILD/STRONG，默认 NONE）。
          高被引文献在保留相关性的前提下上浮；有界、零被引中性。
        - language_affinity  → 模糊搜索语言亲和加权（NONE/MILD/STRONG，默认 NONE）。
          非 query 语言的结果降序（不排除）；目标语言由服务端从 query 文本判定；
          语言未知的文献中性不降权。要硬排除某语言用 filters_advanced 的 language 字段。
        三个 boost 可叠加（均为乘法因子）；任一生效时为浅翻页（无 next_cursor）。
        """
        body = _to_backend_payload(kwargs)
        resp = await self._client.post("/meta-search", json=body)
        resp.raise_for_status()
        return resp.json()

    async def list_paper_relations(
        self,
        *,
        unique_id: str,
        relation: str,
        page: int = 1,
        page_size: int = 25,
    ) -> dict[str, Any]:
        """对应 POST /meta-paper-relations。分页查某论文的引用关系列表。

        relation：CITATIONS（被引：谁引用了我）/ REFERENCES（参考文献：我引用了谁）/
        RELATED_WORKS（相关工作）。CITATIONS 与 REFERENCES 方向相反。
        unique_id 来自 search_papers / semantic_search（勿传 doc_id）。
        """
        body = {"unique_id": unique_id, "relation": relation, "page": page, "page_size": page_size}
        resp = await self._client.post("/meta-paper-relations", json=body)
        resp.raise_for_status()
        return resp.json()

    async def semantic_search(self, *, query: str, **kwargs: Any) -> dict[str, Any]:
        """对应 POST /agentic-search。

        mode（fast/balanced/quality）在 SDK 层翻译为上游参数：
        fast → retrieval=es；balanced → retrieval=hybrid；
        quality → retrieval=hybrid + sub_queries=3。
        显式传入的 retrieval / sub_queries 优先于 mode 映射。
        """
        body = {"query": query, **{k: v for k, v in kwargs.items() if v is not None}}
        mode = body.pop("mode", None)
        if mode is not None:
            if mode not in _SEMANTIC_MODE_MAP:
                raise ValueError(
                    f"mode must be one of {sorted(_SEMANTIC_MODE_MAP)}, got {mode!r}"
                )
            body = {**_SEMANTIC_MODE_MAP[mode], **body}
        resp = await self._client.post("/agentic-search", json=body)
        resp.raise_for_status()
        return resp.json()

    async def list_catalog(
        self,
        *,
        include_sample_values: bool = False,
        include_field_stats: bool = False,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """对应 GET /meta-catalog。

        返回字段 catalog：每个字段的名称 / 类型 / filterable / sortable / default_returned /
        描述 / 适用 FilterOperator，外加 enum-like 字段的样本值（include_sample_values=True 时）。
        collection 指定实体集合（papers 默认 / authors / sources），各 collection 字段集不同。
        Agent 第一次接触 Sciverse 或碰到字段不确定时建议先调一次再构造 search_papers。
        """
        params: dict[str, str] = {"include_sample_values": str(include_sample_values).lower()}
        if include_field_stats:
            params["include_field_stats"] = "true"
        if collection:
            params["collection"] = collection
        resp = await self._client.get("/meta-catalog", params=params)
        resp.raise_for_status()
        return resp.json()

    async def read_content(self, *, doc_id: str, offset: int = 0, limit: int = 4096) -> dict[str, Any]:
        """对应 GET /content。"""
        params = {"doc_id": doc_id, "offset": offset, "limit": limit}
        resp = await self._client.get("/content", params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_resource(self, *, file_name: str) -> tuple[bytes, str]:
        """对应 GET /resource。

        取文献附属图片字节流。触发场景：read_content 返回的 Markdown 中含
        `![alt](file_name)` 图片占位时，调本接口拿图片 binary。

        返回 (bytes, mime_type)。mime_type 来自响应头 content-type，如
        "image/png" / "image/jpeg" / "application/octet-stream"。
        """
        resp = await self._client.get(
            "/resource",
            params={"file_name": file_name},
            headers={"accept": "image/*"},
        )
        resp.raise_for_status()
        mime = (resp.headers.get("content-type") or "application/octet-stream").split(";")[0].strip()
        return resp.content, mime

"""Auto-generated. Do not edit. Run `python -m generators.to_langchain` to regenerate."""
from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field

TOOLS_VERSION = "1.0.0"

_NO_CLIENT = (
    "No Sciverse client bound. Build these tools with build_tools(client), passing a "
    "sciverse.AgentToolsClient — it holds the credentials and translates arguments such "
    "as `mode` into the parameters the API actually accepts."
)

# The Sciverse client is async-only, and calling asyncio.run() from inside a running
# event loop raises. Async-only tools are a standard LangChain pattern: drive them with
# ainvoke() / an async executor.
_SYNC_UNSUPPORTED = (
    "{name} is async-only. Use `await tool.ainvoke(...)` or an async agent executor."
)


class SearchMetadataArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    fields: list[str] | None = Field(None, description='返回字段，须为当前collection已授权且可投影字段；省略返回默认字段集与授权交集。')
    collection: str = Field('papers', description='实体集合；用 list_catalog 查看对应字段权限和能力。')
    query: str | None = Field(None, description='BM25 关键词，匹配当前实体已授权的可检索字段；专利包含 invention_title、abstract、claims.claim_text。留空则纯靠结构化过滤。\n普通关键词是宽松匹配（任一词命中、按相关性排序）。\n\n也支持布尔检索式：全大写 AND / OR / NOT、括号分组、引号短语；优先级\nNOT > AND > OR，相邻词隐式 AND。例如\n  (histopathology OR pathology) AND ("deep learning" OR "machine learning") AND (prognosis OR survival)\n布尔式里每个检索词都是硬条件、不做放宽——0 命中就是 0。\n- query 只放检索词：「检索式1（预后预测）」这类标签/说明也会变成必须命中的词。\n- 小写 and/or 是普通词；要检索字面量 OR（如比值比）加引号 "OR"。\n- 引号需与运算符同时出现才生效：只写 "spread through air spaces" 不带运算符时\n  按普通关键词处理；写成 "spread through air spaces" AND lung 才是短语精确匹配。\n- 最多 64 个检索词、括号嵌套 10 层，超限返回 400；复杂检索请拆成多次调用。\n')
    page: int = Field(1, description='')
    page_size: int = Field(25, description='每页条数。省略时为服务端默认 25（SDK / MCP 不注入默认值）；工具层上限 50。')
    freshness_boost: str = Field('NONE', description='模糊搜索新鲜度加权：结果偏向新文献（仅 query 非空时生效；传排序\n（sort_by_year 非 none / sort_advanced）时被忽略，硬排优先）。\nMILD: 近 10 年加权，适合日常查文献；STRONG: 近 3 年加权，适合跟踪\n研究方向 / 追最新进展。与 impact_boost / language_affinity 可叠加\n（均为乘法因子）。boost 生效时为浅翻页：不产 next_cursor、不支持\ncursor 深翻页。\n')
    impact_boost: str = Field('NONE', description='模糊搜索影响力加权：高被引文献在保留相关性的前提下上浮（仅 query\n非空时生效；传排序时被忽略）。MILD: 轻度上浮，相关性仍主导；\nSTRONG: 明显偏向高被引。引用因子有界、零被引中性（不会归零）。\n与 freshness_boost / language_affinity 可叠加；boost 生效时为浅翻页。\n')
    language_affinity: str = Field('NONE', description='模糊搜索语言亲和加权：非 query 语言的结果降序、但不排除（仅 query\n非空时生效；传排序时被忽略）。目标语言由服务端从 query 文本判定\n（假名→ja / 谚文→ko / 汉字→zh / 拉丁→en，其他书写系统不生效）；\n语言未知的文献保持中性不降权。MILD: 非目标语言 ×0.5，跨语言强相关\n结果仍可上浮；STRONG: ×0.2，几乎只看目标语言。与 freshness_boost /\nimpact_boost 可叠加；boost 生效时为浅翻页。要硬排除某语言请改用\nfilters_advanced 的 language 字段（如 {"field":"language","value":"en"}，\n软硬两层语义不同：本参数只调序，filter 直接排除）。\n')
    filters: list[dict[str, Any]] | None = Field(None, description='按当前实体 catalog 的字段能力填写。')
    sort: list[dict[str, Any]] | None = Field(None, description='按当前实体 catalog 的字段能力填写。')
    cursor: str | None = Field(None, description='使用上页 next_cursor 原样续查，保持查询条件不变；不与 page>1 共用。')
    facets: list[dict[str, Any]] | None = Field(None, description='')


class SearchMetadataTool(BaseTool):
    name: str = "search_metadata"
    description: str = """按 collection 检索元数据。先用 list_catalog 查看该实体已授权字段，再填写 filters、sort、fields。支持关键词 query、游标分页和 facets；默认不加隐式排序。论文正文与专利正文使用 read_content，语义片段检索使用 semantic_search（仅论文）。返回 results、total_count、next_cursor；实体字段不做统一改名，作者和来源的 id 不能用于读取正文。"""
    args_schema: type[BaseModel] = SearchMetadataArgs
    client: Any = None

    def _run(self, **kwargs: Any) -> Any:
        raise NotImplementedError(_SYNC_UNSUPPORTED.format(name=self.name))

    async def _arun(self, **kwargs: Any) -> Any:
        if self.client is None:
            raise ValueError(_NO_CLIENT)
        return await self.client.search_metadata(**kwargs)


class SemanticSearchArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    query: str = Field(..., description='自然语言查询，1-200 字最佳。')
    top_k: int = Field(10, description='返回命中条数上限，合法 1-100（服务端校验，超出报 400）。\n实际条数还受 mode 影响：balanced 单路混合召回在服务端固定截到约 50 条，\ntop_k 超过 50 时多出的部分不会返回；fast 与 quality 可取到 top_k。\n另外同一篇论文最多返回约 3 个 chunk，因此高 top_k 需要命中足够多的不同论文。\n')
    source_types: list[str] | None = Field(None, description='')
    filters: dict[str, Any] | None = Field(None, description='结构化过滤（可选）。在召回阶段与语义检索同时生效（ES+Milvus 双引擎下推，\n不是结果后过滤）；多个字段之间 AND，同一字段传数组时数组内 OR。\n⚠️ 宽松（软）语义：chunk 侧元数据缺失的文档不会被排除——例如按年份过滤时，\n缺年份信息的 chunk 仍可能返回。需要严格范围保证时勿当硬约束使用，\n表述结论时注明范围为"近似过滤"。\n数值/日期字段支持区间：{"gte":2020,"lte":2025} 或 [min,max]（null 表示一侧不限）；\n日期接受 YYYY / YYYY-MM / YYYY-MM-DD。\n实际可用字段受账号字段权限约束；未知字段服务端返回 400。\n例：{"author":["Hinton"],"publication_published_year":{"gte":2023},\n    "topics":{"dimensions":{"primary_topic_domain":"Health Sciences"}}}\n')
    mode: str = Field('balanced', description='fast = 仅关键词召回 (~200ms)；balanced = 混合检索 (~600ms)；quality = LLM 改写 + 混合 (~2-4s)。\n')


class SemanticSearchTool(BaseTool):
    name: str = "semantic_search"
    description: str = """自然语言语义检索，返回相关文献片段（chunk）用于 RAG 回答。
适用：「Transformer 注意力机制如何工作？」「最新的蛋白质折叠预测方法有哪些？」
不适用：精确字段过滤 → search_metadata；取完整原文 → read_content。
返回：相关 chunk 列表，每条含 chunk_id/doc_id/abstract/chunk/score/title/offset。
典型链路：semantic_search → 选取 chunk → read_content(doc_id, offset)。
"""
    args_schema: type[BaseModel] = SemanticSearchArgs
    client: Any = None

    def _run(self, **kwargs: Any) -> Any:
        raise NotImplementedError(_SYNC_UNSUPPORTED.format(name=self.name))

    async def _arun(self, **kwargs: Any) -> Any:
        if self.client is None:
            raise ValueError(_NO_CLIENT)
        return await self.client.semantic_search(**kwargs)


class ListCatalogArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    collection: str = Field('papers', description='字段 catalog 所属实体集合。papers（默认）/ authors / sources，各 collection 字段不同。')
    include_sample_values: bool = Field(False, description='是否拉取 enum-like 字段的取值样本。false 仅返回静态 schema（毫秒级）；true 触发 OpenSearch terms agg（首次几百毫秒，之后 24h 走缓存）。')
    include_field_stats: bool = Field(False, description='是否返回字段统计（keyword 字段基数 + 数值字段 min/max/avg/p50/p95）。触发 OpenSearch 聚合，缓存 24h。')


class ListCatalogTool(BaseTool):
    name: str = "list_catalog"
    description: str = """返回 search_metadata 所有可用字段的 catalog：字段名、类型、能否过滤/排序、
是否默认返回、字段说明、FilterOperator 清单等。
适用：「我该用哪个字段过滤 DOI?」「access_oa_status 有哪些可能值？」
「`metadata_type` 的合法取值是？」
不适用：实际查询文献，那是 search_metadata / semantic_search 的事。
典型用法：Agent 第一次接触 Sciverse 或碰到模糊字段需求时先调一次本接口，
把 schema 装进 working memory，后续精确构造 search_metadata 的 filters。
include_sample_values=true 时返回枚举值样本（OpenSearch terms agg，缓存 24h）。
"""
    args_schema: type[BaseModel] = ListCatalogArgs
    client: Any = None

    def _run(self, **kwargs: Any) -> Any:
        raise NotImplementedError(_SYNC_UNSUPPORTED.format(name=self.name))

    async def _arun(self, **kwargs: Any) -> Any:
        if self.client is None:
            raise ValueError(_NO_CLIENT)
        return await self.client.list_catalog(**kwargs)


class ListPaperRelationsArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    unique_id: str = Field(..., description='目标论文 unique_id（如 paper:10.1038/xxx），来自 search_metadata / semantic_search；勿传 doc_id。')
    relation: str = Field(..., description='关系类型。CITATIONS=被引（谁引用了我）；REFERENCES=参考文献（我引用了谁）；RELATED_WORKS=相关工作。')
    page: int = Field(1, description='')
    page_size: int = Field(25, description='')


class ListPaperRelationsTool(BaseTool):
    name: str = "list_paper_relations"
    description: str = """分页返回某篇论文的引用关系完整列表。citations/references/related_works 是无界数组
（单篇最大 34 万条），在 search_metadata 中**不可投影**，取这些列表只能用本接口。
适用：「论文 X 引用了哪些文献」（relation=REFERENCES）、「哪些文献引用了论文 X」
（relation=CITATIONS）、「与论文 X 相关的工作」（relation=RELATED_WORKS）。
注意：CITATIONS（被引：谁引用了我）与 REFERENCES（参考文献：我引用了谁）方向相反。
典型链路：先 search_metadata / semantic_search 拿到 unique_id，再用本接口按 relation 分页。
两个上限（仅 CITATIONS 可能触发；REFERENCES/RELATED_WORKS 实测最大 11833/20 条）：
关系数超 10000 返回 429；page×page_size 超 10000 返回 400。两种情况都改用
search_metadata 的 filters 传 references_unique_id 反查——可深翻页并任意排序。
total_count 为库内命中数（不含指向库外论文的边），与论文自身 citation_count 可能有 ±1% 差异。
"""
    args_schema: type[BaseModel] = ListPaperRelationsArgs
    client: Any = None

    def _run(self, **kwargs: Any) -> Any:
        raise NotImplementedError(_SYNC_UNSUPPORTED.format(name=self.name))

    async def _arun(self, **kwargs: Any) -> Any:
        if self.client is None:
            raise ValueError(_NO_CLIENT)
        return await self.client.list_paper_relations(**kwargs)


class ReadContentArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    collection: str = Field('papers', description='正文实体；专利必须传 patents，doc_id 来自元数据查询，不能用公开号。')
    doc_id: str = Field(..., description='文献 ID（来自 search_metadata / semantic_search）。')
    offset: int = Field(0, description='起始 Unicode 码点偏移，直接使用 semantic_search 返回的 offset。默认 0。')
    limit: int = Field(4096, description='最多返回的 Unicode 码点数。默认 4096；服务端上限 524288（超出静默钳制）。LLM 场景建议 ≤ 16384，避免撑爆上下文。')


class ReadContentTool(BaseTool):
    name: str = "read_content"
    description: str = """按 Unicode 码点区间读取文献原文片段（offset/limit 均以码点计，与 Python len 一致，不是字节）。
通常配合 semantic_search 返回的 doc_id/offset 使用，用于扩展上下文（往前/往后读更多文本）。
返回：UTF-8 文本片段、bytes_returned（text 的 UTF-8 字节数，仅供参考）、
next_offset（下一段起始码点偏移，翻页请用它而不是 bytes_returned）、是否还有后续。
服务端行为：limit 超过 524288 时静默钳制；未传 offset 时服务端返回整篇全文并忽略 limit——
SDK / MCP server 会自动补 offset=0、limit=4096，直接调 HTTP 时务必显式传 offset。
"""
    args_schema: type[BaseModel] = ReadContentArgs
    client: Any = None

    def _run(self, **kwargs: Any) -> Any:
        raise NotImplementedError(_SYNC_UNSUPPORTED.format(name=self.name))

    async def _arun(self, **kwargs: Any) -> Any:
        if self.client is None:
            raise ValueError(_NO_CLIENT)
        return await self.client.read_content(**kwargs)


class GetResourceArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    file_name: str = Field(..., description='图片相对路径，来自 read_content Markdown 中的 `![alt](file_name)` 占位。禁止 `\\\\` 与 `..`，不能以 `/` 开头。')


class GetResourceTool(BaseTool):
    name: str = "get_resource"
    description: str = """按文件名取文献中嵌入的图片字节流（PNG / JPG 等）。
触发场景：read_content 返回的 Markdown 中含 `![alt](file_name)` 形式的图片占位，
agent 需要把图给用户看时调本接口。
入参 file_name 来自 markdown 内的 url 段（相对路径，禁止 `\\` 或 `..`）。
返回：HTTP 二进制流 + image/* Content-Type。
SDK / MCP server 包装层会做 base64 + mime 转换以便 agent 多模态使用。
"""
    args_schema: type[BaseModel] = GetResourceArgs
    client: Any = None

    def _run(self, **kwargs: Any) -> Any:
        raise NotImplementedError(_SYNC_UNSUPPORTED.format(name=self.name))

    async def _arun(self, **kwargs: Any) -> Any:
        if self.client is None:
            raise ValueError(_NO_CLIENT)
        return await self.client.get_resource(**kwargs)



TOOL_CLASSES: list[type[BaseTool]] = [SearchMetadataTool, SemanticSearchTool, ListCatalogTool, ListPaperRelationsTool, ReadContentTool, GetResourceTool]


def build_tools(client: Any) -> list[BaseTool]:
    """Return every Sciverse tool bound to `client`, ready to hand to an agent.

    `client` is a `sciverse.AgentToolsClient`. Bind through it rather than calling the
    HTTP API yourself: it owns credentials, retries, and the argument translation the
    raw endpoints do not perform (an unmapped `mode`, for one, is silently ignored
    upstream, so `quality` would quietly behave like `balanced`).

    The tools are async-only — drive them with `ainvoke()` or an async executor.
    """
    return [cls(client=client) for cls in TOOL_CLASSES]


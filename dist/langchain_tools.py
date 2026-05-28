"""Auto-generated. Do not edit. Run `python -m generators.to_langchain` to regenerate."""
from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field

TOOLS_VERSION = "0.7.1"


class SearchPapersArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    query: str | None = Field(None, description='BM25 全文关键词，匹配标题/摘要/期刊名/关键词字段。留空则纯靠结构化过滤。')
    title_contains: str | None = Field(None, description='标题中必须包含的词（仅匹配 title 字段）。')
    abstract_contains: str | None = Field(None, description='摘要中必须包含的词（仅匹配 abstract 字段）。')
    authors: list[str] | None = Field(None, description='作者名（任一命中即可）。SDK 内部映射到后端 `author` 字段（FILTER_OP_IN）。')
    year_from: int | None = Field(None, description='起始发表年（含）。')
    year_to: int | None = Field(None, description='结束发表年（含）。')
    journals: list[str] | None = Field(None, description='期刊名（任一命中即可）。SDK 内部映射到后端 `publication_venue_name_unified` 字段（FILTER_OP_IN，规范化后的载体名）。')
    subjects: list[str] | None = Field(None, description='学科分类，如 "computer science"、"biology"。')
    filters_advanced: list[dict[str, Any]] | None = Field(None, description='高级过滤逃生舱（仅当上述字段不够用时使用）。')
    sort_by_year: str = Field('desc', description='')
    freshness_boost: str = Field('NONE', description='模糊搜索新鲜度加权（仅 query 非空时生效；与 sort_by_year 互斥）。\nMILD: 近 10 年加权，适合日常查文献；STRONG: 近 3 年加权，适合跟踪\n研究方向 / 追最新进展。底层为 function_score + gauss decay over\npublication_published_date。\n')
    page: int = Field(1, description='')
    page_size: int = Field(10, description='')


class SearchPapersTool(BaseTool):
    name: str = "search_papers"
    description: str = """按结构化条件检索学术文献元数据（标题、作者、期刊、年份、摘要等）。
适用：「查找 Hinton 在 2020-2023 年发表的论文」「找 Nature 上关于 CRISPR 的近期文献」。
不适用：自然语言问答检索 → 用 semantic_search；查全文片段 → 用 read_content。
返回：论文元数据列表，每条含 unique_id（始终存在）、doc_id（仅当有全文）、title、author、abstract、publication_venue_name_unified、publication_published_year 等。
"""
    args_schema: type[BaseModel] = SearchPapersArgs

    def _run(self, **kwargs: Any) -> Any:
        raise NotImplementedError("bind a client via .with_client(...)")

    async def _arun(self, **kwargs: Any) -> Any:
        raise NotImplementedError("bind a client via .with_client(...)")


class SemanticSearchArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    query: str = Field(..., description='自然语言查询，1-200 字最佳。')
    top_k: int = Field(10, description='')
    source_types: list[str] | None = Field(None, description='')
    mode: str = Field('balanced', description='fast = 仅关键词召回 (~200ms)；balanced = 混合检索 (~600ms)；quality = LLM 改写 + 混合 (~2-4s)。\n')


class SemanticSearchTool(BaseTool):
    name: str = "semantic_search"
    description: str = """自然语言语义检索，返回相关文献片段（chunk）用于 RAG 回答。
适用：「Transformer 注意力机制如何工作？」「最新的蛋白质折叠预测方法有哪些？」
不适用：精确字段过滤 → search_papers；取完整原文 → read_content。
返回：相关 chunk 列表，每条含 chunk_id/doc_id/abstract/chunk/score/title/offset。
典型链路：semantic_search → 选取 chunk → read_content(doc_id, offset)。
"""
    args_schema: type[BaseModel] = SemanticSearchArgs

    def _run(self, **kwargs: Any) -> Any:
        raise NotImplementedError("bind a client via .with_client(...)")

    async def _arun(self, **kwargs: Any) -> Any:
        raise NotImplementedError("bind a client via .with_client(...)")


class ListCatalogArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    include_sample_values: bool = Field(False, description='是否拉取 enum-like 字段的取值样本。false 仅返回静态 schema（毫秒级）；true 触发 OpenSearch terms agg（首次几百毫秒，之后 24h 走缓存）。')


class ListCatalogTool(BaseTool):
    name: str = "list_catalog"
    description: str = """返回 search_papers 所有可用字段的 catalog：字段名、类型、能否过滤/排序、
是否默认返回、字段说明、FilterOperator 清单等。
适用：「我该用哪个字段过滤 DOI?」「access_oa_status 有哪些可能值？」
「`metadata_type` 的合法取值是？」
不适用：实际查询文献，那是 search_papers / semantic_search 的事。
典型用法：Agent 第一次接触 Sciverse 或碰到模糊字段需求时先调一次本接口，
把 schema 装进 working memory，后续精确构造 search_papers 的 filters。
include_sample_values=true 时返回枚举值样本（OpenSearch terms agg，缓存 24h）。
"""
    args_schema: type[BaseModel] = ListCatalogArgs

    def _run(self, **kwargs: Any) -> Any:
        raise NotImplementedError("bind a client via .with_client(...)")

    async def _arun(self, **kwargs: Any) -> Any:
        raise NotImplementedError("bind a client via .with_client(...)")


class ReadContentArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    doc_id: str = Field(..., description='文献 ID（来自 search_papers / semantic_search）。')
    offset: int = Field(0, description='')
    limit: int = Field(4096, description='')


class ReadContentTool(BaseTool):
    name: str = "read_content"
    description: str = """按字节区间读取文献原文片段。通常配合 semantic_search 返回的 doc_id/offset 使用，
用于扩展上下文（往前/往后读更多字节）。
返回：UTF-8 文本片段、bytes_returned、next_offset、是否还有后续。
"""
    args_schema: type[BaseModel] = ReadContentArgs

    def _run(self, **kwargs: Any) -> Any:
        raise NotImplementedError("bind a client via .with_client(...)")

    async def _arun(self, **kwargs: Any) -> Any:
        raise NotImplementedError("bind a client via .with_client(...)")


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

    def _run(self, **kwargs: Any) -> Any:
        raise NotImplementedError("bind a client via .with_client(...)")

    async def _arun(self, **kwargs: Any) -> Any:
        raise NotImplementedError("bind a client via .with_client(...)")


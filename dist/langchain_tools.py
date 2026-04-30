"""Auto-generated. Do not edit. Run `python -m generators.to_langchain` to regenerate."""
from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field

TOOLS_VERSION = "0.1.0"


class SearchPapersArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    query: str | None = Field(None, description='BM25 关键词，匹配标题/摘要/作者。留空则纯靠 filters 过滤。')
    title_contains: str | None = Field(None, description='标题中必须包含的词（仅匹配 title 字段）。')
    abstract_contains: str | None = Field(None, description='摘要中必须包含的词（仅匹配 abstract 字段）。')
    authors: list[str] | None = Field(None, description='作者名匹配（任一命中）。')
    year_from: int | None = Field(None, description='起始发表年（含）。')
    year_to: int | None = Field(None, description='结束发表年（含）。')
    journals: list[str] | None = Field(None, description='')
    subjects: list[str] | None = Field(None, description='学科分类，如 "computer science"、"biology"。')
    filters_advanced: list[dict[str, Any]] | None = Field(None, description='高级过滤逃生舱（仅当上述字段不够用时使用）。')
    sort_by_year: str = Field('desc', description='')
    page: int = Field(1, description='')
    page_size: int = Field(10, description='')


class SearchPapersTool(BaseTool):
    name: str = "search_papers"
    description: str = """按结构化条件检索学术文献元数据（标题、作者、期刊、年份、摘要等）。
适用：「查找 Hinton 在 2020-2023 年发表的论文」「找 Nature 上关于 CRISPR 的近期文献」。
不适用：自然语言问答检索 → 用 semantic_search；查全文片段 → 用 read_content。
返回：论文元数据列表，每条含 doc_id、title、authors、abstract、journal、year 等。
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


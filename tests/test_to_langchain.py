from pathlib import Path
from generators.to_langchain import generate

FIXTURE = Path(__file__).parent / "fixtures" / "minimal_openapi.yaml"


def test_generates_langchain_module():
    code = generate(FIXTURE)
    # 必须能 compile
    compile(code, "<generated>", "exec")
    # 必须包含 BaseTool 子类
    assert "class DoFooTool" in code
    assert "from langchain_core.tools import BaseTool" in code
    # 必须有 args_schema 引用 pydantic
    assert "args_schema" in code
    assert "TOOLS_VERSION" in code


def test_preserves_openapi_defaults():
    """OpenAPI 中有 default 的字段应该作为 pydantic Field default 保留，而非 None。"""
    fixture_path = Path(__file__).parent / "fixtures" / "with_defaults_openapi.yaml"
    code = generate(fixture_path)
    # 验证 default 被透传
    assert "Field(10," in code or "Field(10, " in code, code  # top_k default 10
    assert "Field('balanced'," in code, code  # mode default 'balanced'
    # required 字段应该是 "..."
    assert "Field(..., description=" in code


def test_handles_multiline_description():
    """多行 description 应通过 repr() 转义为合法 Python 字符串。"""
    fixture_path = Path(__file__).parent / "fixtures" / "with_defaults_openapi.yaml"
    code = generate(fixture_path)
    # 必须能 compile（即转义正确）
    compile(code, "<generated>", "exec")
    # 多行内容应该用 \n 表示，而不是字面 newline
    assert "line1\\nline2" in code


def test_tools_dispatch_to_a_bound_client():
    """生成的工具必须真能执行：绑定 client 后 _arun 按 operationId 分发。

    历史问题：_run/_arun 一律抛 NotImplementedError，且提示指向从未实现的
    .with_client()。工具形似可执行实则不可用，而 mode 之类需要 client 翻译的
    参数会被使用者的裸 HTTP 调用静默丢弃。
    """
    code = generate(FIXTURE)
    assert "client: Any = None" in code
    assert "return await self.client.do_foo(**kwargs)" in code
    assert "def build_tools(client: Any)" in code
    assert "TOOL_CLASSES" in code
    # 不再指向不存在的方法
    assert "with_client" not in code


def test_generated_module_executes_end_to_end():
    """真正 import 生成的模块并跑一次调用，而不是只 compile。"""
    import asyncio
    import importlib.util
    import sys

    import pytest

    pytest.importorskip("langchain_core")

    code = generate(FIXTURE)
    module = importlib.util.module_from_spec(
        importlib.util.spec_from_loader("lc_tools_under_test", loader=None)
    )
    sys.modules["lc_tools_under_test"] = module
    try:
        exec(compile(code, "<generated>", "exec"), module.__dict__)

        seen = []

        class FakeClient:
            async def do_foo(self, **kwargs):
                seen.append(kwargs)
                return {"ok": True}

        tool = module.build_tools(FakeClient())[0]
        assert asyncio.run(tool.ainvoke({"name": "x"})) == {"ok": True}
        assert seen and seen[0]["name"] == "x"

        # 未绑定 client 要给出可操作的错误，而不是 AttributeError
        with pytest.raises(ValueError, match="build_tools"):
            asyncio.run(module.DoFooTool().ainvoke({"name": "x"}))

        # 同步入口明确指向异步用法
        with pytest.raises(NotImplementedError, match="async-only"):
            tool.invoke({"name": "x"})
    finally:
        sys.modules.pop("lc_tools_under_test", None)

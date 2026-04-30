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

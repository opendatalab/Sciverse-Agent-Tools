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

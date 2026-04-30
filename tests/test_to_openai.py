from pathlib import Path
from generators.to_openai import generate

FIXTURE = Path(__file__).parent / "fixtures" / "minimal_openapi.yaml"


def test_generates_openai_tool_format():
    result = generate(FIXTURE)
    assert result["version"] == "1.0.0"
    assert len(result["tools"]) == 1
    tool = result["tools"][0]
    assert tool["type"] == "function"
    assert tool["function"]["name"] == "do_foo"
    assert tool["function"]["description"] == "测试 tool。"
    assert tool["function"]["parameters"]["type"] == "object"
    assert tool["function"]["parameters"]["required"] == ["name"]
    assert tool["function"]["parameters"]["properties"]["name"]["type"] == "string"


def test_inlines_refs():
    """验证 $ref 被内联展开（OpenAI 不支持 $ref）"""
    result = generate(FIXTURE)
    tool = result["tools"][0]
    payload_str = str(tool)
    assert "$ref" not in payload_str

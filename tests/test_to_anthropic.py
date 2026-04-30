from pathlib import Path
from generators.to_anthropic import generate

FIXTURE = Path(__file__).parent / "fixtures" / "minimal_openapi.yaml"


def test_generates_anthropic_tool_format():
    result = generate(FIXTURE)
    assert result["version"] == "1.0.0"
    tool = result["tools"][0]
    assert tool["name"] == "do_foo"
    assert tool["description"] == "测试 tool。"
    assert tool["input_schema"]["type"] == "object"
    assert tool["input_schema"]["required"] == ["name"]


def test_no_refs_in_output():
    result = generate(FIXTURE)
    assert "$ref" not in str(result)

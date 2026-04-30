"""派生器：OpenAPI → LangChain BaseTool Python 模块。"""
from __future__ import annotations

from pathlib import Path

from ._common import get_request_schema, iter_operations, load_openapi


HEADER = '''"""Auto-generated. Do not edit. Run `python -m generators.to_langchain` to regenerate."""
from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field

TOOLS_VERSION = "{version}"
'''


def _camel(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("_"))


def _emit_args_model(class_name: str, schema: dict) -> str:
    lines = [f"class {class_name}(BaseModel):", "    model_config = ConfigDict(extra='forbid')"]
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    for prop_name, prop in properties.items():
        py_type = _json_type_to_python(prop)
        default = "..." if prop_name in required else "None"
        if default == "None" and not py_type.endswith(" | None"):
            py_type = f"{py_type} | None"
        desc = prop.get("description", "").replace('"', '\\"').replace("\n", " ")
        lines.append(f'    {prop_name}: {py_type} = Field({default}, description="{desc}")')
    if not properties:
        lines.append("    pass")
    return "\n".join(lines)


def _json_type_to_python(prop: dict) -> str:
    t = prop.get("type")
    if t == "string":
        return "str"
    if t == "integer":
        return "int"
    if t == "number":
        return "float"
    if t == "boolean":
        return "bool"
    if t == "array":
        item_t = _json_type_to_python(prop.get("items", {"type": "string"}))
        return f"list[{item_t}]"
    if t == "object":
        return "dict[str, Any]"
    return "Any"


def _emit_tool_class(operation_id: str, description: str, args_class: str) -> str:
    class_name = f"{_camel(operation_id)}Tool"
    desc = description.replace('"""', '\\"\\"\\"')
    return f'''
class {class_name}(BaseTool):
    name: str = "{operation_id}"
    description: str = """{desc}"""
    args_schema: type[BaseModel] = {args_class}

    def _run(self, **kwargs: Any) -> Any:
        raise NotImplementedError("bind a client via .with_client(...)")

    async def _arun(self, **kwargs: Any) -> Any:
        raise NotImplementedError("bind a client via .with_client(...)")
'''


def generate(openapi_path: Path) -> str:
    spec = load_openapi(openapi_path)
    version = spec["info"]["x-sciverse-tools-version"]
    out = [HEADER.format(version=version)]
    for _path, _method, op in iter_operations(spec):
        args_class = f"{_camel(op['operationId'])}Args"
        schema = get_request_schema(op, spec)
        out.append(_emit_args_model(args_class, schema))
        out.append(_emit_tool_class(op["operationId"], op.get("description", ""), args_class))
    return "\n\n".join(out) + "\n"


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    code = generate(root / "openapi.yaml")
    target = root / "dist" / "langchain_tools.py"
    target.write_text(code, encoding="utf-8")
    print(f"wrote {target.relative_to(root)}")


if __name__ == "__main__":
    main()

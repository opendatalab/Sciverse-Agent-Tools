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

_NO_CLIENT = (
    "No Sciverse client bound. Build these tools with build_tools(client), passing a "
    "sciverse.AgentToolsClient — it holds the credentials and translates arguments such "
    "as `mode` into the parameters the API actually accepts."
)

# The Sciverse client is async-only, and calling asyncio.run() from inside a running
# event loop raises. Async-only tools are a standard LangChain pattern: drive them with
# ainvoke() / an async executor.
_SYNC_UNSUPPORTED = (
    "{{name}} is async-only. Use `await tool.ainvoke(...)` or an async agent executor."
)
'''


def _camel(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("_"))


def _emit_args_model(class_name: str, schema: dict) -> str:
    lines = [f"class {class_name}(BaseModel):", "    model_config = ConfigDict(extra='forbid')"]
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    for prop_name, prop in properties.items():
        py_type = _json_type_to_python(prop)
        if prop_name in required:
            default_expr = "..."
        elif "default" in prop:
            default_expr = repr(prop["default"])
        else:
            default_expr = "None"
        if default_expr == "None" and not py_type.endswith(" | None"):
            py_type = f"{py_type} | None"
        desc = prop.get("description", "")
        lines.append(f'    {prop_name}: {py_type} = Field({default_expr}, description={repr(desc)})')
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
    client: Any = None

    def _run(self, **kwargs: Any) -> Any:
        raise NotImplementedError(_SYNC_UNSUPPORTED.format(name=self.name))

    async def _arun(self, **kwargs: Any) -> Any:
        if self.client is None:
            raise ValueError(_NO_CLIENT)
        return await self.client.{operation_id}(**kwargs)
'''


FOOTER = '''
TOOL_CLASSES: list[type[BaseTool]] = [{class_list}]


def build_tools(client: Any) -> list[BaseTool]:
    """Return every Sciverse tool bound to `client`, ready to hand to an agent.

    `client` is a `sciverse.AgentToolsClient`. Bind through it rather than calling the
    HTTP API yourself: it owns credentials, retries, and the argument translation the
    raw endpoints do not perform (an unmapped `mode`, for one, is silently ignored
    upstream, so `quality` would quietly behave like `balanced`).

    The tools are async-only — drive them with `ainvoke()` or an async executor.
    """
    return [cls(client=client) for cls in TOOL_CLASSES]
'''


def generate(openapi_path: Path) -> str:
    spec = load_openapi(openapi_path)
    version = spec["info"]["x-sciverse-tools-version"]
    out = [HEADER.format(version=version)]
    class_names = []
    for _path, _method, op in iter_operations(spec):
        args_class = f"{_camel(op['operationId'])}Args"
        schema = get_request_schema(op, spec)
        out.append(_emit_args_model(args_class, schema))
        out.append(_emit_tool_class(op["operationId"], op.get("description", ""), args_class))
        class_names.append(f"{_camel(op['operationId'])}Tool")
    out.append(FOOTER.format(class_list=", ".join(class_names)))
    return "\n\n".join(out) + "\n"


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    code = generate(root / "openapi.yaml")
    target = root / "dist" / "langchain_tools.py"
    target.write_text(code, encoding="utf-8")
    print(f"wrote {target.relative_to(root)}")


if __name__ == "__main__":
    main()

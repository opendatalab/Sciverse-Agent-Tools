"""派生器：OpenAPI → OpenAI tool calling 格式。"""
from __future__ import annotations

import json
from pathlib import Path

from ._common import get_request_schema, iter_operations, load_openapi


def generate(openapi_path: Path) -> dict:
    spec = load_openapi(openapi_path)
    version = spec["info"]["x-sciverse-tools-version"]

    tools = []
    for _path, _method, op in iter_operations(spec):
        tools.append({
            "type": "function",
            "function": {
                "name": op["operationId"],
                "description": op.get("description", op.get("summary", "")).strip(),
                "parameters": get_request_schema(op, spec),
            },
        })
    return {"version": version, "tools": tools}


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    out = generate(root / "openapi.yaml")
    target = root / "dist" / "openai-tools.json"
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {target.relative_to(root)}: {len(out['tools'])} tools")


if __name__ == "__main__":
    main()

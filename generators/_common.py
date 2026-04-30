"""派生器共享工具：加载 OpenAPI、$ref 内联、operation 抽取。"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml


def load_openapi(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def inline_refs(node: Any, root: dict[str, Any]) -> Any:
    """递归把 {$ref: "#/..."} 替换为指向的实际节点（深拷贝）。"""
    if isinstance(node, dict):
        if "$ref" in node and len(node) == 1:
            ref = node["$ref"]
            if not ref.startswith("#/"):
                raise ValueError(f"only local $ref supported, got {ref!r}")
            target = root
            for part in ref[2:].split("/"):
                target = target[part]
            return inline_refs(copy.deepcopy(target), root)
        return {k: inline_refs(v, root) for k, v in node.items()}
    if isinstance(node, list):
        return [inline_refs(item, root) for item in node]
    return node


def iter_operations(spec: dict[str, Any]):
    """yield (path, method, op) for each POST/GET path."""
    for path, methods in spec.get("paths", {}).items():
        for method, op in methods.items():
            if method in ("post", "get"):
                yield path, method, op


def get_request_schema(operation: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    """提取 operation 的输入 schema：POST 用 requestBody，GET 用 parameters 拼装。"""
    if "requestBody" in operation:
        schema = operation["requestBody"]["content"]["application/json"]["schema"]
        return inline_refs(schema, spec)

    properties: dict[str, Any] = {}
    required: list[str] = []
    for param in operation.get("parameters", []):
        if param.get("in") != "query":
            continue
        prop = inline_refs(param["schema"], spec)
        if "description" in param:
            prop["description"] = param["description"]
        properties[param["name"]] = prop
        if param.get("required"):
            required.append(param["name"])
    return {"type": "object", "properties": properties, "required": required}

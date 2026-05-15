"""端到端示例：使用 OpenAI function calling + SciVerse 五个 tool。

`OPENAI_TOOLS` 包含全部 5 个 schema；dispatch 表必须全覆盖，否则模型
调到没接的 tool 时 KeyError。

运行：
    pip install openai sciverse
    export SCIVERSE_API_TOKEN=...
    export OPENAI_API_KEY=...
    python examples/python_openai_function_call.py
"""
import asyncio
import base64
import json
import os

from openai import OpenAI
from sciverse import OPENAI_TOOLS, AgentToolsClient

BASE_URL = os.environ.get("SCIVERSE_BASE_URL", "https://api.sciverse.space")
TOKEN = os.environ["SCIVERSE_API_TOKEN"]


async def call_tool(sv: AgentToolsClient, name: str, args: dict):
    if name == "get_resource":
        img_bytes, mime = await sv.get_resource(**args)
        return {"data": base64.b64encode(img_bytes).decode(), "mime_type": mime}
    handler = {
        "list_catalog": sv.list_catalog,
        "search_papers": sv.search_papers,
        "semantic_search": sv.semantic_search,
        "read_content": sv.read_content,
    }[name]
    return await handler(**args)


async def main(question: str) -> None:
    openai = OpenAI()
    async with AgentToolsClient(base_url=BASE_URL, token=TOKEN) as sv:
        messages = [{"role": "user", "content": question}]
        for _ in range(5):
            resp = openai.chat.completions.create(
                model="gpt-4o",
                tools=OPENAI_TOOLS,
                messages=messages,
            )
            msg = resp.choices[0].message
            messages.append(msg.model_dump(exclude_none=True))
            if not msg.tool_calls:
                print("\n=== 回答 ===\n", msg.content)
                return
            for call in msg.tool_calls:
                args = json.loads(call.function.arguments)
                result = await call_tool(sv, call.function.name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, ensure_ascii=False)[:8000],
                })


if __name__ == "__main__":
    asyncio.run(main("最近三年关于蛋白质结构预测有哪些重要论文？"))

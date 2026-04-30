"""端到端示例：使用 OpenAI function calling + SciVerse 三个 tool。

运行：
    pip install openai sciverse-agent-tools
    export SCIVERSE_API_TOKEN=...
    export OPENAI_API_KEY=...
    python examples/python_openai_function_call.py
"""
import asyncio
import json
import os

from openai import OpenAI
from sciverse_agent_tools import OPENAI_TOOLS, AgentToolsClient

BASE_URL = os.environ.get("SCIVERSE_BASE_URL", "https://sciverse.space/api")
TOKEN = os.environ["SCIVERSE_API_TOKEN"]


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
                handler = {
                    "search_papers": sv.search_papers,
                    "semantic_search": sv.semantic_search,
                    "read_content": sv.read_content,
                }[call.function.name]
                result = await handler(**args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, ensure_ascii=False)[:8000],
                })


if __name__ == "__main__":
    asyncio.run(main("最近三年关于蛋白质结构预测有哪些重要论文？"))

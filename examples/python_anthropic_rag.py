"""端到端示例：使用 Anthropic + SciVerse 三个 tool 跑一次 RAG。

运行：
    pip install anthropic sciverse-agent-tools
    export SCIVERSE_API_TOKEN=...
    export ANTHROPIC_API_KEY=...
    python examples/python_anthropic_rag.py
"""
import asyncio
import json
import os

from anthropic import Anthropic
from sciverse_agent_tools import ANTHROPIC_TOOLS, AgentToolsClient

BASE_URL = os.environ.get("SCIVERSE_BASE_URL", "https://sciverse.space/api")
TOKEN = os.environ["SCIVERSE_API_TOKEN"]


async def call_tool(client: AgentToolsClient, name: str, args: dict) -> dict:
    if name == "search_papers":
        return await client.search_papers(**args)
    if name == "semantic_search":
        return await client.semantic_search(**args)
    if name == "read_content":
        return await client.read_content(**args)
    raise ValueError(f"unknown tool {name}")


async def main(question: str) -> None:
    anthropic = Anthropic()
    async with AgentToolsClient(base_url=BASE_URL, token=TOKEN) as sv:
        messages = [{"role": "user", "content": question}]
        for _ in range(5):  # 最多 5 轮 tool 调用
            resp = anthropic.messages.create(
                model="claude-opus-4-7",
                max_tokens=4096,
                tools=ANTHROPIC_TOOLS,
                messages=messages,
            )
            messages.append({"role": "assistant", "content": resp.content})
            if resp.stop_reason != "tool_use":
                print("\n=== 回答 ===")
                for block in resp.content:
                    if block.type == "text":
                        print(block.text)
                return
            tool_results = []
            for block in resp.content:
                if block.type == "tool_use":
                    print(f"[tool] {block.name}({json.dumps(block.input, ensure_ascii=False)[:120]}...)")
                    out = await call_tool(sv, block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(out, ensure_ascii=False)[:8000],
                    })
            messages.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    asyncio.run(main("Transformer 自注意力机制是怎么工作的？给我引用支持。"))

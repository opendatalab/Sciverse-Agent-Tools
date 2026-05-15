"""端到端示例：使用 Anthropic + SciVerse 五个 tool 跑一次 RAG。

`ANTHROPIC_TOOLS` 包含全部 5 个 schema（list_catalog / search_papers /
semantic_search / read_content / get_resource），dispatch 表必须覆盖
全部，否则模型一调没接的 tool 就会 fall through。

运行：
    pip install anthropic sciverse
    export SCIVERSE_API_TOKEN=...
    export ANTHROPIC_API_KEY=...
    python examples/python_anthropic_rag.py
"""
import asyncio
import base64
import json
import os

from anthropic import Anthropic
from sciverse import ANTHROPIC_TOOLS, AgentToolsClient

BASE_URL = os.environ.get("SCIVERSE_BASE_URL", "https://api.sciverse.space")
TOKEN = os.environ["SCIVERSE_API_TOKEN"]


async def call_tool(client: AgentToolsClient, name: str, args: dict) -> dict:
    if name == "list_catalog":
        return await client.list_catalog(**args)
    if name == "search_papers":
        return await client.search_papers(**args)
    if name == "semantic_search":
        return await client.semantic_search(**args)
    if name == "read_content":
        return await client.read_content(**args)
    if name == "get_resource":
        # 二进制 → base64，agent 可直接当 image block 使用
        img_bytes, mime = await client.get_resource(**args)
        return {"data": base64.b64encode(img_bytes).decode(), "mime_type": mime}
    raise ValueError(f"unknown tool {name}")


async def main(question: str) -> None:
    anthropic = Anthropic()
    async with AgentToolsClient(base_url=BASE_URL, token=TOKEN) as sv:
        messages = [{"role": "user", "content": question}]
        for _ in range(5):  # 最多 5 轮 tool 调用
            resp = anthropic.messages.create(
                # 按需替换为最新 model id 或 alias（如 claude-opus-latest）
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

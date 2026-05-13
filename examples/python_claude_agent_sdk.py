"""端到端示例：Claude Agent SDK + SciVerse MCP server 跑一次 RAG。

与 `python_anthropic_rag.py` 的区别：
- 该示例用 `anthropic` SDK 的 `messages.create` 原生 tool calling 回环
  + `sciverse-agent-tools` Python SDK 内嵌的 ANTHROPIC_TOOLS 常量
- 本示例用 `claude-agent-sdk`，通过 `mcp_servers` 配置直接挂 sciverse-mcp-server，
  Claude Code 风格的 agent loop 由 SDK 全权处理 —— 这是 coding-agent 风格应用的主流方式

运行：
    pip install claude-agent-sdk
    npm install -g sciverse-mcp-server  # 或省略，由 SDK 通过 npx 拉
    export SCIVERSE_API_TOKEN=...
    export ANTHROPIC_API_KEY=...
    python examples/python_claude_agent_sdk.py
"""
import anyio
import os

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient


async def main() -> None:
    options = ClaudeAgentOptions(
        # mcp_servers：直接挂 sciverse-mcp-server，Claude Code agent loop
        # 自动 spawn 进程、转发 tool list / call。
        mcp_servers={
            "sciverse": {
                "command": "npx",
                "args": ["-y", "sciverse-mcp-server"],
                "env": {
                    "SCIVERSE_API_TOKEN": os.environ["SCIVERSE_API_TOKEN"],
                },
            },
        },
        # 显式允许 sciverse 暴露的 3 个 tool；默认 Claude Code 会请求确认，
        # agent 场景下用 allowed_tools 跳过 prompt。
        allowed_tools=[
            "mcp__sciverse__search_papers",
            "mcp__sciverse__semantic_search",
            "mcp__sciverse__read_content",
        ],
        # 按需指定 model（默认走 SDK 配置的 Claude Code 默认模型）
        # 例如：model="claude-opus-4-7" 或 model="claude-sonnet-4-6"
        system_prompt=(
            "你是学术文献检索助手。优先用 semantic_search 找相关 chunk，"
            "需要扩展上下文时用 read_content。每个引用都附 doc_id 与 title。"
        ),
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            "找 3 篇关于 Transformer 注意力机制的论文，每篇引用一段原文。"
        )
        async for message in client.receive_response():
            # message 类型：AssistantMessage / ToolUseBlock / TextBlock / ResultMessage 等。
            # 简单 demo：把所有 text 打出来。
            for block in getattr(message, "content", []) or []:
                if hasattr(block, "text"):
                    print(block.text, end="", flush=True)
        print()  # 末尾换行


if __name__ == "__main__":
    anyio.run(main)

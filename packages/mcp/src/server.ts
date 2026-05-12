// MCP server：注册 list_tools / call_tool 两个 handler。
// TODO: 后续可加 SSE / Streamable HTTP 形态（目前只支持 stdio，覆盖主流 coding agent）。

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

import type { Config } from "./config.js";
import { TOOLS, TOOLS_VERSION } from "./generated/tools.js";
import { executeTool } from "./tools.js";

export function createServer(config: Config): Server {
  const server = new Server(
    {
      name: "sciverse-mcp",
      version: TOOLS_VERSION,
    },
    {
      capabilities: {
        tools: {},
      },
    },
  );

  server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: TOOLS,
  }));

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    const result = await executeTool(config, name, (args ?? {}) as Record<string, unknown>);
    // SDK 的 CallTool 响应 schema 含可选 _meta / structuredContent 等字段，我们只用 content + isError。
    return result as unknown as { content: { type: "text"; text: string }[]; isError: boolean };
  });

  return server;
}

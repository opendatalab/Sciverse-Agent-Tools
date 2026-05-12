#!/usr/bin/env node
// 入口：从 stdio 启动 MCP server。
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { ConfigError, loadConfig } from "./config.js";
import { createServer } from "./server.js";

async function main(): Promise<void> {
  let config;
  try {
    config = loadConfig();
  } catch (err) {
    if (err instanceof ConfigError) {
      process.stderr.write(`[sciverse-mcp] ${err.message}\n`);
      process.exit(2);
    }
    throw err;
  }
  const server = createServer(config);
  const transport = new StdioServerTransport();
  await server.connect(transport);
  // 进程长驻；stdio 关闭时 transport 会触发退出。
}

main().catch((err) => {
  process.stderr.write(`[sciverse-mcp] fatal: ${err instanceof Error ? err.stack ?? err.message : String(err)}\n`);
  process.exit(1);
});

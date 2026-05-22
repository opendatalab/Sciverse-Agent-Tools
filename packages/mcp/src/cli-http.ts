#!/usr/bin/env node
// 入口：以 Streamable-HTTP 形态启动 MCP server，供 SCP Hub 等公网调用方使用。
//
// 设计要点：
//   1. 与 stdio 入口 (cli.ts) 共享 createServer(config)，业务逻辑零改动；transport 解耦。
//   2. 每个 MCP session 独立一份 Server + Transport，避免不同会话间状态串扰；
//      session id 由 SDK 在 initialize 阶段通过 crypto.randomUUID() 分配，
//      存到内存 Map，容器重启即清空。Phase 1 单副本部署可接受。
//   3. 边缘信任模型：本进程不校验 SCP-HUB-API-KEY，由 Ingress IP 白名单兜底；
//      Phase 1.5 再补 header 校验。
//   4. /healthz 返回 200 纯文本，供 K8s readiness/liveness probe 使用。
//   5. 配置错误 (loadConfig 抛 ConfigError) 时 stderr 输出并 exit(2)，
//      与 cli.ts 行为一致。
import { randomUUID } from "node:crypto";
import { createServer as createHttpServer, type IncomingMessage, type ServerResponse } from "node:http";

import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { isInitializeRequest } from "@modelcontextprotocol/sdk/types.js";

import { ConfigError, loadConfig, type Config } from "./config.js";
import { createServer } from "./server.js";

const DEFAULT_PORT = 8080;
const MCP_PATH = "/mcp";
const HEALTHZ_PATH = "/healthz";

// 读完整请求体到 Buffer；遇到客户端断开等错误会 reject。
function readBody(req: IncomingMessage): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    req.on("data", (chunk: Buffer) => chunks.push(chunk));
    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", reject);
  });
}

// 把 raw body 解析为 JSON（POST /mcp 必为 JSON-RPC payload）；空 body 返回 undefined。
function parseJsonBody(buf: Buffer): unknown {
  if (buf.length === 0) return undefined;
  try {
    return JSON.parse(buf.toString("utf8"));
  } catch {
    return undefined;
  }
}

// 用 405 + JSON-RPC error 拒绝非 POST /mcp 之外的请求里 transport 不接受的方法。
function writeJsonRpcError(res: ServerResponse, status: number, message: string): void {
  res.statusCode = status;
  res.setHeader("content-type", "application/json");
  res.end(
    JSON.stringify({
      jsonrpc: "2.0",
      error: { code: -32000, message },
      id: null,
    }),
  );
}

export interface HttpServerHandle {
  // 真正监听到的端口（传 0 时由内核分配，便于测试取真实端口）。
  port: number;
  // 优雅停服：关闭 HTTP server + 所有未结束的 transport。
  close: () => Promise<void>;
}

// 启动 HTTP server，返回句柄。导出供测试复用，避免 spawn 子进程。
export async function startHttpServer(
  config: Config,
  options: { port?: number; host?: string } = {},
): Promise<HttpServerHandle> {
  const port = options.port ?? DEFAULT_PORT;
  const host = options.host ?? "0.0.0.0";

  // session id → { transport, server } 映射。Phase 1 进程内 Map 即可。
  const sessions = new Map<
    string,
    { transport: StreamableHTTPServerTransport; close: () => Promise<void> }
  >();

  const handleMcp = async (req: IncomingMessage, res: ServerResponse): Promise<void> => {
    const method = req.method ?? "GET";
    const sessionId = req.headers["mcp-session-id"];
    const sessionIdStr = Array.isArray(sessionId) ? sessionId[0] : sessionId;

    // POST：初始化 or 后续 JSON-RPC 调用
    if (method === "POST") {
      const raw = await readBody(req);
      const body = parseJsonBody(raw);

      // 已有 session：复用 transport
      if (sessionIdStr && sessions.has(sessionIdStr)) {
        const entry = sessions.get(sessionIdStr)!;
        await entry.transport.handleRequest(req, res, body);
        return;
      }

      // 无 session + 是 initialize：新建 transport + Server
      if (!sessionIdStr && isInitializeRequest(body)) {
        const transport = new StreamableHTTPServerTransport({
          sessionIdGenerator: () => randomUUID(),
          onsessioninitialized: (sid) => {
            // 在 initialize 完成时把 transport 注册进表；规避请求先于 sessionId 落表的竞态。
            sessions.set(sid, {
              transport,
              close: async () => {
                await transport.close();
                await server.close();
              },
            });
          },
        });
        transport.onclose = () => {
          const sid = transport.sessionId;
          if (sid && sessions.has(sid)) {
            sessions.delete(sid);
          }
        };
        const server = createServer(config);
        await server.connect(transport);
        await transport.handleRequest(req, res, body);
        return;
      }

      // 既无 session 又不是 initialize：按 SDK 规范返 400
      writeJsonRpcError(res, 400, "Bad Request: No valid session ID provided");
      return;
    }

    // GET (SSE 长轮询) / DELETE (session 终止)：必须带 session id
    if (method === "GET" || method === "DELETE") {
      if (!sessionIdStr || !sessions.has(sessionIdStr)) {
        res.statusCode = 400;
        res.setHeader("content-type", "text/plain");
        res.end("Invalid or missing session ID");
        return;
      }
      const entry = sessions.get(sessionIdStr)!;
      await entry.transport.handleRequest(req, res);
      return;
    }

    res.statusCode = 405;
    res.setHeader("allow", "POST, GET, DELETE");
    res.end();
  };

  const httpServer = createHttpServer((req, res) => {
    const url = req.url ?? "/";
    // K8s probe
    if (url === HEALTHZ_PATH || url.startsWith(`${HEALTHZ_PATH}?`)) {
      res.statusCode = 200;
      res.setHeader("content-type", "text/plain; charset=utf-8");
      res.end("ok");
      return;
    }
    if (url === MCP_PATH || url.startsWith(`${MCP_PATH}?`) || url.startsWith(`${MCP_PATH}/`)) {
      handleMcp(req, res).catch((err) => {
        process.stderr.write(
          `[sciverse-mcp] handleRequest error: ${err instanceof Error ? err.stack ?? err.message : String(err)}\n`,
        );
        if (!res.headersSent) {
          writeJsonRpcError(res, 500, "Internal server error");
        } else {
          res.end();
        }
      });
      return;
    }
    res.statusCode = 404;
    res.setHeader("content-type", "text/plain");
    res.end("Not Found");
  });

  await new Promise<void>((resolve, reject) => {
    httpServer.once("error", reject);
    httpServer.listen(port, host, () => {
      httpServer.off("error", reject);
      resolve();
    });
  });

  const address = httpServer.address();
  const actualPort = typeof address === "object" && address ? address.port : port;

  return {
    port: actualPort,
    close: async () => {
      // 先关 HTTP server（停止接受新连接），再清理所有活动 session。
      await new Promise<void>((resolve, reject) => {
        httpServer.close((err) => (err ? reject(err) : resolve()));
      });
      const entries = Array.from(sessions.values());
      sessions.clear();
      await Promise.all(entries.map((e) => e.close().catch(() => undefined)));
    },
  };
}

async function main(): Promise<void> {
  // HTTP 入口默认 channel = "scp"（区分 stdio 入口的 "mcp"），用于下游 X-Request-ID 归因。
  // 显式设了 SCIVERSE_MCP_CHANNEL 则不覆盖（允许部署侧自定义）。
  if (!process.env.SCIVERSE_MCP_CHANNEL?.trim()) {
    process.env.SCIVERSE_MCP_CHANNEL = "scp";
  }
  let config: Config;
  try {
    config = loadConfig();
  } catch (err) {
    if (err instanceof ConfigError) {
      process.stderr.write(`[sciverse-mcp] ${err.message}\n`);
      process.exit(2);
    }
    throw err;
  }

  const portEnv = process.env.PORT;
  const port = portEnv ? Number.parseInt(portEnv, 10) : DEFAULT_PORT;
  if (!Number.isFinite(port) || port < 0 || port > 65535) {
    process.stderr.write(`[sciverse-mcp] invalid PORT: ${portEnv}\n`);
    process.exit(2);
  }

  const handle = await startHttpServer(config, { port });
  process.stderr.write(`[sciverse-mcp] listening on :${handle.port}${MCP_PATH}\n`);

  // 收到信号时优雅退出
  const shutdown = async (signal: string): Promise<void> => {
    process.stderr.write(`[sciverse-mcp] received ${signal}, shutting down\n`);
    try {
      await handle.close();
    } finally {
      process.exit(0);
    }
  };
  process.on("SIGINT", () => void shutdown("SIGINT"));
  process.on("SIGTERM", () => void shutdown("SIGTERM"));
}

// 只有作为入口执行时才 main()；被 import（如测试）时不自动起进程。
const isEntrypoint =
  typeof process.argv[1] === "string" &&
  import.meta.url === new URL(`file://${process.argv[1]}`).href;
if (isEntrypoint) {
  main().catch((err) => {
    process.stderr.write(
      `[sciverse-mcp] fatal: ${err instanceof Error ? err.stack ?? err.message : String(err)}\n`,
    );
    process.exit(1);
  });
}

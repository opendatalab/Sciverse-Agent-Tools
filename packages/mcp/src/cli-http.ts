#!/usr/bin/env node
// 入口：以 Streamable-HTTP 形态启动 MCP server，供 SCP Hub 等公网调用方使用。
//
// 设计要点：
//   1. 与 stdio 入口 (cli.ts) 共享 createServer(config)，业务逻辑零改动；transport 解耦。
//   2. 每个 MCP session 独立一份 Server + Transport，避免不同会话间状态串扰；
//      session id 由 SDK 在 initialize 阶段通过 crypto.randomUUID() 分配，
//      存到内存 Map，容器重启即清空。Phase 1 单副本部署可接受。
//   3. 鉴权双通道（Phase 1.5，http-auth.ts）：Authorization: Bearer 透传（channel
//      "remote"）或来源 IP ∈ 可信 IP 白名单走内置 token（channel 沿用配置）；
//      两者皆无 → 401。session 与首次判定的凭据绑定，后续请求不一致同样 401。
//      XFF 仅在 TCP 对端命中信任代理网段时采信（默认永不），防直连伪造。
//   4. /healthz 返回 200 纯文本，供 K8s readiness/liveness probe 使用（不鉴权、不记日志）。
//   5. 配置错误 (loadConfig 抛 ConfigError) 时 stderr 输出并 exit(2)，
//      与 cli.ts 行为一致。
//   6. 每个 /mcp 请求向 stdout 写一行结构化日志（SLS 经 aliyun_logs_app_logs=stdout
//      采集）；恒不落 token。
import { randomUUID } from "node:crypto";
import { createServer as createHttpServer, type IncomingMessage, type ServerResponse } from "node:http";

import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { isInitializeRequest } from "@modelcontextprotocol/sdk/types.js";

import { ConfigError, loadConfig, type Config } from "./config.js";
import { loadAuthOptions, resolveLane, type AuthOptions, type Lane } from "./http-auth.js";
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

// 每请求日志的可变元信息：handleMcp 边处理边填，响应关闭时统一写一行。
interface ReqLogMeta {
  lane: Lane | "anon";
  rpc: string;
  session: string;
}

// 从 JSON-RPC payload 提取方法名（batch 用 + 连接），仅用于日志。
function rpcMethodOf(body: unknown): string {
  if (Array.isArray(body)) {
    const names = body
      .map((m) => (m && typeof m === "object" ? (m as { method?: string }).method : undefined))
      .filter((s): s is string => typeof s === "string");
    return names.length > 0 ? names.join("+") : "batch";
  }
  if (body && typeof body === "object") {
    const method = (body as { method?: unknown }).method;
    if (typeof method === "string") return method;
  }
  return "-";
}

function writeUnauthorized(res: ServerResponse): void {
  res.setHeader("www-authenticate", "Bearer");
  writeJsonRpcError(
    res,
    401,
    "Unauthorized: provide `Authorization: Bearer <sciverse token>` (get one at https://sciverse.space)",
  );
}

// 启动 HTTP server，返回句柄。导出供测试复用，避免 spawn 子进程。
export async function startHttpServer(
  config: Config,
  options: { port?: number; host?: string; auth?: AuthOptions } = {},
): Promise<HttpServerHandle> {
  const port = options.port ?? DEFAULT_PORT;
  const host = options.host ?? "0.0.0.0";
  const auth = options.auth ?? loadAuthOptions();

  // session id → transport + 首次判定的凭据（lane/token 绑定，防 session id 被盗用）。
  const sessions = new Map<
    string,
    {
      transport: StreamableHTTPServerTransport;
      close: () => Promise<void>;
      lane: Lane;
      token: string;
    }
  >();

  const handleMcp = async (
    req: IncomingMessage,
    res: ServerResponse,
    meta: ReqLogMeta,
  ): Promise<void> => {
    const method = req.method ?? "GET";
    const sessionId = req.headers["mcp-session-id"];
    const sessionIdStr = Array.isArray(sessionId) ? sessionId[0] : sessionId;
    if (sessionIdStr) meta.session = sessionIdStr.slice(0, 8);

    // 鉴权判定先于一切处理；不通过的请求不进 MCP 协议层。
    const decision = resolveLane(req, config, auth);
    if (!decision) {
      writeUnauthorized(res);
      return;
    }
    meta.lane = decision.lane;

    // 复用 session 时校验凭据与首次判定一致；不一致按未授权处理（不泄露 session 存在性）。
    const boundEntry = sessionIdStr ? sessions.get(sessionIdStr) : undefined;
    if (boundEntry && (boundEntry.lane !== decision.lane || boundEntry.token !== decision.token)) {
      writeUnauthorized(res);
      return;
    }

    // POST：初始化 or 后续 JSON-RPC 调用
    if (method === "POST") {
      const raw = await readBody(req);
      const body = parseJsonBody(raw);
      meta.rpc = rpcMethodOf(body);

      // 已有 session：复用 transport
      if (boundEntry) {
        await boundEntry.transport.handleRequest(req, res, body);
        return;
      }

      // 无 session + 是 initialize：新建 transport + Server（携带本 session 的凭据）
      if (!sessionIdStr && isInitializeRequest(body)) {
        const transport = new StreamableHTTPServerTransport({
          sessionIdGenerator: () => randomUUID(),
          onsessioninitialized: (sid) => {
            // 在 initialize 完成时把 transport 注册进表；规避请求先于 sessionId 落表的竞态。
            sessions.set(sid, {
              transport,
              lane: decision.lane,
              token: decision.token,
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
        // 每 session 一份 config：token/channel 来自通道判定，其余沿用进程配置。
        const server = createServer({ ...config, token: decision.token, channel: decision.channel });
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
      if (!boundEntry) {
        res.statusCode = 400;
        res.setHeader("content-type", "text/plain");
        res.end("Invalid or missing session ID");
        return;
      }
      await boundEntry.transport.handleRequest(req, res);
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
      const startedAt = Date.now();
      const meta: ReqLogMeta = { lane: "anon", rpc: "-", session: "-" };
      // "close" 同时覆盖正常结束与客户端中断；一行 key=value 结构化日志（恒不含 token）。
      res.once("close", () => {
        process.stdout.write(
          `[sciverse-mcp] req method=${req.method ?? "-"} path=${MCP_PATH} rpc=${meta.rpc} ` +
            `lane=${meta.lane} session=${meta.session} status=${res.statusCode} ` +
            `dur_ms=${Date.now() - startedAt}\n`,
        );
      });
      handleMcp(req, res, meta).catch((err) => {
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
  // HTTP 入口默认 channel = "scp"（区分 stdio 入口的 "mcp"），用于下游 X-Sciverse-Source 归因。
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

  const auth = loadAuthOptions();
  if (auth.trustedIps.size === 0) {
    process.stderr.write(
      "[sciverse-mcp] SCIVERSE_MCP_TRUSTED_IPS 未配置：可信 IP 通道关闭，所有请求都需要 Authorization\n",
    );
  }
  const handle = await startHttpServer(config, { port, auth });
  const proxyCount = auth.trustedProxies.v4.length + auth.trustedProxies.exact.size;
  process.stderr.write(
    `[sciverse-mcp] listening on :${handle.port}${MCP_PATH} ` +
      `(trusted_ips=${auth.trustedIps.size} trusted_proxies=${proxyCount} hops=${auth.trustedHops})\n`,
  );

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

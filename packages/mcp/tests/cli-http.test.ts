// HTTP transport 端到端测试：
//   - 起本地 HTTP server（PORT=0 让内核分配端口）
//   - 用 MCP SDK 的 StreamableHTTPClientTransport + Client 完整跑 initialize → tools/list → tools/call
//   - 业务层 fetch 全部用 vi.stubGlobal mock，避免触达真实 api.sciverse.space
//   - 同时覆盖 /healthz + 大 payload（≈500KB base64）不截断
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

import { startHttpServer, type HttpServerHandle } from "../src/cli-http.js";
import { parseTrustedProxies } from "../src/http-auth.js";
import type { Config } from "../src/config.js";

const CONFIG: Config = {
  token: "sv-test",
  baseUrl: "https://api.sciverse.space",
  channel: "scp",
};

// 测试用鉴权配置：把本地回环列为可信 IP（不配信任代理 → XFF 不采信，直接取 socket 地址），
// 让既有 e2e 用例走 trusted 通道、无需携带 Authorization。
const LOCAL_TRUSTED_AUTH = {
  trustedIps: new Set(["127.0.0.1", "::1"]),
  trustedProxies: parseTrustedProxies(""),
  trustedHops: 1,
};

// 业务层 fetch (tools.ts 内的 fetch) 用 vi.stubGlobal mock；
// 但 MCP client 自己也走 global fetch 访问本地 HTTP server——
// 解决办法：mock 函数里只拦截 sciverse.space 域，其余 fallthrough 到原始 fetch。
function stubUpstreamFetch(handler: (url: string, init: RequestInit) => Response | Promise<Response>): void {
  const originalFetch = globalThis.fetch;
  const fn = vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    if (url.includes("sciverse.space")) {
      return handler(url, init ?? {});
    }
    // 本地回环（MCP client → 我们的 HTTP server）走原 fetch
    return originalFetch(input as RequestInfo, init);
  });
  vi.stubGlobal("fetch", fn);
}

describe("cli-http: Streamable-HTTP transport", () => {
  let handle: HttpServerHandle | undefined;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(async () => {
    if (handle) {
      await handle.close();
      handle = undefined;
    }
    vi.unstubAllGlobals();
  });

  it("/healthz 返回 200 + 'ok'", async () => {
    handle = await startHttpServer(CONFIG, { port: 0, host: "127.0.0.1", auth: LOCAL_TRUSTED_AUTH });
    const res = await fetch(`http://127.0.0.1:${handle.port}/healthz`);
    expect(res.status).toBe(200);
    expect(await res.text()).toBe("ok");
  });

  it("未知路径返回 404", async () => {
    handle = await startHttpServer(CONFIG, { port: 0, host: "127.0.0.1", auth: LOCAL_TRUSTED_AUTH });
    const res = await fetch(`http://127.0.0.1:${handle.port}/nope`);
    expect(res.status).toBe(404);
  });

  it("完整跑通 initialize → tools/list → tools/call (semantic_search)", async () => {
    handle = await startHttpServer(CONFIG, { port: 0, host: "127.0.0.1", auth: LOCAL_TRUSTED_AUTH });

    // mock 下游 sciverse API：返回一组 fake hits
    stubUpstreamFetch(async (url) => {
      expect(url).toBe("https://api.sciverse.space/agentic-search");
      return new Response(JSON.stringify({ hits: [{ doc_id: "p_x", score: 0.9 }] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    });

    const client = new Client(
      { name: "test-client", version: "0.0.0" },
      { capabilities: {} },
    );
    const transport = new StreamableHTTPClientTransport(
      new URL(`http://127.0.0.1:${handle.port}/mcp`),
    );
    await client.connect(transport);

    // initialize 后应分配到 session id
    expect(transport.sessionId).toBeTruthy();

    const tools = await client.listTools();
    expect(tools.tools.length).toBeGreaterThan(0);
    const names = tools.tools.map((t) => t.name);
    expect(names).toContain("semantic_search");

    const result = await client.callTool({
      name: "semantic_search",
      arguments: { query: "transformer", top_k: 3 },
    });
    expect(result.isError).toBeFalsy();
    const content = result.content as { type: string; text: string }[];
    expect(content[0]!.type).toBe("text");
    const payload = JSON.parse(content[0]!.text);
    expect(payload.hits).toHaveLength(1);
    expect(payload.hits[0].doc_id).toBe("p_x");

    await client.close();
  });

  it("大 payload（~500KB）不截断", async () => {
    handle = await startHttpServer(CONFIG, { port: 0, host: "127.0.0.1", auth: LOCAL_TRUSTED_AUTH });

    // 生成 ~500KB 的 ASCII 字符串，包到 JSON 里当 hits 内容
    const bigText = "A".repeat(500 * 1024);
    stubUpstreamFetch(async () => {
      return new Response(JSON.stringify({ hits: [{ doc_id: "p_big", snippet: bigText }] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    });

    const client = new Client(
      { name: "test-client", version: "0.0.0" },
      { capabilities: {} },
    );
    const transport = new StreamableHTTPClientTransport(
      new URL(`http://127.0.0.1:${handle.port}/mcp`),
    );
    await client.connect(transport);

    const result = await client.callTool({
      name: "semantic_search",
      arguments: { query: "x" },
    });
    expect(result.isError).toBeFalsy();
    const content = result.content as { type: string; text: string }[];
    const payload = JSON.parse(content[0]!.text);
    expect(payload.hits[0].snippet.length).toBe(500 * 1024);
    expect(payload.hits[0].snippet).toBe(bigText);

    await client.close();
  });

  it("无 session id 且非 initialize 时返回 400", async () => {
    handle = await startHttpServer(CONFIG, { port: 0, host: "127.0.0.1", auth: LOCAL_TRUSTED_AUTH });
    const res = await fetch(`http://127.0.0.1:${handle.port}/mcp`, {
      method: "POST",
      headers: { "content-type": "application/json", accept: "application/json, text/event-stream" },
      body: JSON.stringify({ jsonrpc: "2.0", method: "tools/list", id: 1 }),
    });
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.error).toBeDefined();
  });
});

// —— Phase 1.5 鉴权双通道（http-auth）——
// 判定规则：Authorization: Bearer 优先（透传，channel=remote）；否则来源 IP ∈ trustedIps
// 走内置 token（XFF 仅在 TCP 对端命中 trustedProxies 时采信）；两者皆无 → 401。
describe("cli-http: 鉴权双通道", () => {
  let handle: HttpServerHandle | undefined;

  afterEach(async () => {
    if (handle) {
      await handle.close();
      handle = undefined;
    }
    vi.unstubAllGlobals();
  });

  const INIT_BODY = JSON.stringify({
    jsonrpc: "2.0",
    id: 1,
    method: "initialize",
    params: {
      protocolVersion: "2025-03-26",
      capabilities: {},
      clientInfo: { name: "test", version: "0.0.0" },
    },
  });

  function rawInit(port: number, headers: Record<string, string> = {}): Promise<Response> {
    return fetch(`http://127.0.0.1:${port}/mcp`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        accept: "application/json, text/event-stream",
        ...headers,
      },
      body: INIT_BODY,
    });
  }

  it("匿名请求（非 hub IP、无 Authorization）返回 401 + WWW-Authenticate", async () => {
    handle = await startHttpServer(CONFIG, {
      port: 0,
      host: "127.0.0.1",
      auth: { trustedIps: new Set<string>(), trustedProxies: parseTrustedProxies(""), trustedHops: 1 },
    });
    const res = await rawInit(handle.port);
    expect(res.status).toBe(401);
    expect(res.headers.get("www-authenticate")).toBe("Bearer");
    const body = await res.json();
    expect(body.error.message).toContain("Unauthorized");
  });

  it("XFF 伪造前缀不生效：只取右起第 trustedHops 个条目", async () => {
    handle = await startHttpServer(CONFIG, {
      port: 0,
      host: "127.0.0.1",
      auth: { trustedIps: new Set(["10.0.0.9"]), trustedProxies: parseTrustedProxies("127.0.0.0/8, ::1"), trustedHops: 1 },
    });
    // 伪造者把 hub IP 放在前缀，信任网关追加了真实来源 6.6.6.6 → 取 6.6.6.6 → 拒绝
    const spoofed = await rawInit(handle.port, { "x-forwarded-for": "10.0.0.9, 6.6.6.6" });
    expect(spoofed.status).toBe(401);
    // 信任网关追加的正是 hub IP → 放行
    const legit = await rawInit(handle.port, { "x-forwarded-for": "10.0.0.9" });
    expect(legit.status).toBe(200);
    expect(legit.headers.get("mcp-session-id")).toBeTruthy();
  });

  it("非信任对端送来的 XFF 不采信（集群内直连伪造被挡）", async () => {
    handle = await startHttpServer(CONFIG, {
      port: 0,
      host: "127.0.0.1",
      // trustedProxies 为空：本地直连不是信任代理，XFF 整条忽略，按 socket 地址判定
      auth: { trustedIps: new Set(["10.0.0.9"]), trustedProxies: parseTrustedProxies(""), trustedHops: 1 },
    });
    const res = await rawInit(handle.port, { "x-forwarded-for": "10.0.0.9" });
    expect(res.status).toBe(401);
  });

  it("trusted 通道：下游收到内置 token，channel 沿用配置（scp）", async () => {
    handle = await startHttpServer(CONFIG, {
      port: 0,
      host: "127.0.0.1",
      auth: LOCAL_TRUSTED_AUTH,
    });
    let upstreamHeaders: Record<string, string> = {};
    stubUpstreamFetch(async (_url, init) => {
      upstreamHeaders = (init.headers ?? {}) as Record<string, string>;
      return new Response(JSON.stringify({ hits: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    });
    const client = new Client({ name: "t", version: "0.0.0" }, { capabilities: {} });
    const transport = new StreamableHTTPClientTransport(
      new URL(`http://127.0.0.1:${handle.port}/mcp`),
    );
    await client.connect(transport);
    await client.callTool({ name: "semantic_search", arguments: { query: "x" } });
    expect(upstreamHeaders["authorization"]).toBe("Bearer sv-test");
    expect(upstreamHeaders["x-sciverse-source"]).toMatch(/-scp$/);
    await client.close();
  });

  it("direct 通道：Authorization 原样透传，channel=remote", async () => {
    handle = await startHttpServer(CONFIG, {
      port: 0,
      host: "127.0.0.1",
      auth: { trustedIps: new Set<string>(), trustedProxies: parseTrustedProxies(""), trustedHops: 1 },
    });
    let upstreamHeaders: Record<string, string> = {};
    stubUpstreamFetch(async (_url, init) => {
      upstreamHeaders = (init.headers ?? {}) as Record<string, string>;
      return new Response(JSON.stringify({ hits: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    });
    const client = new Client({ name: "t", version: "0.0.0" }, { capabilities: {} });
    const transport = new StreamableHTTPClientTransport(
      new URL(`http://127.0.0.1:${handle.port}/mcp`),
      { requestInit: { headers: { authorization: "Bearer user-tok-123" } } },
    );
    await client.connect(transport);
    await client.callTool({ name: "semantic_search", arguments: { query: "x" } });
    expect(upstreamHeaders["authorization"]).toBe("Bearer user-tok-123");
    expect(upstreamHeaders["x-sciverse-source"]).toMatch(/-remote$/);
    await client.close();
  });

  it("session 与凭据绑定：换 token 复用 session 返回 401", async () => {
    handle = await startHttpServer(CONFIG, {
      port: 0,
      host: "127.0.0.1",
      auth: { trustedIps: new Set<string>(), trustedProxies: parseTrustedProxies(""), trustedHops: 1 },
    });
    const init = await rawInit(handle.port, { authorization: "Bearer tok-a" });
    expect(init.status).toBe(200);
    const sid = init.headers.get("mcp-session-id");
    expect(sid).toBeTruthy();

    const listBody = JSON.stringify({ jsonrpc: "2.0", id: 2, method: "tools/list" });
    const hijack = await fetch(`http://127.0.0.1:${handle.port}/mcp`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        accept: "application/json, text/event-stream",
        authorization: "Bearer tok-b",
        "mcp-session-id": sid!,
      },
      body: listBody,
    });
    expect(hijack.status).toBe(401);

    const legit = await fetch(`http://127.0.0.1:${handle.port}/mcp`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        accept: "application/json, text/event-stream",
        authorization: "Bearer tok-a",
        "mcp-session-id": sid!,
      },
      body: listBody,
    });
    expect(legit.status).toBe(200);
  });
});

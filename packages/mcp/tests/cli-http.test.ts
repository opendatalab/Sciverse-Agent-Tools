// HTTP transport 端到端测试：
//   - 起本地 HTTP server（PORT=0 让内核分配端口）
//   - 用 MCP SDK 的 StreamableHTTPClientTransport + Client 完整跑 initialize → tools/list → tools/call
//   - 业务层 fetch 全部用 vi.stubGlobal mock，避免触达真实 api.sciverse.space
//   - 同时覆盖 /healthz + 大 payload（≈500KB base64）不截断
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

import { startHttpServer, type HttpServerHandle } from "../src/cli-http.js";
import type { Config } from "../src/config.js";

const CONFIG: Config = {
  token: "sv-test",
  baseUrl: "https://api.sciverse.space",
  channel: "scp",
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
    handle = await startHttpServer(CONFIG, { port: 0, host: "127.0.0.1" });
    const res = await fetch(`http://127.0.0.1:${handle.port}/healthz`);
    expect(res.status).toBe(200);
    expect(await res.text()).toBe("ok");
  });

  it("未知路径返回 404", async () => {
    handle = await startHttpServer(CONFIG, { port: 0, host: "127.0.0.1" });
    const res = await fetch(`http://127.0.0.1:${handle.port}/nope`);
    expect(res.status).toBe(404);
  });

  it("完整跑通 initialize → tools/list → tools/call (semantic_search)", async () => {
    handle = await startHttpServer(CONFIG, { port: 0, host: "127.0.0.1" });

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
    handle = await startHttpServer(CONFIG, { port: 0, host: "127.0.0.1" });

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
    handle = await startHttpServer(CONFIG, { port: 0, host: "127.0.0.1" });
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

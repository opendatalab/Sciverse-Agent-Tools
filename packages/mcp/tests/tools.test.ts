import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { executeTool } from "../src/tools.js";
import { ENDPOINTS } from "../src/generated/tools.js";
import type { Config } from "../src/config.js";

const CONFIG: Config = {
  token: "sv-test",
  baseUrl: "https://api.sciverse.space",
  channel: "mcp",
};

interface Captured {
  url: string;
  init: RequestInit;
}

function mockFetch(status: number, body: unknown): Captured[] {
  const captured: Captured[] = [];
  const fn = vi.fn(async (url: string, init: RequestInit) => {
    captured.push({ url: url.toString(), init });
    return new Response(typeof body === "string" ? body : JSON.stringify(body), { status });
  });
  vi.stubGlobal("fetch", fn);
  return captured;
}

describe("executeTool", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("search_papers: 转换 agent-友好参数为 backend canonical filters", async () => {
    const captured = mockFetch(200, { hits: [], total: 0 });
    const result = await executeTool(CONFIG, "search_papers", {
      query: "transformer",
      authors: ["Hinton"],
      year_from: 2020,
      year_to: 2023,
      title_contains: "attention",
      sort_by_year: "desc",
      page_size: 5,
    });
    expect(result.isError).toBe(false);
    expect(captured).toHaveLength(1);
    expect(captured[0]!.url).toBe("https://api.sciverse.space/meta-search");
    expect(captured[0]!.init.method).toBe("POST");
    const body = JSON.parse(captured[0]!.init.body as string);
    expect(body.query).toBe("transformer");
    expect(body.page_size).toBe(5);
    expect(body.filters).toEqual(
      expect.arrayContaining([
        { field: "title", operator: "FILTER_OP_CONTAINS", value: "attention" },
        { field: "author", operator: "FILTER_OP_IN", value: ["Hinton"] },
        { field: "publication_published_year", operator: "FILTER_OP_GTE", value: 2020 },
        { field: "publication_published_year", operator: "FILTER_OP_LTE", value: 2023 },
      ]),
    );
    expect(body.sort).toEqual([
      { field: "publication_published_year", order: "SORT_ORDER_DESC" },
    ]);
  });

  it("x-sciverse-source 携带 platform+channel，x-request-id 仅为 uuid", async () => {
    const captured = mockFetch(200, { hits: [] });
    await executeTool(CONFIG, "semantic_search", { query: "x" });
    const headers = captured[0]!.init.headers as Record<string, string>;
    expect(headers["x-sciverse-source"]).toMatch(/^[a-z0-9]+-mcp$/);
    expect(headers["x-request-id"]).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/,
    );

    // 模拟 HTTP 入口的 config：channel = "scp"
    const captured2 = mockFetch(200, { hits: [] });
    await executeTool({ ...CONFIG, channel: "scp" }, "semantic_search", { query: "x" });
    const headers2 = captured2[0]!.init.headers as Record<string, string>;
    expect(headers2["x-sciverse-source"]).toMatch(/^[a-z0-9]+-scp$/);
  });

  it("semantic_search: 透传 body 到 /agentic-search", async () => {
    const captured = mockFetch(200, { hits: [] });
    await executeTool(CONFIG, "semantic_search", {
      query: "Transformer attention",
      top_k: 3,
      mode: "balanced",
    });
    expect(captured[0]!.url).toBe("https://api.sciverse.space/agentic-search");
    expect(captured[0]!.init.method).toBe("POST");
    const body = JSON.parse(captured[0]!.init.body as string);
    expect(body).toEqual({ query: "Transformer attention", top_k: 3, mode: "balanced" });
  });

  it("read_content: 构造 querystring", async () => {
    const captured = mockFetch(200, { text: "x", bytes_returned: 1, next_offset: 1, more: false });
    await executeTool(CONFIG, "read_content", {
      doc_id: "p_abc",
      offset: 100,
      limit: 2048,
    });
    expect(captured[0]!.url).toBe(
      "https://api.sciverse.space/content?doc_id=p_abc&offset=100&limit=2048",
    );
    expect(captured[0]!.init.method).toBe("GET");
  });

  it("list_catalog: 默认不拉 sample_values", async () => {
    const captured = mockFetch(200, { fields: [], default_fields: [], filter_operators: [], index_name: "xinghe_meta" });
    await executeTool(CONFIG, "list_catalog", {});
    expect(captured[0]!.url).toBe(
      "https://api.sciverse.space/meta-catalog?include_sample_values=false",
    );
    expect(captured[0]!.init.method).toBe("GET");
  });

  it("list_catalog: include_sample_values=true 时拼到 querystring", async () => {
    const captured = mockFetch(200, { fields: [], default_fields: [], filter_operators: [], index_name: "xinghe_meta" });
    await executeTool(CONFIG, "list_catalog", { include_sample_values: true });
    expect(captured[0]!.url).toBe(
      "https://api.sciverse.space/meta-catalog?include_sample_values=true",
    );
  });

  it("get_resource: 返回 image content block + base64 + mimeType", async () => {
    const pngBytes = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
    const fn = vi.fn(async (url: string, init: RequestInit) => {
      return new Response(pngBytes, {
        status: 200,
        headers: { "content-type": "image/png" },
      });
    });
    vi.stubGlobal("fetch", fn);
    const result = await executeTool(CONFIG, "get_resource", { file_name: "dt=x/p_y/f3.png" });
    expect(result.isError).toBe(false);
    expect(result.content).toHaveLength(1);
    const block = result.content[0] as { type: string; data: string; mimeType: string };
    expect(block.type).toBe("image");
    expect(block.mimeType).toBe("image/png");
    expect(block.data).toBe(Buffer.from(pngBytes).toString("base64"));
    expect(fn.mock.calls[0]![0]!.toString()).toBe(
      "https://api.sciverse.space/resource?file_name=dt%3Dx%2Fp_y%2Ff3.png",
    );
  });

  it("get_resource: 缺 file_name 时返回 isError", async () => {
    const captured = mockFetch(200, {});
    const result = await executeTool(CONFIG, "get_resource", {});
    expect(result.isError).toBe(true);
    expect(captured).toHaveLength(0);
  });

  it("read_content: 缺 doc_id 时返回 isError", async () => {
    const captured = mockFetch(200, {});
    const result = await executeTool(CONFIG, "read_content", {});
    expect(result.isError).toBe(true);
    expect(captured).toHaveLength(0);
  });

  it("HTTP 非 2xx → isError + status + body", async () => {
    mockFetch(401, { error: { code: "INVALID_API_KEY", message: "Invalid token" } });
    const result = await executeTool(CONFIG, "semantic_search", { query: "x" });
    expect(result.isError).toBe(true);
    const payload = JSON.parse(result.content[0]!.text);
    expect(payload.status).toBe(401);
    expect(payload.body).toEqual({ error: { code: "INVALID_API_KEY", message: "Invalid token" } });
  });

  it("Bearer header 被附加到所有请求", async () => {
    const captured = mockFetch(200, {});
    await executeTool(CONFIG, "semantic_search", { query: "x" });
    const headers = captured[0]!.init.headers as Record<string, string>;
    expect(headers.authorization).toBe("Bearer sv-test");
    expect(headers["content-type"]).toBe("application/json");
  });

  it("未知 tool 返回 isError", async () => {
    const result = await executeTool(CONFIG, "no_such_tool", {});
    expect(result.isError).toBe(true);
  });
});

describe("tool implementation coverage (guard)", () => {
  beforeEach(() => vi.restoreAllMocks());
  afterEach(() => vi.unstubAllGlobals());

  // 守卫：openapi 里每个工具（→ ENDPOINTS）都必须在 executeTool 有专门分支，
  // 否则落到 default 返回 "unhandled tool"。防止"openapi 加了工具但漏 dispatch"。
  it("every advertised tool is handled by executeTool (no 'unhandled tool')", async () => {
    const allArgs = {
      unique_id: "paper:1", relation: "CITATIONS", doc_id: "d1",
      file_name: "a.png", query: "x", page: 1, page_size: 1,
    };
    for (const name of Object.keys(ENDPOINTS)) {
      mockFetch(200, { hits: [], items: [], fields: [] });
      let text = "";
      try {
        const result = await executeTool(CONFIG, name, allArgs);
        text = (result.content ?? []).map((c) => ("text" in c ? c.text : "")).join("");
      } catch {
        // 抛异常说明确有分支在执行（default 是 return 不是 throw）→ 视为已处理
        continue;
      }
      expect(text, `tool '${name}' must have an executeTool branch`).not.toContain("unhandled tool");
    }
  });
});

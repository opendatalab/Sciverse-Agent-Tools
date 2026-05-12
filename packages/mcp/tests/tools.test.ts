import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { executeTool } from "../src/tools.js";
import type { Config } from "../src/config.js";

const CONFIG: Config = {
  token: "sv-test",
  baseUrl: "https://api.sciverse.space",
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

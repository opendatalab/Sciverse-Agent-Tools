import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { AgentToolsClient } from "../src/client";

const server = setupServer();

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("AgentToolsClient", () => {
  it("search_papers happy path", async () => {
    server.use(
      http.post("https://api.example/meta-search", () =>
        HttpResponse.json({ hits: [{ doc_id: "p_1", title: "T" }], total: 1, page: 1, page_size: 10 })
      )
    );
    const c = new AgentToolsClient({ baseUrl: "https://api.example", token: "t" });
    const r: any = await c.searchPapers({ query: "x" });
    expect(r.hits[0].doc_id).toBe("p_1");
  });

  it("sends Bearer token", async () => {
    let captured = "";
    server.use(
      http.post("https://api.example/meta-search", ({ request }) => {
        captured = request.headers.get("authorization") ?? "";
        return HttpResponse.json({ hits: [], total: 0, page: 1, page_size: 10 });
      })
    );
    await new AgentToolsClient({ baseUrl: "https://api.example", token: "abc" }).searchPapers({});
    expect(captured).toBe("Bearer abc");
  });

  it("read_content uses query params", async () => {
    let url = "";
    server.use(
      http.get("https://api.example/content", ({ request }) => {
        url = request.url;
        return HttpResponse.json({ text: "x", bytes_returned: 1, next_offset: 1, more: false });
      })
    );
    await new AgentToolsClient({ baseUrl: "https://api.example", token: "t" }).readContent({ doc_id: "p_1", offset: 100 });
    expect(url).toContain("doc_id=p_1");
    expect(url).toContain("offset=100");
  });

  it("throws on 4xx", async () => {
    server.use(
      http.post("https://api.example/meta-search", () =>
        HttpResponse.json({ code: "TOKEN_INVALID", message: "无效" }, { status: 401 })
      )
    );
    const c = new AgentToolsClient({ baseUrl: "https://api.example", token: "bad" });
    await expect(c.searchPapers({ query: "x" })).rejects.toThrow(/401/);
  });
});

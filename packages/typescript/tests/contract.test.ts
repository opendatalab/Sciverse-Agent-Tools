import { describe, it, expect } from "vitest";
import { AgentToolsClient } from "../src/client";

const TOKEN = process.env.SCIVERSE_TEST_TOKEN;
const BASE = process.env.SCIVERSE_TEST_BASE_URL;
const skip = !TOKEN || !BASE;

describe.skipIf(skip)("Layer 2 contract", () => {
  it("search_papers returns valid shape", async () => {
    const c = new AgentToolsClient({ baseUrl: BASE!, token: TOKEN! });
    const r: any = await c.searchPapers({ query: "transformer", page_size: 3 });
    expect(Array.isArray(r.hits)).toBe(true);
    if (r.hits.length > 0) {
      expect(r.hits[0]).toHaveProperty("doc_id");
      expect(r.hits[0]).toHaveProperty("title");
    }
  });

  it("semantic_search balanced mode", async () => {
    const c = new AgentToolsClient({ baseUrl: BASE!, token: TOKEN! });
    const r: any = await c.semanticSearch({ query: "attention mechanism", top_k: 3, mode: "balanced" });
    expect(r.hits).toBeDefined();
    if (r.hits.length > 0) {
      const hit = r.hits[0];
      ["chunk_id", "doc_id", "title", "score", "offset"].forEach(f => expect(hit).toHaveProperty(f));
    }
  });

  it("read_content after semantic_search", async () => {
    const c = new AgentToolsClient({ baseUrl: BASE!, token: TOKEN! });
    const s: any = await c.semanticSearch({ query: "quantum computing", top_k: 1 });
    if (!s.hits.length) return;
    const r: any = await c.readContent({ doc_id: s.hits[0].doc_id, offset: s.hits[0].offset, limit: 1024 });
    ["text", "bytes_returned", "next_offset", "more"].forEach(f => expect(r).toHaveProperty(f));
  });

  it("invalid token returns 401", async () => {
    const c = new AgentToolsClient({ baseUrl: BASE!, token: "invalid-token-deadbeef" });
    await expect(c.searchPapers({ query: "x" })).rejects.toThrow(/401/);
  });
});

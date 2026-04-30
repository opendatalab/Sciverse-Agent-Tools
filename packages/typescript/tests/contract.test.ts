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
});

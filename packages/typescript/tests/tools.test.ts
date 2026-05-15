import { describe, it, expect } from "vitest";
import { TOOLS_VERSION, OPENAI_TOOLS, ANTHROPIC_TOOLS } from "../src/tools";

describe("tools constants", () => {
  it("exposes all tools", () => {
    // version 是 semver 字符串即可，不硬编码（避免每次 bump 都要改测试）
    expect(typeof TOOLS_VERSION).toBe("string");
    expect(TOOLS_VERSION).toMatch(/^\d+\.\d+\.\d+/);
    const names = OPENAI_TOOLS.map((t: any) => t.function.name).sort();
    expect(names).toEqual(["get_resource", "list_catalog", "read_content", "search_papers", "semantic_search"]);
    expect(ANTHROPIC_TOOLS.map((t: any) => t.name).sort()).toEqual(names);
  });
});

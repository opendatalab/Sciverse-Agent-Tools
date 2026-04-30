import { describe, it, expect } from "vitest";
import { TOOLS_VERSION, OPENAI_TOOLS, ANTHROPIC_TOOLS } from "../src/tools";

describe("tools constants", () => {
  it("exposes three tools", () => {
    expect(TOOLS_VERSION).toBe("0.1.0");
    const names = OPENAI_TOOLS.map((t: any) => t.function.name).sort();
    expect(names).toEqual(["read_content", "search_papers", "semantic_search"]);
    expect(ANTHROPIC_TOOLS.map((t: any) => t.name).sort()).toEqual(names);
  });
});

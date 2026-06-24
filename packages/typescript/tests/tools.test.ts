import { describe, it, expect } from "vitest";
import { TOOLS_VERSION, OPENAI_TOOLS, ANTHROPIC_TOOLS } from "../src/tools";
import { AgentToolsClient } from "../src/client";

describe("tools constants", () => {
  it("exposes all tools", () => {
    // version 是 semver 字符串即可，不硬编码（避免每次 bump 都要改测试）
    expect(typeof TOOLS_VERSION).toBe("string");
    expect(TOOLS_VERSION).toMatch(/^\d+\.\d+\.\d+/);
    const names = OPENAI_TOOLS.map((t: any) => t.function.name).sort();
    expect(names).toEqual(["get_resource", "list_catalog", "list_paper_relations", "read_content", "search_papers", "semantic_search"]);
    expect(ANTHROPIC_TOOLS.map((t: any) => t.name).sort()).toEqual(names);
  });

  // 守卫：每个广告的工具都必须有对应的 client 方法（snake_case → camelCase）。
  // 防止"openapi/生成 schema 加了工具但 TS SDK client 漏了方法"。
  it("every advertised tool has a client method (guard)", () => {
    const toCamel = (s: string) => s.replace(/_([a-z])/g, (_m, c) => c.toUpperCase());
    const client = new AgentToolsClient({ token: "sv-test" });
    for (const t of OPENAI_TOOLS as { function: { name: string } }[]) {
      const method = toCamel(t.function.name);
      expect(
        typeof (client as unknown as Record<string, unknown>)[method],
        `client.${method} for tool ${t.function.name}`,
      ).toBe("function");
    }
  });
});

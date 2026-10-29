import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
const bodies: Record<string, unknown>[] = [];
const urls: URL[] = [];
beforeEach(() => {
  bodies.length = 0; urls.length = 0;
  vi.stubEnv("SCIVERSE_ENABLE_LEGACY_TOOLS", "false");
  vi.stubGlobal("fetch", vi.fn(async (url, init) => {
    urls.push(new URL(String(url)));
    if (init?.body) bodies.push(JSON.parse(init.body));
    return new Response("{}", { status: 200 });
  }));
});
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });
import { AgentToolsClient } from "../src/client.js";
const client = new AgentToolsClient({ token: "test", baseUrl: "https://api.example" });
describe("多实体 SDK", () => {
  it.each(["papers", "authors", "sources", "patents"])("canonical 参数原样发送：%s", async collection => {
    const args = { query: "x", collection, filters: [{field: "id", operator: "FILTER_OP_EQ", value: "x"}], sort: [{field: "id", order: "SORT_ORDER_ASC"}], fields: ["id"], page: 2, page_size: 3, cursor: "next", facets: [{field: "id", size: 50}], freshness_boost: "MILD", impact_boost: "STRONG", language_affinity: "NONE" };
    await client.searchMetadata(args);
    expect(bodies).toEqual([args]);
  });
  it("默认 papers 且不隐式加 sort", async () => {
    await client.searchMetadata({});
    expect(bodies).toEqual([{ collection: "papers" }]);
  });
  it.each([{ typo: true }, { typo: null }, { year_from: 2020 }, { collection: "unknown" }, { facets: [{field: "id", size: 51}] }, { filters: [{field: "id", operator: "FILTER_OP_EQ", value: 1, typo: true}] }])("拒绝错误 canonical 参数 %j", async args => {
    await expect(client.searchMetadata(args)).rejects.toThrow();
    expect(urls).toHaveLength(0);
  });
  it.each(["authors", "sources", "patents"])("旧接口非论文不自动年份排序：%s", async collection => {
    await client.searchPapers({ collection, filters_advanced: [{ field: "id", value: "x" }] });
    expect(bodies[0]).toEqual({collection, filters: [{field: "id", operator: "FILTER_OP_EQ", value: "x"}]});
  });
  it.each([
    ["title_contains", "x"], ["abstract_contains", "x"], ["authors", ["x"]],
    ["year_from", 2020], ["year_to", 2025], ["journals", ["x"]], ["subjects", ["x"]],
  ])("非论文拒绝显式便捷字段 %s", async (field, value) => {
    await expect(client.searchPapers({ collection: "patents", [field as string]: value })).rejects.toThrow(field as string);
    expect(urls).toHaveLength(0);
  });

  it.each(["authors", "sources", "patents"])("非论文保留 auto/none 及显式高级排序：%s", async collection => {
    vi.stubEnv("SCIVERSE_ENABLE_LEGACY_TOOLS", "true");
    for (const sort_by_year of ["auto", "none"]) {
      for (const sort_advanced of [undefined, [{field: "id", order: "SORT_ORDER_ASC"}]]) {
        const args = {collection, sort_by_year, sort_advanced};
        await client.searchPapers(args);
        expect(bodies.at(-1)).toEqual({collection, ...(sort_advanced ? {sort: sort_advanced} : {})});
      }
    }
  });
  it.each(["authors", "sources", "patents"])("非论文拒绝显式年份 asc/desc：%s", async collection => {
    vi.stubEnv("SCIVERSE_ENABLE_LEGACY_TOOLS", "true");
    for (const sort_by_year of ["asc", "desc"]) {
      const args = {collection, sort_by_year};
      await expect(client.searchPapers(args)).rejects.toThrow("sort_by_year");
    }
    expect(urls).toHaveLength(0);
  });
  it("非法 sort_by_year 不得变成隐式升序", async () => {
    vi.stubEnv("SCIVERSE_ENABLE_LEGACY_TOOLS", "true");
    for (const collection of ["papers", "patents"]) {
      const args = {collection, sort_by_year: "typo"};
      await expect(client.searchPapers(args)).rejects.toThrow("sort_by_year");
    }
    expect(urls).toHaveLength(0);
  });
  it("query/collection null 采用缺省，其他 canonical 参数不丢弃", async () => {
    const args = {query: null, collection: null, fields: ["id"], cursor: "next"};
    await client.searchMetadata(args);
    expect(bodies).toEqual([{collection: "papers", fields: ["id"], cursor: "next"}]);
  });
  it("旧接口 null collection 采用 papers 默认排序", async () => {
    vi.stubEnv("SCIVERSE_ENABLE_LEGACY_TOOLS", "true");
    const args = {collection: null, query: null};
    await client.searchPapers(args);
    expect(bodies).toEqual([{sort: [{field: "publication_published_year", order: "SORT_ORDER_DESC"}]}]);
  });

  it("专利正文透传 collection，保留分页默认值", async () => {
    await client.readContent({ doc_id: "patent:1", collection: "patents" });
    expect(Object.fromEntries(urls[0]!.searchParams)).toEqual({doc_id: "patent:1", collection: "patents", offset: "0", limit: "4096"});
  });
  it("catalog 支持 patents", async () => {
    await client.listCatalog({ collection: "patents" });
    expect(urls[0]!.searchParams.get("collection")).toBe("patents");
  });
});

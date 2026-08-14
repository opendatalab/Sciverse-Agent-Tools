import { randomUUID } from "node:crypto";
import { resolveEndpoint, resolveToken } from "./credentials.js";

/**
 * AgentToolsClientOptions
 *
 * `token` 和 `baseUrl` 都是可选的。未传时按以下顺序 fallback：
 *   1. 显式参数
 *   2. 环境变量 SCIVERSE_API_TOKEN / SCIVERSE_BASE_URL
 *   3. ~/.sciverse/credentials.json（由 `sciverse auth login` Python CLI 写入）
 *   4. baseUrl 默认值 https://api.sciverse.space；token 找不到则构造抛错
 */
export interface AgentToolsClientOptions {
  baseUrl?: string;
  token?: string;
}

const CHANNEL = "typescript-sdk";
const PLATFORM = process.platform;
const SOURCE = `${PLATFORM}-${CHANNEL}`;

const PASSTHROUGH = [
  "query", "page", "page_size", "fields", "collection",
  // 软加权档位（NONE/MILD/STRONG，可叠加）：新鲜度 / 影响力 / 语言亲和
  "freshness_boost", "impact_boost", "language_affinity",
] as const;

interface FilterEntry {
  field: string;
  operator?: string;
  value: unknown;
}

function toBackendPayload(args: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  const filters: FilterEntry[] = [];
  const sort: { field: string; order: string }[] = [];

  for (const k of PASSTHROUGH) {
    if (args[k] !== undefined && args[k] !== null) out[k] = args[k];
  }

  const addFilter = (field: string, operator: string, value: unknown) => {
    filters.push({ field, operator, value });
  };

  if (args.title_contains !== undefined && args.title_contains !== null) {
    addFilter("title", "FILTER_OP_CONTAINS", args.title_contains);
  }
  if (args.abstract_contains !== undefined && args.abstract_contains !== null) {
    addFilter("abstract", "FILTER_OP_CONTAINS", args.abstract_contains);
  }
  if (Array.isArray(args.authors) && args.authors.length > 0) {
    addFilter("author", "FILTER_OP_IN", args.authors);
  }
  if (args.year_from !== undefined && args.year_from !== null) {
    addFilter("publication_published_year", "FILTER_OP_GTE", args.year_from);
  }
  if (args.year_to !== undefined && args.year_to !== null) {
    addFilter("publication_published_year", "FILTER_OP_LTE", args.year_to);
  }
  if (Array.isArray(args.journals) && args.journals.length > 0) {
    addFilter("publication_venue_name_unified", "FILTER_OP_IN", args.journals);
  }
  if (Array.isArray(args.subjects) && args.subjects.length > 0) {
    addFilter("subjects", "FILTER_OP_IN", args.subjects);
  }
  if (Array.isArray(args.filters_advanced)) {
    for (const item of args.filters_advanced as FilterEntry[]) {
      filters.push({ operator: "FILTER_OP_EQ", ...item });
    }
  }

  // sort_by_year 默认 auto：有 query（或 sort_advanced）时不加年份排序——保 BM25
  // 相关性且软加权可用；纯结构化筛选时按年份降序（后端默认序实质乱序）。
  let sortByYear = (args.sort_by_year as string | undefined) ?? "auto";
  if (sortByYear === "auto") {
    sortByYear = args.query || (Array.isArray(args.sort_advanced) && args.sort_advanced.length > 0)
      ? "none" : "desc";
  }
  if (sortByYear !== "none") {
    sort.push({
      field: "publication_published_year",
      order: sortByYear === "desc" ? "SORT_ORDER_DESC" : "SORT_ORDER_ASC",
    });
  }

  if (Array.isArray(args.sort_advanced)) {
    for (const item of args.sort_advanced as { field: string; order?: string }[]) {
      if (item && item.field) sort.push({ field: item.field, order: item.order ?? "SORT_ORDER_DESC" });
    }
  }

  if (filters.length > 0) out.filters = filters;
  if (sort.length > 0) out.sort = sort;
  return out;
}

// 上游 agentic-search（Go 服务）没有 mode 字段，未知字段会被静默丢弃，
// 所以 mode 必须在 SDK 层翻译为上游真实参数 retrieval / sub_queries。
const SEMANTIC_MODE_MAP: Record<string, Record<string, unknown>> = {
  fast: { retrieval: "es" },
  balanced: { retrieval: "hybrid" },
  quality: { retrieval: "hybrid", sub_queries: 3 },
};

function toSemanticSearchPayload(body: Record<string, unknown>): Record<string, unknown> {
  const { mode, ...rest } = body;
  const out = Object.fromEntries(Object.entries(rest).filter(([, v]) => v !== undefined));
  if (mode === undefined || mode === null) return out;
  const mapped = SEMANTIC_MODE_MAP[mode as string];
  if (!mapped) {
    throw new Error(
      `mode must be one of ${Object.keys(SEMANTIC_MODE_MAP).join(" / ")}, got ${JSON.stringify(mode)}`,
    );
  }
  // 显式传入的 retrieval / sub_queries 优先于 mode 映射。
  return { ...mapped, ...out };
}

export class AgentToolsClient {
  private baseUrl: string;
  private token: string;

  constructor(opts: AgentToolsClientOptions = {}) {
    const token = resolveToken(opts.token);
    if (!token) {
      throw new Error(
        "未找到 Sciverse API Token。请显式传 token、或设 SCIVERSE_API_TOKEN 环境变量、" +
          "或运行 `pip install sciverse && sciverse auth login` 保存凭据到 ~/.sciverse/credentials.json。",
      );
    }
    this.baseUrl = resolveEndpoint(opts.baseUrl).replace(/\/$/, "");
    this.token = token;
  }

  private async request<T>(path: string, init: RequestInit): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers: {
        ...(init.headers ?? {}),
        authorization: `Bearer ${this.token}`,
        "content-type": "application/json",
        "x-request-id": randomUUID(),
        "x-sciverse-source": SOURCE,
      },
    });
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`Sciverse API ${res.status}: ${body}`);
    }
    return (await res.json()) as T;
  }

  async searchPapers(args: Record<string, unknown>): Promise<unknown> {
    const body = toBackendPayload(args);
    return this.request("/meta-search", { method: "POST", body: JSON.stringify(body) });
  }

  async listPaperRelations(
    args: { unique_id: string; relation: string; page?: number; page_size?: number },
  ): Promise<unknown> {
    return this.request("/meta-paper-relations", { method: "POST", body: JSON.stringify(args) });
  }

  async semanticSearch(body: { query: string } & Record<string, unknown>): Promise<unknown> {
    const cleaned = toSemanticSearchPayload(body);
    return this.request("/agentic-search", { method: "POST", body: JSON.stringify(cleaned) });
  }

  async listCatalog(
    params: { include_sample_values?: boolean; include_field_stats?: boolean; collection?: string } = {},
  ): Promise<unknown> {
    const qs = new URLSearchParams();
    qs.set("include_sample_values", String(Boolean(params.include_sample_values)));
    if (params.include_field_stats) qs.set("include_field_stats", "true");
    if (params.collection) qs.set("collection", params.collection);
    return this.request(`/meta-catalog?${qs.toString()}`, { method: "GET" });
  }

  async getResource(params: { file_name: string }): Promise<{ bytes: Uint8Array; mimeType: string }> {
    const qs = new URLSearchParams({ file_name: params.file_name });
    const res = await fetch(`${this.baseUrl}/resource?${qs.toString()}`, {
      method: "GET",
      headers: {
        authorization: `Bearer ${this.token}`,
        accept: "image/*",
      },
    });
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`Sciverse API ${res.status}: ${body}`);
    }
    const mimeType = (res.headers.get("content-type") || "application/octet-stream").split(";")[0]!.trim();
    const buf = new Uint8Array(await res.arrayBuffer());
    return { bytes: buf, mimeType };
  }

  async readContent(params: { doc_id: string; offset?: number; limit?: number }): Promise<unknown> {
    const qs = new URLSearchParams();
    qs.set("doc_id", params.doc_id);
    if (params.offset !== undefined) qs.set("offset", String(params.offset));
    if (params.limit !== undefined) qs.set("limit", String(params.limit));
    return this.request(`/content?${qs.toString()}`, { method: "GET" });
  }
}

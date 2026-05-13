import { randomUUID } from "node:crypto";

export interface AgentToolsClientOptions {
  baseUrl: string;
  token: string;
}

const SKILL_NAME = "sciverse-academic-retrieval";
const CHANNEL = "typescript-sdk";
const PLATFORM = process.platform;

const PASSTHROUGH = ["query", "page", "page_size", "fields"] as const;

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
    addFilter("publication_venue_name", "FILTER_OP_IN", args.journals);
  }
  if (Array.isArray(args.subjects) && args.subjects.length > 0) {
    addFilter("subjects", "FILTER_OP_IN", args.subjects);
  }
  if (Array.isArray(args.filters_advanced)) {
    for (const item of args.filters_advanced as FilterEntry[]) {
      filters.push({ operator: "FILTER_OP_EQ", ...item });
    }
  }

  const sortByYear = args.sort_by_year as string | undefined;
  if (sortByYear && sortByYear !== "none") {
    sort.push({
      field: "publication_published_year",
      order: sortByYear === "desc" ? "SORT_ORDER_DESC" : "SORT_ORDER_ASC",
    });
  }

  if (filters.length > 0) out.filters = filters;
  if (sort.length > 0) out.sort = sort;
  return out;
}

export class AgentToolsClient {
  private baseUrl: string;
  private token: string;

  constructor(opts: AgentToolsClientOptions) {
    this.baseUrl = opts.baseUrl.replace(/\/$/, "");
    this.token = opts.token;
  }

  private async request<T>(path: string, init: RequestInit): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers: {
        ...(init.headers ?? {}),
        authorization: `Bearer ${this.token}`,
        "content-type": "application/json",
        "x-request-id": `${SKILL_NAME}-${PLATFORM}-${CHANNEL}-${randomUUID()}`,
      },
    });
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`SciVerse API ${res.status}: ${body}`);
    }
    return (await res.json()) as T;
  }

  async searchPapers(args: Record<string, unknown>): Promise<unknown> {
    const body = toBackendPayload(args);
    return this.request("/meta-search", { method: "POST", body: JSON.stringify(body) });
  }

  async semanticSearch(body: { query: string } & Record<string, unknown>): Promise<unknown> {
    const cleaned = Object.fromEntries(Object.entries(body).filter(([, v]) => v !== undefined));
    return this.request("/agentic-search", { method: "POST", body: JSON.stringify(cleaned) });
  }

  async listCatalog(params: { include_sample_values?: boolean } = {}): Promise<unknown> {
    const qs = new URLSearchParams();
    qs.set("include_sample_values", String(Boolean(params.include_sample_values)));
    return this.request(`/meta-catalog?${qs.toString()}`, { method: "GET" });
  }

  async readContent(params: { doc_id: string; offset?: number; limit?: number }): Promise<unknown> {
    const qs = new URLSearchParams();
    qs.set("doc_id", params.doc_id);
    if (params.offset !== undefined) qs.set("offset", String(params.offset));
    if (params.limit !== undefined) qs.set("limit", String(params.limit));
    return this.request(`/content?${qs.toString()}`, { method: "GET" });
  }
}

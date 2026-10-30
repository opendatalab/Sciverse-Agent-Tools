// HTTP 调用层 + agent-友好参数到后端 canonical payload 的转换。
//
// `toBackendPayload` 是从 packages/typescript/src/client.ts 的 `toBackendPayload`
// 复制过来的（约 50 行）。MCP 包刻意不依赖 TS SDK，避免 monorepo 内部环依赖。
// 后续如有第 4 处复制，再用 codegen 收敛。

import type { Config } from "./config.js";
import { ENDPOINTS, LEGACY_ENDPOINTS } from "./generated/tools.js";
import { randomUUID } from "node:crypto";

// MCP content block 类型：text（普通响应）+ image（get_resource binary）。
// image type 是 MCP 1.0 标准能力，data 为 base64，mimeType 必填。
export type ContentBlock =
  | { type: "text"; text: string }
  | { type: "image"; data: string; mimeType: string };

export interface ToolResult {
  isError: boolean;
  content: ContentBlock[];
}

interface FilterEntry {
  field: string;
  operator?: string;
  value: unknown;
}

const PASSTHROUGH = ["query", "page", "page_size", "fields", "collection", "freshness_boost", "impact_boost", "language_affinity"] as const;

const COLLECTIONS = ["papers", "authors", "sources", "patents"] as const;
const CANONICAL_SEARCH_KEYS = [
  "query", "collection", "filters", "sort", "fields", "page", "page_size",
  "cursor", "facets", "freshness_boost", "impact_boost", "language_affinity",
] as const;
const PAPER_CONVENIENCE_KEYS = [
  "title_contains", "abstract_contains", "authors", "year_from", "year_to",
  "journals", "subjects",
] as const;

function validateCollection(collection: unknown, allowed: readonly string[] = COLLECTIONS): void {
  if (collection !== undefined && (typeof collection !== "string" || !allowed.includes(collection))) {
    throw new Error(`collection must be one of ${allowed.join(" / ")}`);
  }
}

function rejectUnknown(args: Record<string, unknown>, allowed: readonly string[]): void {
  for (const key of Object.keys(args)) {
    if (!allowed.includes(key)) throw new Error(`unknown parameter: ${key}`);
  }
}

function toMetadataPayload(args: Record<string, unknown>): Record<string, unknown> {
  rejectUnknown(args, CANONICAL_SEARCH_KEYS);
  // query/collection 的 null 与省略等价，其余参数不做静默过滤。
  args = { ...args, collection: args.collection ?? "papers" };
  if (args.query === null) delete args.query;
  validateCollection(args.collection);
  for (const [key, allowed] of [
    ["filters", ["field", "operator", "value"]],
    ["sort", ["field", "order"]],
    ["facets", ["field", "size"]],
  ] as const) {
    if (args[key] === undefined) continue;
    if (!Array.isArray(args[key])) throw new Error(`${key} must be an array`);
    for (const item of args[key] as unknown[]) {
      if (!item || typeof item !== "object" || Array.isArray(item)) throw new Error(`${key} entries must be objects`);
      rejectUnknown(item as Record<string, unknown>, allowed);
      if (key === "facets") {
        const { size } = item as { size?: unknown };
        if (size !== undefined && (typeof size !== "number" || !Number.isInteger(size) || size < 1 || size > 50)) {
          throw new Error("facets size must be an integer from 1 to 50");
        }
      }
    }
  }
  return { ...args, collection: args.collection ?? "papers" };
}

function toBackendPayload(args: Record<string, unknown>): Record<string, unknown> {
  const collection = args.collection ?? "papers";
  validateCollection(collection);
  let sortByYear = args.sort_by_year ?? "auto";
  if (typeof sortByYear !== "string" || !["auto", "none", "asc", "desc"].includes(sortByYear)) {
    throw new Error("sort_by_year must be one of auto / none / asc / desc");
  }
  if (collection !== "papers") {
    if (sortByYear === "asc" || sortByYear === "desc") {
      throw new Error("sort_by_year asc/desc is only supported for collection papers");
    }
    for (const key of PAPER_CONVENIENCE_KEYS) {
      if (Object.prototype.hasOwnProperty.call(args, key)) {
        throw new Error(`${key} is only supported for collection papers`);
      }
    }
  }
  const out: Record<string, unknown> = {};
  const filters: FilterEntry[] = [];
  const sort: { field: string; order: string }[] = [];

  for (const k of PASSTHROUGH) {
    if (args[k] !== undefined && args[k] !== null) out[k] = args[k];
  }

  const addFilter = (field: string, operator: string, value: unknown) => {
    filters.push({ field, operator, value });
  };

  if (args.title_contains != null) addFilter("title", "FILTER_OP_CONTAINS", args.title_contains);
  if (args.abstract_contains != null) addFilter("abstract", "FILTER_OP_CONTAINS", args.abstract_contains);
  if (Array.isArray(args.authors) && args.authors.length > 0) {
    addFilter("author", "FILTER_OP_IN", args.authors);
  }
  if (args.year_from != null) addFilter("publication_published_year", "FILTER_OP_GTE", args.year_from);
  if (args.year_to != null) addFilter("publication_published_year", "FILTER_OP_LTE", args.year_to);
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
  if (sortByYear === "auto") {
    sortByYear = collection !== "papers" || args.query || (Array.isArray(args.sort_advanced) && args.sort_advanced.length > 0)
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
// 所以 mode 必须在这里翻译为上游真实参数 retrieval / sub_queries。
// 与 packages/typescript/src/client.ts 的 SEMANTIC_MODE_MAP 保持一致（同 toBackendPayload 的复制约定）。
const SEMANTIC_MODE_MAP: Record<string, Record<string, unknown>> = {
  fast: { retrieval: "es" },
  balanced: { retrieval: "hybrid" },
  quality: { retrieval: "hybrid", sub_queries: 3 },
};

function toSemanticSearchPayload(args: Record<string, unknown>): Record<string, unknown> {
  const { mode, ...rest } = args;
  if (mode === undefined || mode === null) return rest;
  const mapped = SEMANTIC_MODE_MAP[mode as string];
  if (!mapped) {
    throw new Error(
      `mode must be one of ${Object.keys(SEMANTIC_MODE_MAP).join(" / ")}, got ${JSON.stringify(mode)}`,
    );
  }
  // 显式传入的 retrieval / sub_queries 优先于 mode 映射。
  return { ...mapped, ...rest };
}

const PLATFORM = process.platform;

async function call(
  config: Config,
  method: "GET" | "POST",
  path: string,
  options: { body?: Record<string, unknown>; query?: Record<string, unknown> } = {},
): Promise<ToolResult> {
  const url = new URL(`${config.baseUrl}${path}`);
  if (options.query) {
    for (const [k, v] of Object.entries(options.query)) {
      if (v !== undefined && v !== null) url.searchParams.set(k, String(v));
    }
  }
  const init: RequestInit = {
    method,
    headers: {
      authorization: `Bearer ${config.token}`,
      "content-type": "application/json",
      "x-request-id": randomUUID(),
      "x-sciverse-source": `${PLATFORM}-${config.channel}`,
    },
  };
  if (options.body !== undefined) {
    init.body = JSON.stringify(
      Object.fromEntries(Object.entries(options.body).filter(([, v]) => v !== undefined)),
    );
  }
  const res = await fetch(url, init);
  const text = await res.text();
  if (!res.ok) {
    return {
      isError: true,
      content: [
        {
          type: "text",
          text: JSON.stringify({ status: res.status, body: safeParse(text) }, null, 2),
        },
      ],
    };
  }
  return {
    isError: false,
    content: [{ type: "text", text }],
  };
}

function safeParse(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

async function callBinary(
  config: Config,
  path: string,
  query: Record<string, unknown>,
): Promise<ToolResult> {
  const url = new URL(`${config.baseUrl}${path}`);
  for (const [k, v] of Object.entries(query)) {
    if (v !== undefined && v !== null) url.searchParams.set(k, String(v));
  }
  const res = await fetch(url, {
    method: "GET",
    headers: {
      authorization: `Bearer ${config.token}`,
      accept: "image/*",
      "x-request-id": randomUUID(),
      "x-sciverse-source": `${PLATFORM}-${config.channel}`,
    },
  });
  if (!res.ok) {
    const body = await res.text();
    return {
      isError: true,
      content: [
        {
          type: "text",
          text: JSON.stringify({ status: res.status, body: safeParse(body) }, null, 2),
        },
      ],
    };
  }
  const mimeType = (res.headers.get("content-type") || "application/octet-stream")
    .split(";")[0]!
    .trim();
  const buf = Buffer.from(await res.arrayBuffer());
  return {
    isError: false,
    content: [{ type: "image", data: buf.toString("base64"), mimeType }],
  };
}

export async function executeTool(
  config: Config,
  name: string,
  args: Record<string, unknown>,
): Promise<ToolResult> {
  const endpoints = process.env.SCIVERSE_ENABLE_LEGACY_TOOLS === "true"
    ? { ...ENDPOINTS, ...LEGACY_ENDPOINTS } : ENDPOINTS;
  const endpoint = Object.prototype.hasOwnProperty.call(endpoints, name) ? endpoints[name] : undefined;
  if (!endpoint) {
    return {
      isError: true,
      content: [{ type: "text", text: JSON.stringify({ error: `unknown tool: ${name}` }) }],
    };
  }

  switch (name) {
    case "search_metadata":
    case "search_papers": {
      let body: Record<string, unknown>;
      try {
        body = name === "search_metadata" ? toMetadataPayload(args) : toBackendPayload(args);
      } catch (e) {
        return { isError: true, content: [{ type: "text", text: JSON.stringify({ error: (e as Error).message }) }] };
      }
      return call(config, "POST", endpoint.path, { body });
    }
    case "semantic_search": {
      let body: Record<string, unknown>;
      try {
        body = toSemanticSearchPayload(args);
      } catch (e) {
        return {
          isError: true,
          content: [{ type: "text", text: JSON.stringify({ error: (e as Error).message }) }],
        };
      }
      return call(config, "POST", endpoint.path, { body });
    }
    case "list_catalog": {
      const { include_sample_values, include_field_stats, collection } = args as {
        include_sample_values?: boolean;
        include_field_stats?: boolean;
        collection?: string;
      };
      const query: Record<string, unknown> = {
        include_sample_values: String(Boolean(include_sample_values)),
      };
      if (include_field_stats) query.include_field_stats = "true";
      if (collection) query.collection = collection;
      return call(config, "GET", endpoint.path, { query });
    }
    case "read_content": {
      const { doc_id, collection, offset, limit } = args as {
        collection?: string;
        doc_id?: string;
        offset?: number;
        limit?: number;
      };
      try {
        validateCollection(collection, ["papers", "patents"]);
      } catch (e) {
        return { isError: true, content: [{ type: "text", text: JSON.stringify({ error: (e as Error).message }) }] };
      }
      if (!doc_id) {
        return {
          isError: true,
          content: [{ type: "text", text: JSON.stringify({ error: "doc_id is required" }) }],
        };
      }
      // 后端未传 offset 时返回整篇全文并忽略 limit；这里始终显式传两者，避免把整篇论文灌进模型上下文。
      return call(config, "GET", endpoint.path, {
        query: { doc_id, offset: offset ?? 0, limit: limit ?? 4096, collection },
      });
    }
    case "get_resource": {
      const { file_name } = args as { file_name?: string };
      if (!file_name) {
        return {
          isError: true,
          content: [{ type: "text", text: JSON.stringify({ error: "file_name is required" }) }],
        };
      }
      return callBinary(config, endpoint.path, { file_name });
    }
    case "list_paper_relations": {
      const { unique_id, relation } = args as { unique_id?: string; relation?: string };
      if (!unique_id || !relation) {
        return {
          isError: true,
          content: [{ type: "text", text: JSON.stringify({ error: "unique_id and relation are required" }) }],
        };
      }
      return call(config, "POST", endpoint.path, { body: args });
    }
    default:
      return {
        isError: true,
        content: [{ type: "text", text: JSON.stringify({ error: `unhandled tool: ${name}` }) }],
      };
  }
}

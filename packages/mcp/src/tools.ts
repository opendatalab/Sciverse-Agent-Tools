// HTTP 调用层 + agent-友好参数到后端 canonical payload 的转换。
//
// `toBackendPayload` 是从 packages/typescript/src/client.ts 的 `toBackendPayload`
// 复制过来的（约 50 行）。MCP 包刻意不依赖 TS SDK，避免 monorepo 内部环依赖。
// 后续如有第 4 处复制，再用 codegen 收敛。

import type { Config } from "./config.js";
import { ENDPOINTS } from "./generated/tools.js";
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

const PASSTHROUGH = ["query", "page", "page_size", "fields", "collection"] as const;

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

  const sortByYear = args.sort_by_year as string | undefined;
  if (sortByYear && sortByYear !== "none") {
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
  const endpoint = ENDPOINTS[name];
  if (!endpoint) {
    return {
      isError: true,
      content: [{ type: "text", text: JSON.stringify({ error: `unknown tool: ${name}` }) }],
    };
  }

  switch (name) {
    case "search_papers":
      return call(config, "POST", endpoint.path, { body: toBackendPayload(args) });
    case "semantic_search":
      return call(config, "POST", endpoint.path, { body: args });
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
      const { doc_id, offset, limit } = args as {
        doc_id?: string;
        offset?: number;
        limit?: number;
      };
      if (!doc_id) {
        return {
          isError: true,
          content: [{ type: "text", text: JSON.stringify({ error: "doc_id is required" }) }],
        };
      }
      return call(config, "GET", endpoint.path, { query: { doc_id, offset, limit } });
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
    default:
      return {
        isError: true,
        content: [{ type: "text", text: JSON.stringify({ error: `unhandled tool: ${name}` }) }],
      };
  }
}

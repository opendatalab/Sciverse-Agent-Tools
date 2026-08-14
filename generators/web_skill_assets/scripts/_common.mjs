// Standalone fetch wrapper for Sciverse skill scripts. Zero external dependencies.

import { randomUUID } from "node:crypto";

const CHANNEL = "skills";
const PLATFORM = process.platform; // "linux" | "darwin" | "win32" ...
// 下游 SLS 日志按 X-Sciverse-Source 归因调用来源；与 SDK / MCP 一致用 `${platform}-${channel}`。
// X-Request-Id 仅承载 uuid（与 SDK / MCP 对齐，归因信息走 X-Sciverse-Source）。
const SOURCE = `${PLATFORM}-${CHANNEL}`;

export const TOKEN = process.env.SCIVERSE_API_TOKEN;
export const BASE_URL = (process.env.SCIVERSE_BASE_URL ?? "https://api.sciverse.space").replace(/\/$/, "");

if (!TOKEN) {
  console.error("[sciverse] 错误：环境变量 SCIVERSE_API_TOKEN 未设置。");
  console.error("请前往 https://sciverse.space 申请 API Token 后导出到环境变量。");
  process.exit(2);
}

// Validate BASE_URL to prevent token leakage to arbitrary endpoints
try {
  const parsedUrl = new URL(BASE_URL);
  if (!parsedUrl.hostname.endsWith(".sciverse.space") && parsedUrl.hostname !== "sciverse.space") {
    console.error("[sciverse] 错误：SCIVERSE_BASE_URL 必须指向 *.sciverse.space 域名。");
    process.exit(2);
  }
} catch {
  console.error("[sciverse] 错误：SCIVERSE_BASE_URL 不是合法的 URL。");
  process.exit(2);
}

export async function callSciverse(method, path, options = {}) {
  const headers = {
    authorization: `Bearer ${TOKEN}`,
    "content-type": "application/json",
    "x-request-id": randomUUID(),
    "x-sciverse-source": SOURCE,
  };
  const init = { method, headers };
  let url = `${BASE_URL}${path}`;
  if (options.query) {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(options.query)) {
      if (v !== undefined && v !== null) qs.set(k, String(v));
    }
    url += `?${qs.toString()}`;
  }
  if (options.body !== undefined) {
    const cleaned = Object.fromEntries(
      Object.entries(options.body).filter(([, v]) => v !== undefined),
    );
    init.body = JSON.stringify(cleaned);
  }
  const res = await fetch(url, init);
  if (!res.ok) {
    const body = await res.text();
    console.error(`[sciverse] Sciverse API ${res.status}: ${body}`);
    process.exit(1);
  }
  return await res.json();
}

export async function fetchSciverseResource(fileName) {
  const url = new URL(`${BASE_URL}/resource`);
  url.searchParams.set("file_name", fileName);
  const res = await fetch(url, {
    method: "GET",
    headers: {
      authorization: `Bearer ${TOKEN}`,
      accept: "image/*",
      "x-request-id": randomUUID(),
      "x-sciverse-source": SOURCE,
    },
  });
  if (!res.ok) {
    const body = await res.text();
    console.error(`[sciverse] Sciverse API ${res.status}: ${body}`);
    process.exit(1);
  }
  return res;
}

export function readJsonArg() {
  // 第 3 个 argv（node, script, payload-json）。若缺则回退空对象。
  const raw = process.argv[2] ?? "{}";
  try {
    return JSON.parse(raw);
  } catch (e) {
    console.error(`[sciverse] 入参不是合法 JSON: ${raw}`);
    process.exit(2);
  }
}

// search_papers 便利参数 → platform-console /meta-search canonical 格式。
// 与 SDK / MCP 的 toBackendPayload 同款语义（后端 Pydantic 会静默忽略未知字段，
// 便利参数不翻译=静默失效，所以必须在脚本侧转换）。
const META_PASSTHROUGH = [
  "query", "page", "page_size", "fields", "collection", "cursor", "facets",
  "freshness_boost", "impact_boost", "language_affinity",
];

export function toMetaSearchPayload(args) {
  const out = {};
  const filters = [];
  const sort = [];
  for (const k of META_PASSTHROUGH) {
    if (args[k] !== undefined && args[k] !== null) out[k] = args[k];
  }
  const addFilter = (field, operator, value) => filters.push({ field, operator, value });
  if (args.title_contains != null) addFilter("title", "FILTER_OP_CONTAINS", args.title_contains);
  if (args.abstract_contains != null) addFilter("abstract", "FILTER_OP_CONTAINS", args.abstract_contains);
  if (Array.isArray(args.authors) && args.authors.length > 0) addFilter("author", "FILTER_OP_IN", args.authors);
  if (args.year_from != null) addFilter("publication_published_year", "FILTER_OP_GTE", args.year_from);
  if (args.year_to != null) addFilter("publication_published_year", "FILTER_OP_LTE", args.year_to);
  if (Array.isArray(args.journals) && args.journals.length > 0) addFilter("publication_venue_name_unified", "FILTER_OP_IN", args.journals);
  if (Array.isArray(args.subjects) && args.subjects.length > 0) addFilter("subjects", "FILTER_OP_IN", args.subjects);
  if (Array.isArray(args.filters)) filters.push(...args.filters); // canonical 直传兼容
  if (Array.isArray(args.filters_advanced)) {
    for (const item of args.filters_advanced) filters.push({ operator: "FILTER_OP_EQ", ...item });
  }
  // sort_by_year 默认 auto：有 query（或 sort_advanced）时不加年份排序——保 BM25
  // 相关性且软加权可用；纯结构化筛选时按年份降序（后端默认序实质乱序）。
  let sortByYear = args.sort_by_year ?? "auto";
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
  if (Array.isArray(args.sort)) sort.push(...args.sort); // canonical 直传兼容
  if (Array.isArray(args.sort_advanced)) {
    for (const item of args.sort_advanced) {
      if (item && item.field) sort.push({ field: item.field, order: item.order ?? "SORT_ORDER_DESC" });
    }
  }
  if (filters.length > 0) out.filters = filters;
  if (sort.length > 0) out.sort = sort;
  return out;
}

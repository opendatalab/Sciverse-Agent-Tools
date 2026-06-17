// Standalone fetch wrapper for ClawHub skill scripts. Zero external dependencies.
// 通过 ClawHub skill scripts 调用 Sciverse API 的共享工具。

import { randomUUID } from "node:crypto";

const CHANNEL = "openclaw";
const PLATFORM = process.platform; // "linux" | "darwin" | "win32" ...
// 下游 SLS 日志按 X-Sciverse-Source 归因调用来源；与 SDK / MCP 一致用 `${platform}-${channel}`。
// X-Request-Id 仅承载 uuid（与 SDK / MCP 对齐，归因信息走 X-Sciverse-Source）。
const SOURCE = `${PLATFORM}-${CHANNEL}`;

const TOKEN = process.env.SCIVERSE_API_TOKEN;
const BASE_URL = (process.env.SCIVERSE_BASE_URL ?? "https://api.sciverse.space").replace(/\/$/, "");

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

#!/usr/bin/env node
// get_resource — GET /resource
// 与其他 tool 不同：返回的是图片二进制流。stdout 写 JSON：
//   { mime_type: "image/png", base64: "..." }
// agent 可以从 base64 还原图片。
import { Buffer } from "node:buffer";
import { readJsonArg } from "./_common.mjs";

const args = readJsonArg();
if (!args.file_name) {
  console.error("[get_resource] 必须提供 file_name 字段。");
  process.exit(2);
}

const TOKEN = process.env.SCIVERSE_API_TOKEN;
const BASE_URL = (process.env.SCIVERSE_BASE_URL ?? "https://api.sciverse.space").replace(/\/$/, "");
if (!TOKEN) {
  console.error("[sciverse] 错误：环境变量 SCIVERSE_API_TOKEN 未设置。");
  process.exit(2);
}

const url = new URL(`${BASE_URL}/resource`);
url.searchParams.set("file_name", args.file_name);

const res = await fetch(url, {
  method: "GET",
  headers: {
    authorization: `Bearer ${TOKEN}`,
    accept: "image/*",
  },
});
if (!res.ok) {
  const body = await res.text();
  console.error(`[sciverse] SciVerse API ${res.status}: ${body}`);
  process.exit(1);
}
const mimeType = (res.headers.get("content-type") || "application/octet-stream").split(";")[0].trim();
const buf = Buffer.from(await res.arrayBuffer());
console.log(JSON.stringify({ mime_type: mimeType, base64: buf.toString("base64") }));

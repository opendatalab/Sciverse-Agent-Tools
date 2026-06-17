#!/usr/bin/env node
// get_resource — GET /resource
// 与其他 tool 不同：返回的是图片二进制流。stdout 写 JSON：
//   { mime_type: "image/png", base64: "..." }
// agent 可以从 base64 还原图片。
import { Buffer } from "node:buffer";
import { fetchSciverseResource, readJsonArg } from "./_common.mjs";

const args = readJsonArg();
if (!args.file_name) {
  console.error("[get_resource] 必须提供 file_name 字段。");
  process.exit(2);
}

const res = await fetchSciverseResource(args.file_name);
const mimeType = (res.headers.get("content-type") || "application/octet-stream").split(";")[0].trim();
const buf = Buffer.from(await res.arrayBuffer());
console.log(JSON.stringify({ mime_type: mimeType, base64: buf.toString("base64") }));

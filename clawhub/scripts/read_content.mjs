#!/usr/bin/env node
// read_content — GET /content
import { callSciverse, readJsonArg } from "./_common.mjs";

const args = readJsonArg();
if (!args.doc_id) {
  console.error("[read_content] 必须提供 doc_id 字段。");
  process.exit(2);
}
const result = await callSciverse("GET", "/content", { query: args });
console.log(JSON.stringify(result));

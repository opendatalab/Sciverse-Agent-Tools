#!/usr/bin/env node
// semantic_search — POST /agentic-search
import { callSciverse, readJsonArg } from "./_common.mjs";

const args = readJsonArg();
if (!args.query) {
  console.error("[semantic_search] 必须提供 query 字段。");
  process.exit(2);
}
const result = await callSciverse("POST", "/agentic-search", { body: args });
console.log(JSON.stringify(result));

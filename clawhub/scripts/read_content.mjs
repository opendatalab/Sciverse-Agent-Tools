#!/usr/bin/env node
// read_content — GET /content
import { callSciverse, readJsonArg, validateCollection } from "./_common.mjs";

const args = readJsonArg();
if (!args.doc_id) {
  console.error("[read_content] 必须提供 doc_id 字段。");
  process.exit(2);
}
const query = { ...args, collection: args.collection ?? "papers",
  offset: args.offset ?? 0, limit: args.limit ?? 4096 };
validateCollection(query.collection, ["papers", "patents"]);
const result = await callSciverse("GET", "/content", { query });
console.log(JSON.stringify(result));

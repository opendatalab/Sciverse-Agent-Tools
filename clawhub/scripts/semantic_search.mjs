#!/usr/bin/env node
// semantic_search — POST /agentic-search
import { callSciverse, readJsonArg } from "./_common.mjs";

// 上游 agentic-search（Go 服务）没有 mode 字段，未知字段会被静默丢弃，
// 所以 mode 必须在这里翻译为上游真实参数 retrieval / sub_queries
// （与 packages/typescript/src/client.ts 的 SEMANTIC_MODE_MAP 保持一致）。
const MODE_MAP = {
  fast: { retrieval: "es" },
  balanced: { retrieval: "hybrid" },
  quality: { retrieval: "hybrid", sub_queries: 3 },
};

const args = readJsonArg();
if (!args.query) {
  console.error("[semantic_search] 必须提供 query 字段。");
  process.exit(2);
}

const { mode, ...rest } = args;
let body = rest;
if (mode !== undefined && mode !== null) {
  const mapped = MODE_MAP[mode];
  if (!mapped) {
    console.error(
      `[semantic_search] mode 必须是 ${Object.keys(MODE_MAP).join(" / ")} 之一，收到 ${JSON.stringify(mode)}。`,
    );
    process.exit(2);
  }
  // 显式传入的 retrieval / sub_queries 优先于 mode 映射。
  body = { ...mapped, ...rest };
}

const result = await callSciverse("POST", "/agentic-search", { body });
console.log(JSON.stringify(result));

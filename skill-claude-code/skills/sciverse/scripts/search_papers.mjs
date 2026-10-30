#!/usr/bin/env node
// search_papers — POST /meta-search
// 便利参数（authors/year_from/sort_by_year/filters_advanced…）在脚本侧翻译为
// canonical 格式——后端会静默忽略未知字段，不翻译=参数静默失效。
import { callSciverse, readJsonArg, toMetaSearchPayload } from "./_common.mjs";

const args = readJsonArg();
const result = await callSciverse("POST", "/meta-search", { body: toMetaSearchPayload(args) });
console.log(JSON.stringify(result));

#!/usr/bin/env node
// list_catalog — GET /meta-catalog
import { callSciverse, readJsonArg } from "./_common.mjs";

const args = readJsonArg();
const query = {
  include_sample_values: String(Boolean(args.include_sample_values)),
};
const result = await callSciverse("GET", "/meta-catalog", { query });
console.log(JSON.stringify(result));

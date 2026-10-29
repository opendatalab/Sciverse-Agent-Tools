#!/usr/bin/env node
// list_catalog — GET /meta-catalog
import { callSciverse, readJsonArg } from "./_common.mjs";

const args = readJsonArg();
const query = {
  include_sample_values: String(Boolean(args.include_sample_values)),
};
if (args.include_field_stats) query.include_field_stats = "true";
if (args.collection) query.collection = args.collection;
const result = await callSciverse("GET", "/meta-catalog", { query });
console.log(JSON.stringify(result));

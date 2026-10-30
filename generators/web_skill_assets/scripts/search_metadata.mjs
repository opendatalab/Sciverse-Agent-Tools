#!/usr/bin/env node
// search_metadata — POST /meta-search，canonical 多实体检索。
import { callSciverse, readJsonArg, toMetadataPayload } from "./_common.mjs";

const body = toMetadataPayload(readJsonArg());
const result = await callSciverse("POST", "/meta-search", { body });
console.log(JSON.stringify(result));

#!/usr/bin/env node
// search_papers — POST /meta-search
import { callSciverse, readJsonArg } from "./_common.mjs";

const args = readJsonArg();
const result = await callSciverse("POST", "/meta-search", { body: args });
console.log(JSON.stringify(result));

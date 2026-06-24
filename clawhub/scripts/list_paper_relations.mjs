#!/usr/bin/env node
// list_paper_relations — POST /meta-paper-relations
import { callSciverse, readJsonArg } from "./_common.mjs";

const args = readJsonArg();
const result = await callSciverse("POST", "/meta-paper-relations", { body: args });
console.log(JSON.stringify(result));

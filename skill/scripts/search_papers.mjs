#!/usr/bin/env node
// search_papers — POST /meta-search
import { callSciVerse, readJsonArg } from "./_common.mjs";

const args = readJsonArg();
const result = await callSciVerse("POST", "/meta-search", { body: args });
console.log(JSON.stringify(result));

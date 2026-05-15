#!/usr/bin/env node
// semantic-release prepareCmd 入口：同步 5 处 version 文件 + 重派生。
//
// 调用：`node scripts/bump-versions.mjs <next-version>`
// CWD：repo 根（GitHub Actions checkout 出来的目录）。
//
// 同步的文件：
//   openapi.yaml                     info.version + x-sciverse-tools-version
//   packages/python/pyproject.toml   version = "..."
//   packages/typescript/package.json {"version": "..."}
//   packages/mcp/package.json        {"version": "..."}
//   clawhub/manifest.json            {"version": "..."}
//
// 之后跑 bash scripts/build.sh 让派生产物（dist/openai-tools.json /
// anthropic-tools.json / langchain_tools.py / SKILL.md 等）同步嵌入
// 新 version。

import { execSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const version = process.argv[2];
if (!version) {
  console.error("usage: bump-versions.mjs <version>");
  process.exit(1);
}

const root = process.cwd();
const log = (msg) => console.log(`[bump-versions] ${msg}`);

function bumpYaml(path) {
  const p = resolve(root, path);
  let txt = readFileSync(p, "utf8");
  // info.version: 与 'title:' 等同级缩进；用顶层 'version:' 锚点（多行模式）
  txt = txt.replace(/^( {2}version: ).+$/m, `$1${version}`);
  txt = txt.replace(/^( {2}x-sciverse-tools-version: ).+$/m, `$1${version}`);
  writeFileSync(p, txt, "utf8");
  log(`${path} → ${version}`);
}

function bumpToml(path) {
  const p = resolve(root, path);
  let txt = readFileSync(p, "utf8");
  // 仅替换顶层 [project] 段的第一个 `version = "..."`
  txt = txt.replace(/(^version = ")[^"]+(")/m, `$1${version}$2`);
  writeFileSync(p, txt, "utf8");
  log(`${path} → ${version}`);
}

function bumpJson(path) {
  const p = resolve(root, path);
  const data = JSON.parse(readFileSync(p, "utf8"));
  data.version = version;
  writeFileSync(p, JSON.stringify(data, null, 2) + "\n", "utf8");
  log(`${path} → ${version}`);
}

// 1. 同步五处 version 字段
bumpYaml("openapi.yaml");
bumpToml("packages/python/pyproject.toml");
bumpJson("packages/typescript/package.json");
bumpJson("packages/mcp/package.json");
bumpJson("clawhub/manifest.json");

// 2. 跑 build.sh 重派生产物（dist/*.json + tools.py + tools.ts +
//    SKILL.md + .claude-plugin/marketplace.json）
log("running build.sh to regenerate derived artifacts");
execSync("bash scripts/build.sh", { cwd: root, stdio: "inherit" });

log(`done — agent-tools bumped to v${version}`);

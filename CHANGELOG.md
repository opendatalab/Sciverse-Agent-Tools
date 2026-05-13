# Changelog

All notable changes to `sciverse-agent-tools` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- 新 npm 包 `@sciverse/mcp-server`（`packages/mcp/`）—— stdio 形态 MCP server，把三个检索 tool 暴露给 Claude Code / Cursor / Codex CLI / Windsurf 等支持 MCP 的 coding agent。Tool schema 构建期从 `openapi.yaml` 派生。
- Claude Code 官方 Agent Skill 形态派生（`skill-claude-code/`）+ Plugin Marketplace 入口（`.claude-plugin/marketplace.json`）。
- 主流 coding agent 接入指南（Claude Code / Cursor / Codex CLI / Windsurf），见 `docs/integrations/`。
- GitHub 公开 mirror `opendatalab/SciVerse-agent-tools` + GitLab CI `agent-tools:mirror-sync` job：main 分支变更后自动 `git subtree split` 推到 mirror，给社区可审计 source 链接（替代原 README 路线图中"v0.2 GitHub mirror"计划）。
- README 中 Claude Code Plugin Marketplace URL 占位符替换为 `https://github.com/opendatalab/SciVerse-agent-tools`。

### Changed
- ClawHub skill 迁到 `@sciverse` 组织：`name` 由 `sciverse-agent-tools` 改为 `sciverse-academic-retrieval`，slug `academic-retrieval`，安装命令 `openclaw skills install academic-retrieval`。
- 派生器 `to_clawhub_skill.py`：manifest.json 和 SKILL.md frontmatter 新增 `slug` 字段；version 不再被 openapi.yaml 强制覆盖，读取 manifest.json 现有 version（首次生成时 fallback 到 openapi），允许 skill 独立 bump。

## [0.1.2] - 2026-04-30

### Fixed
- ClawHub publish 流程修复：`--family skill` 必填 flag、跑 `clawhub login --token` 写入本地 config 后再 publish、复制 skill 到非 git 目录避免 source 检测半失败。
- CI stage 重排：`agent-tools:release` / `agent-tools:publish-skill` 移到独立 `publish` stage，在 monorepo 整体 `release-to-gitlab` 之前，避免发布失败时 monorepo tag 已先打出去的副作用。
- `.releaserc.yaml` 的 `releaseRules` 加 `scope: agent-tools, release: false`，让 agent-tools 子项目 commits 不参与 monorepo 整体 semantic-release（之前会误触发 monorepo patch bump）。
- `agent-tools:release` job 打的 git tag 加 `agent-tools-v` 前缀（如 `agent-tools-v0.1.2`），避免与 monorepo 整体 tag (`v1.x.y`) 命名空间冲突。

## [0.1.1] - 2026-04-30

### Changed
- ClawHub `SKILL.md` 与 `manifest.json` 改为英文输出（与 ClawHub 社区惯例对齐，提升国际可发现性 + semantic search 召回率）。OpenAPI 中文 description 保留不变（继续供 OpenAI/Anthropic tool 派生器使用，对齐中文 agent 调用语境）。
- `to_clawhub_skill.py` 派生器优先读取 OpenAPI 扩展字段 `x-en-summary` / `x-en-description`，fallback 到 `summary` / `description`。
- `skill/README.md` 改为英文为主 + 中文备选段（双语）。
- GitLab CI 新增 `agent-tools:publish-skill` job：main 分支 + skill 改动时自动 `npx clawhub package publish` 到 ClawHub。`CLAWHUB_TOKEN` 未配置时 warn + skip。

### Added
- OpenAPI `info` 与三个 operation 新增 `x-en-summary` / `x-en-description` 扩展字段，承载英文文案。

## [0.1.0] - 2026-04-30

### Added
- 三个任务导向 tool：`search_papers`（结构化文献元数据查询）、`semantic_search`（自然语言语义检索）、`read_content`（原文字节切片）
- OpenAPI 3.0 单源契约 (`agent-tools/openapi.yaml`)，每个 operation 字段定义、参数收敛、错误响应
- 三个派生器：OpenAI tool calling JSON / Anthropic tool use JSON / LangChain BaseTool Python 模块
- Python SDK：`sciverse-agent-tools` (PyPI)，`AgentToolsClient` async client + `OPENAI_TOOLS` / `ANTHROPIC_TOOLS` 嵌入常量 + `types.py` pydantic 模型
- TypeScript SDK：`sciverse-agent-tools` (npm)，`AgentToolsClient` fetch-based + 内嵌 tool 常量 + `types.ts` openapi-typescript 派生
- 4 份端到端框架接入示例（Anthropic / OpenAI / LangChain × Python/TS）
- GitLab CI：lint / test / 派生产物漂移检测 / 双包版本号一致性 / 契约测试 / main 分支 PyPI + npm release
- Bearer Token 鉴权 + 错误透传（`httpx.HTTPStatusError` / `Error` 含 status code）
- ClawHub skill bundle（`skill/`）：OpenClaw 用户可通过 `clawhub install sciverse-agent-tools` 一键安装

### Pre-stable notice
版本 `0.1.0` 为 pre-stable。前几个 minor 版本会根据真实 Agent 调用反馈迭代 description 措辞，可能小幅 breaking。

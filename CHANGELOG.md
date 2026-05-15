## [0.4.3](https://github.com/opendatalab/Sciverse-Agent-Tools/compare/v0.4.2...v0.4.3) (2026-05-15)

### Bug Fixes

* 修 ClawHub publish — 去掉 CLI 不支持的 --source-repo / --source-commit ([c2a00a6](https://github.com/opendatalab/Sciverse-Agent-Tools/commit/c2a00a6309068e9271516652e081c08e82f1ca3a))

# Changelog

All notable changes to `sciverse` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.2] - 2026-05-15

### Changed
- CHANGELOG.md 整理 — 合并 v0.3 累计内容到 0.4.1 段、移除 `[Unreleased]` 段；`# Changelog` header 移到文件顶部正确位置。

## [0.4.1] - 2026-05-15

合并 v0.3 累计内容（agent self-discovery、论文图片取回、Python CLI、breaking
包重命名）一次性发出；agent-tools 从 sciverse-console monorepo 抽出，独立
维护到 GitHub `opendatalab/Sciverse-Agent-Tools`。

### Changed
- **Breaking rename**：Python SDK 包名 / 模块名 + TypeScript SDK 包名统一改为 `sciverse`（最短可用名）：
  - PyPI 包 `sciverse-agent-tools` → `sciverse`
  - Python 模块目录 `src/sciverse_agent_tools/` → `src/sciverse/`，所有 `from sciverse_agent_tools` import 同步替换为 `from sciverse`
  - npm 包 `sciverse-agent-tools` → `sciverse`（TS 导入同步）
  - 用户层影响：`pip install sciverse` / `npm install sciverse`
  - MCP server 包 `sciverse-mcp-server`、ClawHub skill `sciverse-academic-retrieval`、Claude Code skill `sciverse` 均不动（各有独立命名空间）
- **目录重命名**：`skill/` → `clawhub/`，避免与 Claude Code 官方 skill（`skill-claude-code/`）混淆，直接对应 ClawHub 平台。
- **架构重构**：agent-tools 从 sciverse-console monorepo 抽出，独立维护在 GitHub `opendatalab/Sciverse-Agent-Tools`。PyPI / npm / ClawHub 发布 + 版本号管理交给独立 repo 上的 semantic-release。原因：monorepo 整体 semantic-release 显式排除 agent-tools，导致 SDK 版本号靠手动 bump 容易忘；又不能直接接入 monorepo 主 release（不然 `fix(metadata-service)` 会污染 PyPI 包版本）；最干净的方案是独立 repo + 独立 release flow。
- 仓库 URL 从 `SciVerse-agent-tools` 修正为 `Sciverse-Agent-Tools`（与 GitHub 实际仓库名一致），所有 packages metadata + README + Plugin Marketplace 链接同步更新。
- `GetCatalogResponse` 移除 `index_name` 字段（后端 OpenSearch 实现细节不该暴露给外部）。诊断由 metadata-service 端 SLS app_logs 承担。
- ClawHub skill version 由 0.1.5 → 0.1.6（含 list_catalog；skill 与 SDK 版本仍独立维护，name 仍为 `sciverse-academic-retrieval` 不跟 SDK 包改名）。

### Added
- **Python CLI `sciverse`**（两类子命令）：
  - **凭据管理**：`sciverse auth login [--token <t>] [--endpoint <url>] [--no-browser]` / `auth status` / `auth logout`
  - **直接调检索 API**（JSON 到 stdout，可 `| jq`）：
    - `sciverse search [QUERY] [--author --year-from --year-to --journal --subject --title-contains --sort-by-year --page --page-size]`
    - `sciverse semantic-search QUERY [--top-k --mode]`
    - `sciverse content DOC_ID [--offset --limit]`
    - `sciverse catalog [--samples]`
    - `sciverse resource FILE_NAME [-o out.png]`（不传 `-o` 时写 stdout，适合管道 `> figure.png`）
  - 通过 `pyproject.toml [project.scripts]` 暴露，`pip install sciverse` / `pipx install sciverse` 后即可用。
- **共享凭据机制**：`sciverse.credentials` 模块提供 `resolve_token()` / `resolve_endpoint()`，按 [显式参数 → 环境变量 → 凭据文件 → 默认值] 顺序解析。`AgentToolsClient` 构造时 token / base_url 都变可选 —— 不传时按上述顺序 fallback，让 `pip install sciverse && sciverse auth login` 之后用户无须再传 token 即可跑 SDK。
- **TypeScript SDK + MCP server 同款凭据 fallback**：
  - `packages/typescript/src/credentials.ts` 和 `packages/mcp/src/credentials.ts`（两个包独立维护同源契约：路径 `~/.sciverse/credentials.json`、JSON 格式、解析顺序）
  - TS SDK `AgentToolsClient` options 改 `token?` / `baseUrl?`，都可省略，按 [显式 → `SCIVERSE_API_TOKEN` / `SCIVERSE_BASE_URL` env → 凭据文件 → 默认] 顺序
  - MCP server `config.ts` 同样 fallback，启动失败信息引导用户跑 `pip install sciverse && sciverse auth login`
  - 21 个新测试覆盖（TS 11 + MCP 10）：env 优先文件、文件 fallback、`*.sciverse.space` 域名白名单仍生效
  - 跑一次 Python CLI 之后，**Python SDK + TS SDK + MCP server 三个客户端形态都自动认到凭据**，零额外配置。
- **新 tool `list_catalog`**（第 4 个）—— 字段 introspection 接口。返回所有可用字段、类型、能否过滤/排序、默认返回字段集、FilterOperator 清单；`include_sample_values=true` 时拉取 enum-like 字段的 top-20 取值样本（OpenSearch terms aggregation，缓存 24h）。Agent 在构造 `search_papers` 前先调用此接口学 schema，避免猜字段名 / 枚举值导致 0 hit 或 4xx。
- **新 tool `get_resource`**（第 5 个）—— 取文献附属图片字节流。触发场景：`read_content` 返回的 Markdown 含 `![alt](file_name)` 占位时，agent 可调本接口拿图片 binary，MCP server 包装为 `image` content block + base64 + mimeType，Claude（multimodal）可直接读图。SDK 返回 `(bytes, mime_type)` tuple。
- SKILL.md（ClawHub + Claude Code 两份）新增 "Bootstrap: learn the schema first" + "Recipes" 段，引导 agent 先调 `list_catalog` 再做精确查询，含 5 种典型组合 pattern（RAG / DOI 查找 / OA 过滤 / enum 字段过滤 / hybrid）。
- 接入指南 4 篇（claude-code / cursor / codex-cli / windsurf）新增 "schema-aware 精确查询" Hello-world prompt。

### Fixed
- 修 GitHub Actions 上 `build.sh` 跑 rollup 缺 linux x64 binary（npm cli#4828），改用 `rm package-lock.json && npm install` 重新解析。
- `publish.sh` 一系列稳定性修复：PyPI 步骤兼容已存在 venv、去重 `npm ci`、各步骤版本-exists check 实现幂等；ClawHub publish 改用 `npm install -g clawhub@latest` 取代 `npx clawhub@latest`（GitHub Actions ubuntu npm 11 misparses npx@latest 形式）。

## [0.2.0] - 2026-05-13

Coding-agent 接入大版本：补齐 MCP / Claude Code Skill / 接入文档三条入口，
ClawHub skill 迁组织，公开 mirror 接通。

### Added
- 新 npm 包 `sciverse-mcp-server`（`packages/mcp/`）—— stdio 形态 MCP server，把三个检索 tool 暴露给 Claude Code / Cursor / Codex CLI / Windsurf 等支持 MCP 的 coding agent。Tool schema 构建期从 `openapi.yaml` 派生。
- Claude Code 官方 Agent Skill 形态派生（`skill-claude-code/`）+ Plugin Marketplace 入口（`.claude-plugin/marketplace.json`）。
- 主流 coding agent 接入指南（Claude Code / Cursor / Codex CLI / Windsurf），见 `docs/integrations/`。
- GitHub 公开 mirror `opendatalab/Sciverse-Agent-Tools` + GitLab CI `agent-tools:mirror-sync` job：main 分支变更后自动 `git subtree split` 推到 mirror，给社区可审计 source 链接（替代原 README 路线图中"v0.2 GitHub mirror"计划）。
- README 中 Claude Code Plugin Marketplace URL 占位符替换为 `https://github.com/opendatalab/Sciverse-Agent-Tools`。

### Changed
- ClawHub skill 迁到 `@sciverse` 组织：`name` 由 `sciverse-agent-tools` 改为 `sciverse-academic-retrieval`，slug `academic-retrieval`，安装命令 `openclaw skills install academic-retrieval`。
- 派生器 `to_clawhub_skill.py`：manifest.json 和 SKILL.md frontmatter 新增 `slug` 字段；version 不再被 openapi.yaml 强制覆盖，读取 manifest.json 现有 version（首次生成时 fallback 到 openapi），允许 skill 独立 bump。
- npm 包名由 `@sciverse/mcp-server` 改为无 scope 的 `sciverse-mcp-server`（避免 npmjs.org 组织注册成本）。所有引用同步替换：README / docs/integrations / Claude skill 派生器 + 产物 / 测试。
- GitLab CI 新增 `agent-tools:release-mcp` job：main + `packages/mcp/**` 变更时 `npm publish` 到 npmjs.org；version 独立读 `packages/mcp/package.json`（不绑 openapi.yaml），tag 前缀 `sciverse-mcp-v` 区分于 SDK 的 `agent-tools-v`。
- `examples/` 新增 Agent SDK 形态示例：`python_claude_agent_sdk.py`（Claude Agent SDK + `mcp_servers` 注入）和 `ts_openai_agents.ts`（`@openai/agents` + `MCPServerStdio`）。与已有的"自己写 tool calling 回环"示例互补，演示 coding-agent 风格 agent loop 由 SDK 处理。
- 根级 `LICENSE`（Apache-2.0 全文）。
- 三个发布包补全 metadata：`repository` / `homepage` / `bugs` / `documentation` / `changelog` URLs（指向 `github.com/opendatalab/Sciverse-Agent-Tools`），Python `pyproject.toml` 中原本拼写错误的 Homepage URL 一并修正。
- README API 速览段新增"长生命周期 client"段，演示手动 `await c.aclose()` 关闭连接池的用法（web server / agent runtime 场景）。
- 版本号 bump `0.1.2` → `0.2.0`（openapi.yaml + Python/TS SDK 同步；MCP `sciverse-mcp-server` 与 SDK 对齐首发 `0.2.0`；ClawHub skill 仍独立维护在 `0.1.5`）。
- examples 中 `claude-opus-4-7` 加注释"按需替换为最新 model id 或 alias"。

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
- OpenAPI 3.0 单源契约 (`openapi.yaml`)，每个 operation 字段定义、参数收敛、错误响应
- 三个派生器：OpenAI tool calling JSON / Anthropic tool use JSON / LangChain BaseTool Python 模块
- Python SDK：`sciverse-agent-tools` (PyPI)，`AgentToolsClient` async client + `OPENAI_TOOLS` / `ANTHROPIC_TOOLS` 嵌入常量 + `types.py` pydantic 模型
- TypeScript SDK：`sciverse-agent-tools` (npm)，`AgentToolsClient` fetch-based + 内嵌 tool 常量 + `types.ts` openapi-typescript 派生
- 4 份端到端框架接入示例（Anthropic / OpenAI / LangChain × Python/TS）
- GitLab CI：lint / test / 派生产物漂移检测 / 双包版本号一致性 / 契约测试 / main 分支 PyPI + npm release
- Bearer Token 鉴权 + 错误透传（`httpx.HTTPStatusError` / `Error` 含 status code）
- ClawHub skill bundle（`skill/`，v0.3 重命名为 `clawhub/`）：OpenClaw 用户可通过 `clawhub install sciverse-agent-tools` 一键安装（v0.2 后改名为 `sciverse-academic-retrieval`）

### Pre-stable notice
版本 `0.1.0` 为 pre-stable。前几个 minor 版本会根据真实 Agent 调用反馈迭代 description 措辞，可能小幅 breaking。

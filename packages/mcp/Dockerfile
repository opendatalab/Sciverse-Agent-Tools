# SciVerse MCP server — Streamable-HTTP transport 镜像
#
# 多阶段构建：
#   - builder: 装全量依赖 + 跑 tsc 产 dist/
#   - runtime: 只 COPY dist/ + package.json，按 --omit=dev 装运行时依赖，减体积
#
# **构建上下文必须是仓库根目录**（因为 packages/mcp/scripts/gen-tools.mjs 通过
# 相对路径 ../../openapi.yaml 读单源 OpenAPI spec）。
# 在仓库根目录执行：
#   docker build -f packages/mcp/Dockerfile \
#     -t docker.shlab.tech/public/sciverse-mcp-server:0.5.0 .
#
# 同目录 .dockerignore（仓库根）已排除 node_modules / .venv / dist / .git 等大目录。

# ---- builder ----
FROM docker.shlab.tech/public/node:21.7.3-alpine AS builder

WORKDIR /app

# 子项目锁文件先拷以最大化 layer cache（源码变更时不会触发 npm ci 重跑）
COPY packages/mcp/package.json packages/mcp/package-lock.json ./
RUN npm ci

# tsconfig + 源码 + 构建脚本
COPY packages/mcp/tsconfig.json ./
COPY packages/mcp/scripts ./scripts
COPY packages/mcp/src ./src

# gen-tools.mjs 解析的目标路径是 ROOT/../../openapi.yaml；容器内 ROOT=/app，
# 所以 OpenAPI 文件必须落在 /openapi.yaml。
COPY openapi.yaml /openapi.yaml

# 跑 gen + tsc 产 dist/
RUN npm run build

# ---- runtime ----
FROM docker.shlab.tech/public/node:21.7.3-alpine AS runtime

WORKDIR /app

# 只装 prod 依赖
COPY packages/mcp/package.json packages/mcp/package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force

# builder 产 dist/
COPY --from=builder /app/dist ./dist

# node:21-alpine 自带 node 用户（uid 1000），切到它
USER node

# 默认监听 8080，由 cli-http 入口读 PORT env
ENV PORT=8080
EXPOSE 8080

CMD ["node", "dist/cli-http.js"]

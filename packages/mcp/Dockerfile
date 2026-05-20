# SciVerse MCP server — Streamable-HTTP transport 镜像
#
# 多阶段构建：
#   - builder: 装全量依赖 + 跑 tsc 产 dist/
#   - runtime: 只 COPY dist/ + package.json，按 --omit=dev 装运行时依赖，减体积
#
# 构建上下文应该为 packages/mcp 目录（COPY 相对路径以此为根）。
# 例如：
#   docker build -f packages/mcp/Dockerfile -t docker.shlab.tech/public/sciverse-mcp-server:0.5.x packages/mcp

# ---- builder ----
FROM node:22-alpine AS builder

WORKDIR /app

# 先 COPY 锁文件以最大化 layer cache：源码变更不会触发 npm ci 重跑
COPY package.json package-lock.json ./
RUN npm ci

# 再 COPY 源码 + 构建脚本
COPY tsconfig.json ./
COPY scripts ./scripts
COPY src ./src

# 跑 gen + tsc，产出 dist/
RUN npm run build

# ---- runtime ----
FROM node:22-alpine AS runtime

# 用非 root 用户跑，最小权限
WORKDIR /app

# 只装 prod 依赖
COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force

# 把 builder 阶段产出的 dist/ 拷过来
COPY --from=builder /app/dist ./dist

# node:22-alpine 自带 node 用户（uid 1000），切到它
USER node

# 默认配置：监听 8080，由 cli-http 入口读 PORT env
ENV PORT=8080
EXPOSE 8080

CMD ["node", "dist/cli-http.js"]

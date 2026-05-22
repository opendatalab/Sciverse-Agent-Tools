#!/usr/bin/env bash
# semantic-release publishCmd：发 PyPI / npm / ClawHub。
#
# 调用：`bash scripts/publish.sh <version>`
# CWD：repo 根。
#
# 设计为完全幂等（idempotent）：脚本任意 step 失败后重跑都安全 ——
# 已发的包 skip、已 push 的 tag 不重复打。详见各 step 内的注释。
#
# 顺序：
#   1. PyPI 包 sciverse                         (twine)
#   2. npm 包 sciverse                          (npm publish)
#   3. npm 包 sciverse-mcp-server               (npm publish)
#   4. ClawHub skill sciverse-academic-retrieval (clawhub skill publish)
#
# 所需 GitHub Actions secrets（在 repo Settings 配）：
#   PYPI_API_TOKEN    — PyPI 上传 token
#   NPM_TOKEN         — npm 上传 token（两个包共用）
#   CLAWHUB_TOKEN     — ClawHub publish token
#
# 失败行为：set -e 任一步失败立即退出，semantic-release 整体 fail，
# 留下 next release notes 草稿但不创建 GitHub Release / 不打 tag。
# 该版本号会"卡住"——下次再合 main 时如果还有未发版改动，会算成
# next version + 0.1（patch）继续尝试。
set -euo pipefail

VERSION="${1:?usage: publish.sh <version>}"
echo "================================="
echo "Publishing Sciverse-Agent-Tools v${VERSION}"
echo "================================="

# 工具：检查 npm 上某版本是否已发过
npm_version_exists() {
  local pkg="$1" ver="$2"
  npm view "${pkg}@${ver}" version --registry=https://registry.npmjs.org 2>/dev/null \
    | grep -q "^${ver}$"
}

# 工具：写完 .npmrc 后立即用 whoami 验证 NPM_TOKEN 当前身份。失败比
# `npm publish` 报的"404 Not Found"清楚得多（npm 对无权限的 PUT 会
# 伪装成 404 避免泄露包存在性，肉眼无法区分 token 失效 vs 名字被占）。
npm_assert_auth() {
  local who
  who=$(npm whoami --registry=https://registry.npmjs.org 2>&1) || {
    echo "  ✗ NPM auth check failed: ${who}" >&2
    echo "    NPM_TOKEN 可能过期/被吊销/类型不对（2FA 账号需 Automation 或 Granular Access token）。" >&2
    exit 1
  }
  echo "  ✓ NPM authed as: ${who}"
}

# ---- 1. PyPI ----
echo "[1/4] PyPI: sciverse"
cd packages/python
uv pip install --quiet build twine
uv build
# `--skip-existing` 让 PyPI 已发同版本时静默跳过（不算失败）
uv run twine upload --skip-existing --non-interactive \
  --username __token__ --password "${PYPI_API_TOKEN}" \
  dist/*
cd ../..

# ---- 2. npm sciverse ----
echo "[2/4] npm: sciverse"
cd packages/typescript
npm run build
if npm_version_exists "sciverse" "${VERSION}"; then
  echo "  sciverse@${VERSION} already on npm, skipping"
else
  echo "//registry.npmjs.org/:_authToken=${NPM_TOKEN}" > .npmrc
  npm_assert_auth
  npm publish --access public --registry=https://registry.npmjs.org
  rm .npmrc
fi
cd ../..

# ---- 3. npm sciverse-mcp-server ----
echo "[3/4] npm: sciverse-mcp-server"
cd packages/mcp
npm run build
if npm_version_exists "sciverse-mcp-server" "${VERSION}"; then
  echo "  sciverse-mcp-server@${VERSION} already on npm, skipping"
else
  echo "//registry.npmjs.org/:_authToken=${NPM_TOKEN}" > .npmrc
  npm_assert_auth
  npm publish --access public --registry=https://registry.npmjs.org
  rm .npmrc
fi
cd ../..

# ---- 4. ClawHub skill ----
echo "[4/4] ClawHub: sciverse-academic-retrieval"
# 预装 clawhub CLI 到一个绝对路径，避免后续 `npx clawhub` 在某些 npm
# 版本上把 'clawhub@latest' 当成命令名查 PATH 而不是包名（GitHub
# Actions ubuntu runner 上 npm 11 行为）。
echo "Installing clawhub CLI..."
npm install --global --no-audit --no-fund clawhub@latest
CLAWHUB_BIN="$(command -v clawhub)"
if [ -z "${CLAWHUB_BIN}" ]; then
  echo "ClawHub CLI install failed" >&2
  exit 1
fi
echo "  clawhub at: ${CLAWHUB_BIN}"

# ClawHub CLI 不读 env，必须先 login 写本地 config
# 重试 3 次（CI runner 出口偶发不稳）
for i in 1 2 3; do
  if "${CLAWHUB_BIN}" login --token "${CLAWHUB_TOKEN}"; then
    echo "ClawHub login OK (attempt $i)"
    break
  fi
  if [ "$i" = "3" ]; then
    echo "ClawHub login failed after 3 attempts" >&2
    exit 1
  fi
  echo "Login attempt $i failed, retrying in 10s..."
  sleep 10
done

# 复制到非 git 目录避免 CLI 嗅探 .git remote
cp -r clawhub /tmp/sciverse-academic-retrieval
cd /tmp/sciverse-academic-retrieval

for i in 1 2 3; do
  # 捕获 stderr 以便识别 "already exists" 类错误
  if OUTPUT=$("${CLAWHUB_BIN}" skill publish . \
       --owner sciverse \
       --slug academic-retrieval \
       --version "${VERSION}" \
       --name "sciverse academic retrieval" 2>&1); then
    echo "${OUTPUT}"
    echo "ClawHub publish OK (attempt $i)"
    break
  fi
  echo "${OUTPUT}"
  # idempotent：版本已发过算成功（重跑 publish.sh 不阻塞）
  if echo "${OUTPUT}" | grep -qi "already exists\|version exists\|duplicate"; then
    echo "ClawHub: ${VERSION} already published, skipping"
    break
  fi
  if [ "$i" = "3" ]; then
    echo "ClawHub publish failed after 3 attempts" >&2
    exit 1
  fi
  echo "Publish attempt $i failed, retrying in 10s..."
  sleep 10
done

echo "================================="
echo "All 4 packages published @ v${VERSION}"
echo "================================="

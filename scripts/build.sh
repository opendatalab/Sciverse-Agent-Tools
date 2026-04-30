#!/usr/bin/env bash
# 全量构建 agent-tools 派生产物：dist/ + packages/*/src/generated/。
# 单一真相源：agent-tools/openapi.yaml 中 info.version。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# 1. 抽取版本号
VERSION=$(uv run python -c "import yaml; print(yaml.safe_load(open('openapi.yaml'))['info']['version'])")
echo "Building agent-tools v${VERSION}"

# 2. 跑三个派生器（OpenAPI → tool format JSON）
uv run python -m generators.to_openai
uv run python -m generators.to_anthropic
uv run python -m generators.to_langchain

# 3. 派生 Python pydantic 模型
uv run datamodel-codegen \
    --input openapi.yaml \
    --input-file-type openapi \
    --output packages/python/src/sciverse_agent_tools/types.py \
    --output-model-type pydantic_v2.BaseModel \
    --target-python-version 3.10 \
    --use-schema-description \
    --field-constraints \
    --use-double-quotes \
    --disable-timestamp
echo "wrote packages/python/src/sciverse_agent_tools/types.py"

# 4. 把 dist/ 下的 tool JSON 嵌入 Python SDK
uv run python - <<'PY'
import json
from pathlib import Path

openai = json.loads(Path("dist/openai-tools.json").read_text(encoding="utf-8"))
anthropic = json.loads(Path("dist/anthropic-tools.json").read_text(encoding="utf-8"))
target = Path("packages/python/src/sciverse_agent_tools/tools.py")
target.write_text(
    f'"""Auto-generated. Do not edit. Run scripts/build.sh."""\n'
    f'TOOLS_VERSION = {json.dumps(openai["version"])}\n'
    f'OPENAI_TOOLS = {json.dumps(openai["tools"], ensure_ascii=False, indent=2)}\n'
    f'ANTHROPIC_TOOLS = {json.dumps(anthropic["tools"], ensure_ascii=False, indent=2)}\n',
    encoding="utf-8"
)
print(f"wrote {target}")
PY

# 5. 派生 TypeScript types
if [ -d "packages/typescript/node_modules" ]; then
    npx --prefix packages/typescript openapi-typescript openapi.yaml -o packages/typescript/src/types.ts
    echo "wrote packages/typescript/src/types.ts"
else
    echo "skipping TS types (run 'npm install' in packages/typescript first)"
fi

# 6. 嵌入 tool 常量到 TypeScript SDK
node -e "
const fs = require('fs');
const openai = JSON.parse(fs.readFileSync('dist/openai-tools.json', 'utf8'));
const anthropic = JSON.parse(fs.readFileSync('dist/anthropic-tools.json', 'utf8'));
const out = \`/** Auto-generated. Do not edit. Run scripts/build.sh. */
export const TOOLS_VERSION = '\${openai.version}';
export const OPENAI_TOOLS = \${JSON.stringify(openai.tools, null, 2)} as const;
export const ANTHROPIC_TOOLS = \${JSON.stringify(anthropic.tools, null, 2)} as const;
\`;
fs.writeFileSync('packages/typescript/src/tools.ts', out);
console.log('wrote packages/typescript/src/tools.ts');
"

# 7. 同步包版本号（packages/* 在后续 phase 创建后这两行才会真正命中）
if [ -f "packages/python/pyproject.toml" ]; then
    sed -i.bak -E "s/^version *= *\".*\"/version = \"${VERSION}\"/" packages/python/pyproject.toml && rm packages/python/pyproject.toml.bak
fi
if [ -f "packages/typescript/package.json" ]; then
    node -e "const fs=require('fs'),p='packages/typescript/package.json';const j=JSON.parse(fs.readFileSync(p));j.version='${VERSION}';fs.writeFileSync(p,JSON.stringify(j,null,2)+'\n')"
fi

# 8. 派生 ClawHub skill bundle (SKILL.md + manifest.json)
uv run python -m generators.to_clawhub_skill

# 9. 自检：派生产物 schema 应能被基础校验通过
uv run python <<'PY'
import json
from pathlib import Path

for p in ["dist/openai-tools.json", "dist/anthropic-tools.json"]:
    data = json.loads(Path(p).read_text(encoding="utf-8"))
    assert "version" in data, f"{p} missing version"
    assert isinstance(data.get("tools"), list) and len(data["tools"]) >= 1, f"{p} tools empty"
print("self-check OK")
PY

echo "Build complete."

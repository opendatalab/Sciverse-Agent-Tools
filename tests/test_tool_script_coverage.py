"""守卫：openapi 每个 operation 都必须有同名 .mjs 脚本（clawhub + web skill）。

脚本式 skill（clawhub / web）的 SKILL.md 会让 agent 运行 `node scripts/<operationId>.mjs`，
若脚本缺失就会"广告了却跑不了"（曾发生于 list_paper_relations）。本守卫确保新增 operation
时不会漏掉对应脚本。
"""
from pathlib import Path

import yaml

from generators._common import iter_operations

ROOT = Path(__file__).resolve().parent.parent
SPEC = yaml.safe_load((ROOT / "openapi.yaml").read_text(encoding="utf-8"))

_SCRIPT_DIRS = (
    ROOT / "clawhub" / "scripts",
    ROOT / "generators" / "web_skill_assets" / "scripts",
)


def test_every_operation_has_skill_script():
    op_ids = [op["operationId"] for _path, _method, op in iter_operations(SPEC)]
    assert op_ids, "openapi 未解析出任何 operation"
    for op_id in op_ids:
        for scripts_dir in _SCRIPT_DIRS:
            mjs = scripts_dir / f"{op_id}.mjs"
            assert mjs.exists(), (
                f"operation '{op_id}' 缺少脚本 {scripts_dir.parent.name}/scripts/{op_id}.mjs"
                " —— 脚本式 skill 的 SKILL.md 会让 agent 跑一个不存在的脚本"
            )

"""共享凭据文件读写。

约定（与 MCP server / TS SDK 一致）：
- 路径：`~/.sciverse/credentials.json`
- 文件权限：0600（仅当前用户可读写）
- 内容：
  {
    "token": "sv-xxx",
    "endpoint": "https://api.sciverse.space",
    "saved_at": "2026-05-14T15:30:00Z"
  }

读取顺序（client.py / cli.py 共用）：
  1. 显式构造 client 传 token
  2. 环境变量 SCIVERSE_API_TOKEN
  3. 凭据文件
"""
from __future__ import annotations

import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict


class Credentials(TypedDict, total=False):
    token: str
    endpoint: str
    saved_at: str


DEFAULT_ENDPOINT = "https://api.sciverse.space"


def credentials_path() -> Path:
    return Path.home() / ".sciverse" / "credentials.json"


def load_credentials() -> Credentials | None:
    """读凭据文件。文件不存在 / 解析失败 / 不是 dict 时返回 None（不抛错）。"""
    path = credentials_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data  # type: ignore[return-value]


def save_credentials(token: str, endpoint: str = DEFAULT_ENDPOINT) -> Path:
    """保存凭据到 ~/.sciverse/credentials.json，文件权限设为 0600。返回 path。"""
    path = credentials_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: Credentials = {
        "token": token,
        "endpoint": endpoint,
        "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    # 0600
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        # Windows / 某些 FS 不支持 chmod；保留文件，不抛错
        pass
    return path


def delete_credentials() -> bool:
    """删凭据文件。文件不存在时返回 False，删除成功返回 True。"""
    path = credentials_path()
    if not path.exists():
        return False
    path.unlink()
    return True


def resolve_token(explicit: str | None = None) -> str | None:
    """按 [显式参数 → SCIVERSE_API_TOKEN → 凭据文件] 顺序返回 token，
    都没有时返回 None（不抛错；让调用方决定怎么提示用户）。"""
    if explicit:
        return explicit
    env_token = os.environ.get("SCIVERSE_API_TOKEN")
    if env_token:
        return env_token
    creds = load_credentials()
    if creds and creds.get("token"):
        return creds["token"]
    return None


def resolve_endpoint(explicit: str | None = None) -> str:
    """按 [显式参数 → SCIVERSE_BASE_URL → 凭据文件 → 默认值] 顺序返回 endpoint。"""
    if explicit:
        return explicit
    env_url = os.environ.get("SCIVERSE_BASE_URL")
    if env_url:
        return env_url
    creds = load_credentials()
    if creds and creds.get("endpoint"):
        return creds["endpoint"]
    return DEFAULT_ENDPOINT

"""凭据文件读写 + resolve_token / resolve_endpoint 单测。"""
from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from sciverse import credentials as creds_mod
from sciverse.credentials import (
    DEFAULT_ENDPOINT,
    delete_credentials,
    load_credentials,
    resolve_endpoint,
    resolve_token,
    save_credentials,
)


@pytest.fixture
def tmp_home(tmp_path, monkeypatch):
    """把 HOME 指向 tmp，让凭据文件落在 tmp_path/.sciverse/credentials.json。"""
    monkeypatch.setenv("HOME", str(tmp_path))
    # 同时清掉环境变量影响
    monkeypatch.delenv("SCIVERSE_API_TOKEN", raising=False)
    monkeypatch.delenv("SCIVERSE_BASE_URL", raising=False)
    return tmp_path


def test_save_and_load_roundtrip(tmp_home):
    path = save_credentials("sv-abc123", "https://api-custom.sciverse.space")
    assert path.exists()
    assert path == tmp_home / ".sciverse" / "credentials.json"

    loaded = load_credentials()
    assert loaded is not None
    assert loaded["token"] == "sv-abc123"
    assert loaded["endpoint"] == "https://api-custom.sciverse.space"
    assert "saved_at" in loaded


def test_save_sets_0600_permissions(tmp_home):
    path = save_credentials("sv-abc")
    if sys.platform == "win32":
        pytest.skip("Windows 不强校验 POSIX 权限")
    mode = path.stat().st_mode & 0o777
    assert mode == 0o600, f"expected 0600 got {oct(mode)}"


def test_load_returns_none_when_missing(tmp_home):
    assert load_credentials() is None


def test_load_returns_none_on_corrupt_file(tmp_home):
    path = tmp_home / ".sciverse" / "credentials.json"
    path.parent.mkdir()
    path.write_text("not json")
    assert load_credentials() is None


def test_delete(tmp_home):
    save_credentials("sv-xxx")
    assert delete_credentials() is True
    assert not (tmp_home / ".sciverse" / "credentials.json").exists()
    # 再删一次返回 False
    assert delete_credentials() is False


def test_resolve_token_explicit_wins(tmp_home, monkeypatch):
    save_credentials("sv-from-file")
    monkeypatch.setenv("SCIVERSE_API_TOKEN", "sv-from-env")
    assert resolve_token("sv-explicit") == "sv-explicit"


def test_resolve_token_env_beats_file(tmp_home, monkeypatch):
    save_credentials("sv-from-file")
    monkeypatch.setenv("SCIVERSE_API_TOKEN", "sv-from-env")
    assert resolve_token() == "sv-from-env"


def test_resolve_token_falls_back_to_file(tmp_home):
    save_credentials("sv-from-file")
    assert resolve_token() == "sv-from-file"


def test_resolve_token_none_when_no_source(tmp_home):
    assert resolve_token() is None


def test_resolve_endpoint_default(tmp_home):
    assert resolve_endpoint() == DEFAULT_ENDPOINT


def test_resolve_endpoint_from_file(tmp_home):
    save_credentials("sv-x", "https://api-custom.sciverse.space")
    assert resolve_endpoint() == "https://api-custom.sciverse.space"


def test_resolve_endpoint_env_beats_file(tmp_home, monkeypatch):
    save_credentials("sv-x", "https://api-custom.sciverse.space")
    monkeypatch.setenv("SCIVERSE_BASE_URL", "https://api.sciverse.space")
    assert resolve_endpoint() == "https://api.sciverse.space"


def test_client_fallback_to_credentials(tmp_home):
    """AgentToolsClient 不传 token 时应该从凭据文件 fallback 拿到。"""
    save_credentials("sv-from-file", "https://api.sciverse.space")
    from sciverse import AgentToolsClient

    c = AgentToolsClient()
    assert c._token == "sv-from-file"
    assert c._base_url == "https://api.sciverse.space"


def test_client_raises_when_no_token_anywhere(tmp_home):
    from sciverse import AgentToolsClient

    with pytest.raises(ValueError, match="未找到 Sciverse API Token"):
        AgentToolsClient()

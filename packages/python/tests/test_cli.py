"""`sciverse` CLI 单测。"""
from __future__ import annotations

import pytest

from sciverse.cli import main


@pytest.fixture
def tmp_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("SCIVERSE_API_TOKEN", raising=False)
    monkeypatch.delenv("SCIVERSE_BASE_URL", raising=False)
    return tmp_path


def test_status_when_logged_out(tmp_home, capsys):
    code = main(["auth", "status"])
    assert code == 1
    out = capsys.readouterr().out
    assert "未登录" in out


def test_login_with_explicit_token(tmp_home, capsys):
    code = main(["auth", "login", "--token", "sv-test123", "--no-browser"])
    assert code == 0
    out = capsys.readouterr().out
    assert "凭据已保存" in out
    # 文件实际写入
    creds_file = tmp_home / ".sciverse" / "credentials.json"
    assert creds_file.exists()


def test_status_after_login(tmp_home, capsys):
    main(["auth", "login", "--token", "sv-abcdef12345", "--no-browser"])
    capsys.readouterr()  # discard login output
    code = main(["auth", "status"])
    assert code == 0
    out = capsys.readouterr().out
    assert "已登录" in out
    # token 应被打码
    assert "sv-abcdef12345" not in out


def test_login_custom_endpoint(tmp_home, capsys):
    main([
        "auth", "login",
        "--token", "sv-x",
        "--endpoint", "https://api-custom.sciverse.space",
        "--no-browser",
    ])
    out = capsys.readouterr().out
    assert "api-custom.sciverse.space" in out


def test_login_empty_token_fails(tmp_home, capsys):
    code = main(["auth", "login", "--token", "  ", "--no-browser"])
    assert code == 1


def test_logout_when_logged_in(tmp_home, capsys):
    main(["auth", "login", "--token", "sv-x", "--no-browser"])
    capsys.readouterr()
    code = main(["auth", "logout"])
    assert code == 0
    assert "已删除" in capsys.readouterr().out


def test_logout_when_not_logged_in(tmp_home, capsys):
    code = main(["auth", "logout"])
    assert code == 1


# ---- 检索类命令路由测试（mock AgentToolsClient，不真发请求） ----


import json
from unittest.mock import AsyncMock, patch


@pytest.fixture
def logged_in(tmp_home):
    """先 login 一个测试 token，避免 client 构造抛 ValueError。"""
    main(["auth", "login", "--token", "sv-test", "--no-browser"])


def _patch_client(method_name: str, return_value):
    """patch AgentToolsClient.{method} 返指定值；同时让 aclose 是 no-op。
    cli.py 里走 `from .client import AgentToolsClient`，所以 patch
    `sciverse.client.AgentToolsClient` 命中模块级符号。"""
    client_target = "sciverse.client.AgentToolsClient"
    instance = type("FakeClient", (), {})()
    setattr(instance, method_name, AsyncMock(return_value=return_value))
    instance.aclose = AsyncMock(return_value=None)
    return patch(client_target, return_value=instance), instance


def test_search_basic(logged_in, capsys):
    p, inst = _patch_client("search_papers", {"hits": [{"doc_id": "p_1", "title": "T"}], "total": 1})
    with p:
        code = main(["search", "transformer", "--year-from", "2020", "--author", "Hinton"])
    assert code == 0
    inst.search_papers.assert_awaited_once()
    call_kwargs = inst.search_papers.call_args.kwargs
    assert call_kwargs["query"] == "transformer"
    assert call_kwargs["year_from"] == 2020
    assert call_kwargs["authors"] == ["Hinton"]
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["hits"][0]["doc_id"] == "p_1"


def test_search_sort_by_year_passed_through_verbatim(logged_in, capsys):
    """CLI 把 sort_by_year 原样透传给 SDK（auto/none 语义由 client 统一解析，
    避免 CLI 与 SDK 各解析一套出现渠道分叉——曾经 CLI 默认 desc、SDK 默认无排序）。"""
    p, inst = _patch_client("search_papers", {"hits": [], "total": 0})
    with p:
        code = main(["search", "x", "--sort-by-year", "none"])
    assert code == 0
    assert inst.search_papers.call_args.kwargs["sort_by_year"] == "none"

    p, inst = _patch_client("search_papers", {"hits": [], "total": 0})
    with p:
        code = main(["search", "x"])
    assert code == 0
    assert inst.search_papers.call_args.kwargs["sort_by_year"] == "auto"


def test_semantic_search(logged_in, capsys):
    p, inst = _patch_client("semantic_search", {"hits": [{"chunk_id": "c1", "doc_id": "p_1"}]})
    with p:
        code = main(["semantic-search", "attention", "--top-k", "5", "--mode", "fast"])
    assert code == 0
    kw = inst.semantic_search.call_args.kwargs
    assert kw == {"query": "attention", "top_k": 5, "mode": "fast"}
    data = json.loads(capsys.readouterr().out)
    assert data["hits"][0]["chunk_id"] == "c1"


def test_content(logged_in, capsys):
    p, inst = _patch_client(
        "read_content",
        {"text": "abc", "bytes_returned": 3, "next_offset": 3, "more": False},
    )
    with p:
        code = main(["content", "p_xxx", "--offset", "100", "--limit", "1024"])
    assert code == 0
    kw = inst.read_content.call_args.kwargs
    assert kw == {"doc_id": "p_xxx", "offset": 100, "limit": 1024}


def test_catalog_without_samples(logged_in, capsys):
    p, inst = _patch_client("list_catalog", {"fields": [], "default_fields": [], "filter_operators": []})
    with p:
        code = main(["catalog"])
    assert code == 0
    kw = inst.list_catalog.call_args.kwargs
    assert kw["include_sample_values"] is False


def test_catalog_with_samples(logged_in, capsys):
    p, inst = _patch_client("list_catalog", {"fields": [], "default_fields": [], "filter_operators": []})
    with p:
        code = main(["catalog", "--samples"])
    assert code == 0
    assert inst.list_catalog.call_args.kwargs["include_sample_values"] is True


def test_resource_to_file(logged_in, tmp_path, capsys):
    png = b"\x89PNG\r\n\x1a\n"
    p, inst = _patch_client("get_resource", (png, "image/png"))
    out_file = tmp_path / "out.png"
    with p:
        code = main(["resource", "dt=x/p/y.png", "-o", str(out_file)])
    assert code == 0
    assert out_file.read_bytes() == png
    # 状态信息到 stderr
    err = capsys.readouterr().err
    assert "image/png" in err and "8 bytes" in err


def test_search_without_login_returns_2(tmp_home, capsys):
    """没 login 也没 env 时，client 构造抛 ValueError，CLI 返 2。"""
    code = main(["search", "x"])
    assert code == 2
    err = capsys.readouterr().err
    assert "未找到 Sciverse API Token" in err

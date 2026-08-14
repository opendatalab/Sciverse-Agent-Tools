"""`sciverse` CLI

两类子命令：
  - `auth login/logout/status`：本地凭据管理（token-paste 模式，类似
    `aws configure` / `gh auth login --with-token`；不实现完整 OAuth
    device-code flow，需要后端 + 控制台前端配套时再升级，命令接口保持
    兼容）
  - `search` / `semantic-search` / `content` / `catalog` / `resource`：
    直接调五个检索 API；JSON 输出到 stdout，方便 `| jq` / `| less`，
    错误输出到 stderr，与 token / endpoint fallback 链路共用（env >
    凭据文件 > 默认）
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import webbrowser
from pathlib import Path
from typing import Any, Sequence

from .credentials import (
    DEFAULT_ENDPOINT,
    credentials_path,
    delete_credentials,
    load_credentials,
    save_credentials,
)

CONSOLE_TOKEN_URL = "https://sciverse.space/tokens"


def _print_json(data: Any) -> None:
    """JSON 输出（pretty 但保留 unicode）。"""
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _run_with_client(coro_factory) -> int:
    """共享：构造 AgentToolsClient，捕获常见错误返出适当 exit code。"""
    from .client import AgentToolsClient
    try:
        client = AgentToolsClient()
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2  # config-like error

    async def _runner() -> int:
        try:
            await coro_factory(client)
        finally:
            await client.aclose()
        return 0

    try:
        return asyncio.run(_runner())
    except Exception as e:
        print(f"错误：{e}", file=sys.stderr)
        return 1


def _cmd_login(args: argparse.Namespace) -> int:
    print("Sciverse 登录")
    print("-" * 40)
    print(f"1. 浏览器将打开控制台 token 页：{CONSOLE_TOKEN_URL}")
    print("2. 登录后创建 / 复制一个 API Token（形如 sv-xxx）")
    print("3. 把 token 粘贴回这里")
    print()

    if not args.no_browser:
        try:
            webbrowser.open(CONSOLE_TOKEN_URL)
        except Exception:
            print(f"[warn] 无法自动打开浏览器，请手动访问 {CONSOLE_TOKEN_URL}")

    # 用 getpass 避免 token 在 shell history 留痕
    if args.token:
        token = args.token.strip()
    else:
        try:
            from getpass import getpass
            token = getpass("Token: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已取消", file=sys.stderr)
            return 1

    if not token:
        print("错误：token 为空", file=sys.stderr)
        return 1
    if not token.startswith("sv-"):
        print(
            "[warn] token 看起来不像 Sciverse 格式（应以 sv- 开头），"
            "但仍按用户输入保存。",
            file=sys.stderr,
        )

    endpoint = args.endpoint or DEFAULT_ENDPOINT
    path = save_credentials(token, endpoint)
    print(f"✓ 凭据已保存到 {path}（权限 0600）")
    print(f"  endpoint: {endpoint}")
    print()
    print("现在 Python / TS SDK / MCP server 不需要再传 token —— 会自动读取本文件。")
    print("更换 token：再跑一次 `sciverse auth login`。")
    print("删除：`sciverse auth logout`。")
    return 0


def _cmd_logout(_: argparse.Namespace) -> int:
    if delete_credentials():
        print(f"✓ 已删除 {credentials_path()}")
        return 0
    print(f"凭据文件不存在：{credentials_path()}", file=sys.stderr)
    return 1


def _cmd_status(_: argparse.Namespace) -> int:
    path = credentials_path()
    creds = load_credentials()
    if creds is None:
        print(f"未登录。运行 `sciverse auth login` 完成登录。")
        print(f"凭据文件路径（未创建）：{path}")
        return 1
    token = creds.get("token", "")
    masked = (token[:6] + "…" + token[-4:]) if len(token) > 12 else "***"
    print(f"已登录")
    print(f"  凭据文件: {path}")
    print(f"  token:    {masked}")
    print(f"  endpoint: {creds.get('endpoint', DEFAULT_ENDPOINT)}")
    print(f"  保存时间: {creds.get('saved_at', '?')}")
    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    async def _do(client):
        kwargs = {}
        if args.query: kwargs["query"] = args.query
        if args.authors: kwargs["authors"] = args.authors
        if args.year_from is not None: kwargs["year_from"] = args.year_from
        if args.year_to is not None: kwargs["year_to"] = args.year_to
        if args.journals: kwargs["journals"] = args.journals
        if args.subjects: kwargs["subjects"] = args.subjects
        if args.title_contains: kwargs["title_contains"] = args.title_contains
        if args.abstract_contains: kwargs["abstract_contains"] = args.abstract_contains
        kwargs["sort_by_year"] = args.sort_by_year  # auto/none 的语义由 client 统一解析
        if getattr(args, "collection", "papers") != "papers": kwargs["collection"] = args.collection
        if args.freshness_boost != "NONE": kwargs["freshness_boost"] = args.freshness_boost
        if args.impact_boost != "NONE": kwargs["impact_boost"] = args.impact_boost
        if args.language_affinity != "NONE": kwargs["language_affinity"] = args.language_affinity
        kwargs["page"] = args.page
        kwargs["page_size"] = args.page_size
        r = await client.search_papers(**kwargs)
        _print_json(r)

    return _run_with_client(_do)


def _cmd_semantic_search(args: argparse.Namespace) -> int:
    async def _do(client):
        r = await client.semantic_search(
            query=args.query, top_k=args.top_k, mode=args.mode,
        )
        _print_json(r)

    return _run_with_client(_do)


def _cmd_paper_relations(args: argparse.Namespace) -> int:
    async def _do(client):
        r = await client.list_paper_relations(
            unique_id=args.unique_id, relation=args.relation,
            page=args.page, page_size=args.page_size,
        )
        _print_json(r)

    return _run_with_client(_do)


def _cmd_content(args: argparse.Namespace) -> int:
    async def _do(client):
        r = await client.read_content(
            doc_id=args.doc_id, offset=args.offset, limit=args.limit,
        )
        _print_json(r)

    return _run_with_client(_do)


def _cmd_catalog(args: argparse.Namespace) -> int:
    async def _do(client):
        r = await client.list_catalog(
            include_sample_values=args.samples,
            collection=getattr(args, "collection", None),
        )
        _print_json(r)

    return _run_with_client(_do)


def _cmd_resource(args: argparse.Namespace) -> int:
    """图片二进制：默认写到 stdout（binary），加 `-o` 时写文件。"""
    async def _do(client):
        bytes_, mime = await client.get_resource(file_name=args.file_name)
        if args.output:
            out = Path(args.output)
            out.write_bytes(bytes_)
            print(f"✓ wrote {len(bytes_)} bytes to {out} (mime: {mime})", file=sys.stderr)
        else:
            # stdout binary 写入（适合 `sciverse resource ... > out.png`）
            sys.stdout.buffer.write(bytes_)
            print(f"[wrote {len(bytes_)} bytes to stdout, mime: {mime}]", file=sys.stderr)

    return _run_with_client(_do)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sciverse",
        description="Sciverse 开发者工具 CLI。",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    auth = sub.add_parser("auth", help="本地凭据管理")
    auth_sub = auth.add_subparsers(dest="auth_command", required=True)

    login = auth_sub.add_parser(
        "login",
        help="保存 API Token 到 ~/.sciverse/credentials.json",
    )
    login.add_argument(
        "--token",
        help="直接传入 token（跳过交互式粘贴；适合脚本场景）",
    )
    login.add_argument(
        "--endpoint",
        help=f"API endpoint，默认 {DEFAULT_ENDPOINT}",
    )
    login.add_argument(
        "--no-browser",
        action="store_true",
        help="不自动打开浏览器（远程 / 无桌面环境）",
    )
    login.set_defaults(func=_cmd_login)

    logout = auth_sub.add_parser("logout", help="删除本地凭据文件")
    logout.set_defaults(func=_cmd_logout)

    status = auth_sub.add_parser("status", help="查看当前凭据状态")
    status.set_defaults(func=_cmd_status)

    # ---- 检索类子命令（直接调五个 API） ----

    search = sub.add_parser(
        "search",
        help="结构化元数据检索（POST /meta-search）",
        description=(
            "按结构化字段过滤检索文献元数据。query 走全文 BM25（可选），"
            "其它参数是可叠加的精确过滤。所有 hits 以 JSON pretty 输出到 stdout。"
        ),
    )
    search.add_argument("query", nargs="?", default="", help="全文 BM25 关键词（可选）")
    search.add_argument("--collection", choices=["papers", "authors", "sources"], default="papers",
                        help="实体集合（默认 papers）。authors/sources 的高级字段过滤请用 SDK 的 "
                             "filters_advanced / sort_advanced；CLI 主要支持 query 与 catalog 自省")
    search.add_argument("--author", "--authors", action="append", default=[], dest="authors",
                        help="作者名（可多次传，任一命中即可）")
    search.add_argument("--year-from", type=int, dest="year_from", help="起始年（含）")
    search.add_argument("--year-to", type=int, dest="year_to", help="结束年（含）")
    search.add_argument("--journal", "--journals", action="append", default=[], dest="journals",
                        help="期刊名（可多次传）")
    search.add_argument("--subject", "--subjects", action="append", default=[], dest="subjects",
                        help="学科分类（可多次传）")
    search.add_argument("--title-contains", dest="title_contains", help="标题包含关键词")
    search.add_argument("--abstract-contains", dest="abstract_contains", help="摘要包含关键词")
    search.add_argument("--sort-by-year", choices=["auto", "desc", "asc", "none"], default="auto",
                        dest="sort_by_year",
                        help="按年份排序，默认 auto（有 query 走相关性、纯筛选按年降序）；"
                             "query+desc 会让相关性失效，求「相关且新」用 --freshness-boost")
    search.add_argument("--freshness-boost", choices=["NONE", "MILD", "STRONG"], default="NONE",
                        dest="freshness_boost",
                        help="模糊搜索新鲜度加权：MILD=近10年加权 / STRONG=近3年加权。仅 query 非空时生效；传排序时被忽略")
    search.add_argument("--impact-boost", choices=["NONE", "MILD", "STRONG"], default="NONE",
                        dest="impact_boost",
                        help="模糊搜索影响力加权：高被引上浮（有界、零被引中性）。仅 query 非空时生效；可与其他 boost 叠加")
    search.add_argument("--language-affinity", choices=["NONE", "MILD", "STRONG"], default="NONE",
                        dest="language_affinity",
                        help="模糊搜索语言亲和加权：非 query 语言结果降序（不排除）；MILD=×0.5 / STRONG=×0.2。仅 query 非空时生效")
    search.add_argument("--page", type=int, default=1, help="页码，从 1 开始")
    search.add_argument("--page-size", type=int, default=10, dest="page_size",
                        help="每页数量，默认 10，上限 50")
    search.set_defaults(func=_cmd_search)

    sem = sub.add_parser(
        "semantic-search",
        help="自然语言语义检索（POST /agentic-search，返回 chunk）",
    )
    sem.add_argument("query", help="自然语言查询（1-200 字最佳）")
    sem.add_argument("--top-k", type=int, default=10, dest="top_k",
                     help="返回 chunk 数量，默认 10，上限 100（balanced 在服务端固定截到约 50，"
                          "要更多请用 --mode quality 或 fast）")
    sem.add_argument("--mode", choices=["fast", "balanced", "quality"], default="balanced",
                     help="fast=纯关键词 (~200ms) / balanced=混合 (~600ms，默认) / quality=LLM 改写 (~2-4s)")
    sem.set_defaults(func=_cmd_semantic_search)

    rel = sub.add_parser(
        "paper-relations",
        help="分页查某论文的引用/被引/相关工作（POST /meta-paper-relations）",
    )
    rel.add_argument("unique_id", help="目标论文 unique_id（来自 search / semantic-search；勿传 doc_id）")
    rel.add_argument("--relation", choices=["CITATIONS", "REFERENCES", "RELATED_WORKS"], required=True,
                     help="CITATIONS=被引（谁引用了我）/ REFERENCES=参考文献（我引用了谁）/ RELATED_WORKS=相关工作")
    rel.add_argument("--page", type=int, default=1, help="页码，从 1 开始")
    rel.add_argument("--page-size", type=int, default=25, dest="page_size",
                     help="每页数量，默认 25，上限 200")
    rel.set_defaults(func=_cmd_paper_relations)

    content = sub.add_parser("content", help="读文献原文字节区间（GET /content）")
    content.add_argument("doc_id", help="文献 ID（来自 search / semantic-search hits）")
    content.add_argument("--offset", type=int, default=0, help="起始字节偏移，默认 0")
    content.add_argument("--limit", type=int, default=4096,
                         help="读取字节数，默认 4096，上限 16384")
    content.set_defaults(func=_cmd_content)

    cat = sub.add_parser(
        "catalog",
        help="字段 introspection（GET /meta-catalog），第一次接入时建议先调",
    )
    cat.add_argument("--collection", choices=["papers", "authors", "sources"], default="papers",
                     help="字段目录所属实体集合（默认 papers）")
    cat.add_argument("--samples", action="store_true",
                     help="拉枚举字段的取值样本（首次 OpenSearch terms agg，~几百 ms；之后 24h 缓存）")
    cat.set_defaults(func=_cmd_catalog)

    res = sub.add_parser(
        "resource",
        help="取文献附属图片二进制（GET /resource）",
    )
    res.add_argument("file_name", help="图片相对路径，来自 content 输出 Markdown 的 ![alt](file_name) 占位")
    res.add_argument("-o", "--output", help="输出文件路径；省略则写到 stdout（适合管道，如 > out.png）")
    res.set_defaults(func=_cmd_resource)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

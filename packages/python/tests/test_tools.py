from sciverse import OPENAI_TOOLS, ANTHROPIC_TOOLS, TOOLS_VERSION, AgentToolsClient


def test_all_tools_exposed():
    # version 是 semver 字符串即可，不硬编码具体值（避免每次 bump 都要改测试）
    assert isinstance(TOOLS_VERSION, str) and TOOLS_VERSION.count(".") >= 1
    names = {t["function"]["name"] for t in OPENAI_TOOLS}
    assert names == {"search_papers", "semantic_search", "list_catalog", "list_paper_relations", "read_content", "get_resource"}
    anthropic_names = {t["name"] for t in ANTHROPIC_TOOLS}
    assert anthropic_names == names


def test_every_tool_has_client_method():
    """守卫：每个广告的工具都必须有对应的 AgentToolsClient 方法（方法名即 snake_case
    工具名）。防止"openapi/生成 schema 加了工具但 SDK client 漏了方法"。"""
    for t in OPENAI_TOOLS:
        name = t["function"]["name"]
        assert hasattr(AgentToolsClient, name), f"AgentToolsClient 缺少工具 '{name}' 的方法"

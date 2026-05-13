from sciverse_agent_tools import OPENAI_TOOLS, ANTHROPIC_TOOLS, TOOLS_VERSION


def test_all_tools_exposed():
    # version 是 semver 字符串即可，不硬编码具体值（避免每次 bump 都要改测试）
    assert isinstance(TOOLS_VERSION, str) and TOOLS_VERSION.count(".") >= 1
    names = {t["function"]["name"] for t in OPENAI_TOOLS}
    assert names == {"search_papers", "semantic_search", "list_catalog", "read_content"}
    anthropic_names = {t["name"] for t in ANTHROPIC_TOOLS}
    assert anthropic_names == names

from sciverse_agent_tools import OPENAI_TOOLS, ANTHROPIC_TOOLS, TOOLS_VERSION


def test_three_tools_exposed():
    assert TOOLS_VERSION == "0.1.2"
    names = {t["function"]["name"] for t in OPENAI_TOOLS}
    assert names == {"search_papers", "semantic_search", "read_content"}
    anthropic_names = {t["name"] for t in ANTHROPIC_TOOLS}
    assert anthropic_names == names

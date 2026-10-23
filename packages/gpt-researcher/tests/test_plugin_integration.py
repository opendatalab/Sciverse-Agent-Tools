"""Exercise the installed wheel against real upstream discovery and consumption."""

import asyncio
from importlib.metadata import entry_points
from types import SimpleNamespace
from unittest.mock import Mock

import requests

from gpt_researcher_sciverse import SciverseSearch


def test_installed_plugin_is_discovered_and_accepted(monkeypatch):
    from gpt_researcher.actions.retriever import get_retriever, get_retrievers
    from gpt_researcher.config.config import Config

    eps = list(entry_points(group="gpt_researcher.retrievers", name="sciverse"))
    assert len(eps) == 1
    assert eps[0].load() is SciverseSearch
    assert get_retriever("sciverse") is SciverseSearch
    monkeypatch.setenv("RETRIEVER", "sciverse")
    cfg = Config()
    assert cfg.retrievers == ["sciverse"]
    assert get_retrievers({}, cfg) == [SciverseSearch]
    mixed = get_retrievers({"retrievers": "sciverse, duckduckgo"}, cfg)
    assert mixed[0] is SciverseSearch
    assert mixed[1] is get_retriever("duckduckgo")


def test_passage_reaches_upstream_context_without_scraping(monkeypatch):
    from gpt_researcher.actions.retriever import get_retriever
    from gpt_researcher.skills.researcher import ResearchConductor

    monkeypatch.setenv("SCIVERSE_API_TOKEN", "test-token")
    monkeypatch.delenv("SCIVERSE_MODE", raising=False)
    monkeypatch.delenv("SCIVERSE_BASE_URL", raising=False)
    response = Mock()
    response.json.return_value = {
        "hits": [
            {
                "title": "P",
                "chunk": "Short evidence",
                "source": "https://example.org/p",
            }
        ]
    }
    monkeypatch.setattr(requests, "post", Mock(return_value=response))
    parent = SimpleNamespace(
        retrievers=[get_retriever("sciverse")],
        cfg=SimpleNamespace(max_search_results_per_query=3),
        add_research_sources=Mock(),
        visited_urls=set(),
        verbose=False,
    )
    conductor = ResearchConductor(parent)
    urls, prefetched = asyncio.run(conductor._search_relevant_source_urls("q"))
    assert urls == []
    assert prefetched == [
        {
            "url": "https://example.org/p",
            "raw_content": "Title: P\n\nPassage from full text: Short evidence",
        }
    ]
    parent.add_research_sources.assert_called_once_with([{"url": "https://example.org/p"}])

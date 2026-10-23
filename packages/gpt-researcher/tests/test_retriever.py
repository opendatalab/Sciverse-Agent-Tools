"""Offline regression tests: mock HTTP only, not the requests module."""

from unittest.mock import Mock

import pytest
import requests

from gpt_researcher_sciverse import SciverseSearch


@pytest.fixture(autouse=True)
def environment(monkeypatch):
    monkeypatch.setenv("SCIVERSE_API_TOKEN", "test-token")
    monkeypatch.delenv("SCIVERSE_MODE", raising=False)
    monkeypatch.delenv("SCIVERSE_BASE_URL", raising=False)


@pytest.fixture
def http(monkeypatch):
    post = Mock()
    monkeypatch.setattr(requests, "post", post)
    return post


def response(data=None, error=None):
    result = Mock()
    result.json.return_value = data
    result.json.side_effect = error
    return result


def hit(**kwargs):
    return {"title": "Paper", "chunk": "Relevant passage", "doc_id": "sha_a", **kwargs}


def test_second_positional_argument_is_domains(http):
    http.return_value = response({"hits": []})
    assert SciverseSearch("q", ["example.org"]).search() == []


def test_invalid_json_returns_empty(http):
    http.return_value = response(error=ValueError("Invalid JSON"))
    assert SciverseSearch("q").search() == []


@pytest.mark.parametrize("records", [None, 42, "wrong", {}])
def test_invalid_metadata_records_preserve_web_fallback(http, records):
    http.side_effect = [
        response({"hits": [hit(source="https://example.org/paper")]}),
        response({"results": records}),
    ]
    assert SciverseSearch("q").search()[0]["href"] == "https://example.org/paper"


@pytest.mark.parametrize(
    "bad_hit",
    [None, "bad", {"doc_id": [], "chunk": "x"}, {"doc_id": "x", "chunk": {"bad": "text"}}],
)
def test_malformed_hit_does_not_discard_valid_hit(http, bad_hit):
    http.side_effect = [
        response({"hits": [bad_hit, hit()]}),
        response({"results": [{"doc_id": "sha_a", "doi": "10.1/a"}]}),
    ]
    results = SciverseSearch("q").search()
    assert len(results) == 1
    assert results[0]["href"] == "https://doi.org/10.1/a"


def test_maps_passage_and_abstract_without_claiming_entire_paper(http):
    http.side_effect = [
        response({"hits": [hit(abstract="Abstract text")]}),
        response(
            {
                "results": [
                    {
                        "doc_id": "sha_a",
                        "doi": "10.1/a",
                        "access_oa_url": ["https://example.org/p.pdf"],
                    }
                ]
            }
        ),
    ]
    results = SciverseSearch("q").search(5)
    assert results == [
        {
            "title": "Paper",
            "href": "https://example.org/p.pdf",
            "url": "https://example.org/p.pdf",
            "body": "Relevant passage",
            "raw_content": "Title: Paper\n\nAbstract: Abstract text\n\nPassage from full text: Relevant passage",
        }
    ]


@pytest.mark.parametrize(
    "mode,params",
    [
        ("fast", {"retrieval": "es"}),
        ("balanced", {"retrieval": "hybrid"}),
        ("quality", {"retrieval": "hybrid", "sub_queries": 3}),
    ],
)
def test_modes_and_attribution(http, mode, params):
    http.return_value = response({"hits": []})
    SciverseSearch("q", mode=mode).search(5)
    call = http.call_args
    assert call.kwargs["json"] == {"query": "q", "top_k": 5, **params}
    assert call.kwargs["headers"]["Authorization"] == "Bearer test-token"
    assert call.kwargs["headers"]["X-Sciverse-Source"] == "oss_gptresearcher"
    assert call.kwargs["timeout"] > 0


@pytest.mark.parametrize("data", [None, [], {"hits": None}, {"hits": 42}])
def test_bad_search_envelope(http, data):
    http.return_value = response(data)
    assert SciverseSearch("q").search() == []


@pytest.mark.parametrize(
    "error", [requests.Timeout(), requests.HTTPError(), requests.ConnectionError()]
)
def test_http_errors(http, error):
    http.side_effect = error
    assert SciverseSearch("q").search() == []


def test_metadata_failure_keeps_web_result(http):
    http.side_effect = [
        response({"hits": [hit(), hit(doc_id=None, source="https://example.org/a")]}),
        requests.Timeout(),
    ]
    assert [r["href"] for r in SciverseSearch("q").search()] == ["https://example.org/a"]


@pytest.mark.parametrize(
    "oa,doi",
    [(42, "10.1/a"), ([None, "https://example.org/p"], None), ("javascript:bad", "10.1/a")],
)
def test_malformed_links_do_not_escape(http, oa, doi):
    http.side_effect = [
        response({"hits": [hit()]}),
        response(
            {
                "results": [
                    {"doc_id": [], "doi": "bad"},
                    {"doc_id": "sha_a", "access_oa_url": oa, "doi": doi},
                ]
            }
        ),
    ]
    result = SciverseSearch("q").search()
    assert len(result) == 1
    assert result[0]["href"].startswith("https://")


def test_invalid_explicit_mode_is_value_error():
    with pytest.raises(ValueError):
        SciverseSearch("q", mode="invalid")


def test_environment_mode_and_explicit_override(http, monkeypatch):
    http.return_value = response({"hits": []})
    monkeypatch.setenv("SCIVERSE_MODE", "quality")
    SciverseSearch("q").search()
    assert http.call_args.kwargs["json"]["sub_queries"] == 3
    SciverseSearch("q", mode="fast").search()
    assert http.call_args.kwargs["json"]["retrieval"] == "es"
    monkeypatch.setenv("SCIVERSE_MODE", "invalid")
    SciverseSearch("q").search()
    assert http.call_args.kwargs["json"]["retrieval"] == "hybrid"


@pytest.mark.parametrize("token", [None, "", "   "])
def test_missing_or_empty_token(token, monkeypatch):
    if token is None:
        monkeypatch.delenv("SCIVERSE_API_TOKEN")
    else:
        monkeypatch.setenv("SCIVERSE_API_TOKEN", token)
    with pytest.raises(ValueError, match="SCIVERSE_API_TOKEN"):
        SciverseSearch("q")


@pytest.mark.parametrize("limit", [0, -1])
def test_nonpositive_limit_does_not_query(http, limit):
    assert SciverseSearch("q").search(limit) == []
    http.assert_not_called()


def test_caps_results_and_batches_metadata(http):
    http.side_effect = [
        response({"hits": [hit(), hit(), hit(doc_id="sha_b")]}),
        response({"results": []}),
    ]
    SciverseSearch("q").search(200)
    assert http.call_args_list[0].kwargs["json"]["top_k"] == 100
    assert http.call_args_list[1].kwargs["json"]["filters"][0]["value"] == ["sha_a", "sha_b"]

"""Sciverse passage search plugin for GPT Researcher."""

import logging
import os
from typing import ClassVar
from urllib.parse import urlsplit

import requests

logger = logging.getLogger(__name__)


class SciverseSearch:
    """Retrieve citable scientific literature passages using the Sciverse API.

    ``raw_content`` contains title, abstract and a retrieved passage, not the
    complete paper. GPT Researcher can consume this context without scraping
    publisher/DOI pages. Domain filters are accepted for interface compatibility
    but are not applied to Sciverse's literature corpus.
    """

    requires_scraping = False
    DEFAULT_BASE_URL = "https://api.sciverse.space"
    MODE_PARAMS: ClassVar[dict[str, dict[str, str | int]]] = {
        "fast": {"retrieval": "es"},
        "balanced": {"retrieval": "hybrid"},
        "quality": {"retrieval": "hybrid", "sub_queries": 3},
    }

    def __init__(self, query: str, query_domains=None, *, mode: str | None = None):
        self.query = query
        self.query_domains = query_domains or []
        if mode is not None and mode not in self.MODE_PARAMS:
            raise ValueError(f"Invalid Sciverse mode: {mode}")
        self.mode = mode if mode is not None else os.environ.get("SCIVERSE_MODE", "balanced")
        if self.mode not in self.MODE_PARAMS:
            logger.warning("Invalid SCIVERSE_MODE; falling back to balanced")
            self.mode = "balanced"
        self.api_key = os.environ.get("SCIVERSE_API_TOKEN", "").strip()
        if not self.api_key:
            raise ValueError("Set SCIVERSE_API_TOKEN to a token from https://sciverse.space/")
        self.base_url = (os.environ.get("SCIVERSE_BASE_URL") or self.DEFAULT_BASE_URL).rstrip("/")

    def _request(self, endpoint: str, payload: dict) -> dict:
        """Return an object response, or an empty object on transport/JSON errors."""
        try:
            response = requests.post(
                f"{self.base_url}/{endpoint}",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "X-Sciverse-Source": "oss_gptresearcher",
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            # Do not log response bodies or headers, which may contain credentials.
            logger.warning("Sciverse %s failed (%s)", endpoint, type(exc).__name__)
            return {}
        return data if isinstance(data, dict) else {}

    def search(self, max_results: int = 7) -> list[dict[str, str]]:
        """Return prefetched passages; errors produce no results.

        Requests are capped at 100 passages. Nonpositive limits return no results.
        Metadata lookup failure retains only hits with usable source URLs.
        """
        if max_results <= 0:
            return []
        limit = min(max_results, 100)
        data = self._request(
            "agentic-search",
            {
                "query": self.query,
                "top_k": limit,
                **self.MODE_PARAMS[self.mode],
            },
        )
        hits = data.get("hits")
        if not isinstance(hits, list):
            return []
        hits = [hit for hit in hits if isinstance(hit, dict)]
        hrefs = self._resolve_hrefs(hits)
        results = []
        for hit in hits:
            chunk = self._text(hit.get("chunk"))
            abstract = self._text(hit.get("abstract"))
            body = chunk or abstract
            href = hrefs.get(self._text(hit.get("doc_id"))) or self._web_url(hit.get("source"))
            if not body or not href:
                continue
            title = self._text(hit.get("title")) or "No Title"
            parts = [f"Title: {title}"]
            if abstract:
                parts.append(f"Abstract: {abstract}")
            if chunk:
                parts.append(f"Passage from full text: {chunk}")
            results.append(
                {
                    "title": title,
                    "href": href,
                    "url": href,
                    "body": body,
                    "raw_content": "\n\n".join(parts),
                }
            )
            if len(results) >= limit:
                break
        return results

    def _resolve_hrefs(self, hits: list[dict]) -> dict[str, str]:
        doc_ids = sorted({self._text(hit.get("doc_id")) for hit in hits} - {""})
        if not doc_ids:
            return {}
        data = self._request(
            "meta-search",
            {
                "filters": [{"field": "doc_id", "operator": "FILTER_OP_IN", "value": doc_ids}],
                "fields": ["doc_id", "access_oa_url", "doi"],
                "page_size": min(len(doc_ids), 200),
            },
        )
        records = data.get("results")
        if not isinstance(records, list):
            return {}
        hrefs = {}
        for record in records:
            if not isinstance(record, dict):
                continue
            doc_id = self._text(record.get("doc_id"))
            href = self._pick_href(record)
            if doc_id and href:
                hrefs[doc_id] = href
        return hrefs

    @classmethod
    def _pick_href(cls, record: dict) -> str:
        urls = record.get("access_oa_url")
        for candidate in urls if isinstance(urls, list) else [urls]:
            if url := cls._web_url(candidate):
                return url
        doi = cls._text(record.get("doi")).strip()
        if url := cls._web_url(doi):
            return url
        if doi.startswith("10.") and "/" in doi and not any(c.isspace() for c in doi):
            return f"https://doi.org/{doi}"
        return ""

    @staticmethod
    def _text(value) -> str:
        return value if isinstance(value, str) else ""

    @staticmethod
    def _web_url(value) -> str:
        if not isinstance(value, str):
            return ""
        try:
            parsed = urlsplit(value)
            if parsed.scheme in ("http", "https") and parsed.hostname:
                return value
        except ValueError:
            pass
        return ""

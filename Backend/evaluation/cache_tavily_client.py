"""
Benchmark-only Tavily cache client.

Wraps the real TavilyClient to capture raw search responses for
deterministic benchmark replay.  NEVER used in production — only
injected by evaluation/run.py when --cache-tavily is active.

Cache key = SHA-256( query + JSON-sorted parameters ).
Each cached file stores the COMPLETE raw Tavily response dict
so the ranking pipeline receives identical input on replay.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from web_discovery.tavily_client import TavilyClient


CACHE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "cache",
    "tavily",
)

# Default mode: 'skip' = do not cache, 'build' = call + save,
_ENV_CACHE_MODE = "TAVILY_CACHE_MODE"   # build | replay | skip
_ENV_CACHE_DIR  = "TAVILY_CACHE_DIR"


def _cache_dir() -> str:
    return os.getenv(_ENV_CACHE_DIR, CACHE_DIR)


def _cache_key(
    query: str,
    *,
    max_results: int,
    chunks_per_source: int,
    include_domains: list[str] | None,
    exclude_domains: list[str] | None,
    search_depth: str,
    include_raw_content: bool,
) -> str:
    """Deterministic SHA-256 cache key for a single search call."""
    key_parts = {
        "query": query,
        "max_results": max_results,
        "chunks_per_source": chunks_per_source,
        "include_domains": sorted(include_domains or []),
        "exclude_domains": sorted(exclude_domains or []),
        "search_depth": search_depth,
        "include_raw_content": include_raw_content,
    }
    raw = json.dumps(key_parts, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _cache_path(
    query_id: str,
    call_index: int,
    key_hash: str,
) -> str:
    return os.path.join(
        _cache_dir(),
        query_id,
        f"call_{call_index}_{key_hash}.json",
    )


class CachedTavilyClient:
    """
    Drop-in replacement for TavilyClient that intercepts search()
    calls and caches raw responses.

    Parameters
    ----------
    real_client : TavilyClient
        The actual Tavily client to delegate to in BUILD mode.
    query_id : str
        Current benchmark query ID (e.g. 'q001').
    mode : str
        'build' — call Tavily, save response, return it.
        'replay' — load from cache, never call Tavily.
    force : bool
        If True, overwrite existing cache entries in BUILD mode.
    """

    def __init__(
        self,
        real_client: TavilyClient,
        query_id: str = "",
        mode: str = "skip",
        force: bool = False,
    ):
        self._real = real_client
        self._query_id = query_id
        self._mode = mode
        self._force = force
        self._call_index = 0


    def set_query(self, query_id: str) -> None:
        """Reset call counter for a new query."""
        self._query_id = query_id
        self._call_index = 0


    def is_configured(self) -> bool:
        return self._real.is_configured()

    def require_configuration(self) -> None:
        self._real.require_configuration()

    def search(
        self,
        query: str,
        *,
        max_results: int = 20,
        chunks_per_source: int = 3,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        search_depth: str = "advanced",
        include_raw_content: bool = True,
    ) -> dict[str, Any]:

        if self._mode == "skip":
            return self._real.search(
                query,
                max_results=max_results,
                chunks_per_source=chunks_per_source,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
                search_depth=search_depth,
                include_raw_content=include_raw_content,
            )

        key_hash = _cache_key(
            query,
            max_results=max_results,
            chunks_per_source=chunks_per_source,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            search_depth=search_depth,
            include_raw_content=include_raw_content,
        )

        cache_file = _cache_path(
            self._query_id,
            self._call_index,
            key_hash,
        )

        if self._mode == "replay":
            if not os.path.exists(cache_file):
                raise FileNotFoundError(
                    f"Cache miss for {self._query_id} "
                    f"call {self._call_index}: {cache_file}"
                )
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._call_index += 1
            return data

        response = self._real.search(
            query,
            max_results=max_results,
            chunks_per_source=chunks_per_source,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            search_depth=search_depth,
            include_raw_content=include_raw_content,
        )

        if not self._force and os.path.exists(cache_file):
            self._call_index += 1
            return response

        os.makedirs(os.path.dirname(cache_file), exist_ok=True)

        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(response, f, ensure_ascii=False, indent=2)

        self._call_index += 1
        return response

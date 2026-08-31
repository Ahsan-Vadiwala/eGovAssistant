"""
Tavily web-search client.

This module is the ONLY place where the application communicates
with Tavily.

Responsibilities:
- Send web-search requests
- Keep Tavily credentials server-side
- Rotate between two API keys when one fails
- Return raw search results
- Never generate answers
- Never perform RAG
"""

from __future__ import annotations

import os
from typing import Any

import requests
from dotenv import load_dotenv


load_dotenv()


TAVILY_SEARCH_URL = (
    "https://api.tavily.com/search"
)

DEFAULT_TIMEOUT_SECONDS = 30

DEFAULT_MAX_RESULTS = 20
DEFAULT_CHUNKS_PER_SOURCE = 3

MAX_API_KEYS = 2


class TavilyConfigurationError(
    RuntimeError
):
    """Raised when Tavily is not configured."""


class TavilyAPIError(
    RuntimeError
):
    """Raised when all Tavily API attempts fail."""


class TavilyClient:

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ):

        self.timeout = timeout

        self.api_keys = self._load_api_keys()

        self.active_key_index = 0


    @staticmethod
    def _load_api_keys() -> list[str]:

        keys = []


        for name in (
            "TAVILY_API_KEY_1",
            "TAVILY_API_KEY_2",
        ):

            value = os.getenv(
                name
            )

            if value and value.strip():

                keys.append(
                    value.strip()
                )


        legacy = os.getenv(
            "TAVILY_API_KEY"
        )

        if (
            legacy
            and legacy.strip()
            and legacy.strip() not in keys
        ):

            keys.insert(
                0,
                legacy.strip(),
            )

        return keys[
            :MAX_API_KEYS
        ]


    def is_configured(self) -> bool:

        return bool(
            self.api_keys
        )


    def require_configuration(self) -> None:

        if not self.api_keys:

            raise TavilyConfigurationError(
                "No Tavily API key is configured. "
                "Set TAVILY_API_KEY_1 and optionally "
                "TAVILY_API_KEY_2 in the backend .env file."
            )


    def search(
        self,
        query: str,
        *,
        max_results: int = DEFAULT_MAX_RESULTS,
        chunks_per_source: int = DEFAULT_CHUNKS_PER_SOURCE,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        search_depth: str = "advanced",
        include_raw_content: bool = True,
    ) -> dict[str, Any]:

        query = query.strip()

        if not query:

            raise ValueError(
                "Tavily search query cannot be empty."
            )

        self.require_configuration()

        max_results = max(
            1,
            min(
                int(max_results),
                20,
            ),
        )

        chunks_per_source = max(
            1,
            min(
                int(chunks_per_source),
                3,
            ),
        )

        payload = {

            "query": query,

            "search_depth": search_depth,

            "chunks_per_source": (
                chunks_per_source
            ),

            "max_results": (
                max_results
            ),

            "topic": "general",

            "include_answer": False,

            "include_raw_content": (
                "markdown"
                if include_raw_content
                else False
            ),

            "include_images": False,

            "include_image_descriptions": False,

            "include_favicon": True,

            "include_domains": (
                include_domains or []
            ),

            "exclude_domains": (
                exclude_domains or []
            ),

            "auto_parameters": False,

            "exact_match": False,

            "include_usage": False,

            "safe_search": False,
        }

        errors = []


        key_count = len(
            self.api_keys
        )

        for attempt in range(
            key_count
        ):

            key_index = (
                self.active_key_index
                + attempt
            ) % key_count

            api_key = self.api_keys[
                key_index
            ]

            headers = {
                "Authorization": (
                    f"Bearer {api_key}"
                ),
                "Content-Type": (
                    "application/json"
                ),
            }

            try:

                response = requests.post(
                    TAVILY_SEARCH_URL,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                )

            except requests.RequestException as error:

                errors.append(
                    f"key_{key_index + 1}: "
                    f"network error: {error}"
                )

                continue

            if not response.ok:

                body = response.text[
                    :1000
                ]

                errors.append(
                    f"key_{key_index + 1}: "
                    f"HTTP {response.status_code}: "
                    f"{body}"
                )

                continue

            try:

                data = response.json()

            except ValueError as error:

                errors.append(
                    f"key_{key_index + 1}: "
                    "non-JSON response"
                )

                continue

            if not isinstance(
                data,
                dict,
            ):

                errors.append(
                    f"key_{key_index + 1}: "
                    "unexpected response format"
                )

                continue


            self.active_key_index = (
                key_index
            )

            return data


        raise TavilyAPIError(
            "All configured Tavily API keys failed. "
            + " | ".join(errors)
        )

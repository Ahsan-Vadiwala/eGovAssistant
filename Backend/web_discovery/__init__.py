"""
eGovAssist Web Discovery Layer.

Responsibilities:
- Query classification
- Jurisdiction resolution
- Tavily web discovery
- Official-source prioritization
- BM25 keyword ranking
- Evidence-threshold routing

This layer does NOT:
- generate answers
- perform citation validation
- replace RAG
"""

from .service import (
    WebDiscoveryService,
)
from .tavily_client import (
    TavilyClient,
)
from .firecrawl_client import (
    FirecrawlClient,
)
from .providers import (
    resolve_providers,
)
from .query_classifier import (
    QueryClassifier,
    QueryClassification,
)


__all__ = [
    "WebDiscoveryService",
    "TavilyClient",
    "FirecrawlClient",
    "resolve_providers",
    "QueryClassifier",
    "QueryClassification",
]

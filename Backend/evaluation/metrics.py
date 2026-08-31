"""
Metric calculations for the eGovAssist web-evidence benchmark.

Every function here is a pure function operating on plain
Python data structures (lists / dicts of primitives) so it can
be unit-tested with synthetic data, independent of the real
WebDiscoveryService, network access, or API keys.

============================================================
DEFINITIONS (documented per STEP 6 of the task spec)
============================================================

WebDiscoveryService.discover() returns a ranked list of TEXT
CHUNKS, not a ranked list of unique sources -- a single
source_url can legitimately appear multiple times (once per
chunk of that page). Evaluating recall/MRR/domain-accuracy at
the raw chunk level would double count the same source and
would misrepresent "how many distinct relevant sources did we
surface" -- which is what actually matters for a citizen asking
a question.

Therefore, before computing Recall@K / MRR / Domain Accuracy,
we DEDUPLICATE the ranked chunk list down to a ranked list of
DISTINCT SOURCE URLS, keeping each URL's *first* (best) rank.
This is the "URL-deduplicated ranking" and is the basis for all
rank-sensitive metrics below. This choice is documented again
in evaluation/README.md.

Domain Accuracy is reported at TWO granularities so both
questions ("is the top result usually right?" and "how much of
everything we show is authoritative?") can be answered:

  - domain_accuracy_top1   (per-query): top-ranked URL's domain
    is in the query's authoritative_domains list.
  - domain_accuracy_result (per-result): across every retrieved,
    URL-deduplicated result in top 10, what fraction have a
    domain in the query's authoritative_domains list.

Official Source Rate reuses the existing `official` boolean
already computed by WebDiscoveryService (OFFICIAL_DOMAINS list)
-- no new classifier is introduced, per STEP 7.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .normalize import domain_matches_any, normalize_domain, normalize_url, url_matches_any


def dedupe_by_url(results: list[dict]) -> list[dict]:
    """
    Collapse a ranked chunk-level result list into a ranked,
    URL-deduplicated list, keeping the first (highest-ranked)
    occurrence of each normalized URL.

    Each input dict is expected to have a 'source_url' (or
    'url') key. Items without a resolvable URL are dropped.
    """

    seen: set[str] = set()
    deduped: list[dict] = []

    for item in results:

        raw_url = item.get("source_url") or item.get("url") or ""
        norm = normalize_url(raw_url)

        if not norm:
            continue

        if norm in seen:
            continue

        seen.add(norm)
        deduped.append(item)

    return deduped


def is_relevant(result: dict, relevant_urls: list[str], relevant_domains: list[str]) -> bool:
    """
    A retrieved result is relevant if its URL exactly matches
    (after normalization) a ground-truth relevant URL, OR its
    domain matches a ground-truth relevant domain.
    """

    raw_url = result.get("source_url") or result.get("url") or ""

    if relevant_urls and url_matches_any(raw_url, relevant_urls):
        return True

    domain = normalize_domain(raw_url)

    if relevant_domains and domain_matches_any(domain, relevant_domains):
        return True

    return False


@dataclass
class QueryRetrievalOutcome:
    first_relevant_rank: int | None
    reciprocal_rank: float
    recall_at_1: int
    recall_at_5: int
    recall_at_10: int
    ranked_urls: list[dict] = field(default_factory=list)


def evaluate_query_retrieval(
    deduped_results: list[dict],
    relevant_urls: list[str],
    relevant_domains: list[str],
) -> QueryRetrievalOutcome:
    """
    deduped_results must already be URL-deduplicated and in
    rank order (rank 1 = deduped_results[0]).
    """

    first_relevant_rank = None

    for rank, result in enumerate(deduped_results, start=1):

        if is_relevant(result, relevant_urls, relevant_domains):
            first_relevant_rank = rank
            break

    if first_relevant_rank is None:
        reciprocal_rank = 0.0
    else:
        reciprocal_rank = 1.0 / first_relevant_rank

    def recall_at(k: int) -> int:
        return int(first_relevant_rank is not None and first_relevant_rank <= k)

    return QueryRetrievalOutcome(
        first_relevant_rank=first_relevant_rank,
        reciprocal_rank=reciprocal_rank,
        recall_at_1=recall_at(1),
        recall_at_5=recall_at(5),
        recall_at_10=recall_at(10),
        ranked_urls=deduped_results,
    )


def aggregate_recall_mrr(outcomes: list[QueryRetrievalOutcome]) -> dict:

    n = len(outcomes)

    if n == 0:
        return {
            "recall_at_1": 0.0,
            "recall_at_5": 0.0,
            "recall_at_10": 0.0,
            "mrr": 0.0,
            "n_queries": 0,
        }

    return {
        "recall_at_1": sum(o.recall_at_1 for o in outcomes) / n,
        "recall_at_5": sum(o.recall_at_5 for o in outcomes) / n,
        "recall_at_10": sum(o.recall_at_10 for o in outcomes) / n,
        "mrr": sum(o.reciprocal_rank for o in outcomes) / n,
        "n_queries": n,
    }


def domain_accuracy_top1(deduped_results: list[dict], authoritative_domains: list[str]) -> int | None:
    """
    1 if the top-ranked (rank-1) URL's domain is an
    authoritative domain for this query, 0 if not, None if
    there were no results at all (query produced zero evidence
    -- excluded from the denominator rather than counted as a
    failure, and reported separately as a coverage gap).
    """

    if not deduped_results:
        return None

    top = deduped_results[0]
    raw_url = top.get("source_url") or top.get("url") or ""
    domain = normalize_domain(raw_url)

    return int(domain_matches_any(domain, authoritative_domains))


def domain_accuracy_result_level(
    deduped_results: list[dict],
    authoritative_domains: list[str],
    top_n: int = 10,
) -> tuple[int, int]:
    """
    Returns (n_authoritative, n_total) among the top `top_n`
    URL-deduplicated results for one query. Caller sums these
    across all queries to get the global per-result rate.
    """

    window = deduped_results[:top_n]

    n_total = len(window)
    n_authoritative = 0

    for result in window:
        raw_url = result.get("source_url") or result.get("url") or ""
        domain = normalize_domain(raw_url)
        if domain_matches_any(domain, authoritative_domains):
            n_authoritative += 1

    return n_authoritative, n_total


def official_source_rate(
    deduped_results: list[dict],
    top_n: int = 10,
) -> tuple[int, int]:
    """
    Returns (n_official, n_total) among the top `top_n`
    URL-deduplicated results for one query, using the existing
    `official` flag already produced by WebDiscoveryService.
    """

    window = deduped_results[:top_n]

    n_total = len(window)
    n_official = sum(1 for r in window if bool(r.get("official", False)))

    return n_official, n_total

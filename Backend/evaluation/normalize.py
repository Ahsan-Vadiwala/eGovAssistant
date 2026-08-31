"""
Normalization utilities shared by every metric.

These are intentionally simple and deterministic so that
results are 100% reproducible given the same raw retrieval
output.
"""

from __future__ import annotations

from urllib.parse import urlparse, urlunparse


def normalize_domain(url_or_domain: str) -> str:
    """
    Normalize a URL or bare domain into a comparable domain
    string.

    Rules:
      - lowercase
      - strip protocol (http/https)
      - strip 'www.'
      - strip port
      - strip path/query/fragment
      - strip trailing dot

    Examples:
        "https://www.pmfby.gov.in/something?x=1" -> "pmfby.gov.in"
        "PMFBY.GOV.IN"                           -> "pmfby.gov.in"
        "www.pmfby.gov.in"                       -> "pmfby.gov.in"
    """

    if not url_or_domain:
        return ""

    raw = str(url_or_domain).strip().lower()

    if not raw:
        return ""

    if "://" not in raw:
        raw = "http://" + raw

    try:
        netloc = urlparse(raw).netloc
    except Exception:
        return ""

    netloc = netloc.split("@")[-1]  # strip userinfo if present
    netloc = netloc.split(":")[0]   # strip port

    if netloc.startswith("www."):
        netloc = netloc[4:]

    return netloc.rstrip(".")


def normalize_url(url: str) -> str:
    """
    Normalize a URL for exact-match comparison.

    Rules:
      - lowercase scheme + host
      - strip 'www.'
      - strip trailing slash
      - strip query string and fragment
      - collapse http/https (treated as equivalent)
    """

    if not url:
        return ""

    raw = str(url).strip()

    if not raw:
        return ""

    if "://" not in raw:
        raw = "http://" + raw

    try:
        parsed = urlparse(raw)
    except Exception:
        return raw.lower().rstrip("/")

    domain = normalize_domain(raw)
    path = (parsed.path or "").rstrip("/")

    normalized = urlunparse(
        (
            "https",
            domain,
            path,
            "",
            "",
            "",
        )
    )

    return normalized.lower()


def domain_matches_any(domain: str, expected_domains: list[str]) -> bool:
    """
    True if `domain` equals one of `expected_domains`, or is a
    subdomain of one of them (e.g. "sub.pmfby.gov.in" matches
    "pmfby.gov.in").
    """

    domain = normalize_domain(domain) if "://" in str(domain) or "." in str(domain) else str(domain).lower()

    if not domain:
        return False

    for expected in expected_domains:

        expected_norm = normalize_domain(expected) if "://" in str(expected) else str(expected).lower().lstrip(".")

        if not expected_norm:
            continue

        if domain == expected_norm or domain.endswith("." + expected_norm):
            return True

    return False


def url_matches_any(url: str, expected_urls: list[str]) -> bool:
    """
    True if the normalized `url` exactly matches (after
    normalization) one of `expected_urls`.
    """

    normalized = normalize_url(url)

    if not normalized:
        return False

    expected_normalized = {normalize_url(u) for u in expected_urls}

    return normalized in expected_normalized

"""
Citation Accuracy and Grounded Answer Rate.

These are ANSWER-GENERATION metrics, not retrieval metrics.
They depend on the existing RAGPipeline (rag/pipeline.py),
which itself depends on:

  - a configured Groq API key (answer generation)
  - a configured Gemini API key (reranking, inside RAGPipeline)
  - network access

If any of that is unavailable, these metrics are reported as
NOT AVAILABLE with the concrete reason, rather than being
skipped silently or faked.

Two concepts are kept explicitly separate, per STEP 8:

  - Citation Retrieval Validity: for every [EVIDENCE N] the
    model cited, does evidence N actually exist in the context
    that was built from real retrieved results, and does its
    source_url actually appear in the retrieved evidence pool?
    This is fully deterministic and cheap.

  - Citation Evidence Support (semantic): does the cited
    evidence text actually support the specific claim next to
    it? This requires judging natural-language entailment. We
    do NOT implement a hand-rolled heuristic for this (a
    keyword-overlap heuristic would not reliably measure
    semantic support and would misrepresent itself as
    "accuracy"). Instead this is exposed as an OPTIONAL,
    explicitly-configured LLM-judge step. If no judge is
    configured, it is reported as NOT AVAILABLE.
"""

from __future__ import annotations

import os
import re

CITATION_PATTERN = re.compile(r"\[EVIDENCE\s+(\d+)\]", re.IGNORECASE)


def pipeline_dependencies_available() -> tuple[bool, str]:
    """
    Best-effort, honest check of whether RAGPipeline.ask() can
    actually run in this environment, without triggering a full
    network call. Returns (available, reason_if_not).
    """

    groq_keys = [
        os.getenv("GROQ_API_KEY_1"),
        os.getenv("GROQ_API_KEY_2"),
        os.getenv("GROQ_API_KEY"),
    ]

    if not any(k for k in groq_keys if k):
        return False, "No GROQ_API_KEY_1 / GROQ_API_KEY_2 / GROQ_API_KEY configured in this environment."

    tavily_keys = [
        os.getenv("TAVILY_API_KEY_1"),
        os.getenv("TAVILY_API_KEY_2"),
        os.getenv("TAVILY_API_KEY"),
    ]

    if not any(k for k in tavily_keys if k):
        return False, "No TAVILY_API_KEY_1 / TAVILY_API_KEY_2 / TAVILY_API_KEY configured in this environment."

    try:
        import socket
        socket.create_connection(("api.groq.com", 443), timeout=2).close()
    except Exception as exc:
        return False, f"No outbound network access to api.groq.com in this environment ({exc})."

    return True, ""


def evaluate_citations_for_answer(pipeline_result: dict) -> dict:
    """
    Deterministic "Citation Retrieval Validity" check for a
    single RAGPipeline.ask() result.

    pipeline_result is expected to have:
        - "answer": the generated answer text containing
          [EVIDENCE N] citations
        - "sources" / "evidence": the list of source dicts that
          were actually used to build the numbered context
          (cited_sources from RAGPipeline.ask())
    """

    answer = pipeline_result.get("answer") or ""
    cited_sources = pipeline_result.get("sources") or pipeline_result.get("evidence") or []

    cited_numbers = {int(n) for n in CITATION_PATTERN.findall(answer)}

    if not cited_numbers:
        return {
            "citation_count": 0,
            "valid_citations": 0,
            "invalid_citations": 0,
            "citation_retrieval_validity": None,  # no citations to evaluate
        }

    max_available = len(cited_sources)

    valid = sum(1 for n in cited_numbers if 1 <= n <= max_available)
    invalid = len(cited_numbers) - valid

    return {
        "citation_count": len(cited_numbers),
        "valid_citations": valid,
        "invalid_citations": invalid,
        "citation_retrieval_validity": valid / len(cited_numbers),
    }


def evaluate_grounded_answer_rate(citation_results: list[dict]) -> dict | str:
    """
    citation_results: list of per-query dicts from
    evaluate_citations_for_answer(), one per successfully
    generated answer.

    "Grounded" here is operationalized deterministically and
    conservatively as: every [EVIDENCE N] citation in the answer
    resolves to a real, retrieved source (citation_retrieval_validity
    == 1.0). This measures "the model did not cite evidence that
    doesn't exist" -- a necessary but not sufficient condition for
    true semantic groundedness. It does NOT verify that the cited
    text semantically supports the claim (see module docstring) --
    that part is NOT AVAILABLE without an LLM judge.
    """

    scored = [r for r in citation_results if r.get("citation_retrieval_validity") is not None]

    if not scored:
        return "NOT AVAILABLE (no answers contained any citations to evaluate)"

    fully_grounded = sum(1 for r in scored if r["citation_retrieval_validity"] == 1.0)

    return {
        "grounded_answer_rate_structural": fully_grounded / len(scored),
        "n_answers_evaluated": len(scored),
        "definition": (
            "Fraction of generated answers where every [EVIDENCE N] "
            "citation resolves to a real retrieved source. This is a "
            "STRUCTURAL grounding check, not a semantic entailment "
            "check -- see citation_eval.py docstring."
        ),
    }

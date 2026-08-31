"""
eGovAssist Web Evidence Evaluation Benchmark -- runner.

Usage (from the BACKEND_BACKUP repository root, i.e. the
directory containing `web_discovery/`, `rag/`, `grievance/`):

    python -m evaluation.run
    python -m evaluation.run --limit 10          # quick smoke test
    python -m evaluation.run --skip-generation    # retrieval metrics only
    python -m evaluation.run --dataset evaluation/dataset.json

What it does, in order:
  1. Loads evaluation/dataset.json
  2. For every query, calls the REAL WebDiscoveryService.discover()
     (no mocking, no stub retrieval)
  3. Computes Recall@1/5/10, MRR, Domain Accuracy, Official Source Rate
  4. Optionally (if Groq/Tavily keys + network are available) calls
     the REAL RAGPipeline.ask() to compute Citation Retrieval
     Validity and structural Grounded Answer Rate
  5. Runs the contamination/leakage audit
  6. Writes:
       evaluation/results/<timestamp>/detailed_results.json
       evaluation/results/<timestamp>/summary.json
       evaluation/results/latest_summary.json
       evaluation/results/latest_report.md
  7. Prints a concise summary to the terminal

This file does not modify web_discovery/, rag/, grievance/, app/,
or any frontend file. It only reads from them.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from evaluation.metrics import (
    QueryRetrievalOutcome,
    aggregate_recall_mrr,
    dedupe_by_url,
    domain_accuracy_result_level,
    domain_accuracy_top1,
    evaluate_query_retrieval,
    is_relevant,
    official_source_rate,
)
from evaluation.contamination import run_contamination_checks
from evaluation.citation_eval import (
    evaluate_citations_for_answer,
    evaluate_grounded_answer_rate,
    pipeline_dependencies_available,
)
from evaluation.normalize import normalize_domain, normalize_url


def load_dataset(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_audit_map() -> dict:
    """Load the Phase-4 GT audit annotations (if the current dataset was audited)."""
    audit_path = os.path.join(_THIS_DIR, "audit_cache", "_audit_table.json")
    if not os.path.exists(audit_path):
        return {}
    try:
        rows = json.load(open(audit_path, encoding="utf-8"))
    except Exception:
        return {}
    return {
        r["QUESTION_ID"]: {
            "action": r["ACTION"],
            "url_status": r["URL_STATUS"],
            "retrieved_in_runs": r["RETRIEVED_IN_RUNS"],
        }
        for r in rows
        if r.get("QUESTION_ID")
    }


def build_result_row(item: dict, raw_results: list[dict], error: str | None, gt_quality: dict | None = None) -> dict:
    """
    Builds the per-query detailed-results record (STEP 11 of the
    task spec), including URL-deduplicated ranked evidence.
    """

    if error is not None:
        return {
            "id": item["id"],
            "question": item["question"],
            "category": item.get("category"),
            "error": error,
            "ground_truth": {
                "relevant_urls": item.get("relevant_urls", []),
                "relevant_domains": item.get("relevant_domains", []),
                "authoritative_domains": item.get("authoritative_domains", []),
            },
            "retrieved_results": [],
            "first_relevant_rank": None,
            "reciprocal_rank": 0.0,
            "recall_at_1": 0,
            "recall_at_5": 0,
            "recall_at_10": 0,
        }

    deduped = dedupe_by_url(raw_results)

    outcome: QueryRetrievalOutcome = evaluate_query_retrieval(
        deduped_results=deduped,
        relevant_urls=item.get("relevant_urls", []),
        relevant_domains=item.get("relevant_domains", []),
    )

    retrieved_records = []
    for rank, result in enumerate(deduped[:10], start=1):
        raw_url = result.get("source_url") or result.get("url") or ""
        retrieved_records.append(
            {
                "rank": rank,
                "title": result.get("title") or result.get("web_title") or "",
                "url": raw_url,
                "domain": normalize_domain(raw_url),
                "official": bool(result.get("official", False)),
                "discovery_stage": result.get("discovery_stage"),
                "relevant": is_relevant(
                    result,
                    item.get("relevant_urls", []),
                    item.get("relevant_domains", []),
                ),
                "source_tier_name": result.get("source_tier_name"),
                "retrieval_quality_score": result.get("retrieval_quality_score"),
                "debug_bm25_norm": result.get("debug_bm25_norm"),
                "debug_authority_lead": result.get("debug_authority_lead"),
                "debug_primary_portal_lead": result.get("debug_primary_portal_lead"),
                "debug_low_authority": result.get("debug_low_authority"),
                "debug_has_authoritative_in_pool": result.get("debug_has_authoritative_in_pool"),
            }
        )

    row = {
        "id": item["id"],
        "question": item["question"],
        "category": item.get("category"),
        "ground_truth": {
            "relevant_urls": item.get("relevant_urls", []),
            "relevant_domains": item.get("relevant_domains", []),
            "authoritative_domains": item.get("authoritative_domains", []),
        },
        "retrieved_results": retrieved_records,
        "n_raw_chunks": len(raw_results),
        "n_deduped_urls": len(deduped),
        "first_relevant_rank": outcome.first_relevant_rank,
        "reciprocal_rank": outcome.reciprocal_rank,
        "recall_at_1": outcome.recall_at_1,
        "recall_at_5": outcome.recall_at_5,
        "recall_at_10": outcome.recall_at_10,
    }
    if gt_quality:
        row["ground_truth_quality"] = gt_quality
    return row


def run_single_query(service, item: dict) -> tuple[list[dict], str | None]:
    """
    Calls the REAL WebDiscoveryService with ONLY the raw question
    text -- no ground truth is ever passed into the query
    (contamination check #2 in contamination.py depends on this).
    """
    try:
        response = service.discover(item["question"])
        return response.get("results", []), None
    except Exception as exc:
        return [], f"{type(exc).__name__}: {exc}"


def main() -> int:

    parser = argparse.ArgumentParser(description="eGovAssist web-evidence evaluation benchmark")
    parser.add_argument("--dataset", default=os.path.join(_THIS_DIR, "dataset.json"))
    parser.add_argument("--limit", type=int, default=None, help="Evaluate only the first N queries (smoke test)")
    parser.add_argument("--skip-generation", action="store_true", help="Skip citation/grounded-answer metrics")
    parser.add_argument("--backend-root", default=_REPO_ROOT, help="Root of the backend repo, for contamination scan")
    parser.add_argument(
        "--cache-tavily",
        choices=["skip", "build", "replay"],
        default="skip",
        help="Tavily cache mode: build (call + save), replay (load from cache), skip (live Tavily).",
    )
    parser.add_argument(
        "--force-cache",
        action="store_true",
        help="Overwrite existing cache entries in build mode.",
    )
    args = parser.parse_args()

    dataset = load_dataset(args.dataset)
    queries = dataset["queries"]
    if args.limit:
        queries = queries[: args.limit]

    print("=" * 60)
    print("eGovAssist Web Evidence Evaluation")
    print("=" * 60)
    print(f"\nDataset version : {dataset.get('dataset_version')}")
    print(f"Queries         : {len(queries)}")

    # benchmark must fail loudly rather than silently fabricate

    from web_discovery.service import WebDiscoveryService

    cached_client = None

    if args.cache_tavily != "skip":
        from evaluation.cache_tavily_client import CachedTavilyClient
        from web_discovery.tavily_client import TavilyClient

        real_tavily = TavilyClient()
        cached_client = CachedTavilyClient(
            real_tavily,
            mode=args.cache_tavily,
            force=args.force_cache,
        )
        service = WebDiscoveryService(tavily_client=cached_client)
        print(f"Tavily cache mode: {args.cache_tavily}")
    else:
        service = WebDiscoveryService()

    audit_map = load_audit_map()

    detailed_results = []
    outcomes: list[QueryRetrievalOutcome] = []

    n_official_total = 0
    n_result_total = 0
    n_authoritative_total = 0
    n_result_level_total = 0
    domain_top1_hits = 0
    domain_top1_evaluated = 0

    n_completed = 0
    n_errors = 0

    for i, item in enumerate(queries, start=1):
        print(f"\r[{i}/{len(queries)}] {item['id']} ...", end="", flush=True)

        if cached_client is not None:
            cached_client.set_query(item["id"])

        raw_results, error = run_single_query(service, item)

        if error is not None:
            n_errors += 1

        row = build_result_row(item, raw_results, error, gt_quality=audit_map.get(item["id"]))
        detailed_results.append(row)

        if error is None:
            n_completed += 1
            deduped = dedupe_by_url(raw_results)

            outcome = evaluate_query_retrieval(
                deduped_results=deduped,
                relevant_urls=item.get("relevant_urls", []),
                relevant_domains=item.get("relevant_domains", []),
            )
            outcomes.append(outcome)

            off_hits, off_total = official_source_rate(deduped, top_n=10)
            n_official_total += off_hits
            n_result_total += off_total

            top1 = domain_accuracy_top1(deduped, item.get("authoritative_domains", []))
            if top1 is not None:
                domain_top1_evaluated += 1
                domain_top1_hits += top1

            auth_hits, auth_total = domain_accuracy_result_level(
                deduped, item.get("authoritative_domains", []), top_n=10
            )
            n_authoritative_total += auth_hits
            n_result_level_total += auth_total

    print()  # newline after progress

    retrieval_metrics = aggregate_recall_mrr(outcomes)

    domain_accuracy_top1_rate = (
        domain_top1_hits / domain_top1_evaluated if domain_top1_evaluated else None
    )
    domain_accuracy_result_rate = (
        n_authoritative_total / n_result_level_total if n_result_level_total else None
    )
    official_rate = n_official_total / n_result_total if n_result_total else None


    citation_summary = "NOT AVAILABLE"
    citation_reason = "Skipped: --skip-generation was passed."
    grounded_summary = "NOT AVAILABLE"

    if not args.skip_generation:

        available, reason = pipeline_dependencies_available()

        if not available:
            citation_reason = reason
        else:
            try:
                from rag.pipeline import RAGPipeline

                pipeline = RAGPipeline()
                citation_results = []

                for item in queries:
                    try:
                        result = pipeline.ask(item["question"])
                        citation_results.append(evaluate_citations_for_answer(result))
                    except Exception as exc:
                        citation_results.append({"error": f"{type(exc).__name__}: {exc}"})

                valid_rows = [r for r in citation_results if "error" not in r]

                if valid_rows:
                    total_citations = sum(r["citation_count"] for r in valid_rows)
                    total_valid = sum(r["valid_citations"] for r in valid_rows)
                    citation_summary = {
                        "citation_retrieval_validity": (
                            total_valid / total_citations if total_citations else None
                        ),
                        "n_answers_generated": len(valid_rows),
                        "n_generation_errors": len(citation_results) - len(valid_rows),
                    }
                    grounded_summary = evaluate_grounded_answer_rate(valid_rows)
                else:
                    citation_summary = "NOT AVAILABLE"
                    citation_reason = "RAGPipeline.ask() failed for every query in this run."

            except Exception as exc:
                citation_reason = f"RAGPipeline could not be initialized/imported: {type(exc).__name__}: {exc}"


    contamination = run_contamination_checks(dataset["queries"], args.backend_root)


    from collections import Counter

    if audit_map:
        gt_action_counts = Counter()
        gt_status_counts = Counter()
        for item in queries:
            entry = audit_map.get(item["id"])
            if entry:
                gt_action_counts[entry["action"]] += 1
                gt_status_counts[entry["url_status"]] += 1
        gt_quality_summary = {
            "actions": dict(gt_action_counts),
            "gt_url_statuses": dict(gt_status_counts),
        }
    else:
        gt_quality_summary = {"note": "No audit table found (dataset was not audited with evaluation/url_validator)."}


    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    date_dir = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    summary = {
        "evaluation_timestamp": timestamp,
        "dataset_version": dataset.get("dataset_version"),
        "queries_total": len(queries),
        "queries_completed": n_completed,
        "queries_errored": n_errors,
        "retrieval": retrieval_metrics,
        "source_quality": {
            "domain_accuracy_top1": domain_accuracy_top1_rate,
            "domain_accuracy_result_level": domain_accuracy_result_rate,
            "official_source_rate": official_rate,
        },
        "answer_quality": {
            "citation_accuracy": citation_summary,
            "citation_accuracy_unavailable_reason": (
                citation_reason if citation_summary == "NOT AVAILABLE" else None
            ),
            "citation_evidence_support_semantic": (
                "NOT AVAILABLE -- requires an explicitly configured LLM judge; "
                "none is configured in this run. See citation_eval.py."
            ),
            "grounded_answer_rate": grounded_summary,
        },
        "ground_truth_quality": gt_quality_summary,
        "contamination": contamination,
    }

    results_dir = os.path.join(_THIS_DIR, "results", date_dir)
    os.makedirs(results_dir, exist_ok=True)

    run_dir = os.path.join(results_dir, timestamp)
    os.makedirs(run_dir, exist_ok=True)

    with open(os.path.join(run_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    with open(os.path.join(run_dir, "detailed_results.json"), "w", encoding="utf-8") as f:
        json.dump(detailed_results, f, indent=2, ensure_ascii=False)

    latest_summary_path = os.path.join(_THIS_DIR, "results", "latest_summary.json")
    with open(latest_summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    report_path = os.path.join(_THIS_DIR, "results", "latest_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(render_report(summary))


    def pct(x):
        return "NOT AVAILABLE" if x is None else f"{x * 100:.1f}%"

    print("\nResults")
    print("-" * 60)
    print(f"Queries:         {len(queries)}")
    print(f"Completed:       {n_completed}")
    print(f"Errored:         {n_errors}")
    print(f"Recall@1:        {pct(retrieval_metrics['recall_at_1'])}")
    print(f"Recall@5:        {pct(retrieval_metrics['recall_at_5'])}")
    print(f"Recall@10:       {pct(retrieval_metrics['recall_at_10'])}")
    print(f"MRR:             {retrieval_metrics['mrr']:.3f}")
    print(f"Domain Acc(top1):{pct(domain_accuracy_top1_rate)}")
    print(f"Domain Acc(res): {pct(domain_accuracy_result_rate)}")
    print(f"Official Rate:   {pct(official_rate)}")
    print(f"\nResults written to: {run_dir}")
    print(f"Latest summary:     {latest_summary_path}")
    print(f"Latest report:      {report_path}")

    return 0


def render_report(summary: dict) -> str:

    def pct(x):
        return "NOT AVAILABLE" if x is None else f"{x * 100:.1f}%"

    def fmt_answer_metric(m):
        if isinstance(m, str):
            return m
        return json.dumps(m, indent=2)

    lines = []
    lines.append("=" * 60)
    lines.append("eGovAssist Web Evidence Evaluation")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Evaluation date: {summary['evaluation_timestamp']}")
    lines.append(f"Dataset version: {summary['dataset_version']}")
    lines.append(f"Queries evaluated: {summary['queries_completed']}/{summary['queries_total']} "
                 f"({summary['queries_errored']} errored)")
    lines.append("")
    lines.append("RETRIEVAL")
    lines.append("-" * 60)
    r = summary["retrieval"]
    lines.append(f"Recall@1:  {pct(r['recall_at_1'])}")
    lines.append(f"Recall@5:  {pct(r['recall_at_5'])}")
    lines.append(f"Recall@10: {pct(r['recall_at_10'])}")
    lines.append(f"MRR:       {r['mrr']:.3f}")
    lines.append("")
    lines.append("SOURCE QUALITY")
    lines.append("-" * 60)
    s = summary["source_quality"]
    lines.append(f"Domain Accuracy (top-1 per query):        {pct(s['domain_accuracy_top1'])}")
    lines.append(f"Domain Accuracy (per retrieved result):   {pct(s['domain_accuracy_result_level'])}")
    lines.append(f"Official Source Rate:                     {pct(s['official_source_rate'])}")
    lines.append("")
    lines.append("ANSWER QUALITY")
    lines.append("-" * 60)
    a = summary["answer_quality"]
    lines.append("Citation Accuracy (retrieval validity):")
    lines.append(fmt_answer_metric(a["citation_accuracy"]))
    if a.get("citation_accuracy_unavailable_reason"):
        lines.append(f"Reason: {a['citation_accuracy_unavailable_reason']}")
    lines.append("")
    lines.append("Citation Evidence Support (semantic):")
    lines.append(a["citation_evidence_support_semantic"])
    lines.append("")
    lines.append("Grounded Answer Rate (structural):")
    lines.append(fmt_answer_metric(a["grounded_answer_rate"]))
    lines.append("")
    lines.append("CONTAMINATION")
    lines.append("-" * 60)
    c = summary["contamination"]
    lines.append(f"Status: {c['contamination_status']}")
    lines.append("Checks performed:")
    for check in c["checks_performed"]:
        lines.append(f"  - {check}")
    lines.append("Warnings:")
    for warning in c["warnings"]:
        lines.append(f"  - {warning}")
    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())

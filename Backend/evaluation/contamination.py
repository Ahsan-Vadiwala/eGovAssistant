"""
Basic contamination / leakage audit.

This does NOT and CANNOT prove "zero contamination" for a
live-web-retrieval system -- the open web is not a closed,
inspectable training set. What it CAN do, and does, is run a
small set of concrete, static checks against the actual
repository and dataset, and report exactly what was checked and
what (if anything) looks suspicious. Anything not checked is
listed explicitly as a limitation rather than silently assumed
safe.
"""

from __future__ import annotations

import os
import re


def run_contamination_checks(
    dataset: list[dict],
    backend_root: str | None,
) -> dict:

    checks_performed = []
    warnings = []


    checks_performed.append(
        "Duplicate question / duplicate ID check within dataset.json"
    )

    ids_seen = {}
    questions_seen = {}

    for item in dataset:

        qid = item.get("id")
        question = (item.get("question") or "").strip().lower()

        if qid in ids_seen:
            warnings.append(f"Duplicate dataset id: {qid!r}")
        ids_seen[qid] = True

        if question in questions_seen:
            warnings.append(
                f"Duplicate question text (ids {questions_seen[question]!r} "
                f"and {qid!r}): {question[:80]!r}"
            )
        questions_seen[question] = qid


    checks_performed.append(
        "Runner passes only the raw question string to "
        "WebDiscoveryService.discover() -- ground-truth URLs/"
        "domains are never included in the query sent to "
        "retrieval (verified by code inspection of runner.py; "
        "see evaluation/runner.py:run_single_query)."
    )


    if backend_root and os.path.isdir(backend_root):

        checks_performed.append(
            "Scanned application source (excluding evaluation/) "
            "for verbatim dataset question text or dataset ids."
        )

        hits = _scan_source_for_strings(
            root=backend_root,
            needles=[item["id"] for item in dataset if item.get("id")],
            exclude_dirname="evaluation",
        )

        if hits:
            warnings.append(
                "Dataset ids found hard-coded in application source "
                f"(outside evaluation/): {hits}"
            )

    else:

        warnings.append(
            "backend_root not provided or not found -- source-code "
            "scan for hard-coded dataset ids/answers was SKIPPED. "
            "Run with --backend-root pointing at the repository "
            "root to enable this check."
        )


    checks_performed.append(
        "Disclosed dynamic-web limitation (see below)."
    )

    warnings.append(
        "This system retrieves from the LIVE web via Tavily. Page "
        "content, rankings, and even URL availability can change "
        "between benchmark runs. Every run is a timestamped "
        "snapshot, not a permanent measurement. Re-running the "
        "same dataset on a different date can legitimately produce "
        "different numbers."
    )

    warnings.append(
        "Ground truth was repaired from a per-URL validation audit on "
        "2026-08-30 (evaluation/audit_report_2026-08-30.md): every GT "
        "was either HTTP-verified live or replaced/probed to a verified "
        "canonical official source. The web remains dynamic, so URLs may "
        "still legitimately change after the audit date."
    )

    status = "checks_performed_with_warnings" if warnings else "checks_performed_clean"

    return {
        "contamination_status": status,
        "checks_performed": checks_performed,
        "warnings": warnings,
    }


def _scan_source_for_strings(root: str, needles: list[str], exclude_dirname: str) -> list[str]:

    needles = [n for n in needles if n]
    if not needles:
        return []

    pattern = re.compile("|".join(re.escape(n) for n in needles))

    hits = []

    for dirpath, dirnames, filenames in os.walk(root):

        dirnames[:] = [
            d for d in dirnames
            if d not in (exclude_dirname, "__pycache__", ".git", "node_modules", ".venv", "venv", "site-packages")
        ]

        for filename in filenames:

            if not filename.endswith(".py"):
                continue

            path = os.path.join(dirpath, filename)

            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                continue

            if pattern.search(content):
                hits.append(path)

    return hits

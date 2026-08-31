# Web Evidence Benchmark

This folder contains the reproducible evaluation used for eGovAssist web retrieval.

## Run

From the backend root:

```bash
python -m evaluation.run
```

For retrieval-only evaluation:

```bash
python -m evaluation.run --skip-generation
```

For a small smoke run:

```bash
python -m evaluation.run --limit 5
```

For a zero-credit deterministic replay using the included frozen Tavily cache:

```bash
python -m evaluation.run --skip-generation --cache-tavily replay
```

The benchmark dataset is `dataset.json`. `run.py` calls the real `WebDiscoveryService`; it is not a mocked application benchmark.

## Metrics

The evaluator reports Recall@1, Recall@5, Recall@10, MRR, domain accuracy, and official-source rate. When generation is enabled and the required providers are available, it also reports the existing structural citation/grounding metrics.

Rank-sensitive metrics deduplicate results by normalized source URL before scoring so multiple chunks from the same page do not occupy multiple ranks.

## Frozen baseline

The latest validated A2.1 retrieval baseline on the frozen 61-query replay is:

- R@1: **37.7% (23/61)**
- R@5: **63.9% (39/61)**
- R@10: **65.6% (40/61)**
- MRR: **0.4810**
- Empty results: **0**

The A3 proposal was analyzed but is not implemented in this handoff.

# eGovAssist Backend

eGovAssist is a web-grounded government-assistance backend. It discovers current government information from the web, ranks and verifies sources, builds grounded context, and generates answers. It also contains the grievance workflow and persistent chat history.

## Current scope

This handoff contains the working production pipeline and the real 61-query evaluation benchmark. The legacy document-upload/ingestion layer and the old standalone language layer have been removed because those features are being handled separately by the team.

The A2.1 retrieval baseline is retained:

- R@1: **37.7% (23/61)**
- R@5: **63.9% (39/61)**
- R@10: **65.6% (40/61)**
- MRR: **0.4810**
- Empty results: **0**
- Benchmark replay: deterministic on the frozen cache

A2.1 includes the authority-aware scheme-candidate promotion gate and the title-aware `source_tier()` comparison. The next experimental change (A3) was **not** included in this handoff.

## Architecture

```text
Browser / Frontend
        |
        | HTTP JSON
        v
FastAPI: app/main.py
        |
        +--> SQLite conversation history: app/database.py
        |
        +--> Grievance detection/workflow: grievance/
        |
        +--> Evidence location: evidence/source_locator.py
        |
        +--> RAGPipeline: rag/pipeline.py
                 |
                 +--> Query classification
                 +--> Web discovery: web_discovery/service.py
                 |       |
                 |       +--> Tavily / Firecrawl providers
                 |       +--> BM25 ranking
                 |       +--> Scheme candidate detection/promotion
                 |       +--> Retrieval scoring / authority tiers
                 |
                 +--> BM25 retrieval: retrieval/bm25_retriever.py
                 +--> RRF fusion: retrieval/rrf.py
                 +--> Gemini/Groq reranking
                 +--> Source verification: security/source_verifier.py
                 +--> Context building: rag/context_builder.py
                 +--> Grounded prompt: rag/prompt_builder.py
                 +--> Answer generation: rag/answer_generator.py

Benchmark
    evaluation/run.py
        |
        +--> evaluation/dataset.json
        +--> evaluation/metrics.py
        +--> evaluation/normalize.py
        +--> evaluation/contamination.py
        +--> evaluation/citation_eval.py
        +--> WebDiscoveryService / RAGPipeline
```

## Important production modules

| Path | Responsibility |
|---|---|
| `app/main.py` | FastAPI application, chat/conversation/evidence endpoints, orchestration |
| `app/database.py` | SQLite persistence for conversations/messages |
| `rag/pipeline.py` | End-to-end retrieval, verification, context and generation orchestration |
| `rag/context_builder.py` | Converts retrieved evidence into grounded model context |
| `rag/prompt_builder.py` | Builds grounded answer prompts |
| `rag/answer_generator.py` | Generates and validates the final response |
| `web_discovery/service.py` | Main web discovery pipeline |
| `web_discovery/tavily_client.py` | Tavily search provider |
| `web_discovery/firecrawl_client.py` | Page/content retrieval provider |
| `web_discovery/bm25_ranker.py` | BM25 web-result ranking |
| `web_discovery/retrieval_scorer.py` | Authority/relevance scoring and source tiers |
| `web_discovery/scheme_candidate.py` | Scheme-candidate identification and A2.1 authority gate |
| `web_discovery/query_classifier.py` | Query classification |
| `retrieval/bm25_retriever.py` | Retrieval-stage BM25 logic |
| `retrieval/rrf.py` | Reciprocal Rank Fusion |
| `retrieval/gemini_reranker.py` | Gemini reranking |
| `retrieval/groq_reranker.py` | Groq reranking where configured |
| `retrieval/retriever.py` | Retrieval coordination |
| `security/source_verifier.py` | Source trust/verification logic |
| `evidence/source_locator.py` | Exact evidence passage/page location and caching |
| `grievance/` | Structured grievance classification, extraction, drafting and follow-up workflow |
| `providers/gemini_embeddings.py` | Gemini embedding provider |
| `evaluation/run.py` | Real 61-query benchmark runner |

## Running the backend

From the backend repository root:

```bash
python -m uvicorn app.main:app --reload
```

Or without reload:

```bash
python -m uvicorn app.main:app
```

Install dependencies with:

```bash
pip install -r requirements.txt
```

Keep API credentials in environment variables / `.env`; do not hard-code keys or machine-specific paths.

## Frontend

The supplied frontend is a small static application:

```text
Frontend/
  index.html
  css/style.css
  js/app.js
```

`js/app.js` communicates with the FastAPI server through `API_URL`. The frontend uses relative paths for its own CSS/JS assets, so moving the project to another parent directory does not require filesystem-path changes.

## Benchmark

The real benchmark is:

```bash
python -m evaluation.run
```

Useful modes:

```bash
python -m evaluation.run --skip-generation
python -m evaluation.run --limit 5
python -m evaluation.run --dataset evaluation/dataset.json
```

The benchmark uses `evaluation/dataset.json` and calls the real `WebDiscoveryService`; it is not a mocked retrieval test. Results are written under `evaluation/results/` when the benchmark is executed. Those generated results are intentionally not included in this handoff ZIP.

## Debugging guide

### Retrieval quality

Start with:

- `web_discovery/service.py` — discovery flow and result assembly
- `web_discovery/retrieval_scorer.py` — authority/relevance scoring
- `web_discovery/scheme_candidate.py` — scheme promotion behavior
- `web_discovery/bm25_ranker.py` — lexical ranking
- `retrieval/retriever.py` / `retrieval/bm25_retriever.py` — downstream retrieval

For ranking changes, run the frozen benchmark and compare R@1, R@5, R@10 and MRR. Do not judge a ranking patch from a single query.

### Evidence/citations

Trace:

```text
retrieved result
  -> source verification
  -> context_builder.py
  -> answer_generator.py
  -> evidence/source_locator.py
  -> API response
```

### Grievances

Trace:

```text
app/main.py
  -> grievance/workflow.py
  -> classifier / semantic extractor / entity extractor
  -> state + draft builder + submission guide
```

### Path portability

Production Python code should derive repository-relative resources from `__file__` / `Path(__file__).resolve()` or accept an explicit configurable path. Do not introduce absolute machine paths such as `C:\...`, `A:\...`, `/Users/...`, or `/home/...`.

Evaluation output paths are deliberately derived from the evaluation module location, so the repository can be moved to another parent directory.

## Handoff notes

- Do not treat the old A1/A2 experiment scripts as production code; they were removed from this handoff.
- A3 was analyzed but not implemented.
- The remaining same-tier scheme-ranking cases were intentionally left for future improvement rather than introducing a higher-risk heuristic before handoff.
- Generated caches, benchmark result folders, bytecode, and temporary forensic scripts are not part of the clean source handoff.

## Handoff structure

```text
backend/
├── app/              # FastAPI entrypoint + persistence
├── grievance/        # grievance workflow
├── web_discovery/    # live web search, ranking, scheme logic
├── retrieval/        # local/vector retrieval + reranking
├── rag/              # grounding + answer generation
├── evidence/         # source/evidence location
├── security/         # source verification
├── providers/        # model providers
├── evaluation/       # 61-query benchmark + frozen Tavily cache
└── data/indexes/     # retained local indexes

frontend/
├── index.html
├── css/style.css
└── js/app.js
```

The repository root is intentionally portable: production filesystem paths are derived from `Path(__file__).resolve()` or runtime configuration rather than machine-specific absolute paths.

Unused experimental modules and temporary test artifacts were removed. The production pipeline logic was not redesigned during cleanup.

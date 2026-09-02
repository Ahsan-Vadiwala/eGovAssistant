# eGovAssist — Clean Handoff

eGovAssist is a web-grounded government assistance application with a FastAPI backend and a lightweight browser frontend. This repository is the cleaned handoff baseline intended for the team to extend.

## Repository

```text
.
├── backend/
│   ├── app/              # FastAPI entrypoint and conversation persistence
│   ├── grievance/        # grievance classification and workflow
│   ├── web_discovery/    # live search, ranking, source scoring, scheme logic
│   ├── retrieval/        # local/vector retrieval and Gemini reranking
│   ├── rag/              # grounding, context, prompting and answer generation
│   ├── evidence/         # evidence/source location
│   ├── security/         # source verification
│   ├── providers/        # model providers
│   ├── data/indexes/     # retained local retrieval indexes
│   └── evaluation/       # frozen 61-query benchmark and replay cache
└── frontend/
    ├── index.html
    ├── css/style.css
    └── js/app.js
```

## Main request flow

```text
Frontend
  -> FastAPI (app/main.py)
  -> query classification / grievance routing
  -> web discovery + ranking
  -> local retrieval / reranking where applicable
  -> source verification
  -> evidence/context construction
  -> grounded answer generation
  -> JSON response + conversation history
```

## Retrieval pipeline

`web_discovery/service.py` is the main live-web retrieval path. It coordinates Tavily/Firecrawl, BM25 ranking, retrieval scoring, authority tiers and scheme-candidate handling. `retrieval_scorer.py` contains the shared source-authority/relevance scoring. `scheme_candidate.py` contains the A2.1 authority-aware promotion gate, including title-aware tier comparison.


## .env : example
`.env` file contains all your API keys for web-search, pre- & re-ranking gemini key, answer generation Groq api key.

-> For maximum usage & credits, Tavily & Groq has backup API keys to never run-out of your daily API tokens limit.

```
GROQ_API_KEY_1=your_main_api_key
GROQ_API_KEY_2=your_2nd_groq_api_key
GROQ_API_KEY=your_backup_groq_api_key

GEMINI_API_KEY=your_gemini_api_key

TAVILY_API_KEY_1=your_main_tavily_api_key
TAVILY_API_KEY_2=your_backup_tavily_api_key

FIRECRAWL_API_KEY=your_firecrawl_api_key

SEARCH_PROVIDERS=tavily,firecrawl
```

## Current benchmark baseline

The retained frozen benchmark is the 61-query evaluation used during the retrieval experiments. The verified A2.1 replay baseline is:

- R@1: 37.7% (23/61)
- R@5: 63.9% (39/61)
- R@10: 65.6% (40/61)
- MRR: 0.4810
- Empty results: 0

The next experimental A3 change was not included.

## Portability

Production Python code should resolve repository-relative resources from `Path(__file__).resolve()` or runtime configuration. No machine-specific absolute filesystem paths were found in the retained backend Python source during the cleanup audit. Keep this convention when adding files.

## Debugging

Start with `backend/app/main.py` for API behavior, `backend/rag/pipeline.py` for end-to-end answer flow, `backend/web_discovery/service.py` for live search/ranking, `backend/web_discovery/retrieval_scorer.py` for scoring, `backend/web_discovery/scheme_candidate.py` for scheme promotion, and `backend/grievance/workflow.py` for grievance behavior. The benchmark entrypoint is `backend/evaluation/run.py`.

## Cleanup policy

Temporary experiments, obsolete retrieval variants, Python caches, uploaded-document legacy code, standalone legacy language-layer code, and non-benchmark test fixtures were removed. The production pipeline logic was not redesigned as part of this cleanup. The frozen benchmark dataset/cache and retained static retrieval indexes were kept because they are useful for reproducible validation and runtime retrieval.

## Run

From `backend/`, install `requirements.txt` & enter `.venv` mode by running `.venv\scripts\activate.ps1` from `backend/`

then start the FastAPI application with:

```bash
python -m uvicorn app.main:app --reload
```

The frontend can be served as static files by the team's existing frontend setup.

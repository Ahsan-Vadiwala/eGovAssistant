import json
from pathlib import Path

import faiss
import numpy as np

from providers.gemini_embeddings import (
    GeminiEmbeddingProvider,
)


BASE_DIR = Path(__file__).resolve().parent.parent

INDEX_PATH = (
    BASE_DIR
    / "data"
    / "indexes"
    / "section_knowledge_gemini.faiss"
)

METADATA_PATH = (
    BASE_DIR
    / "data"
    / "indexes"
    / "section_metadata.json"
)

EMBEDDING_DIMENSION = 768


class SectionRetriever:

    def __init__(
        self,
        index_path=INDEX_PATH,
        metadata_path=METADATA_PATH,
    ):

        print("Loading Gemini semantic retrieval system...")


        if not Path(index_path).exists():
            raise FileNotFoundError(
                f"Gemini FAISS index not found: {index_path}"
            )

        if not Path(metadata_path).exists():
            raise FileNotFoundError(
                f"Metadata not found: {metadata_path}"
            )


        print("Loading Gemini FAISS index...")

        self.index = faiss.read_index(
            str(index_path)
        )


        print("Loading metadata...")

        with open(
            metadata_path,
            "r",
            encoding="utf-8",
        ) as f:

            self.metadata = json.load(f)


        print("Loading Gemini embedding provider...")

        self.embedding_provider = (
            GeminiEmbeddingProvider()
        )

        print(
            f"Model     : gemini-embedding-001"
        )

        print(
            f"Dimensions: {EMBEDDING_DIMENSION}"
        )


        if self.index.d != EMBEDDING_DIMENSION:

            raise RuntimeError(
                "FAISS index dimension mismatch: "
                f"expected {EMBEDDING_DIMENSION}, "
                f"got {self.index.d}."
            )

        if self.index.ntotal != len(self.metadata):

            raise RuntimeError(
                "FAISS index and metadata size mismatch: "
                f"{self.index.ntotal} vectors vs "
                f"{len(self.metadata)} metadata entries."
            )

        print("Gemini semantic retrieval system ready.")

        print(
            f"Vectors  : {self.index.ntotal}"
        )

        print(
            f"Dimension: {self.index.d}"
        )


    def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ):

        query = query.strip()

        if not query:
            return []


        embedding = (
            self.embedding_provider.embed_one(
                query
            )
        )

        embedding = np.array(
            [embedding],
            dtype="float32",
        )


        if embedding.shape[1] != self.index.d:

            raise RuntimeError(
                "Query embedding dimension does not "
                "match FAISS index: "
                f"{embedding.shape[1]} vs "
                f"{self.index.d}"
            )


        scores, indices = self.index.search(
            embedding,
            top_k,
        )

        results = []


        for score, index_id in zip(
            scores[0],
            indices[0],
        ):

            if index_id < 0:
                continue

            metadata = self.metadata[index_id]

            results.append({
                "score": float(score),
                "chunk_id": metadata.get(
                    "chunk_id"
                ),
                "document_id": metadata.get(
                    "document_id"
                ),
                "section_id": metadata.get(
                    "section_id"
                ),
                "section_title": metadata.get(
                    "section_title"
                ),
                "section_type": metadata.get(
                    "section_type"
                ),
                "page": metadata.get(
                    "page"
                ),
                "language": metadata.get(
                    "language"
                ),
                "text": metadata.get(
                    "text"
                ),
            })

        return results


_retriever = None


def retrieve(
    query: str,
    top_k: int = 5,
):

    global _retriever

    if _retriever is None:

        _retriever = SectionRetriever()

    return _retriever.retrieve(
        query,
        top_k=top_k,
    )

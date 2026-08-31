import os

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()


MODEL_NAME = "gemini-embedding-001"
EMBEDDING_DIMENSION = 768


class GeminiEmbeddingProvider:

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set."
            )

        self.client = genai.Client(
            api_key=api_key
        )

    def embed(
        self,
        texts: list[str],
    ) -> list[list[float]]:

        if not texts:
            return []

        embeddings = []

        for text in texts:

            response = self.client.models.embed_content(
                model=MODEL_NAME,
                contents=text,
                config=types.EmbedContentConfig(
                    output_dimensionality=EMBEDDING_DIMENSION,
                ),
            )

            embeddings.append(
                response.embeddings[0].values
            )

        return embeddings

    def embed_one(
        self,
        text: str,
    ) -> list[float]:

        results = self.embed([text])

        if not results:
            raise RuntimeError(
                "Gemini returned no embedding."
            )

        return results[0]

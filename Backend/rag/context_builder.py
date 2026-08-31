
class ContextBuilder:
    """
    Converts verified retrieval results into grounded evidence
    for the generation layer.

    Supports both:
        - local/document evidence
        - web evidence

    This class does NOT generate answers.
    """

    def __init__(
        self,
        max_chunks: int = 8,
        max_chars_per_chunk: int = 3000,
    ):
        self.max_chunks = max_chunks
        self.max_chars_per_chunk = (
            max_chars_per_chunk
        )


    def build(
        self,
        results: list[dict],
    ) -> str:

        if not results:
            return ""

        selected_results = results[
            :self.max_chunks
        ]

        context_parts = []

        evidence_index = 1

        for result in selected_results:

            text = str(
                result.get(
                    "text",
                    "",
                )
            ).strip()

            if not text:
                continue


            if len(text) > self.max_chars_per_chunk:

                text = (
                    text[
                        :self.max_chars_per_chunk
                    ]
                    + "..."
                )

            chunk_id = result.get(
                "chunk_id",
                "unknown",
            )

            title = (
                result.get(
                    "title"
                )
                or result.get(
                    "web_title"
                )
                or result.get(
                    "document_id"
                )
                or "Unknown source"
            )

            document_id = result.get(
                "document_id"
            )

            section = (
                result.get(
                    "section_title"
                )
                or result.get(
                    "section"
                )
                or "Unknown section"
            )

            page = result.get(
                "page"
            )

            source_url = (
                result.get(
                    "source_url"
                )
                or result.get(
                    "url"
                )
            )

            source_type = result.get(
                "source_type"
            )

            domain = result.get(
                "query_domain"
            )

            jurisdiction = result.get(
                "jurisdiction"
            )

            state = result.get(
                "state"
            )

            reranker = result.get(
                "reranker"
            )

            rerank_score = result.get(
                "rerank_score"
            )

            metadata_lines = []

            metadata_lines.append(
                f"Source Title: {title}"
            )

            if document_id:
                metadata_lines.append(
                    f"Document ID: {document_id}"
                )

            if source_url:
                metadata_lines.append(
                    f"Source URL: {source_url}"
                )

            if source_type:
                metadata_lines.append(
                    f"Source Type: {source_type}"
                )

            if domain:
                metadata_lines.append(
                    f"Query Domain: {domain}"
                )

            if jurisdiction:
                metadata_lines.append(
                    f"Jurisdiction: {jurisdiction}"
                )

            if state:
                metadata_lines.append(
                    f"State: {state}"
                )

            if section:
                metadata_lines.append(
                    f"Section: {section}"
                )

            if page is not None:
                metadata_lines.append(
                    f"Page: {page}"
                )

            if result.get(
                "official"
            ):

                metadata_lines.append(
                    "Authority Priority: "
                    "Official Government Source"
                )

            elif result.get(
                "trusted_secondary"
            ):

                metadata_lines.append(
                    "Authority Priority: "
                    "Trusted Secondary Source"
                )

            if reranker:
                metadata_lines.append(
                    f"Reranker: {reranker}"
                )

            if rerank_score is not None:
                metadata_lines.append(
                    f"Relevance Score: "
                    f"{rerank_score}"
                )

            metadata = "\n".join(
                metadata_lines
            )


            evidence_block = (
                f"[EVIDENCE {evidence_index}]\n"
                f"Chunk ID: {chunk_id}\n"
                f"{metadata}\n"
                f"Text:\n"
                f"{text}"
            )

            context_parts.append(
                evidence_block
            )

            evidence_index += 1

        return "\n\n".join(
            context_parts
        )


_context_builder = None


def build_context(
    results: list[dict],
    max_chunks: int = 8,
) -> str:

    global _context_builder

    if _context_builder is None:

        _context_builder = (
            ContextBuilder(
                max_chunks=max_chunks
            )
        )

    return _context_builder.build(
        results
    )


from __future__ import annotations

from web_discovery.service import (
    WebDiscoveryService,
)

from web_discovery.query_classifier import (
    QueryClassification,
)

from security.source_verifier import (
    SourceVerifier,
)

from retrieval.bm25_retriever import (
    BM25Retriever,
)

from retrieval.rrf import (
    reciprocal_rank_fusion,
)

from retrieval.gemini_reranker import (
    GeminiReranker,
)

from .context_builder import (
    ContextBuilder,
)

from .prompt_builder import (
    PromptBuilder,
)

from .answer_generator import (
    AnswerGenerator,
)


class RAGPipeline:
    """
    End-to-end web-grounded RAG pipeline.

    Architecture:

        User Query
             ↓
        Existing QueryClassifier
             ↓
        Web Discovery
             ↓
        BM25 Ranking
             ↓
        Gemini Pre-Ranking
             ↓
        RRF Fusion
             ↓
        Gemini Final Reranking
             ↓
        RELEVANCE GATE
             ↓
        Source Verification
             ↓
        Evidence Gate
             ↓
        Context Building
             ↓
        Grounded Generation
             ↓
        Gemini Evidence Validation
             ↓
        Final Answer + Used Evidence

    IMPORTANT:

    QueryClassifier is NOT duplicated here.

    /chat may classify the query first and pass the resulting
    QueryClassification into ask().

    If no classification is supplied, WebDiscoveryService
    performs classification itself for backward compatibility.

    Gemini remains the retrieval/reranking layer.

    Source verification checks source trustworthiness.

    The relevance gate separately checks whether the retrieved
    evidence is actually relevant to the user's question.

    An irrelevant question MUST NOT reach answer generation.

    Only evidence actually cited by the final answer is exposed
    through `evidence` and `sources`.
    """


    DEFAULT_MIN_RELEVANCE_SCORE = 60.0

    def __init__(
        self,
        retrieval_top_k: int = 8,
        context_max_chunks: int = 8,
        minimum_trust_score: float = 35.0,
        bm25_top_k: int = 15,
        gemini_pre_top_k: int = 15,
        final_top_k: int = 8,
        rrf_k: int = 60,
        minimum_relevance_score: float = (
            DEFAULT_MIN_RELEVANCE_SCORE
        ),
    ):

        print("=" * 70)

        print(
            "INITIALIZING WEB-GROUNDED RAG PIPELINE"
        )

        print("=" * 70)


        self.retrieval_top_k = (
            retrieval_top_k
        )

        self.bm25_top_k = (
            bm25_top_k
        )

        self.gemini_pre_top_k = (
            gemini_pre_top_k
        )

        self.final_top_k = (
            final_top_k
        )

        self.rrf_k = (
            rrf_k
        )

        self.minimum_relevance_score = float(
            minimum_relevance_score
        )


        print(
            "\nInitializing web discovery..."
        )

        self.web_discovery = (
            WebDiscoveryService()
        )


        print(
            "\nInitializing BM25 retrieval..."
        )

        self.bm25 = (
            BM25Retriever()
        )


        print(
            "\nInitializing Gemini reranker..."
        )

        self.reranker = (
            GeminiReranker()
        )


        print(
            "\nInitializing source verification..."
        )

        self.source_verifier = (
            SourceVerifier(
                minimum_trust_score=(
                    minimum_trust_score
                )
            )
        )


        print(
            "\nInitializing context builder..."
        )

        self.context_builder = (
            ContextBuilder(
                max_chunks=context_max_chunks
            )
        )


        print(
            "\nInitializing prompt builder..."
        )

        self.prompt_builder = (
            PromptBuilder()
        )


        print(
            "\nInitializing answer generator..."
        )

        self.answer_generator = (
            AnswerGenerator()
        )

        print(
            "\nWeb-grounded RAG pipeline ready.\n"
        )


    @staticmethod
    def _empty_verification() -> dict:

        return {

            "total_sources": 0,

            "verified_sources": 0,

            "partially_verified_sources": 0,

            "unverified_sources": 0,

            "average_trust_score": 0.0,

            "highest_trust_score": 0.0,

            "lowest_trust_score": 0.0,

        }


    @staticmethod
    def _empty_analysis() -> dict:

        return {

            "question_type": None,

            "depth": None,

            "architecture": None,

            "target_length": None,

        }


    @classmethod
    def _base_result(
        cls,
        *,
        status: str,
        answer: str,
        evidence=None,
        sources=None,
        accepted_sources=None,
        rejected_sources=None,
        verification=None,
        context: str = "",
        provider=None,
        model=None,
        classification=None,
        discovery=None,
        analysis=None,
        evidence_citations=None,
        evidence_validation_status=None,
    ) -> dict:

        return {

            "status": status,

            "answer": answer,

            "evidence": (
                evidence
                if evidence is not None
                else []
            ),

            "sources": (
                sources
                if sources is not None
                else []
            ),

            "accepted_sources": (
                accepted_sources
                if accepted_sources is not None
                else []
            ),

            "rejected_sources": (
                rejected_sources
                if rejected_sources is not None
                else []
            ),

            "verification": (
                verification
                if verification is not None
                else cls._empty_verification()
            ),

            "context": context,

            "provider": provider,

            "model": model,

            "classification": (
                classification
                if classification is not None
                else {}
            ),

            "discovery": (
                discovery
                if discovery is not None
                else {}
            ),

            "analysis": (
                analysis
                if analysis is not None
                else cls._empty_analysis()
            ),

            "evidence_citations": (
                evidence_citations
                if evidence_citations is not None
                else []
            ),

            "evidence_validation_status": (
                evidence_validation_status
            ),

        }


    def _check_evidence_relevance(
        self,
        results: list[dict],
    ) -> dict:
        """
        Determine whether the final Gemini-ranked evidence
        is sufficiently relevant to the user's question.

        IMPORTANT:

        Source trustworthiness and question relevance are
        separate properties.

        A source can be official and trustworthy while still
        being completely irrelevant to the question.

        This gate therefore runs BEFORE source verification,
        context building, and answer generation.

        Expected Gemini relevance scale:

            100 = directly answers
            80-99 = highly relevant
            60-79 = useful supporting evidence
            40-59 = somewhat relevant
            20-39 = weakly relevant
            0-19 = irrelevant
        """

        if not results:

            return {
                "relevant": False,
                "status": "no_final_evidence",
                "top_score": 0.0,
                "relevant_count": 0,
                "scores": [],
            }

        scores = []

        explicitly_inapplicable = []

        for result in results:

            if not isinstance(
                result,
                dict,
            ):
                continue


            applicable = result.get(
                "rerank_applicable"
            )

            if (
                applicable is False
                or str(applicable).strip().lower()
                in {
                    "false",
                    "no",
                    "not_applicable",
                    "irrelevant",
                }
            ):

                explicitly_inapplicable.append(
                    result
                )


            raw_score = result.get(
                "rerank_score"
            )

            if raw_score is None:

                raw_score = result.get(
                    "gemini_score"
                )

            if raw_score is None:

                raw_score = result.get(
                    "relevance_score"
                )

            try:

                score = float(
                    raw_score
                    if raw_score is not None
                    else 0.0
                )

            except (
                TypeError,
                ValueError,
            ):

                score = 0.0

            scores.append(
                score
            )

        if not scores:

            return {
                "relevant": False,
                "status": "no_relevance_scores",
                "top_score": 0.0,
                "relevant_count": 0,
                "scores": [],
            }

        top_score = max(
            scores
        )

        relevant_scores = [
            score
            for score in scores
            if score >= self.minimum_relevance_score
        ]


        if not relevant_scores:

            return {
                "relevant": False,
                "status": "below_relevance_threshold",
                "top_score": top_score,
                "relevant_count": 0,
                "scores": scores,
            }

        # are inapplicable, do not allow a score anomaly to

        if (
            len(explicitly_inapplicable)
            == len(results)
        ):

            return {
                "relevant": False,
                "status": "all_candidates_inapplicable",
                "top_score": top_score,
                "relevant_count": 0,
                "scores": scores,
            }


        return {
            "relevant": True,
            "status": "relevant",
            "top_score": top_score,
            "relevant_count": len(
                relevant_scores
            ),
            "scores": scores,
        }


    @staticmethod
    def _extract_evidence_references(
        answer: str,
    ) -> tuple[list[int], bool]:

        """
        Extract [EVIDENCE N] references from the final answer.
        """

        import re

        answer = str(
            answer or ""
        )

        malformed_pattern = re.compile(
            r"\[\s*EVIDENCE\s+[^\]]+\]",
            re.IGNORECASE,
        )

        valid_pattern = re.compile(
            r"\[\s*EVIDENCE\s+(\d+)\s*\]",
            re.IGNORECASE,
        )

        all_markers = (
            malformed_pattern.findall(
                answer
            )
        )

        valid_markers = (
            valid_pattern.findall(
                answer
            )
        )

        malformed = False

        if all_markers:

            malformed = (
                len(all_markers)
                != len(valid_markers)
            )

        references = []

        for number in valid_markers:

            number = int(
                number
            )

            if number not in references:

                references.append(
                    number
                )

        return (
            references,
            malformed,
        )


    @classmethod
    def _validate_generated_evidence(
        cls,
        answer: str,
        accepted_sources: list[dict],
    ) -> dict:

        if not accepted_sources:

            return {

                "valid": False,

                "status": "no_accepted_evidence",

                "references": [],

                "used_sources": [],

                "invalid_references": [],

            }

        references, malformed = (
            cls._extract_evidence_references(
                answer
            )
        )

        if malformed:

            return {

                "valid": False,

                "status": (
                    "malformed_evidence_reference"
                ),

                "references": references,

                "used_sources": [],

                "invalid_references": [],

            }

        if not references:

            return {

                "valid": False,

                "status": "no_evidence_citation",

                "references": [],

                "used_sources": [],

                "invalid_references": [],

            }

        invalid_references = []

        used_sources = []

        for number in references:

            if (
                number < 1
                or number > len(
                    accepted_sources
                )
            ):

                invalid_references.append(
                    number
                )

                continue

            source = (
                accepted_sources[
                    number - 1
                ]
            )

            used_sources.append(
                source
            )

        if invalid_references:

            return {

                "valid": False,

                "status": (
                    "invalid_evidence_reference"
                ),

                "references": references,

                "used_sources": [],

                "invalid_references": (
                    invalid_references
                ),

            }

        if not used_sources:

            return {

                "valid": False,

                "status": "no_valid_evidence",

                "references": references,

                "used_sources": [],

                "invalid_references": [],

            }

        return {

            "valid": True,

            "status": "validated",

            "references": references,

            "used_sources": used_sources,

            "invalid_references": [],

        }


    def ask(
        self,
        query: str,
        top_k: int | None = None,
        classification: QueryClassification | None = None,
    ) -> dict:

        query = str(
            query or ""
        ).strip()

        if not query:

            raise ValueError(
                "Query cannot be empty."
            )

        if top_k is None:

            top_k = self.final_top_k

        if top_k <= 0:

            raise ValueError(
                "top_k must be greater than zero."
            )

        print(
            "\n"
            + "=" * 70
        )

        print(
            "WEB-GROUNDED RAG PIPELINE"
        )

        print(
            "=" * 70
        )

        print(
            f"\nQuestion: {query}"
        )

        # scope, so this check must run before evidence is even

        if (
            classification is not None
            and classification.domain == "general"
        ):

            print(
                "\n[0/10] Domain scope gate: "
                "UNSUPPORTED DOMAIN."
            )

            print(
                "Query does not match any supported "
                "eGovAssistant domain. Abstaining before "
                "web discovery."
            )

            scope_classification_data = {

                "domain": classification.domain,

                "jurisdiction": (
                    classification.jurisdiction
                ),

                "state": classification.state,

                "confidence": (
                    classification.confidence
                ),

            }

            return self._base_result(

                status="abstained",

                answer=(
                    "This question is outside the scope of "
                    "eGovAssistant. I can help with "
                    "government schemes, cooperative societies, "
                    "PACS, crop insurance (PMFBY), agriculture, "
                    "financial literacy, and grievance-redressal "
                    "questions."
                ),

                classification=(
                    scope_classification_data
                ),

                discovery={},

                evidence_validation_status=(
                    "out_of_domain"
                ),

            )


        print(
            "\n[1/10] Discovering web evidence..."
        )

        discovery = (
            self.web_discovery.discover(
                query=query,
                classification=classification,
            )
        )

        discovered_results = (
            discovery.get(
                "results",
                [],
            )
        )

        classification_data = (
            discovery.get(
                "classification",
                {},
            )
        )

        print(
            f"Domain       : "
            f"{classification_data.get('domain')}"
        )

        print(
            f"Jurisdiction : "
            f"{classification_data.get('jurisdiction')}"
        )

        print(
            f"State        : "
            f"{classification_data.get('state')}"
        )

        print(
            f"Confidence    : "
            f"{classification_data.get('confidence')}"
        )

        print(
            f"Discovery    : "
            f"{discovery.get('discovery_stage')}"
        )

        print(
            f"Web candidates: "
            f"{len(discovered_results)}"
        )

        if not discovered_results:

            return self._base_result(

                status="abstained",

                answer=(
                    "No sufficiently relevant web "
                    "evidence was found for this question."
                ),

                classification=classification_data,

                discovery=discovery,

                evidence_validation_status=(
                    "no_discovered_evidence"
                ),
            )


        print(
            "\n[2/10] BM25 ranking discovered candidates..."
        )

        bm25_results = (
            self.bm25.rank_candidates(
                query=query,
                candidates=discovered_results,
                top_k=self.bm25_top_k,
            )
        )

        print(
            f"BM25 candidates: "
            f"{len(bm25_results)}"
        )

        for rank, result in enumerate(
            bm25_results,
            start=1,
        ):

            print(
                f"  BM25 #{rank}: "
                f"{result.get('chunk_id')} "
                f"score={result.get('bm25_score', 0.0):.4f}"
            )

        if not bm25_results:

            return self._base_result(

                status="abstained",

                answer=(
                    "The discovered evidence could not "
                    "be ranked using BM25."
                ),

                classification=classification_data,

                discovery=discovery,

                evidence_validation_status=(
                    "bm25_failed"
                ),
            )


        print(
            "\n[3/10] Gemini pre-ranking discovered candidates..."
        )

        gemini_pre_results = (
            self.reranker.pre_rank(
                query=query,
                candidates=discovered_results,
                top_k=self.gemini_pre_top_k,
                classification=classification_data,
            )
        )

        print(
            f"Gemini pre-rank candidates: "
            f"{len(gemini_pre_results)}"
        )

        for rank, result in enumerate(
            gemini_pre_results,
            start=1,
        ):

            print(
                f"  Gemini #{rank}: "
                f"{result.get('chunk_id')} "
                f"score={result.get('gemini_score', 0.0):.1f} "
                f"applicable={result.get('rerank_applicable')}"
            )

        if not gemini_pre_results:

            return self._base_result(

                status="abstained",

                answer=(
                    "The discovered evidence could not "
                    "be semantically ranked."
                ),

                classification=classification_data,

                discovery=discovery,

                evidence_validation_status=(
                    "gemini_pre_rank_failed"
                ),
            )


        print(
            "\n[4/10] Fusing BM25 and Gemini rankings with RRF..."
        )

        fused_results = (
            reciprocal_rank_fusion(
                result_lists=[
                    bm25_results,
                    gemini_pre_results,
                ],
                k=self.rrf_k,
                top_k=None,
            )
        )

        print(
            f"RRF fused candidates: "
            f"{len(fused_results)}"
        )

        for rank, result in enumerate(
            fused_results,
            start=1,
        ):

            print(
                f"  RRF #{rank}: "
                f"{result.get('chunk_id')} "
                f"score={result.get('rrf_score', 0.0):.6f} "
                f"BM25={result.get('bm25_score', 'n/a')} "
                f"Gemini={result.get('gemini_score', 'n/a')}"
            )

        if not fused_results:

            return self._base_result(

                status="abstained",

                answer=(
                    "The retrieval systems did not "
                    "produce a fused evidence set."
                ),

                classification=classification_data,

                discovery=discovery,

                evidence_validation_status=(
                    "rrf_failed"
                ),
            )


        print(
            "\n[5/10] Gemini final reranking..."
        )

        final_results = (
            self.reranker.final_rerank(
                query=query,
                candidates=fused_results,
                top_k=top_k,
                classification=classification_data,
            )
        )

        for result in final_results:

            result[
                "query_domain"
            ] = classification_data.get(
                "domain"
            )

            result[
                "jurisdiction"
            ] = classification_data.get(
                "jurisdiction"
            )

            result[
                "state"
            ] = classification_data.get(
                "state"
            )

            result[
                "classification_confidence"
            ] = classification_data.get(
                "confidence"
            )

        print(
            f"Final evidence chunks: "
            f"{len(final_results)}"
        )

        for rank, result in enumerate(
            final_results,
            start=1,
        ):

            print(
                f"  FINAL #{rank}: "
                f"{result.get('chunk_id')} "
                f"score={result.get('rerank_score', 0.0):.1f} "
                f"RRF={result.get('rrf_score', 0.0):.6f} "
                f"applicable={result.get('rerank_applicable')}"
            )

        if not final_results:

            return self._base_result(

                status="abstained",

                answer=(
                    "The retrieval system did not "
                    "produce sufficiently applicable "
                    "evidence for the question."
                ),

                classification=classification_data,

                discovery=discovery,

                evidence_validation_status=(
                    "final_rerank_failed"
                ),
            )

        # Do NOT continue merely because sources exist.

        print(
            "\n[5.5/10] Checking question-evidence relevance..."
        )

        relevance_result = (
            self._check_evidence_relevance(
                final_results
            )
        )

        print(
            f"Relevance status : "
            f"{relevance_result.get('status')}"
        )

        print(
            f"Top relevance    : "
            f"{relevance_result.get('top_score')}"
        )

        print(
            f"Relevant chunks  : "
            f"{relevance_result.get('relevant_count')}"
        )

        print(
            f"Relevance scores : "
            f"{relevance_result.get('scores')}"
        )

        if not relevance_result.get(
            "relevant",
            False,
        ):

            print(
                "\nRELEVANCE GATE FAILED."
            )

            print(
                "Question will be abstained from."
            )

            return self._base_result(

                status="abstained",

                answer=(
                    "I could not find sufficiently "
                    "relevant evidence to answer this "
                    "question reliably."
                ),

                evidence=[],

                sources=[],

                accepted_sources=[],

                rejected_sources=final_results,

                classification=classification_data,

                discovery=discovery,

                evidence_validation_status=(
                    "relevance_gate_failed"
                ),

            )


        print(
            "\n[6/10] Verifying final evidence sources..."
        )

        verification_result = (
            self.source_verifier.verify_and_filter(
                final_results
            )
        )

        verified_sources = (
            verification_result.get(
                "verified_sources",
                [],
            )
        )

        accepted_sources = (
            verification_result.get(
                "accepted_sources",
                [],
            )
        )

        rejected_sources = (
            verification_result.get(
                "rejected_sources",
                [],
            )
        )

        verification_summary = (
            verification_result.get(
                "summary",
                self._empty_verification(),
            )
        )

        print(
            f"Verified sources: "
            f"{len(verified_sources)}"
        )

        print(
            f"Accepted sources: "
            f"{len(accepted_sources)}"
        )

        print(
            f"Rejected sources: "
            f"{len(rejected_sources)}"
        )


        print(
            "\n[7/10] Checking evidence threshold..."
        )

        if not accepted_sources:

            return self._base_result(

                status="abstained",

                answer=(
                    "I could not find enough verified "
                    "evidence from the available web sources "
                    "to answer this reliably."
                ),

                evidence=verified_sources,

                sources=verified_sources,

                accepted_sources=[],

                rejected_sources=rejected_sources,

                verification=verification_summary,

                classification=classification_data,

                discovery=discovery,

                evidence_validation_status=(
                    "evidence_gate_failed"
                ),
            )


        print(
            "\n[8/10] Building grounded evidence context..."
        )

        context = (
            self.context_builder.build(
                accepted_sources
            )
        )

        if not context:

            return self._base_result(

                status="abstained",

                answer=(
                    "The retrieved sources did not "
                    "contain usable evidence."
                ),

                evidence=accepted_sources,

                sources=verified_sources,

                accepted_sources=accepted_sources,

                rejected_sources=rejected_sources,

                verification=verification_summary,

                classification=classification_data,

                discovery=discovery,

                evidence_validation_status=(
                    "context_build_failed"
                ),
            )


        print(
            "\n[9/10] Generating grounded answer..."
        )

        system_prompt, user_prompt = (
            self.prompt_builder.build(
                query=query,
                context=context,
            )
        )

        generation_result = (
            self.answer_generator.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        )

        analysis = (
            generation_result.get(
                "analysis",
                self._empty_analysis(),
            )
        )

        answer = str(
            generation_result.get(
                "answer",
                "",
            )
            or ""
        ).strip()


        print(
            "\n[10/10] Validating generated evidence citations..."
        )

        evidence_validation = (
            self._validate_generated_evidence(
                answer=answer,
                accepted_sources=accepted_sources,
            )
        )

        print(
            f"Evidence validation: "
            f"{evidence_validation.get('status')}"
        )

        print(
            f"Cited evidence: "
            f"{evidence_validation.get('references')}"
        )


        if not evidence_validation.get(
            "valid",
            False,
        ):

            print(
                "\nGenerated answer failed evidence "
                "citation validation."
            )

            return self._base_result(

                status="abstained",

                answer=(
                    "The available evidence could not be "
                    "reliably linked to the generated answer."
                ),

                evidence=[],

                sources=[],

                accepted_sources=accepted_sources,

                rejected_sources=rejected_sources,

                verification=verification_summary,

                context=context,

                provider=generation_result.get(
                    "provider"
                ),

                model=generation_result.get(
                    "model"
                ),

                classification=classification_data,

                discovery=discovery,

                analysis=analysis,

                evidence_citations=(
                    evidence_validation.get(
                        "references",
                        [],
                    )
                ),

                evidence_validation_status=(
                    evidence_validation.get(
                        "status"
                    )
                ),

            )


        cited_sources = (
            evidence_validation.get(
                "used_sources",
                [],
            )
        )

        cited_references = (
            evidence_validation.get(
                "references",
                [],
            )
        )


        cited_sources = [
            {
                **source,
                "evidence_number": cited_references[i],
            }
            for i, source in enumerate(
                cited_sources
            )
            if i < len(cited_references)
        ]


        print(
            "\nFinalizing cited response..."
        )

        print(
            f"Returning {len(cited_sources)} "
            f"answer-used evidence source(s)."
        )

        return self._base_result(

            status="success",

            answer=answer,

            evidence=cited_sources,

            sources=cited_sources,

            accepted_sources=accepted_sources,

            rejected_sources=rejected_sources,

            verification=verification_summary,

            context=context,

            provider=generation_result.get(
                "provider"
            ),

            model=generation_result.get(
                "model"
            ),

            classification=classification_data,

            discovery=discovery,

            analysis=analysis,

            evidence_citations=(
                cited_references
            ),

            evidence_validation_status=(
                "validated"
            ),

        )


_pipeline = None


def ask(
    query: str,
    top_k: int = 8,
    classification: QueryClassification | None = None,
) -> dict:

    global _pipeline

    if _pipeline is None:

        _pipeline = RAGPipeline(
            retrieval_top_k=top_k,
            final_top_k=top_k,
        )

    return _pipeline.ask(
        query=query,
        top_k=top_k,
        classification=classification,
    )

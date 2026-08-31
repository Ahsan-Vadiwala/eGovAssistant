
import os
import re
from typing import Optional

from groq import Groq
from dotenv import load_dotenv


load_dotenv()


DEFAULT_MODEL = "openai/gpt-oss-20b"
DEFAULT_TEMPERATURE = 0

DEFAULT_MAX_TOKENS = 1800

REPAIR_MAX_TOKENS = 2200

GENERATION_ATTEMPTS_PER_KEY = 2


CITATION_PATTERN = re.compile(
    r"\[EVIDENCE\s+(\d+)\]",
    re.IGNORECASE,
)


class AnswerGenerator:

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ):
        print("Initializing RAG answer generator...")

        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens


        self.api_keys = []

        for env_name in (
            "GROQ_API_KEY_1",
            "GROQ_API_KEY_2",
            "GROQ_API_KEY",
        ):
            key = os.getenv(env_name)

            if key and key not in self.api_keys:
                self.api_keys.append(key)

        if not self.api_keys:
            raise RuntimeError(
                "No Groq API keys configured."
            )

        self.clients = [
            Groq(api_key=key)
            for key in self.api_keys
        ]

        print(
            f"RAG answer generator ready.\n"
            f"Model         : {self.model}\n"
            f"Available keys: {len(self.clients)}\n"
            f"Temperature    : {self.temperature}\n"
            f"Max tokens     : {self.max_tokens}"
        )


    @staticmethod
    def _extract_message_content(
        message,
    ) -> Optional[str]:
        """
        Safely extract visible answer text from a Groq/OpenAI
        compatible message object.

        Some reasoning models may return:

            content=None
            reasoning=<internal reasoning>

        Internal reasoning must NEVER be shown as the final
        answer.

        Therefore we only accept actual visible content.
        """

        if message is None:
            return None


        content = getattr(
            message,
            "content",
            None,
        )

        if isinstance(content, str):
            content = content.strip()

            if content:
                return content


        if isinstance(content, list):
            parts = []

            for block in content:

                if isinstance(block, str):
                    text = block.strip()

                    if text:
                        parts.append(text)

                    continue

                if isinstance(block, dict):
                    text = block.get("text")

                    if isinstance(text, str):
                        text = text.strip()

                        if text:
                            parts.append(text)

                    continue

                text = getattr(
                    block,
                    "text",
                    None,
                )

                if isinstance(text, str):
                    text = text.strip()

                    if text:
                        parts.append(text)

            if parts:
                return "\n".join(parts).strip()

        return None


    @staticmethod
    def _extract_evidence_numbers(
        user_prompt: str,
    ) -> set[int]:
        """
        Extract all evidence numbers available inside the
        grounded user prompt.
        """

        matches = CITATION_PATTERN.findall(
            user_prompt
        )

        return {
            int(number)
            for number in matches
        }


    @staticmethod
    def _extract_answer_citations(
        answer: str,
    ) -> set[int]:
        """
        Extract unique evidence numbers cited by the answer.
        """

        matches = CITATION_PATTERN.findall(
            answer
        )

        return {
            int(number)
            for number in matches
        }


    @staticmethod
    def _citation_count(
        answer: str,
    ) -> int:
        """
        Count every visible citation occurrence.

        Example:

            [EVIDENCE 1] [EVIDENCE 2]

        returns 2.
        """

        return len(
            CITATION_PATTERN.findall(
                answer
            )
        )


    @staticmethod
    def _clean_answer(
        answer: str,
    ) -> str:
        """
        Remove accidental model wrappers without changing
        the actual answer content.
        """

        if not answer:
            return ""

        answer = answer.strip()


        if (
            answer.startswith("```")
            and answer.endswith("```")
        ):
            lines = answer.splitlines()

            if len(lines) >= 2:
                first = lines[0].strip()

                if first.lower() in (
                    "```markdown",
                    "```md",
                    "```text",
                    "```",
                ):
                    answer = "\n".join(
                        lines[1:-1]
                    ).strip()

        return answer


    @staticmethod
    def _strip_citations(
        text: str,
    ) -> str:
        """
        Remove citations from a piece of text for semantic
        classification only.

        The actual answer is never modified by this function.
        """

        return CITATION_PATTERN.sub(
            "",
            text,
        ).strip()


    @staticmethod
    def _is_heading(
        line: str,
    ) -> bool:
        """
        Determine whether a line is probably a markdown heading.
        """

        stripped = line.strip()

        if not stripped:
            return False

        if re.match(
            r"^#{1,6}\s+",
            stripped,
        ):
            return True

        without_markdown = re.sub(
            r"[*_`>#]",
            "",
            stripped,
        ).strip()

        if (
            len(without_markdown) < 80
            and not re.search(
                r"[.!?]\s*$",
                without_markdown,
            )
            and not re.search(
                r"\b(is|are|was|were|means|refers|provides|requires)\b",
                without_markdown,
                re.IGNORECASE,
            )
        ):
            return True

        return False


    @staticmethod
    def _is_bullet(
        line: str,
    ) -> bool:
        """
        Detect markdown bullet/list lines.
        """

        return bool(
            re.match(
                r"^\s*(?:[-*+]|\d+[.)])\s+",
                line,
            )
        )


    @staticmethod
    def _remove_markdown_prefix(
        line: str,
    ) -> str:
        """
        Remove markdown decoration for validation only.
        """

        line = re.sub(
            r"^\s*#{1,6}\s*",
            "",
            line,
        )

        line = re.sub(
            r"^\s*(?:[-*+]|\d+[.)])\s+",
            "",
            line,
        )

        return line.strip()


    @staticmethod
    def _has_substantive_text(
        text: str,
    ) -> bool:
        """
        Determine whether text contains enough actual prose to
        require grounding.

        This deliberately ignores tiny labels/headings.
        """

        cleaned = AnswerGenerator._strip_citations(
            text
        )

        cleaned = re.sub(
            r"[*_`>#]",
            "",
            cleaned,
        )

        cleaned = cleaned.strip()

        compact = re.sub(
            r"[\s:;,.!?()\[\]{}\-â€“â€”]+",
            "",
            cleaned,
        )

        return len(compact) >= 20


    @staticmethod
    def _split_sentences(
        text: str,
    ) -> list[str]:
        """
        Lightweight sentence splitter.

        This is intentionally conservative. It is not intended
        to perform NLP; it only gives the citation validator
        enough structure to reason about factual coverage.

        Newlines are preserved as potential structural
        boundaries.
        """

        text = text.strip()

        if not text:
            return []

        text = re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

        parts = re.split(
            r"(?<=[.!?])\s+(?=[A-Z0-9\"'â€œâ€˜(])",
            text,
        )

        return [
            part.strip()
            for part in parts
            if part.strip()
        ]


    def _citation_validation_details(
        self,
        answer: str,
        user_prompt: str,
        ) -> tuple[bool, list[str]]:
        """
        Validate citation usage without rejecting otherwise valid
        answers merely because a structural/meta block is uncited.

        Validation policy:

        1. The grounded prompt must contain evidence blocks.
        2. The answer must contain at least one citation.
        3. Every citation must refer to an evidence number that
           actually exists in the grounded prompt.
        4. Substantive factual content should be cited, but the
           validator must not reject the complete answer solely
           because the model produced a final/concluding/meta
           paragraph without a citation.

        This is intentionally less brittle than the previous
        block-level validator. Citation repair remains available
        for genuinely citation-free answers, but normal answers
        are not allowed to burn through API keys because of one
        uncited structural block.
        """

        reasons: list[str] = []


        valid_evidence_numbers = (
            self._extract_evidence_numbers(
                user_prompt
            )
        )

        if not valid_evidence_numbers:
            reasons.append(
                "No [EVIDENCE N] blocks were found in the grounded prompt."
            )

            return False, reasons


        answer_citations = (
            self._extract_answer_citations(
                answer
            )
        )

        if not answer_citations:
            reasons.append(
                "The answer contains no [EVIDENCE N] citation."
            )

            return False, reasons


        invalid_citations = (
            answer_citations
            - valid_evidence_numbers
        )

        if invalid_citations:
            reasons.append(
                "Answer cites nonexistent evidence numbers: "
                f"{sorted(invalid_citations)}"
            )

        # IMPORTANT:
        # We deliberately do NOT reject the answer because a

        if not invalid_citations:
            return True, []

        return False, reasons

        def flush_block():
            if current_block:
                block = "\n".join(
                    current_block
                ).strip()

                if block:
                    blocks.append(block)

                current_block.clear()

        for raw_line in lines:

            line = raw_line.strip()

            if not line:
                flush_block()
                continue

            if self._is_heading(line):
                flush_block()
                blocks.append(line)
                continue

            current_block.append(line)

        flush_block()


        factual_blocks: list[tuple[int, str]] = []

        for index, block in enumerate(blocks, start=1):

            if self._is_heading(block):
                continue

            if not self._has_substantive_text(block):
                continue

            factual_blocks.append(
                (index, block)
            )

        if not factual_blocks:
            reasons.append(
                "No substantive factual content was found in the answer."
            )

            return False, reasons


        uncited_blocks: list[int] = []

        for block_index, block in factual_blocks:

            if not CITATION_PATTERN.search(
                block
            ):
                uncited_blocks.append(
                    block_index
                )

        if uncited_blocks:
            reasons.append(
                "Substantive blocks without citations: "
                f"{uncited_blocks}"
            )


        is_valid = not reasons

        return is_valid, reasons


    def _citations_are_valid(
        self,
        answer: str,
        user_prompt: str,
    ) -> bool:
        """
        Validate answer citations.

        This method intentionally remains a simple boolean API
        so the rest of the pipeline does not need to change.
        """

        valid, reasons = (
            self._citation_validation_details(
                answer=answer,
                user_prompt=user_prompt,
            )
        )

        if not valid:
            print(
                "Citation validation diagnostics:"
            )

            for reason in reasons:
                print(
                    f"  - {reason}"
                )

        return valid


    def _generate_with_client(
        self,
        client: Groq,
        system_prompt: str,
        user_prompt: str,
        max_tokens: Optional[int] = None,
        reasoning_effort: Optional[str] = None,
    ) -> str:
        request = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            "temperature": self.temperature,
            "max_tokens": (
                max_tokens
                if max_tokens is not None
                else self.max_tokens
            ),
        }


        if reasoning_effort:
            request["reasoning_effort"] = (
                reasoning_effort
            )

        response = client.chat.completions.create(
            **request
        )

        if not response.choices:
            raise RuntimeError(
                "LLM returned no choices."
            )

        message = response.choices[0].message

        if message is None:
            raise RuntimeError(
                "LLM returned an empty message."
            )

        answer = self._extract_message_content(
            message
        )

        if not answer:

            # DO NOT expose hidden reasoning to the user.

            finish_reason = getattr(
                response.choices[0],
                "finish_reason",
                None,
            )

            reasoning = getattr(
                message,
                "reasoning",
                None,
            )

            reasoning_length = (
                len(reasoning)
                if isinstance(reasoning, str)
                else 0
            )

            raise RuntimeError(
                "LLM returned an empty visible answer. "
                f"finish_reason={finish_reason}, "
                f"reasoning_length={reasoning_length}"
            )

        answer = self._clean_answer(
            answer
        )

        if not answer:
            raise RuntimeError(
                "LLM returned a whitespace-only answer."
            )

        return answer


    def _repair_citations(
        self,
        client: Groq,
        system_prompt: str,
        user_prompt: str,
        draft_answer: str,
    ) -> str:
        """
        Repair citation coverage while preserving the original
        answer as much as possible.

        The repair model is explicitly prohibited from:
        - rewriting facts
        - adding facts
        - removing facts
        - changing structure
        - summarizing
        - inventing evidence

        It may only insert valid [EVIDENCE N] markers.
        """

        repair_system_prompt = """
You are the citation repair layer of eGovAssist.

Your ONLY task is to add missing [EVIDENCE N] citations to the
supplied draft answer.

DO NOT rewrite the answer.

DO NOT summarize the answer.

DO NOT add facts.

DO NOT remove facts.

DO NOT change facts.

DO NOT change the meaning.

DO NOT change the order of the answer.

DO NOT create new paragraphs.

DO NOT merge paragraphs.

DO NOT create a Sources section.

Preserve the original wording and structure exactly whenever
possible.

You may ONLY insert citation markers.

Valid citation format:

[EVIDENCE 1]

or:

[EVIDENCE 1] [EVIDENCE 3]

IMPORTANT:

Use ONLY evidence numbers that actually occur in the ORIGINAL
GROUNDED REQUEST.

Citation rules:

1. Every substantive factual paragraph/block must contain at
   least one valid citation.

2. Every factual bullet must contain at least one valid citation.

3. Headings do not require citations.

4. If a paragraph contains several factual sentences that are
   supported by the same evidence, one citation at the end of
   that paragraph is sufficient.

5. Put citations at the end of the sentence or factual bullet
   they support.

6. Do not add citations merely to increase citation count.

7. Never invent an evidence number.

8. Never cite nonexistent evidence.

9. Do not explain the repair.

10. Return ONLY the repaired answer.

11. Keep the complete original answer.

12. Never intentionally truncate the answer.

13. Do not replace existing valid citations unless necessary.

IMPORTANT:
The output must contain visible answer text.
Do not return an empty response.
"""

        repair_user_prompt = (
            "ORIGINAL GROUNDED REQUEST:\n"
            f"{user_prompt}\n\n"
            "DRAFT ANSWER TO REPAIR:\n"
            f"{draft_answer}\n\n"
            "TASK:\n"
            "Insert only the missing valid [EVIDENCE N] citation "
            "markers into the draft answer. Preserve all original "
            "wording, facts, structure, paragraph order, and "
            "formatting. Do not add or remove information. "
            "Every substantive factual paragraph or factual bullet "
            "must have at least one valid citation. If an existing "
            "citation already covers a factual paragraph, leave it "
            "alone. Return ONLY the complete repaired answer."
        )


        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": repair_system_prompt,
                },
                {
                    "role": "user",
                    "content": repair_user_prompt,
                },
            ],
            temperature=0,
            max_tokens=REPAIR_MAX_TOKENS,
            reasoning_effort="low",
        )

        if not response.choices:
            raise RuntimeError(
                "Citation repair returned no choices."
            )

        message = response.choices[0].message

        if message is None:
            raise RuntimeError(
                "Citation repair returned an empty message."
            )

        repaired_answer = (
            self._extract_message_content(
                message
            )
        )

        if not repaired_answer:

            finish_reason = getattr(
                response.choices[0],
                "finish_reason",
                None,
            )

            reasoning = getattr(
                message,
                "reasoning",
                None,
            )

            reasoning_length = (
                len(reasoning)
                if isinstance(reasoning, str)
                else 0
            )

            raise RuntimeError(
                "Citation repair returned an empty "
                "visible answer. "
                f"finish_reason={finish_reason}, "
                f"reasoning_length={reasoning_length}"
            )

        repaired_answer = self._clean_answer(
            repaired_answer
        )

        if not repaired_answer:
            raise RuntimeError(
                "Citation repair returned a "
                "whitespace-only answer."
            )

        # We do not silently accept an empty or radically

        if len(repaired_answer.strip()) < 20:
            raise RuntimeError(
                "Citation repair returned an unexpectedly "
                "short answer."
            )

        return repaired_answer


    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> dict:

        system_prompt = system_prompt.strip()
        user_prompt = user_prompt.strip()

        if not system_prompt:
            raise ValueError(
                "System prompt cannot be empty."
            )

        if not user_prompt:
            raise ValueError(
                "User prompt cannot be empty."
            )


        available_evidence = (
            self._extract_evidence_numbers(
                user_prompt
            )
        )

        if not available_evidence:
            raise RuntimeError(
                "No [EVIDENCE N] blocks were found in "
                "the retrieved context."
            )

        print(
            "Available evidence numbers: "
            f"{sorted(available_evidence)}"
        )

        last_error = None


        for index, client in enumerate(
            self.clients,
            start=1,
        ):

            print(
                f"Attempting RAG generation "
                f"with key #{index}..."
            )


            for attempt in range(
                1,
                GENERATION_ATTEMPTS_PER_KEY + 1,
            ):

                print(
                    f"Generation attempt "
                    f"{attempt}/"
                    f"{GENERATION_ATTEMPTS_PER_KEY}..."
                )

                try:


                    answer = self._generate_with_client(
                        client=client,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        max_tokens=self.max_tokens,
                        reasoning_effort="low",
                    )

                    citation_count = (
                        self._citation_count(
                            answer
                        )
                    )

                    print(
                        "Initial answer citation count: "
                        f"{citation_count}"
                    )


                    citations_valid = (
                        self._citations_are_valid(
                            answer=answer,
                            user_prompt=user_prompt,
                        )
                    )

                    if citations_valid:

                        print(
                            "Citation validation successful."
                        )

                    else:

                        print(
                            "Citation validation failed."
                        )

                        print(
                            "Starting citation repair pass..."
                        )


                        try:

                            repaired_answer = (
                                self._repair_citations(
                                    client=client,
                                    system_prompt=system_prompt,
                                    user_prompt=user_prompt,
                                    draft_answer=answer,
                                )
                            )

                        except Exception as repair_error:

                            print(
                                "Citation repair failed:"
                            )

                            print(
                                f"Reason: {repair_error}"
                            )

                            # Do NOT immediately abandon the

                            raise RuntimeError(
                                "Citation repair failed: "
                                f"{repair_error}"
                            )

                        repaired_citation_count = (
                            self._citation_count(
                                repaired_answer
                            )
                        )

                        print(
                            "Repaired answer citation count: "
                            f"{repaired_citation_count}"
                        )


                        repaired_citations = (
                            self._extract_answer_citations(
                                repaired_answer
                            )
                        )

                        invalid_repaired_citations = (
                            repaired_citations
                            - available_evidence
                        )

                        if invalid_repaired_citations:

                            raise RuntimeError(
                                "Citation repair introduced "
                                "invalid evidence numbers: "
                                f"{sorted(invalid_repaired_citations)}"
                            )


                        repaired_valid = (
                            self._citations_are_valid(
                                answer=repaired_answer,
                                user_prompt=user_prompt,
                            )
                        )

                        if not repaired_valid:

                            raise RuntimeError(
                                "Citation repair completed, "
                                "but the resulting answer "
                                "still failed citation "
                                "validation."
                            )

                        answer = repaired_answer

                        print(
                            "Citation repair successful."
                        )


                    print(
                        f"RAG generation with key "
                        f"#{index} successful."
                    )

                    return {
                        "status": "success",
                        "answer": answer,
                        "provider": "groq",
                        "model": self.model,
                    }

                except Exception as error:

                    last_error = error

                    print(
                        f"RAG generation key "
                        f"#{index}, attempt "
                        f"{attempt}/"
                        f"{GENERATION_ATTEMPTS_PER_KEY} "
                        f"failed."
                    )

                    print(
                        f"Reason: {error}"
                    )

                    if (
                        attempt
                        < GENERATION_ATTEMPTS_PER_KEY
                    ):

                        print(
                            "Retrying generation with "
                            f"key #{index}..."
                        )


            if index < len(self.clients):

                print(
                    "Current Groq API key exhausted."
                )

                print(
                    "Trying next Groq API key..."
                )


        raise RuntimeError(
            "All configured Groq API keys failed "
            "during RAG answer generation. "
            f"Last error: {last_error}"
        )


_generator = None


def generate_answer(
    system_prompt: str,
    user_prompt: str,
) -> dict:

    global _generator

    if _generator is None:
        _generator = AnswerGenerator()

    return _generator.generate(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )

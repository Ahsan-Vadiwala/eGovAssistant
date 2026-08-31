
# IMPORTANT:

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)


@dataclass
class SemanticExtractionResult:
    """Structured result of interpreting one user reply."""

    extracted_fields: dict[str, str] = field(default_factory=dict)

    invalid: bool = False

    unrelated: bool = False

    needs_clarification: bool = False


_NUMERIC_HINT_TOKENS = (
    "number",
    "amount",
    "pincode",
    "aadhaar",
    "phone",
    "id",
    "cibil_score",
    "load_required",
    "sum_insured",
    "premium_paid",
)


def _is_numeric_expecting_field(field_name: str) -> bool:
    fl = field_name.lower()
    return any(tok in fl for tok in _NUMERIC_HINT_TOKENS)


_NEGATIVE_PATTERNS = re.compile(
    r"\b(i\s+)?(don'?t|do not)\s+know\b|"
    r"\bnot\s+sure\b|"
    r"\bno\s+idea\b|"
    r"\bunknown\b|"
    r"\bnot\s+applicable\b|"
    r"\bn/?a\b|"
    r"\bcan'?t\s+recall\b|"
    r"\bdo not\s+remember\b|"
    r"\bdon'?t\s+remember\b",
    re.IGNORECASE,
)


_INFORMATIONAL_STARTERS = (
    "what is",
    "what are",
    "how does",
    "how do",
    "how to",
    "explain",
    "tell me about",
    "define",
    "meaning of",
    "who is",
    "why",
)


_CONFIRMATION_WORDS = {
    "yes",
    "yeah",
    "yep",
    "correct",
    "right",
    "ok",
    "okay",
    "confirm",
    "confirmed",
    "proceed",
    "continue",
    "sure",
    "no",
    "nope",
    "wrong",
    "incorrect",
}


def _looks_unrelated(text: str) -> bool:
    stripped = text.strip().rstrip(".!").lower()

    if not stripped:
        return True

    words = stripped.replace(",", " ").split()

    if words and all(w in _CONFIRMATION_WORDS for w in words):
        return True

    if text.strip().endswith("?") and any(
        stripped.startswith(s) for s in _INFORMATIONAL_STARTERS
    ):
        return True

    return False


_WARD_NUMBER_RE = re.compile(
    r"\bward\s*(?:no\.?|number)?\s*[:#\-]?\s*(\d+)\b",
    re.IGNORECASE,
)

_LANDMARK_CUE_RE = re.compile(
    r"\blandmark\s+(?:is|:|-)\s*(.+)",
    re.IGNORECASE,
)

_NEAR_CUE_RE = re.compile(
    r"\b(?:near|nearby|close to)\s+(.+)",
    re.IGNORECASE,
)

_LOCALITY_CUE_RE = re.compile(
    r"\blocality\s+(?:is|:|-)\s*(.+)",
    re.IGNORECASE,
)


def _generic_cue_re(field_name: str) -> re.Pattern:
    alias = field_name.replace("_", " ")
    return re.compile(
        rf"\b{re.escape(alias)}\s+(?:is|:|-)\s*(.+)",
        re.IGNORECASE,
    )


def _split_clauses(text: str) -> list[str]:
    """Split on conjunctions/sentence boundaries, but NOT bare commas.

    Commas are frequently part of a legitimate locality/value such as:
    'Manjalpur, Vadodara'.
    """
    parts = re.split(
        r"\s+and\s+|;\s+|\.\s+",
        text.strip(),
    )

    return [
        p.strip(" .")
        for p in parts
        if p.strip(" .")
    ]


def _clean_value(value: str) -> str:
    return value.strip(" .,")


# IMPORTANT:

_GEMINI_FIELD_PROPERTIES = {
    "ward_number": {
        "type": "string",
        "description": "Ward number, e.g. 'Ward 12'.",
    },
    "locality": {
        "type": "string",
        "description": "Locality or area name.",
    },
    "zone": {
        "type": "string",
        "description": "Municipal zone, if explicitly provided.",
    },
    "landmark": {
        "type": "string",
        "description": "Nearby landmark, if explicitly provided.",
    },
    "person_name": {
        "type": "string",
        "description": "Person's name, only if explicitly provided.",
    },
    "description": {
        "type": "string",
        "description": "Complaint description, only when explicitly requested/appropriate.",
    },
    "address": {
        "type": "string",
        "description": "Address, if explicitly provided.",
    },
    "village": {
        "type": "string",
        "description": "Village name, if explicitly provided.",
    },
    "district": {
        "type": "string",
        "description": "District name, if explicitly provided.",
    },
    "state": {
        "type": "string",
        "description": "State name, if explicitly provided.",
    },
    "pincode": {
        "type": "string",
        "description": "PIN/pincode, if explicitly provided.",
    },
    "phone": {
        "type": "string",
        "description": "Phone number, if explicitly provided.",
    },
}


class GrievanceSemanticExtractor:
    """Semantic extraction/validation layer for the Grievance workflow.

    This class interprets one user reply.

    It NEVER owns workflow transitions and NEVER directly mutates
    grievance state.
    """

    def __init__(self, use_gemini: bool | None = None):
        self.model = os.getenv(
            "GRIEVANCE_GEMINI_MODEL",
            "gemini-3.5-flash-lite",
        )

        api_key = os.getenv("GEMINI_API_KEY")

        self._gemini_enabled = (
            bool(api_key)
            if use_gemini is None
            else bool(use_gemini)
        )

        self._client = None

        if self._gemini_enabled:
            try:
                from google import genai

                self._client = genai.Client(api_key=api_key)

                logger.info(
                    "Grievance semantic extraction: Gemini enabled "
                    "(model=%s)",
                    self.model,
                )

            except Exception:
                logger.exception(
                    "Failed to initialize Gemini for grievance "
                    "semantic extraction; using heuristic fallback."
                )

                self._client = None
                self._gemini_enabled = False

        else:
            logger.info(
                "Grievance semantic extraction: Gemini disabled; "
                "using deterministic heuristic fallback."
            )

        self._cache: dict[
            tuple[str | None, str],
            SemanticExtractionResult,
        ] = {}


    def extract(
        self,
        *,
        current_field: str | None,
        user_message: str,
        known_fields: set[str],
        required_fields: list[str],
        optional_fields: list[str],
        missing_fields: list[str],
        original_complaint: str,
        category: str,
        sub_category: str,
        department: str,
    ) -> SemanticExtractionResult:
        """Interpret user_message using the existing grievance context.

        Does NOT mutate grievance state.
        """

        message = (user_message or "").strip()

        if not message:
            return SemanticExtractionResult(unrelated=True)

        cache_key = (current_field, message)

        if cache_key in self._cache:
            return self._cache[cache_key]

        if _looks_unrelated(message):
            result = SemanticExtractionResult(unrelated=True)
            self._cache[cache_key] = result
            return result

        result: SemanticExtractionResult | None = None


        if self._gemini_enabled and self._client is not None:
            try:
                result = self._extract_via_gemini(
                    current_field=current_field,
                    user_message=message,
                    known_fields=known_fields,
                    required_fields=required_fields,
                    optional_fields=optional_fields,
                    missing_fields=missing_fields,
                    original_complaint=original_complaint,
                    category=category,
                    sub_category=sub_category,
                    department=department,
                )


                if (
                    result is not None
                    and not result.extracted_fields
                    and not result.invalid
                    and not result.unrelated
                ):
                    logger.warning(
                        "Gemini returned no extracted fields for "
                        "current_field=%r; falling back to heuristic.",
                        current_field,
                    )

                    result = None

            except Exception:
                logger.exception(
                    "Gemini grievance extraction failed for "
                    "current_field=%r; falling back to heuristic.",
                    current_field,
                )

                result = None


        if result is None:
            result = self._extract_heuristic(
                current_field=current_field,
                user_message=message,
            )

        logger.debug(
            "Grievance semantic extraction result: "
            "current_field=%r extracted_fields=%r invalid=%s "
            "unrelated=%s needs_clarification=%s",
            current_field,
            result.extracted_fields,
            result.invalid,
            result.unrelated,
            result.needs_clarification,
        )

        self._cache[cache_key] = result

        return result


    def _extract_via_gemini(
        self,
        *,
        current_field: str | None,
        user_message: str,
        known_fields: set[str],
        required_fields: list[str],
        optional_fields: list[str],
        missing_fields: list[str],
        original_complaint: str,
        category: str,
        sub_category: str,
        department: str,
    ) -> SemanticExtractionResult:

        from google.genai import types

        system_prompt = (
            "You are the semantic field-extraction layer of "
            "eGovAssist's Grievance workflow.\n\n"

            "You do NOT control the workflow.\n"
            "You do NOT decide whether a grievance is complete.\n"
            "You do NOT submit a grievance.\n"
            "You only interpret the citizen's latest message and "
            "return structured information that is actually present.\n\n"

            "IMPORTANT:\n"
            "The latest user message is NOT automatically the value "
            "of the currently requested field.\n\n"

            "Analyze the message semantically.\n"
            "Extract only information that is actually present.\n\n"

            "Rules:\n"
            "1. If the user directly provides the requested field, "
            "extract only its value.\n"

            "2. If the user provides additional known information "
            "in the same message, extract those values under their "
            "own field names as well.\n"

            "3. Never copy an entire narrative sentence into a field "
            "when only part of the sentence represents the value.\n"

            "4. Never invent values.\n"

            "5. If the user says they do not know, are unsure, "
            "cannot remember, or otherwise cannot provide a value, "
            "do NOT extract a value for that field.\n"

            "6. If the answer is clearly nonsensical for the requested "
            "field, set invalid=true and do not extract that value.\n"

            "7. If the message is unrelated to the current field, "
            "set unrelated=true.\n"

            "8. Never extract a person's name unless a person's name "
            "is explicitly present.\n"

            "9. Preserve the original complaint. Never rewrite or "
            "replace it with the latest field response.\n"

            "10. Return only structured field values using the allowed "
            "field names.\n"
        )

        user_prompt = json.dumps(
            {
                "original_complaint": original_complaint,
                "category": category,
                "sub_category": sub_category,
                "department": department,
                "required_fields": required_fields,
                "optional_fields": optional_fields,
                "already_collected_fields": sorted(known_fields),
                "missing_fields": missing_fields,
                "current_requested_field": current_field,
                "latest_user_message": user_message,
            },
            ensure_ascii=False,
            indent=2,
        )

        logger.debug(
            "Calling Gemini grievance semantic extraction: "
            "current_field=%r message=%r",
            current_field,
            user_message,
        )

        response = self._client.models.generate_content(
            model=self.model,
            contents=[
                system_prompt,
                user_prompt,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "object",
                    "properties": {
                        "extracted_fields": {
                            "type": "object",
                            "properties": _GEMINI_FIELD_PROPERTIES,
                        },
                        "invalid": {
                            "type": "boolean",
                        },
                        "unrelated": {
                            "type": "boolean",
                        },
                        "needs_clarification": {
                            "type": "boolean",
                        },
                    },
                    "required": [
                        "extracted_fields",
                        "invalid",
                        "unrelated",
                    ],
                },
            ),
        )

        content = response.text

        if not content:
            raise RuntimeError(
                "Gemini returned an empty extraction response."
            )

        data = json.loads(content)

        raw_extracted = data.get("extracted_fields") or {}

        if not isinstance(raw_extracted, dict):
            raise RuntimeError(
                "Gemini returned an invalid extracted_fields object."
            )

        extracted: dict[str, str] = {}

        for key, value in raw_extracted.items():
            if value is None:
                continue

            value_text = str(value).strip()

            if not value_text:
                continue

            extracted[str(key)] = value_text

        logger.debug(
            "Gemini grievance extraction parsed: "
            "current_field=%r extracted_fields=%r invalid=%r "
            "unrelated=%r needs_clarification=%r",
            current_field,
            extracted,
            data.get("invalid", False),
            data.get("unrelated", False),
            data.get("needs_clarification", False),
        )

        return SemanticExtractionResult(
            extracted_fields=extracted,
            invalid=bool(data.get("invalid", False)),
            unrelated=bool(data.get("unrelated", False)),
            needs_clarification=bool(
                data.get("needs_clarification", False)
            ),
        )


    def _extract_heuristic(
        self,
        *,
        current_field: str | None,
        user_message: str,
    ) -> SemanticExtractionResult:

        message = user_message.strip()


        if _NEGATIVE_PATTERNS.search(message):
            return SemanticExtractionResult()

        extracted: dict[str, str] = {}

        clauses = _split_clauses(message)

        if not clauses:
            clauses = [message]

        for clause in clauses:


            if "ward_number" not in extracted:
                ward_match = _WARD_NUMBER_RE.search(clause)

                if ward_match:
                    extracted["ward_number"] = (
                        f"Ward {ward_match.group(1)}"
                    )


            if "landmark" not in extracted:

                landmark_match = _LANDMARK_CUE_RE.search(clause)

                if landmark_match:
                    extracted["landmark"] = _clean_value(
                        landmark_match.group(1)
                    )

                else:
                    near_match = _NEAR_CUE_RE.search(clause)

                    if near_match:
                        extracted["landmark"] = (
                            "Near "
                            + _clean_value(
                                near_match.group(1)
                            )
                        )


            if "locality" not in extracted:

                locality_match = _LOCALITY_CUE_RE.search(clause)

                if locality_match:
                    extracted["locality"] = _clean_value(
                        locality_match.group(1)
                    )


            if current_field and current_field not in extracted:

                generic_match = _generic_cue_re(
                    current_field
                ).search(clause)

                if generic_match:
                    extracted[current_field] = _clean_value(
                        generic_match.group(1)
                    )

        # IMPORTANT:

        if current_field and current_field not in extracted:

            words = message.split()

            starts_narrative = (
                message.lower().split(" ", 1)[0]
                in (
                    "i",
                    "i'm",
                    "we",
                    "we're",
                    "my",
                    "our",
                )
            )

            looks_like_question = (
                message.strip().endswith("?")
            )

            if (
                words
                and len(words) <= 6
                and not starts_narrative
                and not looks_like_question
            ):

                candidate = _clean_value(message)

                if (
                    _is_numeric_expecting_field(current_field)
                    and not any(
                        ch.isdigit()
                        for ch in candidate
                    )
                ):
                    return SemanticExtractionResult(
                        invalid=True
                    )

                if candidate:
                    extracted[current_field] = candidate


        if not extracted:
            return SemanticExtractionResult(
                needs_clarification=True
            )

        return SemanticExtractionResult(
            extracted_fields=extracted
        )


_extractor: GrievanceSemanticExtractor | None = None


def get_semantic_extractor() -> GrievanceSemanticExtractor:
    global _extractor

    if _extractor is None:
        _extractor = GrievanceSemanticExtractor()

    return _extractor

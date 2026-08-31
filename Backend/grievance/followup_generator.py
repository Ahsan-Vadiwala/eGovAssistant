
from __future__ import annotations

from typing import Any

from .models import GrievanceDraft, GrievanceSubCategory
from .field_detector import GrievanceFieldDetector


class GrievanceFollowupGenerator:
    """Generates follow-up questions for missing grievance fields."""

    def __init__(self):
        self.field_detector = GrievanceFieldDetector()

    def generate_questions(
        self,
        draft: GrievanceDraft,
        user_message: str = "",
        max_questions: int = 3,
    ) -> list[str]:
        """Generate follow-up questions for missing fields."""
        missing_required, missing_optional = self.field_detector.detect_missing_fields(
            draft, user_message
        )

        questions = []
        prompts = self.field_detector.get_field_prompts(draft.sub_category)

        for field in missing_required:
            if len(questions) >= max_questions:
                break
            prompt = prompts.get(field, f"Please provide {field.replace('_', ' ')}.")
            questions.append(prompt)

        for field in missing_optional:
            if len(questions) >= max_questions:
                break
            prompt = prompts.get(field, f"Please provide {field.replace('_', ' ')} (optional).")
            questions.append(prompt + " (optional)")

        return questions

    def generate_single_question(
        self,
        draft: GrievanceDraft,
        user_message: str = "",
    ) -> str | None:
        """Generate a single follow-up question."""
        questions = self.generate_questions(draft, user_message, max_questions=1)
        return questions[0] if questions else None

    def format_questions_response(
        self,
        questions: list[str],
        stage: str = "followup",
    ) -> str:
        """Format questions into a user-friendly response."""
        if not questions:
            return ""

        if len(questions) == 1:
            return (
                "To help you better, I need one more detail:\n\n"
                f"❓ {questions[0]}"
            )

        response = (
            "To complete your grievance draft, I need a few more details:\n\n"
        )
        for i, q in enumerate(questions, 1):
            response += f"{i}. {q}\n\n"

        response += (
            "You can answer them one by one or provide multiple details at once."
        )
        return response

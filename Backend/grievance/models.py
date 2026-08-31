
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class GrievanceCategory(str, Enum):
    """Top-level grievance categories."""

    PUBLIC_SERVICE = "public_service"
    POLICE = "police"
    REVENUE = "revenue"
    MUNICIPAL = "municipal"
    ELECTRICITY = "electricity"
    WATER = "water"
    TRANSPORT = "transport"
    HEALTH = "health"
    EDUCATION = "education"
    FOOD_CIVIL_SUPPLIES = "food_civil_supplies"
    SOCIAL_WELFARE = "social_welfare"
    LABOUR = "labour"
    COOPERATIVE = "cooperative"
    AGRICULTURE = "agriculture"
    BANKING = "banking"
    OTHER = "other"


class GrievanceSubCategory(str, Enum):
    """Sub-categories for each main category."""

    RTI_DELAY = "rti_delay"
    CERTIFICATE_DELAY = "certificate_delay"
    PENSION_DELAY = "pension_delay"
    SCHEME_BENEFIT_DENIED = "scheme_benefit_denied"

    FIR_REFUSAL = "fir_refusal"
    HARASSMENT = "harassment"
    INACTION = "inaction"
    CORRUPTION = "corruption"

    LAND_RECORD_ERROR = "land_record_error"
    MUTATION_DELAY = "mutation_delay"
    COMPENSATION_DELAY = "compensation_delay"

    GARBAGE = "garbage"
    DRAINAGE = "drainage"
    STREET_LIGHT = "street_light"
    BUILDING_PERMIT = "building_permit"
    PROPERTY_TAX = "property_tax"
    ROAD_DAMAGE = "road_damage"

    BILLING_DISPUTE = "billing_dispute"
    METER_FAULT = "meter_fault"
    NEW_CONNECTION_DELAY = "new_connection_delay"
    POWER_CUT = "power_cut"

    SUPPLY_ISSUE = "supply_issue"
    QUALITY_ISSUE = "quality_issue"
    BILLING_DISPUTE_WATER = "billing_dispute_water"
    NEW_CONNECTION_DELAY_WATER = "new_connection_delay_water"

    LICENCE_DELAY = "licence_delay"
    PERMIT_ISSUE = "permit_issue"
    BUS_SERVICE = "bus_service"

    HOSPITAL_NEGLIGENCE = "hospital_negligence"
    MEDICINE_SHORTAGE = "medicine_shortage"
    AMBULANCE_DELAY = "ambulance_delay"

    ADMISSION_DENIED = "admission_denied"
    SCHOLARSHIP_DELAY = "scholarship_delay"
    MID_DAY_MEAL = "mid_day_meal"

    RATION_CARD_DELAY = "ration_card_delay"
    QUANTITY_SHORTAGE = "quantity_shortage"
    QUALITY_COMPLAINT = "quality_complaint"

    PENSION_NOT_RECEIVED = "pension_not_received"
    SCHEME_EXCLUSION = "scheme_exclusion"

    WAGE_DISPUTE = "wage_dispute"
    UNFAIR_TERMINATION = "unfair_termination"
    SAFETY_VIOLATION = "safety_violation"

    MEMBER_RIGHTS = "member_rights"
    ELECTION_DISPUTE = "election_dispute"
    FUND_MISUSE = "fund_misuse"

    PMFBY_CLAIM_DELAY = "pmfby_claim_delay"
    SUBSIDY_DELAY = "subsidy_delay"
    SEED_QUALITY = "seed_quality"

    LOAN_REJECTION = "loan_rejection"
    FRAUD = "fraud"
    SERVICE_DEFICIENCY = "service_deficiency"

    OTHER = "other"


class GrievanceStage(str, Enum):
    """Workflow stages."""

    INTAKE = "intake"
    CLASSIFICATION = "classification"
    ENTITY_EXTRACTION = "entity_extraction"
    MISSING_FIELDS = "missing_fields"
    FOLLOWUP = "followup"
    DRAFT_READY = "draft_ready"
    SUBMISSION_GUIDE = "submission_guide"
    STATUS_LOOKUP = "status_lookup"
    COMPLETE = "complete"


@dataclass
class GrievanceEntity:
    """Extracted entity from grievance description."""

    name: str
    value: str
    confidence: float
    source_text: str


@dataclass
class GrievanceDraft:
    """Structured grievance draft."""

    category: GrievanceCategory
    sub_category: GrievanceSubCategory
    title: str
    description: str
    entities: dict[str, GrievanceEntity]
    missing_fields: list[str]
    required_fields: list[str]
    optional_fields: list[str]
    jurisdiction: str
    state: str | None
    department: str
    reference_number: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "sub_category": self.sub_category.value,
            "title": self.title,
            "description": self.description,
            "entities": {k: {
                "name": v.name,
                "value": v.value,
                "confidence": v.confidence,
                "source_text": v.source_text,
            } for k, v in self.entities.items()},
            "missing_fields": self.missing_fields,
            "required_fields": self.required_fields,
            "optional_fields": self.optional_fields,
            "jurisdiction": self.jurisdiction,
            "state": self.state,
            "department": self.department,
            "reference_number": self.reference_number,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GrievanceDraft:
        entities = {}
        for k, v in data.get("entities", {}).items():
            entities[k] = GrievanceEntity(
                name=v["name"],
                value=v["value"],
                confidence=v["confidence"],
                source_text=v["source_text"],
            )
        return cls(
            category=GrievanceCategory(data["category"]),
            sub_category=GrievanceSubCategory(data["sub_category"]),
            title=data["title"],
            description=data["description"],
            entities=entities,
            missing_fields=data.get("missing_fields", []),
            required_fields=data.get("required_fields", []),
            optional_fields=data.get("optional_fields", []),
            jurisdiction=data.get("jurisdiction", "central"),
            state=data.get("state"),
            department=data.get("department", ""),
            reference_number=data.get("reference_number"),
            created_at=data.get("created_at", datetime.now().isoformat()),
        )


@dataclass
class GrievanceTurn:
    """Single turn in grievance conversation."""

    turn_id: int
    user_message: str
    assistant_message: str
    stage: GrievanceStage
    extracted_entities: dict[str, GrievanceEntity] = field(default_factory=dict)
    asked_questions: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class GrievanceState:
    """Multi-turn grievance conversation state."""

    conversation_id: str
    user_id: str
    stage: GrievanceStage = GrievanceStage.INTAKE
    draft: GrievanceDraft | None = None
    turns: list[GrievanceTurn] = field(default_factory=list)
    pending_questions: list[str] = field(default_factory=list)
    answered_questions: dict[str, str] = field(default_factory=dict)
    current_question_index: int = 0
    is_complete: bool = False
    current_field: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "stage": self.stage.value,
            "draft": self.draft.to_dict() if self.draft else None,
            "current_field": self.current_field,
            "turns": [
                {
                    "turn_id": t.turn_id,
                    "user_message": t.user_message,
                    "assistant_message": t.assistant_message,
                    "stage": t.stage.value,
                    "extracted_entities": {k: {
                        "name": v.name,
                        "value": v.value,
                        "confidence": v.confidence,
                        "source_text": v.source_text,
                    } for k, v in t.extracted_entities.items()},
                    "asked_questions": t.asked_questions,
                    "timestamp": t.timestamp,
                }
                for t in self.turns
            ],
            "pending_questions": self.pending_questions,
            "answered_questions": self.answered_questions,
            "current_question_index": self.current_question_index,
            "is_complete": self.is_complete,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GrievanceState:
        draft = None
        if data.get("draft"):
            draft = GrievanceDraft.from_dict(data["draft"])

        turns = []
        for t in data.get("turns", []):
            entities = {}
            for k, v in t.get("extracted_entities", {}).items():
                entities[k] = GrievanceEntity(
                    name=v["name"],
                    value=v["value"],
                    confidence=v["confidence"],
                    source_text=v["source_text"],
                )
            turns.append(GrievanceTurn(
                turn_id=t["turn_id"],
                user_message=t["user_message"],
                assistant_message=t["assistant_message"],
                stage=GrievanceStage(t["stage"]),
                extracted_entities=entities,
                asked_questions=t.get("asked_questions", []),
                timestamp=t.get("timestamp", datetime.now().isoformat()),
            ))

        return cls(
            conversation_id=data["conversation_id"],
            user_id=data["user_id"],
            stage=GrievanceStage(data.get("stage", "intake")),
            draft=draft,
            turns=turns,
            pending_questions=data.get("pending_questions", []),
            answered_questions=data.get("answered_questions", {}),
            current_question_index=data.get("current_question_index", 0),
            is_complete=data.get("is_complete", False),
            current_field=data.get("current_field"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )


@dataclass
class SubmissionRoute:
    """Official submission route reference (prototype)."""

    portal_name: str
    portal_url: str
    department: str
    level: str  # "central", "state", "district", "local"
    steps: list[str]
    required_documents: list[str]
    estimated_timeline: str
    disclaimer: str = (
        "This is a prototype reference. eGovAssistant does NOT submit "
        "grievances on your behalf. Please visit the official portal directly."
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "portal_name": self.portal_name,
            "portal_url": self.portal_url,
            "department": self.department,
            "level": self.level,
            "steps": self.steps,
            "required_documents": self.required_documents,
            "estimated_timeline": self.estimated_timeline,
            "disclaimer": self.disclaimer,
        }


@dataclass
class StatusLookupResult:
    """Status lookup guidance (prototype)."""

    portal_name: str
    portal_url: str
    lookup_method: str  # "reference_number", "mobile_otp", "captcha"
    required_fields: list[str]
    disclaimer: str = (
        "This is a prototype reference. eGovAssistant does NOT access "
        "live government systems. Please use the official portal directly."
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "portal_name": self.portal_name,
            "portal_url": self.portal_url,
            "lookup_method": self.lookup_method,
            "required_fields": self.required_fields,
            "disclaimer": self.disclaimer,
        }

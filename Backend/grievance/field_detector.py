
from __future__ import annotations

from typing import Any

from .models import GrievanceDraft, GrievanceEntity, GrievanceSubCategory
from .entity_extractor import GrievanceEntityExtractor


_PERSON_NAME_TOKENS = (
    "complainant", "applicant", "consumer", "pensioner", "owner",
    "beneficiary", "account_holder", "student", "parent", "candidate",
    "member", "employee", "farmer", "patient", "doctor", "land_owner",
)

_LOCATION_FIELDS = {
    "district": {"district_name"},
    "tehsil": {"tehsil_name"},
    "taluk": {"taluk_name"},
    "village": {"village_name"},
    "area": {"area_name"},
    "locality": {"locality_name", "colony_name", "area_name"},
    "ward_number": {"ward_name"},
    "block": {"block_name"},
    "zone": {"sector_name"},
    "location": {
        "district_name", "tehsil_name", "taluk_name", "village_name",
        "area_name", "locality_name", "ward_name", "block_name",
        "colony_name", "city_name", "sector_name",
    },
}

_REFERENCE_FIELDS = {
    "application_number", "application_id", "reference_number",
    "complaint_number", "ppo_number", "registration_number", "member_id",
    "survey_number", "khata_number", "patta_number", "lot_number",
    "transaction_id", "rti_application_number", "learner_licence_number",
    "account_number", "fps_code", "property_id", "case_number",
}

_AMOUNT_FIELDS = {
    "disputed_amount", "amount_involved", "award_amount", "loan_amount",
    "amount_claimed", "sum_insured", "premium_paid",
    "compensation_claimed", "amount",
}

_LOCATION_ENTITY_KEYS = {
    "district_name", "tehsil_name", "taluk_name", "village_name",
    "area_name", "locality_name", "ward_name", "block_name",
    "colony_name", "city_name", "sector_name",
}


def is_field_satisfied(
    field: str,
    extracted_keys: set[str],
    draft: GrievanceDraft,
) -> bool:
    """
    Determine whether a required/optional field is effectively
    covered by what has already been extracted.

    The entity extractor produces generic entity types (e.g. "date",
    "person_name", "reference_number") while each grievance sub-category
    defines its own specific field names (e.g. "date_of_incident",
    "complainant_name", "application_number"). This helper bridges the
    two so the workflow doesn't get stuck asking for information that
    has, in substance, already been provided.
    """
    if field in extracted_keys:
        return True

    fl = field.lower()

    if fl.endswith("_description") or fl == "description":
        return bool(draft.description and draft.description.strip())

    if "date" in fl or fl in {"billing_month", "month_not_received", "period"}:
        return "date" in extracted_keys

    if fl.endswith("_name") and any(tok in fl for tok in _PERSON_NAME_TOKENS):
        return "person_name" in extracted_keys

    if fl == "police_station":
        if "police_station_name" in extracted_keys:
            return True
        return "police station" in (draft.description or "").lower()

    if fl.endswith("_name") or fl in {"municipality", "insurance_company"}:
        if any(k.endswith("_name") for k in extracted_keys):
            return True
        return bool(draft.department)

    if fl in _LOCATION_FIELDS:
        return bool(extracted_keys & _LOCATION_FIELDS[fl])

    if fl in _REFERENCE_FIELDS:
        return bool(extracted_keys & {"reference_number", "account_number"})

    if fl in _AMOUNT_FIELDS:
        return "amount" in extracted_keys

    return False


class GrievanceFieldDetector:
    """Detects missing required fields in grievance draft."""

    def __init__(self):
        self.entity_extractor = GrievanceEntityExtractor()

    def detect_missing_fields(
        self,
        draft: GrievanceDraft,
        user_message: str = "",
    ) -> tuple[list[str], list[str]]:
        """
        Detect missing required and optional fields.

        Returns:
            tuple: (missing_required, missing_optional)
        """
        required_fields = self.entity_extractor.get_required_fields(draft.sub_category)
        optional_fields = self.entity_extractor.get_optional_fields(draft.sub_category)

        extracted_keys = set(draft.entities.keys())

        if user_message:
            new_extractions = self.entity_extractor.extract(user_message, draft.sub_category)
            extracted_keys.update(new_extractions.entities.keys())

        missing_required = [
            f for f in required_fields
            if not is_field_satisfied(f, extracted_keys, draft)
        ]
        missing_optional = [
            f for f in optional_fields
            if not is_field_satisfied(f, extracted_keys, draft)
        ]

        return missing_required, missing_optional

    def get_field_prompts(self, sub_category: GrievanceSubCategory) -> dict[str, str]:
        """Get user-friendly prompts for each field."""
        prompts = {
            "rti_application_number": "What is your RTI application number?",
            "date_of_application": "When did you submit the application? (date)",
            "department": "Which government department/office is this regarding?",
            "applicant_name": "What is the applicant's full name?",
            "address": "What is the complete address?",
            "phone": "What is the contact phone number?",
            "email": "What is the email address?",

            "certificate_type": "What type of certificate? (caste, income, domicile, birth, death, etc.)",
            "application_number": "What is the application/reference number?",
            "issuing_authority": "Which office/department issues this certificate?",

            "pension_type": "What type of pension? (old age, widow, disability, etc.)",
            "ppo_number": "What is the PPO (Pension Payment Order) number?",
            "bank_account": "What is the bank account number?",
            "bank_name": "What is the bank name?",
            "pensioner_name": "What is the pensioner's name?",
            "aadhaar": "What is the Aadhaar number?",

            "scheme_name": "What is the name of the government scheme?",
            "application_id": "What is the application/registration ID?",
            "beneficiary_name": "What is the beneficiary's name?",

            "police_station": "Which police station?",
            "date_of_incident": "When did the incident occur? (date)",
            "incident_description": "Please describe what happened.",
            "complainant_name": "What is your full name?",
            "accused_details": "Do you have details of the accused person(s)?",
            "witnesses": "Are there any witnesses?",
            "evidence": "Do you have any evidence (photos, documents, etc.)?",
            "complaint_number": "What is the complaint/diary number?",
            "followup_dates": "When did you follow up?",
            "officer_name": "What is the officer's name/designation?",
            "officer_details": "Can you describe the officer (name, rank, badge number)?",
            "medical_report": "Is there a medical report?",

            "district": "Which district?",
            "tehsil": "Which tehsil/taluk?",
            "village": "Which village?",
            "survey_number": "What is the survey/khasra number?",
            "error_description": "What is the error in the land record?",
            "owner_name": "What is the owner's name?",
            "khata_number": "What is the khata number?",
            "patta_number": "What is the patta number?",
            "document_reference": "Any document reference number?",
            "previous_owner": "Who was the previous owner?",
            "mutation_type": "What type of mutation? (inheritance, sale, gift, etc.)",
            "project_name": "What is the project name (for land acquisition)?",
            "award_amount": "What is the compensation award amount?",
            "land_owner_name": "What is the land owner's name?",
            "award_date": "What is the award date?",

            "ward_number": "What is the ward number?",
            "locality": "What is the locality/area name?",
            "issue_description": "Please describe the issue.",
            "municipality": "Which municipality/corporation?",
            "zone": "Which zone?",
            "landmark": "Any nearby landmark?",
            "photos": "Do you have photos of the issue?",
            "plot_number": "What is the plot number?",
            "building_type": "What type of building? (residential, commercial, etc.)",
            "architect_name": "Architect/engineer name?",
            "property_id": "What is the property ID/assessment number?",
            "assessment_year": "Which assessment year?",
            "amount_paid": "How much have you paid?",
            "payment_date": "When did you pay?",

            "consumer_number": "What is your consumer/account number?",
            "billing_month": "Which billing month is this for? (e.g., January 2024)",
            "disputed_amount": "What is the disputed amount?",
            "discom_name": "Which electricity distribution company (DISCOM)?",
            "consumer_name": "Consumer name on the bill?",
            "meter_number": "What is the meter number?",
            "previous_bill_amount": "What was the previous bill amount?",
            "fault_description": "Describe the meter fault.",
            "date_noticed": "When did you first notice this?",
            "connection_type": "What type of connection? (domestic, commercial, agricultural, industrial)",
            "load_required": "What is the required load (kW)?",
            "category": "What category? (BPL, APL, etc.)",
            "area": "Which area/locality?",
            "frequency": "How frequent are the power cuts? (daily, weekly, etc.)",
            "duration": "How long does each power cut last?",
            "feeder_name": "Do you know the feeder name?",
            "complaint_number": "Any previous complaint number?",

            "water_board_name": "Which water board/supply authority?",
            "quality_description": "Describe the water quality issue (color, smell, taste).",
            "lab_report": "Do you have a lab report?",
            "timing": "What time does supply usually come?",

            "rto_office": "Which RTO office?",
            "licence_type": "What type of licence? (learner, permanent, renewal, etc.)",
            "learner_licence_number": "What is the learner licence number?",
            "test_date": "When was/will be the driving test?",
            "vehicle_number": "What is the vehicle registration number?",
            "permit_type": "What type of permit?",
            "owner_name": "Vehicle owner's name?",
            "vehicle_type": "Vehicle type? (goods, passenger, etc.)",
            "route": "Route/permit area?",
            "depot": "Which bus depot?",
            "route_number": "Which route number?",
            "date_time": "Date and time of the issue?",
            "bus_number": "Bus number (if known)?",
            "driver_conductor_details": "Driver/conductor details?",
            "ticket_number": "Ticket number?",

            "hospital_name": "Which hospital/health center?",
            "patient_name": "Patient's name?",
            "doctor_name": "Doctor's name?",
            "medical_records": "Do you have medical records/reports?",
            "medicine_name": "Which medicine is unavailable?",
            "prescription": "Do you have a prescription?",
            "alternative_suggested": "Was any alternative suggested?",
            "ambulance_number_or_service": "Ambulance number or service (108, 102, private)?",
            "pickup_location": "Pickup location?",
            "destination": "Destination hospital?",
            "call_number": "Call reference number?",
            "response_time": "How long did it take?",

            "school_name": "Which school/college?",
            "class_applied": "Which class/grade?",
            "reason_given": "What reason was given for denial?",
            "student_name": "Student's name?",
            "parent_name": "Parent/guardian name?",
            "rte_category": "RTE category? (EWS, DG, CWSN, etc.)",
            "institute_name": "Institute name?",
            "academic_year": "Academic year?",
            "course": "Course name?",
            "class": "Class/standard?",
            "meal_type": "Meal type? (breakfast, lunch)",

            "card_type": "What type of ration card? (APL, BPL, AAY, PHH)",
            "family_members": "Number of family members on card?",
            "fps_code": "Fair Price Shop (FPS) code?",
            "fps_name": "FPS dealer name/shop name?",
            "commodity": "Which commodity? (wheat, rice, sugar, kerosene, etc.)",
            "entitled_quantity": "What is your entitled quantity?",
            "received_quantity": "What quantity did you receive?",
            "ration_card_number": "Ration card number?",
            "beneficiary_name": "Beneficiary name on card?",
            "dealer_name": "Dealer name?",
            "quality_issue": "Describe the quality issue.",
            "sample_available": "Do you have a sample?",

            "month_not_received": "Which month's pension not received?",
            "reason_for_exclusion": "What reason was given for exclusion?",
            "category": "Category? (SC, ST, OBC, General, etc.)",
            "income_certificate": "Do you have income certificate?",

            "employer_name": "Employer/company name?",
            "employee_name": "Employee name?",
            "period": "For which period? (month/year)",
            "amount_claimed": "Amount claimed?",
            "wage_type": "Type of wages? (basic, overtime, bonus, etc.)",
            "employer_address": "Employer address?",
            "pf_number": "PF account number?",
            "esi_number": "ESI number?",
            "appointment_letter": "Do you have appointment letter?",
            "date_of_termination": "Date of termination?",
            "notice_period": "Notice period given?",
            "compensation_claimed": "Compensation amount claimed?",
            "factory_name": "Factory/establishment name?",
            "location": "Location of factory?",
            "violation_description": "Describe the safety violation.",
            "injury_details": "Any injury details?",
            "inspection_report": "Any inspection report?",

            "society_name": "Cooperative society name?",
            "registration_number": "Society registration number?",
            "member_id": "Your member ID?",
            "member_name": "Member name?",
            "share_amount": "Share capital amount?",
            "dividend_due": "Dividend amount due?",
            "meeting_date": "Meeting date?",
            "election_date": "Election date?",
            "dispute_description": "Describe the election dispute.",
            "candidate_name": "Candidate name?",
            "voter_id": "Voter ID?",
            "returning_officer": "Returning officer name?",
            "accused_office_bearer": "Accused office bearer name/position?",
            "period": "Period of alleged misuse?",
            "audit_report": "Any audit report?",
            "amount_involved": "Amount involved?",

            "farmer_name": "Farmer's name?",
            "crop": "Crop name?",
            "season": "Season? (Kharif, Rabi, Summer)",
            "year": "Crop year?",
            "insurance_company": "Insurance company name?",
            "survey_number": "Survey number?",
            "block": "Block name?",
            "sum_insured": "Sum insured amount?",
            "premium_paid": "Premium paid?",
            "component": "Subsidy component?",
            "seed_name": "Seed name?",
            "variety": "Variety?",
            "lot_number": "Lot/batch number?",
            "dealer_name": "Dealer/shop name?",
            "purchase_date": "Purchase date?",
            "bill_number": "Bill/invoice number?",
            "certification_agency": "Certification agency?",

            "branch": "Bank branch name?",
            "loan_type": "Loan type? (home, personal, vehicle, agriculture, etc.)",
            "rejection_reason": "Reason given for rejection?",
            "loan_amount": "Loan amount applied for?",
            "cibil_score": "CIBIL score?",
            "income_proof": "Income proof submitted?",
            "account_number": "Bank account number?",
            "transaction_date": "Transaction date?",
            "amount": "Transaction amount?",
            "fraud_type": "Type of fraud? (UPI, card, net banking, ATM, etc.)",
            "account_holder_name": "Account holder name?",
            "transaction_id": "Transaction ID/reference?",
            "merchant_name": "Merchant name?",
            "police_complaint": "Police complaint filed?",
            "service_type": "Service type? (account, loan, card, locker, etc.)",
            "reference_number": "Reference/complaint number?",
            "officer_name": "Bank officer name?",
        }

        all_fields = self.entity_extractor.get_all_fields(sub_category)
        return {field: prompts.get(field, f"Please provide {field.replace('_', ' ')}.") for field in all_fields}

    def get_next_missing_field(
        self,
        draft: GrievanceDraft,
        user_message: str = "",
    ) -> str | None:
        """Get the field key (not the prompt text) for the next missing
        required field, or None if none are missing. Used by the workflow
        to track exactly which field an upcoming user answer should be
        mapped to (one-field-at-a-time, context-aware extraction)."""
        missing_required, _ = self.detect_missing_fields(draft, user_message)
        return missing_required[0] if missing_required else None

    def get_next_missing_field_prompt(
        self,
        draft: GrievanceDraft,
        user_message: str = "",
    ) -> str | None:
        """Get prompt for the next missing required field."""
        missing_required, _ = self.detect_missing_fields(draft, user_message)
        if not missing_required:
            return None

        field = missing_required[0]
        prompts = self.get_field_prompts(draft.sub_category)
        return prompts.get(field, f"Please provide {field.replace('_', ' ')}.")

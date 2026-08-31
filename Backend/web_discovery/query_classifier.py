"""
Deterministic query classification for the MVP.

This module does NOT generate answers.

It determines:
- domain
- jurisdiction
- state
- intent

Supported domains:
- cooperative
- pacs
- schemes
- pmfby
- agriculture
- finlit
- grievance
- driving_licence

Supported intents:
- INFORMATIONAL
- ELIGIBILITY
- APPLICATION
- REGISTRATION
- DOCUMENT_REQUIREMENTS
- BENEFIT
- SUBSIDY_AMOUNT
- DEADLINE
- STATUS
- GRIEVANCE
- CONTACT
- SERVICE_ACCESS
- LOCATION
- COMPARISON
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class QueryClassification:

    domain: str
    jurisdiction: str
    state: str | None
    intent: str
    confidence: float


DOMAIN_KEYWORDS = {

    "pmfby": [
        "pmfby",
        "fasal bima",
        "crop insurance",
        "pradhan mantri fasal bima",
        "crop insurance scheme",
    ],

    "pacs": [
        "pacs",
        "primary agricultural credit society",
        "primary agriculture credit society",
    ],

    "cooperative": [
        "cooperative",
        "co-operative",
        "cooperative society",
        "cooperative law",
        "bylaws",
        "by-laws",
        "member rights",
        "society registration",
    ],

    "schemes": [
        "scheme",
        "yojana",
        "ministry of cooperation",
        "government scheme",
        "subsidy",
        "benefit",
        "eligibility",
        "apply for",
        "apply to",
        "applicant",
        "beneficiary",
        "government program",
        "government programme",
        "portal",
        "registration for",
    ],

    "agriculture": [
        "farmer",
        "agriculture",
        "agricultural",
        "crop",
        "cultivation",
        "fertilizer",
        "irrigation",
        "kisan",
    ],

    "finlit": [
        "financial literacy",
        "loan",
        "credit",
        "interest",
        "banking",
        "savings",
        "financial",
        "account",
    ],

    "grievance": [
        "grievance",
        "complaint",
        "complain",
        "appeal",
        "dispute",
        "redressal",
        "redress",
    ],

    "driving_licence": [
        "driving licence",
        "driving license",
        "learner licence",
        "learner license",
        "learner's licence",
        "learner's license",
        "driving licence application",
        "rto",
        "motor vehicle",
        "driving test",
    ],
}


INTENT_KEYWORDS = {
    "INFORMATIONAL": [
        "what is",
        "who is",
        "history",
        "overview",
        "about",
        "definition",
        "explain",
        "details",
        "information",
        "tell me about",
    ],
    "ELIGIBILITY": [
        "eligible",
        "eligibility",
        "qualify",
        "qualification",
        "who can",
        "requirements for",
        "criteria",
    ],
    "APPLICATION": [
        "apply",
        "application",
        "how to apply",
        "application process",
        "fill out",
        "submit application",
    ],
    "REGISTRATION": [
        "register",
        "registration",
        "how to register",
        "sign up",
        "enroll",
        "enrollment",
    ],
    "DOCUMENT_REQUIREMENTS": [
        "documents required",
        "what documents",
        "paperwork",
        "forms needed",
        "required documents",
    ],
    "BENEFIT": [
        "benefit",
        "benefits",
        "what do i get",
        "advantages",
        "help",
        "assistance",
    ],
    "SUBSIDY_AMOUNT": [
        "subsidy amount",
        "how much",
        "amount",
        "value",
        "sum",
        "financial aid",
        "money",
    ],
    "DEADLINE": [
        "deadline",
        "last date",
        "due date",
        "when to apply",
        "closing date",
        "time limit",
    ],
    "STATUS": [
        "status",
        "track",
        "check status",
        "application status",
        "progress",
    ],
    "GRIEVANCE": [
        "grievance",
        "complaint",
        "complain",
        "appeal",
        "dispute",
        "redressal",
        "redress",
    ],
    "CONTACT": [
        "contact",
        "phone number",
        "email",
        "address",
        "helpline",
        "customer care",
    ],
    "SERVICE_ACCESS": [
        "access",
        "how to access",
        "use the service",
        "avail",
        "availment",
    ],
    "LOCATION": [
        "where",
        "location",
        "nearest",
        "near me",
        "address",
        "branch",
        "office",
    ],
    "COMPARISON": [
        "compare",
        "difference",
        "vs",
        "versus",
        "better",
        "which is better",
    ],
}


STATE_KEYWORDS = {

    "andhra pradesh": "Andhra Pradesh",
    "arunachal pradesh": "Arunachal Pradesh",
    "assam": "Assam",
    "bihar": "Bihar",
    "chhattisgarh": "Chhattisgarh",
    "goa": "Goa",
    "gujarat": "Gujarat",
    "haryana": "Haryana",
    "himachal pradesh": "Himachal Pradesh",
    "jharkhand": "Jharkhand",
    "karnataka": "Karnataka",
    "kerala": "Kerala",
    "madhya pradesh": "Madhya Pradesh",
    "maharashtra": "Maharashtra",
    "manipur": "Manipur",
    "meghalaya": "Meghalaya",
    "mizoram": "Mizoram",
    "nagaland": "Nagaland",
    "odisha": "Odisha",
    "punjab": "Punjab",
    "rajasthan": "Rajasthan",
    "sikkim": "Sikkim",
    "tamil nadu": "Tamil Nadu",
    "telangana": "Telangana",
    "tripura": "Tripura",
    "uttar pradesh": "Uttar Pradesh",
    "uttarakhand": "Uttarakhand",
    "west bengal": "West Bengal",
}


class QueryClassifier:

    def classify(
        self, query: str,
    ) -> QueryClassification:

        text = query.lower().strip()

        if not text:

            raise ValueError(
                "Query cannot be empty."
            )

        domain_scores = {}
        for domain, keywords in DOMAIN_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword in text:
                    score += 1
            if score:
                domain_scores[domain] = score

        if domain_scores:
            domain = max(
                domain_scores,
                key=domain_scores.get,
            )
            highest_score = domain_scores[domain]
            confidence = min(
                1.0,
                0.55 + (
                    highest_score * 0.1
                ),
            )
        else:
            domain = "general"
            confidence = 0.25

        intent_scores = {}
        for intent, keywords in INTENT_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword in text:
                    score += 1
            if score:
                intent_scores[intent] = score

        if intent_scores:
            intent = max(
                intent_scores,
                key=intent_scores.get,
            )
        else:
            intent = "INFORMATIONAL"  # default intent

        state = None
        for keyword, state_name in (
            STATE_KEYWORDS.items()
        ):
            if keyword in text:
                state = state_name
                break

        if state:
            jurisdiction = "state"
        else:
            jurisdiction = "central"

        return QueryClassification(
            domain=domain,
            jurisdiction=jurisdiction,
            state=state,
            intent=intent,
            confidence=round(
                confidence,
                2,
            ),
        )

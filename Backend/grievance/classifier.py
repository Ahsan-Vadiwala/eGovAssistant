
from __future__ import annotations

from dataclasses import dataclass

from .models import GrievanceCategory, GrievanceSubCategory


@dataclass
class GrievanceClassification:
    """Result of grievance classification."""

    category: GrievanceCategory
    sub_category: GrievanceSubCategory
    confidence: float
    matched_keywords: list[str]


CATEGORY_KEYWORDS = {
    GrievanceCategory.PUBLIC_SERVICE: [
        "public service", "government service", "civil service",
        "rti", "right to information", "certificate", "pension",
        "scheme benefit", "benefit denied", "government scheme",
    ],
    GrievanceCategory.POLICE: [
        "police", "fir", "first information report", "police station",
        "harassment", "inaction", "corruption", "bribe",
        "custody", "arrest", "police complaint",
    ],
    GrievanceCategory.REVENUE: [
        "revenue", "land record", "mutation", "khata", "patta",
        "compensation", "land acquisition", "revenue department",
        "tehsil", "taluk", "land dispute",
    ],
    GrievanceCategory.MUNICIPAL: [
        "municipal", "municipality", "corporation", "nagar nigam",
        "garbage", "drainage", "sewage", "street light",
        "building permit", "property tax", "house tax",
        "water logging", "road", "footpath",
    ],
    GrievanceCategory.ELECTRICITY: [
        "electricity", "electric", "power", "discom", "billing",
        "meter", "connection", "power cut", "load shedding",
        "transformer", "voltage", "electric bill",
    ],
    GrievanceCategory.WATER: [
        "water supply", "water connection", "water bill",
        "water quality", "drinking water", "pipe", "leakage",
        "sewage", "drainage", "jal board", "jal nigam",
    ],
    GrievanceCategory.TRANSPORT: [
        "transport", "rto", "driving licence", "license",
        "vehicle", "permit", "bus", "road tax", "registration",
        "learner", "driving test",
    ],
    GrievanceCategory.HEALTH: [
        "health", "hospital", "doctor", "medicine", "ambulance",
        "negligence", "treatment", "medical", "health centre",
        "phc", "chc", "ayushman",
    ],
    GrievanceCategory.EDUCATION: [
        "education", "school", "college", "admission", "scholarship",
        "mid day meal", "teacher", "fee", "rte", "right to education",
        "university", "exam",
    ],
    GrievanceCategory.FOOD_CIVIL_SUPPLIES: [
        "ration", "ration card", "fair price shop", "fps",
        "food supply", "civil supply", "pdS", "public distribution",
        "wheat", "rice", "sugar", "kerosene",
    ],
    GrievanceCategory.SOCIAL_WELFARE: [
        "pension", "old age", "widow", "disability",
        "social welfare", "scheme", "benefit", "exclusion",
        "anganwadi", "icds",
    ],
    GrievanceCategory.LABOUR: [
        "labour", "labor", "wage", "salary", "termination",
        "factory", "industrial", "safety", "provident fund",
        "pf", "esi", "bonus", "overtime",
    ],
    GrievanceCategory.COOPERATIVE: [
        "cooperative", "co-operative", "society", "pacs",
        "member", "election", "fund", "misuse", "bylaws",
        "by-laws", "registrar",
    ],
    GrievanceCategory.AGRICULTURE: [
        "agriculture", "farmer", "crop", "pmfby", "fasal bima",
        "insurance", "claim", "subsidy", "seed", "fertilizer",
        "kisan", "krishi",
    ],
    GrievanceCategory.BANKING: [
        "bank", "loan", "credit", "fraud", "atm", "account",
        "transaction", "interest", "emi", "cibil", "npa",
        "banking ombudsman",
    ],
}


SUBCATEGORY_KEYWORDS = {
    GrievanceSubCategory.RTI_DELAY: ["rti", "right to information", "information request"],
    GrievanceSubCategory.CERTIFICATE_DELAY: ["certificate", "caste certificate", "income certificate", "domicile", "birth certificate", "death certificate"],
    GrievanceSubCategory.PENSION_DELAY: ["pension", "old age pension", "retirement pension"],
    GrievanceSubCategory.SCHEME_BENEFIT_DENIED: ["scheme benefit", "benefit denied", "not received benefit"],

    GrievanceSubCategory.FIR_REFUSAL: ["fir refusal", "refused to file fir", "police not registering", "refused to register fir", "not filing fir", "denied fir", "refused to file", "refuse to file", "refuse to register", "not registering fir", "refused to lodge", "refuse to lodge"],
    GrievanceSubCategory.HARASSMENT: ["harassment", "harassed", "threatening", "abuse"],
    GrievanceSubCategory.INACTION: ["inaction", "not acting", "no action", "ignoring"],
    GrievanceSubCategory.CORRUPTION: ["corruption", "bribe", "bribery", "corrupt"],

    GrievanceSubCategory.LAND_RECORD_ERROR: ["land record", "khata", "patta", "record error", "wrong entry"],
    GrievanceSubCategory.MUTATION_DELAY: ["mutation", "dakhil kharij", "transfer of title"],
    GrievanceSubCategory.COMPENSATION_DELAY: ["compensation", "land acquisition", "rehabilitation"],

    GrievanceSubCategory.GARBAGE: ["garbage", "waste", "trash", "dustbin", "cleanliness"],
    GrievanceSubCategory.DRAINAGE: ["drainage", "sewage", "drain", "water logging", "flooding"],
    GrievanceSubCategory.STREET_LIGHT: ["street light", "streetlight", "lamp post", "dark street"],
    GrievanceSubCategory.BUILDING_PERMIT: ["building permit", "construction permit", "building plan", "approval"],
    GrievanceSubCategory.PROPERTY_TAX: ["property tax", "house tax", "municipal tax"],
    GrievanceSubCategory.ROAD_DAMAGE: ["damaged road", "road damage", "pothole", "potholes", "broken road", "road repair", "bad road condition", "road condition", "footpath damage", "broken footpath", "road maintenance", "cracked road", "uneven road"],

    GrievanceSubCategory.BILLING_DISPUTE: ["billing", "bill", "wrong bill", "excess bill", "meter reading"],
    GrievanceSubCategory.METER_FAULT: ["meter fault", "meter not working", "defective meter", "meter burnt"],
    GrievanceSubCategory.NEW_CONNECTION_DELAY: ["new connection", "connection delay", "apply connection"],
    GrievanceSubCategory.POWER_CUT: ["power cut", "load shedding", "no electricity", "outage"],

    GrievanceSubCategory.SUPPLY_ISSUE: ["water supply", "no water", "irregular supply", "low pressure"],
    GrievanceSubCategory.QUALITY_ISSUE: ["water quality", "dirty water", "smell", "taste", "contaminated"],
    GrievanceSubCategory.BILLING_DISPUTE_WATER: ["water bill", "water billing"],
    GrievanceSubCategory.NEW_CONNECTION_DELAY_WATER: ["water connection", "new water connection"],

    GrievanceSubCategory.LICENCE_DELAY: ["driving licence", "driving license", "licence delay", "license delay", "learner licence"],
    GrievanceSubCategory.PERMIT_ISSUE: ["permit", "vehicle permit", "goods permit"],
    GrievanceSubCategory.BUS_SERVICE: ["bus", "bus service", "transport service"],

    GrievanceSubCategory.HOSPITAL_NEGLIGENCE: ["hospital negligence", "medical negligence", "doctor negligence", "wrong treatment"],
    GrievanceSubCategory.MEDICINE_SHORTAGE: ["medicine shortage", "no medicine", "drug shortage"],
    GrievanceSubCategory.AMBULANCE_DELAY: ["ambulance", "ambulance delay", "108", "emergency vehicle"],

    GrievanceSubCategory.ADMISSION_DENIED: ["admission denied", "not admitted", "refused admission", "rte admission"],
    GrievanceSubCategory.SCHOLARSHIP_DELAY: ["scholarship", "scholarship delay", "not received scholarship"],
    GrievanceSubCategory.MID_DAY_MEAL: ["mid day meal", "midday meal", "school meal"],

    GrievanceSubCategory.RATION_CARD_DELAY: ["ration card", "new ration card", "ration card delay"],
    GrievanceSubCategory.QUANTITY_SHORTAGE: ["quantity", "less quantity", "short weight", "shortage", "giving less", "less than entitled", "short supply", "underweight"],
    GrievanceSubCategory.QUALITY_COMPLAINT: ["quality", "bad quality", "rotten", "adulterated"],

    GrievanceSubCategory.PENSION_NOT_RECEIVED: ["pension not received", "pension stopped", "delayed pension"],
    GrievanceSubCategory.SCHEME_EXCLUSION: ["excluded", "not included", "left out", "denied scheme"],

    GrievanceSubCategory.WAGE_DISPUTE: ["wage", "salary", "unpaid", "minimum wage", "overtime pay"],
    GrievanceSubCategory.UNFAIR_TERMINATION: ["termination", "fired", "dismissed", "sacked", "laid off"],
    GrievanceSubCategory.SAFETY_VIOLATION: ["safety", "unsafe", "accident", "hazard", "protection"],

    GrievanceSubCategory.MEMBER_RIGHTS: ["member rights", "voting rights", "dividend", "share"],
    GrievanceSubCategory.ELECTION_DISPUTE: ["election", "voting", "cooperative election"],
    GrievanceSubCategory.FUND_MISUSE: ["fund misuse", "embezzlement", "misappropriation", "fraud"],

    GrievanceSubCategory.PMFBY_CLAIM_DELAY: ["pmfby", "fasal bima", "crop insurance", "claim delay", "insurance claim"],
    GrievanceSubCategory.SUBSIDY_DELAY: ["subsidy", "subsidy delay", "not received subsidy"],
    GrievanceSubCategory.SEED_QUALITY: ["seed quality", "bad seed", "fake seed", "spurious seed"],

    GrievanceSubCategory.LOAN_REJECTION: ["loan rejected", "loan denied", "loan refusal", "rejected my loan", "rejected the loan", "rejected my home loan", "rejected my application for loan", "loan application rejected", "loan was rejected"],
    GrievanceSubCategory.FRAUD: ["fraud", "scam", "cheated", "unauthorized transaction"],
    GrievanceSubCategory.SERVICE_DEFICIENCY: ["service deficiency", "poor service", "bank complaint"],
}


class GrievanceClassifier:
    """Classifies grievance into category and sub-category."""

    def classify(self, text: str) -> GrievanceClassification:
        text_lower = text.lower().strip()

        if not text_lower:
            return GrievanceClassification(
                category=GrievanceCategory.OTHER,
                sub_category=GrievanceSubCategory.OTHER,
                confidence=0.0,
                matched_keywords=[],
            )

        category_scores = {}
        category_matched = {}

        for category, keywords in CATEGORY_KEYWORDS.items():
            score = 0
            matched = []
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1
                    matched.append(keyword)
            if score > 0:
                category_scores[category] = score
                category_matched[category] = matched

        if not category_scores:
            return GrievanceClassification(
                category=GrievanceCategory.OTHER,
                sub_category=GrievanceSubCategory.OTHER,
                confidence=0.25,
                matched_keywords=[],
            )

        top_category = max(category_scores, key=category_scores.get)
        top_score = category_scores[top_category]
        matched_keywords = category_matched.get(top_category, [])

        subcategory_scores = {}
        subcategory_matched = {}

        for subcat, keywords in SUBCATEGORY_KEYWORDS.items():
            if self._is_subcategory_relevant(subcat, top_category):
                score = 0
                matched = []
                for keyword in keywords:
                    if keyword in text_lower:
                        score += 1
                        matched.append(keyword)
                if score > 0:
                    subcategory_scores[subcat] = score
                    subcategory_matched[subcat] = matched

        if subcategory_scores:
            top_subcategory = max(subcategory_scores, key=subcategory_scores.get)
            sub_matched = subcategory_matched.get(top_subcategory, [])
            matched_keywords.extend(sub_matched)
            sub_confidence = min(1.0, 0.5 + (subcategory_scores[top_subcategory] * 0.15))
        else:
            top_subcategory = self._get_default_subcategory(top_category)
            sub_confidence = 0.35

        cat_confidence = min(1.0, 0.5 + (top_score * 0.1))
        confidence = round((cat_confidence + sub_confidence) / 2, 2)

        return GrievanceClassification(
            category=top_category,
            sub_category=top_subcategory,
            confidence=confidence,
            matched_keywords=list(set(matched_keywords)),
        )

    def _is_subcategory_relevant(self, subcat: GrievanceSubCategory, category: GrievanceCategory) -> bool:
        """Check if subcategory belongs to category."""
        mapping = {
            GrievanceCategory.PUBLIC_SERVICE: [
                GrievanceSubCategory.RTI_DELAY,
                GrievanceSubCategory.CERTIFICATE_DELAY,
                GrievanceSubCategory.PENSION_DELAY,
                GrievanceSubCategory.SCHEME_BENEFIT_DENIED,
            ],
            GrievanceCategory.POLICE: [
                GrievanceSubCategory.FIR_REFUSAL,
                GrievanceSubCategory.HARASSMENT,
                GrievanceSubCategory.INACTION,
                GrievanceSubCategory.CORRUPTION,
            ],
            GrievanceCategory.REVENUE: [
                GrievanceSubCategory.LAND_RECORD_ERROR,
                GrievanceSubCategory.MUTATION_DELAY,
                GrievanceSubCategory.COMPENSATION_DELAY,
            ],
            GrievanceCategory.MUNICIPAL: [
                GrievanceSubCategory.GARBAGE,
                GrievanceSubCategory.DRAINAGE,
                GrievanceSubCategory.STREET_LIGHT,
                GrievanceSubCategory.BUILDING_PERMIT,
                GrievanceSubCategory.PROPERTY_TAX,
                GrievanceSubCategory.ROAD_DAMAGE,
            ],
            GrievanceCategory.ELECTRICITY: [
                GrievanceSubCategory.BILLING_DISPUTE,
                GrievanceSubCategory.METER_FAULT,
                GrievanceSubCategory.NEW_CONNECTION_DELAY,
                GrievanceSubCategory.POWER_CUT,
            ],
            GrievanceCategory.WATER: [
                GrievanceSubCategory.SUPPLY_ISSUE,
                GrievanceSubCategory.QUALITY_ISSUE,
                GrievanceSubCategory.BILLING_DISPUTE_WATER,
                GrievanceSubCategory.NEW_CONNECTION_DELAY_WATER,
            ],
            GrievanceCategory.TRANSPORT: [
                GrievanceSubCategory.LICENCE_DELAY,
                GrievanceSubCategory.PERMIT_ISSUE,
                GrievanceSubCategory.BUS_SERVICE,
            ],
            GrievanceCategory.HEALTH: [
                GrievanceSubCategory.HOSPITAL_NEGLIGENCE,
                GrievanceSubCategory.MEDICINE_SHORTAGE,
                GrievanceSubCategory.AMBULANCE_DELAY,
            ],
            GrievanceCategory.EDUCATION: [
                GrievanceSubCategory.ADMISSION_DENIED,
                GrievanceSubCategory.SCHOLARSHIP_DELAY,
                GrievanceSubCategory.MID_DAY_MEAL,
            ],
            GrievanceCategory.FOOD_CIVIL_SUPPLIES: [
                GrievanceSubCategory.RATION_CARD_DELAY,
                GrievanceSubCategory.QUANTITY_SHORTAGE,
                GrievanceSubCategory.QUALITY_COMPLAINT,
            ],
            GrievanceCategory.SOCIAL_WELFARE: [
                GrievanceSubCategory.PENSION_NOT_RECEIVED,
                GrievanceSubCategory.SCHEME_EXCLUSION,
            ],
            GrievanceCategory.LABOUR: [
                GrievanceSubCategory.WAGE_DISPUTE,
                GrievanceSubCategory.UNFAIR_TERMINATION,
                GrievanceSubCategory.SAFETY_VIOLATION,
            ],
            GrievanceCategory.COOPERATIVE: [
                GrievanceSubCategory.MEMBER_RIGHTS,
                GrievanceSubCategory.ELECTION_DISPUTE,
                GrievanceSubCategory.FUND_MISUSE,
            ],
            GrievanceCategory.AGRICULTURE: [
                GrievanceSubCategory.PMFBY_CLAIM_DELAY,
                GrievanceSubCategory.SUBSIDY_DELAY,
                GrievanceSubCategory.SEED_QUALITY,
            ],
            GrievanceCategory.BANKING: [
                GrievanceSubCategory.LOAN_REJECTION,
                GrievanceSubCategory.FRAUD,
                GrievanceSubCategory.SERVICE_DEFICIENCY,
            ],
        }
        return subcat in mapping.get(category, [])

    def _get_default_subcategory(self, category: GrievanceCategory) -> GrievanceSubCategory:
        """Get default subcategory for a category."""
        defaults = {
            GrievanceCategory.PUBLIC_SERVICE: GrievanceSubCategory.SCHEME_BENEFIT_DENIED,
            GrievanceCategory.POLICE: GrievanceSubCategory.INACTION,
            GrievanceCategory.REVENUE: GrievanceSubCategory.LAND_RECORD_ERROR,
            GrievanceCategory.MUNICIPAL: GrievanceSubCategory.GARBAGE,
            GrievanceCategory.ELECTRICITY: GrievanceSubCategory.BILLING_DISPUTE,
            GrievanceCategory.WATER: GrievanceSubCategory.SUPPLY_ISSUE,
            GrievanceCategory.TRANSPORT: GrievanceSubCategory.LICENCE_DELAY,
            GrievanceCategory.HEALTH: GrievanceSubCategory.HOSPITAL_NEGLIGENCE,
            GrievanceCategory.EDUCATION: GrievanceSubCategory.ADMISSION_DENIED,
            GrievanceCategory.FOOD_CIVIL_SUPPLIES: GrievanceSubCategory.RATION_CARD_DELAY,
            GrievanceCategory.SOCIAL_WELFARE: GrievanceSubCategory.PENSION_NOT_RECEIVED,
            GrievanceCategory.LABOUR: GrievanceSubCategory.WAGE_DISPUTE,
            GrievanceCategory.COOPERATIVE: GrievanceSubCategory.MEMBER_RIGHTS,
            GrievanceCategory.AGRICULTURE: GrievanceSubCategory.PMFBY_CLAIM_DELAY,
            GrievanceCategory.BANKING: GrievanceSubCategory.SERVICE_DEFICIENCY,
        }
        return defaults.get(category, GrievanceSubCategory.OTHER)

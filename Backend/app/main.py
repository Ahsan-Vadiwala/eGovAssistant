
from __future__ import annotations

import re
from typing import Any

from fastapi import (
    FastAPI,
    HTTPException,
)

from fastapi.middleware.cors import (
    CORSMiddleware,
)

from pydantic import BaseModel


from rag.pipeline import (
    RAGPipeline,
)


from web_discovery.query_classifier import (
    QueryClassifier,
)


from app.database import (
    initialize_database,
    create_conversation,
    get_conversations,
    get_conversation,
    add_message,
    update_conversation_title,
    delete_conversation,
    set_conversation_pinned,
    conversation_belongs_to_user,
)


from evidence.source_locator import (
    get_locator,
)


from grievance.workflow import (
    GrievanceWorkflow,
)

from grievance.state import (
    load_grievance_state,
)


app = FastAPI(
    title="eGovAssist API",
    description=(
        "Backend for the eGovAssist "
        "government assistance system"
    ),
    version="0.6.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):

    message: str

    language: str = "en"

    conversation_id: str | None = None

    user_id: str


class ChatResponse(BaseModel):

    status: str

    answer: str

    language: str

    conversation_id: str

    sources: list

    evidence: list

    provider: str | None = None

    model: str | None = None

    classification: dict = {}

    discovery: dict = {}


class CreateConversationRequest(BaseModel):

    user_id: str

    title: str = "New Chat"


class ConversationTitleRequest(BaseModel):

    user_id: str

    title: str


class ConversationPinRequest(BaseModel):

    user_id: str

    pinned: bool


class EvidenceLocateRequest(BaseModel):

    source_url: str

    excerpt: str

    chunk_id: str = ""

    page: Any = None

    section: str = ""

    title: str = ""

    source_type: str = ""


pipeline = RAGPipeline()


# IMPORTANT:

grievance_workflow = GrievanceWorkflow()


# IMPORTANT:

query_classifier = QueryClassifier()


evidence_locator = None


def get_evidence_locator():

    global evidence_locator

    if evidence_locator is None:

        evidence_locator = get_locator()

    return evidence_locator


@app.on_event("startup")
def startup_event():

    initialize_database()

    print(
        "eGovAssist database initialized."
    )


@app.get("/health")
def health_check():

    return {
        "status": "ok",
        "service": "eGovAssist",
        "web_discovery": "tavily",
        "language_layer": "frozen",
        "chat_history": "sqlite",
        "evidence_locator": "gemini + sqlite cache",
        "query_classifier": "existing QueryClassifier",
    }


def _clean_evidence_passage(
    text: str,
) -> str:

    text = re.sub(
        r"\s+",
        " ",
        str(text or ""),
    ).strip()

    if not text:
        return ""

    return text


def _looks_like_start_fragment(
    text: str,
) -> bool:

    cleaned = (
        str(text or "")
        .strip()
    )

    if not cleaned:
        return False

    if cleaned.startswith(
        "..."
    ):
        return False

    if cleaned.startswith(
        (
            ",",
            ".",
            ";",
            ":",
            ")",
            "]",
            "}",
            "%",
        )
    ):
        return True

    if cleaned[0].islower():
        return True

    return False


def _looks_like_end_fragment(
    text: str,
) -> bool:

    cleaned = (
        str(text or "")
        .strip()
    )

    if not cleaned:
        return False

    if cleaned.endswith(
        "..."
    ):
        return False

    if cleaned.endswith(
        (
            ".",
            "!",
            "?",
            ":",
            ";",
            '"',
            "'",
            ")",
            "]",
            "}",
            "%",
        )
    ):
        return False

    return True


def _build_frontend_excerpt(
    text: str,
) -> str:

    text = _clean_evidence_passage(
        text
    )

    if not text:
        return ""

    starts_fragment = (
        _looks_like_start_fragment(
            text
        )
    )

    ends_fragment = (
        _looks_like_end_fragment(
            text
        )
    )

    if starts_fragment:
        text = (
            "..."
            + text
        )

    if ends_fragment:
        text = (
            text
            + "..."
        )

    return text


def _build_frontend_evidence(
    evidence_sources: list,
) -> list:

    sources = []

    for index, source in enumerate(
        evidence_sources,
        start=1,
    ):

        if not isinstance(
            source,
            dict,
        ):
            continue

        verification = (
            source.get(
                "verification",
                {},
            )
        )

        if not isinstance(
            verification,
            dict,
        ):
            verification = {}

        identity = (
            verification.get(
                "identity",
                {},
            )
        )

        if not isinstance(
            identity,
            dict,
        ):
            identity = {}

        authority = (
            verification.get(
                "authority",
                {},
            )
        )

        if not isinstance(
            authority,
            dict,
        ):
            authority = {}

        evidence_number = (
            source.get(
                "evidence_number",
                index,
            )
        )

        text = (
            source.get(
                "text"
            )
            or identity.get(
                "text"
            )
            or ""
        )

        text = _build_frontend_excerpt(
            text
        )

        source_url = (
            source.get(
                "source_url"
            )
            or source.get(
                "url"
            )
            or identity.get(
                "source_url"
            )
        )

        title = (
            source.get(
                "title"
            )
            or source.get(
                "web_title"
            )
            or identity.get(
                "title"
            )
            or "Unknown source"
        )

        official = bool(
            source.get(
                "official",
                False,
            )
        )

        trusted_secondary = bool(
            source.get(
                "trusted_secondary",
                False,
            )
        )

        locator = source.get(
            "source_locator"
        )

        if not isinstance(
            locator,
            dict,
        ):
            locator = {}

        sources.append(
            {
                "number": evidence_number,

                "document": (
                    source.get(
                        "document_id"
                    )
                    or source.get(
                        "document"
                    )
                    or identity.get(
                        "document_id"
                    )
                    or title
                ),

                "title": title,

                "file_name": (
                    source.get(
                        "file_name"
                    )
                    or identity.get(
                        "file_name"
                    )
                ),

                "issuer": (
                    source.get(
                        "issuer"
                    )
                    or identity.get(
                        "issuer"
                    )
                ),

                "year": (
                    source.get(
                        "year"
                    )
                    or identity.get(
                        "year"
                    )
                ),

                "version": (
                    source.get(
                        "version"
                    )
                    or identity.get(
                        "version"
                    )
                ),

                "source": (
                    source.get(
                        "source"
                    )
                    or "web"
                ),

                "source_type": (
                    source.get(
                        "source_type"
                    )
                    or "url"
                ),

                "section": (
                    source.get(
                        "section_title"
                    )
                    or source.get(
                        "section"
                    )
                    or identity.get(
                        "section"
                    )
                    or "Web page"
                ),

                "page": (
                    source.get(
                        "page"
                    )
                    or identity.get(
                        "page"
                    )
                    or locator.get(
                        "page"
                    )
                ),

                "excerpt": text,

                "source_url": source_url,

                "official": official,

                "trusted_secondary": (
                    trusted_secondary
                ),

                "trust_score": (
                    verification.get(
                        "trust_score"
                    )
                ),

                "verification_status": (
                    verification.get(
                        "status"
                    )
                ),

                "authority": (
                    authority.get(
                        "authority_label"
                    )
                ),

                "verification_reasons": (
                    verification.get(
                        "reasons",
                        [],
                    )
                ),

                "query_domain": (
                    source.get(
                        "query_domain"
                    )
                ),

                "jurisdiction": (
                    source.get(
                        "jurisdiction"
                    )
                ),

                "state": (
                    source.get(
                        "state"
                    )
                ),

                "source_locator": locator,

                "exact_source_available": bool(
                    locator.get(
                        "found",
                        False,
                    )
                ),

                "exact_source_page": (
                    locator.get(
                        "page"
                    )
                ),

                "exact_source_pages": (
                    locator.get(
                        "pages",
                        [],
                    )
                ),

                "exact_source_url": (
                    locator.get(
                        "direct_url"
                    )
                    or source_url
                ),

                "locator_cache_hit": bool(
                    locator.get(
                        "cache_hit",
                        False,
                    )
                ),
            }
        )

    return sources


@app.post("/evidence/locate")
def locate_evidence(
    request: EvidenceLocateRequest,
):

    source_url = (
        request.source_url
        .strip()
    )

    excerpt = (
        request.excerpt
        .strip()
    )

    if not source_url:

        raise HTTPException(
            status_code=400,
            detail=(
                "source_url cannot be empty."
            ),
        )

    if not excerpt:

        raise HTTPException(
            status_code=400,
            detail=(
                "excerpt cannot be empty."
            ),
        )

    locator_text = (
        _clean_evidence_passage(
            excerpt
        )
    )

    try:

        locator = (
            get_evidence_locator()
        )

        result = locator.locate(

            source_url=source_url,

            source_text=locator_text,

            chunk_id=(
                request.chunk_id
                or None
            ),

            source_title=(
                request.title
                or None
            ),

            source_type=(
                request.source_type
                or None
            ),

            page_hint=request.page,

        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:

        print(
            "\nExact evidence location failed:"
        )

        print(
            repr(error)
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to locate the exact "
                "source passage."
            ),
        )

    result = dict(
        result
    )

    result[
        "source_url"
    ] = source_url

    result[
        "direct_url"
    ] = (
        result.get(
            "direct_url"
        )
        or source_url
    )

    result[
        "requested_excerpt"
    ] = locator_text

    result[
        "display_excerpt"
    ] = _build_frontend_excerpt(
        locator_text
    )

    result[
        "chunk_id"
    ] = request.chunk_id

    result[
        "section"
    ] = request.section

    result[
        "title"
    ] = request.title


    if (
        result.get(
            "source_type"
        )
        == "pdf"
        and result.get(
            "page"
        )
    ):

        page = result[
            "page"
        ]

        base_url = (
            result.get(
                "direct_url"
            )
            or source_url
        )

        if "#" not in base_url:

            result[
                "page_url"
            ] = (
                f"{base_url}"
                f"#page={page}"
            )

        else:

            result[
                "page_url"
            ] = base_url

    else:

        result[
            "page_url"
        ] = (
            result.get(
                "direct_url"
            )
            or source_url
        )

    return {

        "status": "success",

        "locator": result,

        "cache_hit": bool(
            result.get(
                "cache_hit",
                False,
            )
        ),

        "found": bool(
            result.get(
                "found",
                False,
            )
        ),

        "source_type": result.get(
            "source_type"
        ),

        "page": result.get(
            "page"
        ),

        "pages": result.get(
            "pages",
            [],
        ),

        "section_title": result.get(
            "section_title"
        ),

        "paragraph_text": result.get(
            "paragraph_text"
        ),

        "matched_text": result.get(
            "matched_text"
        ),

        "source_url": source_url,

        "direct_url": result.get(
            "direct_url"
        ),

        "page_url": result.get(
            "page_url"
        ),

        "confidence": result.get(
            "confidence",
            0.0,
        ),

        "location_reason": result.get(
            "location_reason",
            "",
        ),
    }


@app.post("/conversations")
def create_chat_conversation(
    request: CreateConversationRequest,
):

    user_id = (
        request.user_id.strip()
    )

    if not user_id:

        raise HTTPException(
            status_code=400,
            detail="user_id cannot be empty.",
        )

    conversation = (
        create_conversation(
            user_id=user_id,
            title=request.title,
        )
    )

    return {
        "status": "success",
        "conversation": conversation,
    }


@app.get("/conversations")
def list_chat_conversations(
    user_id: str,
):

    user_id = (
        user_id.strip()
    )

    if not user_id:

        raise HTTPException(
            status_code=400,
            detail="user_id cannot be empty.",
        )

    conversations = (
        get_conversations(
            user_id
        )
    )

    return {
        "status": "success",
        "conversations": conversations,
    }


@app.get(
    "/conversations/{conversation_id}"
)
def get_chat_conversation(
    conversation_id: str,
    user_id: str,
):

    user_id = (
        user_id.strip()
    )

    conversation = (
        get_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
        )
    )

    if conversation is None:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    return {
        "status": "success",
        "conversation": conversation,
    }


@app.patch(
    "/conversations/{conversation_id}"
)
def rename_chat_conversation(
    conversation_id: str,
    request: ConversationTitleRequest,
):

    conversation = (
        update_conversation_title(
            conversation_id=conversation_id,
            user_id=request.user_id.strip(),
            title=request.title,
        )
    )

    if conversation is None:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    return {
        "status": "success",
        "conversation": conversation,
    }


@app.post(
    "/conversations/{conversation_id}/pin"
)
def pin_chat_conversation(
    conversation_id: str,
    request: ConversationPinRequest,
):

    conversation = (
        set_conversation_pinned(
            conversation_id=conversation_id,
            user_id=request.user_id.strip(),
            pinned=request.pinned,
        )
    )

    if conversation is None:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    return {
        "status": "success",
        "conversation": conversation,
    }


@app.delete(
    "/conversations/{conversation_id}"
)
def remove_chat_conversation(
    conversation_id: str,
    user_id: str,
):

    deleted = (
        delete_conversation(
            conversation_id=conversation_id,
            user_id=user_id.strip(),
        )
    )

    if not deleted:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    return {
        "status": "success",
        "conversation_id": conversation_id,
    }


@app.post(
    "/chat",
    response_model=ChatResponse,
)
def chat(
    request: ChatRequest,
):

    if not request.message.strip():

        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    user_id = (
        request.user_id.strip()
    )

    if not user_id:

        raise HTTPException(
            status_code=400,
            detail="user_id cannot be empty.",
        )


    conversation_id = (
        request.conversation_id
    )

    if conversation_id:

        if not conversation_belongs_to_user(
            conversation_id,
            user_id,
        ):

            raise HTTPException(
                status_code=404,
                detail=(
                    "Conversation not found."
                ),
            )

    else:

        conversation = (
            create_conversation(
                user_id=user_id,
                title=(
                    request.message.strip()
                    [:80]
                ),
            )
        )

        conversation_id = (
            conversation["id"]
        )


    add_message(
        conversation_id=conversation_id,
        role="user",
        content=request.message,
        language=request.language,
        evidence=[],
    )

    # IMPORTANT:

    try:

        classification = (
            query_classifier.classify(
                request.message.strip()
            )
        )

    except Exception as error:

        print(
            "\nQuery classification failed:"
        )

        print(
            repr(error)
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to classify the "
                "chat request."
            ),
        )


    classification_data = {

        "domain": (
            classification.domain
        ),

        "jurisdiction": (
            classification.jurisdiction
        ),

        "state": (
            classification.state
        ),

        "confidence": (
            classification.confidence
        ),

    }

    print(
        "\nChat classification:"
    )

    print(
        f"  Domain       : "
        f"{classification.domain}"
    )

    print(
        f"  Jurisdiction : "
        f"{classification.jurisdiction}"
    )

    print(
        f"  State        : "
        f"{classification.state}"
    )

    print(
        f"  Confidence   : "
        f"{classification.confidence}"
    )

    # IMPORTANT:

    existing_grievance_state = (
        load_grievance_state(conversation_id)
    )

    grievance_in_progress = (
        existing_grievance_state is not None
        and not existing_grievance_state.is_complete
    )

    is_new_grievance = (
        grievance_workflow.is_grievance_query(
            request.message
        )
    )

    if grievance_in_progress or is_new_grievance:

        try:

            grievance_result = (
                grievance_workflow.process_message(
                    user_message=request.message,
                    conversation_id=conversation_id,
                    user_id=user_id,
                )
            )

        except Exception as error:

            print(
                "\nGrievance workflow failed:"
            )

            print(
                repr(error)
            )

            raise HTTPException(
                status_code=500,
                detail=(
                    "Failed to process the "
                    "grievance request."
                ),
            )

        grievance_answer = (
            grievance_result.response
        )

        grievance_draft = (
            grievance_result.draft
        )

        grievance_classification_data = {

            "domain": "grievance",

            "jurisdiction": (
                grievance_draft.jurisdiction
                if grievance_draft
                else "unknown"
            ),

            "state": (
                grievance_draft.state
                if grievance_draft
                else None
            ),

            "confidence": 1.0,

        }

        add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=grievance_answer,
            language=request.language,
            evidence=[],
        )

        return {

            "status": "success",

            "answer": grievance_answer,

            "language": request.language,

            "conversation_id": (
                conversation_id
            ),

            "sources": [],

            "evidence": [],

            "provider": "grievance_workflow",

            "model": None,

            "classification": (
                grievance_classification_data
            ),

            "discovery": {

                "workflow": "grievance",

                "stage": (
                    grievance_result.stage.value
                ),

                "is_complete": (
                    grievance_result.is_complete
                ),

                "is_official_submission": False,

            },

        }


    try:

        result = pipeline.ask(
            query=request.message,
            classification=classification,
        )

    except Exception as error:

        print(
            "\nChat request failed:"
        )

        print(
            repr(error)
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to process the "
                "chat request."
            ),
        )


    evidence_sources = (
        result.get(
            "evidence"
        )
        or result.get(
            "sources"
        )
        or []
    )

    sources = (
        _build_frontend_evidence(
            evidence_sources
        )
    )


    answer = str(
        result.get(
            "answer",
            "",
        )
        or ""
    )

    status = result.get(
        "status",
        "failed",
    )


    response_classification = (
        result.get(
            "classification"
        )
        or classification_data
    )

    response_discovery = (
        result.get(
            "discovery"
        )
        or {}
    )


    add_message(
        conversation_id=conversation_id,
        role="assistant",
        content=answer,
        language=request.language,
        evidence=sources,
    )


    return {

        "status": status,

        "answer": answer,

        "language": request.language,

        "conversation_id": (
            conversation_id
        ),

        "sources": sources,

        "evidence": sources,

        "provider": result.get(
            "provider"
        ),

        "model": result.get(
            "model"
        ),

        "classification": (
            response_classification
        ),

        "discovery": (
            response_discovery
        ),
    }

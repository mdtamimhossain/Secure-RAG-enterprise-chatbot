from __future__ import annotations

from time import perf_counter
from functools import lru_cache

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from backend.src.auth import DemoSession, create_demo_session, get_demo_session
from backend.src.database import clear_user_chat_messages, get_chat_messages, save_chat_message
from backend.src.guardrails import GuardrailResult, check_input_guardrails, check_output_guardrails
from backend.src.monitoring import MonitoringMetrics, get_monitoring_metrics, log_chat_event, log_guardrail_event
from backend.src.rag_chain import ChatHistoryMessage
from backend.src.rag_service import RAGService, build_rag_service, get_index_status


app = FastAPI(title="Secure Enterprise RAG Chatbot API")


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    role: str = "employee"
    history: list[ChatHistoryMessage] = Field(default_factory=list)


class LoginRequest(BaseModel):
    name: str = Field(..., min_length=1)
    role: str = "employee"


class LoginResponse(BaseModel):
    session_token: str
    name: str
    role: str


class StoredChatMessageResponse(BaseModel):
    sender: str
    text: str
    sources: list[dict]
    guardrail: dict | None = None
    createdAt: str


class SourceResponse(BaseModel):
    content: str
    metadata: dict


class ChatResponse(BaseModel):
    answer: str
    role: str
    model: str
    sources: list[SourceResponse]
    guardrail: dict[str, str] | None = None


class StatusResponse(BaseModel):
    status: str
    document_count: int
    chunk_count: int
    collection_name: str


class MetricsResponse(BaseModel):
    total_chats: int
    successful_chats: int
    blocked_chats: int
    errored_chats: int
    average_latency_ms: float
    average_source_count: float
    average_history_messages: float
    roles: dict[str, int]
    guardrail_reasons: dict[str, int]
    source_departments: dict[str, int]
    source_categories: dict[str, int]
    source_files: dict[str, int]
    recent_events: list[dict]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/status", response_model=StatusResponse)
def status() -> StatusResponse:
    try:
        index_status = get_index_status()
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return StatusResponse(
        status="ready",
        document_count=index_status.document_count,
        chunk_count=index_status.chunk_count,
        collection_name=index_status.collection_name,
    )


@app.get("/metrics", response_model=MetricsResponse)
def metrics() -> MonitoringMetrics:
    return get_monitoring_metrics()


@app.post("/login", response_model=LoginResponse)
def login(request: LoginRequest) -> LoginResponse:
    try:
        session = create_demo_session(request.name, request.role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return LoginResponse(
        session_token=session.token,
        name=session.name,
        role=session.role,
    )


@app.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    authorization: str | None = Header(default=None),
) -> ChatResponse:
    started_at = perf_counter()
    session = _require_session(authorization)
    effective_role = session.role
    save_chat_message(
        user_id=session.user_id,
        sender="user",
        content=request.question,
    )
    try:
        guardrail_result = check_input_guardrails(request.question)
        if not guardrail_result.allowed:
            return _guardrail_response(request, session, guardrail_result, _latency_ms(started_at))

        rag_service = get_rag_service()
        response = rag_service.rag_chain.answer_question(
            question=request.question,
            role=effective_role,
            top_k=3,
            chat_history=request.history,
        )
        output_guardrail_result = check_output_guardrails(response.answer)
        if not output_guardrail_result.allowed:
            return _guardrail_response(request, session, output_guardrail_result, _latency_ms(started_at))
    except ValueError as exc:
        _log_error_chat_event(request, effective_role, str(exc), _latency_ms(started_at))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        _log_error_chat_event(request, effective_role, str(exc), _latency_ms(started_at))
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    source_metadata = _source_metadata(response.sources)
    log_chat_event(
        question=request.question,
        role=effective_role,
        status="success",
        model=response.model,
        latency_ms=_latency_ms(started_at),
        source_count=len(response.sources),
        source_departments=source_metadata["departments"],
        source_categories=source_metadata["categories"],
        source_files=source_metadata["files"],
        history_message_count=len(request.history),
    )

    chat_response = ChatResponse(
        answer=response.answer,
        role=effective_role,
        model=response.model,
        sources=[
            SourceResponse(
                content=source["content"],
                metadata=source["metadata"],
            )
            for source in response.sources
        ],
    )
    save_chat_message(
        user_id=session.user_id,
        sender="assistant",
        content=chat_response.answer,
        sources=[source.model_dump() for source in chat_response.sources],
        guardrail=chat_response.guardrail,
    )
    return chat_response


@app.get("/chat/history", response_model=list[StoredChatMessageResponse])
def chat_history(authorization: str | None = Header(default=None)) -> list[dict]:
    session = _require_session(authorization)
    return get_chat_messages(session.user_id)


@app.delete("/chat/history")
def clear_chat_history(authorization: str | None = Header(default=None)) -> dict[str, str]:
    session = _require_session(authorization)
    clear_user_chat_messages(session.user_id)
    return {"status": "cleared"}


def _guardrail_response(
    request: ChatRequest,
    session: DemoSession,
    result: GuardrailResult,
    latency_ms: float,
) -> ChatResponse:
    log_guardrail_event(
        question=request.question,
        role=session.role,
        reason=result.reason,
        stage=result.stage,
        intent=result.intent.value,
        message=result.message,
    )
    log_chat_event(
        question=request.question,
        role=session.role,
        status="blocked",
        model=f"Guardrails:{result.reason}",
        latency_ms=latency_ms,
        guardrail_reason=result.reason,
        history_message_count=len(request.history),
    )

    chat_response = ChatResponse(
        answer=result.message,
        role=session.role,
        model=f"Guardrails:{result.reason}",
        sources=[],
        guardrail={
            "reason": result.reason,
            "stage": result.stage,
            "intent": result.intent.value,
        },
    )
    save_chat_message(
        user_id=session.user_id,
        sender="assistant",
        content=chat_response.answer,
        sources=[],
        guardrail=chat_response.guardrail,
    )
    return chat_response


def _log_error_chat_event(request: ChatRequest, role: str, error: str, latency_ms: float) -> None:
    log_chat_event(
        question=request.question,
        role=role,
        status="error",
        model="",
        latency_ms=latency_ms,
        error=error,
        history_message_count=len(request.history),
    )


def _require_session(authorization: str | None) -> DemoSession:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    session = get_demo_session(token.strip())
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return session


def _source_metadata(sources: list[dict]) -> dict[str, list[str]]:
    departments = []
    categories = []
    files = []
    for source in sources:
        metadata = source.get("metadata", {})
        department = metadata.get("department")
        if department and department not in departments:
            departments.append(department)
        category = metadata.get("category")
        if category and category not in categories:
            categories.append(category)
        filename = metadata.get("filename")
        if filename and filename not in files:
            files.append(filename)
    return {
        "departments": departments,
        "categories": categories,
        "files": files,
    }


def _latency_ms(started_at: float) -> float:
    return (perf_counter() - started_at) * 1000


@lru_cache(maxsize=1)
def get_rag_service() -> RAGService:
    return build_rag_service()

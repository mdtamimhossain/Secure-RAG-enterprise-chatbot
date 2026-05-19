from __future__ import annotations

from functools import lru_cache

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from backend.src.guardrails import GuardrailResult, check_input_guardrails, check_output_guardrails
from backend.src.monitoring import log_guardrail_event
from backend.src.rag_chain import ChatHistoryMessage
from backend.src.rag_service import RAGService, build_rag_service, get_index_status


app = FastAPI(title="Secure Enterprise RAG Chatbot API")


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    role: str = "employee"
    history: list[ChatHistoryMessage] = Field(default_factory=list)


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


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        guardrail_result = check_input_guardrails(request.question)
        if not guardrail_result.allowed:
            return _guardrail_response(request, guardrail_result)

        rag_service = get_rag_service()
        response = rag_service.rag_chain.answer_question(
            question=request.question,
            role=request.role,
            top_k=3,
            chat_history=request.history,
        )
        output_guardrail_result = check_output_guardrails(response.answer)
        if not output_guardrail_result.allowed:
            return _guardrail_response(request, output_guardrail_result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ChatResponse(
        answer=response.answer,
        role=request.role,
        model=response.model,
        sources=[
            SourceResponse(
                content=source["content"],
                metadata=source["metadata"],
            )
            for source in response.sources
        ],
    )


def _guardrail_response(request: ChatRequest, result: GuardrailResult) -> ChatResponse:
    log_guardrail_event(
        question=request.question,
        role=request.role,
        reason=result.reason,
        stage=result.stage,
        intent=result.intent.value,
        message=result.message,
    )

    return ChatResponse(
        answer=result.message,
        role=request.role,
        model=f"Guardrails:{result.reason}",
        sources=[],
        guardrail={
            "reason": result.reason,
            "stage": result.stage,
            "intent": result.intent.value,
        },
    )


@lru_cache(maxsize=1)
def get_rag_service() -> RAGService:
    return build_rag_service()

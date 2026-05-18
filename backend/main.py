from __future__ import annotations

from functools import lru_cache

from fastapi import FastAPI
from pydantic import BaseModel, Field

from backend.src.rag_service import RAGService, build_rag_service


app = FastAPI(title="Secure Enterprise RAG Chatbot API")


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    role: str = "employee"


class SourceResponse(BaseModel):
    content: str
    metadata: dict


class ChatResponse(BaseModel):
    answer: str
    role: str
    model: str
    sources: list[SourceResponse]


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
    rag_service = get_rag_service()
    return StatusResponse(
        status="ready",
        document_count=rag_service.document_count,
        chunk_count=rag_service.chunk_count,
        collection_name=rag_service.collection_name,
    )


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    rag_service = get_rag_service()
    response = rag_service.rag_chain.answer_question(
        question=request.question,
        role=request.role,
        top_k=3,
    )

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


@lru_cache(maxsize=1)
def get_rag_service() -> RAGService:
    return build_rag_service()

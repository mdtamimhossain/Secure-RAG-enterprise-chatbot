from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from backend.src.retriever import Retriever


class LLMClient(Protocol):
    def generate(self, prompt: str) -> str:
        """Generate a text response from a prompt."""


@dataclass(frozen=True)
class LLMResponse:
    answer: str
    model: str


@dataclass(frozen=True)
class RAGResponse:
    answer: str
    sources: list[dict[str, Any]]
    model: str


class FakeLLM:
    """Simple local LLM stand-in for tests and early backend wiring."""

    def __init__(self, response: str = "This is a test answer.") -> None:
        self.response = response
        self.last_prompt = ""

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        if not prompt.strip():
            return "I need a question before I can answer."
        return self.response


class GroqLLM:
    """Small Groq chat-completions client using only the Python standard library."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "llama-3.1-8b-instant",
        api_url: str = "https://api.groq.com/openai/v1/chat/completions",
        timeout_seconds: int = 30,
    ) -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is required to use GroqLLM")

        self.model = model
        self.api_url = api_url
        self.timeout_seconds = timeout_seconds

    def generate(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a secure internal company assistant. "
                        "Answer only from the provided context."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }

        request = Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                response_data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            message = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Groq API request failed: {exc.code} {message}") from exc
        except URLError as exc:
            raise RuntimeError(f"Groq API request failed: {exc.reason}") from exc

        return response_data["choices"][0]["message"]["content"]


class OpenAILLM:
    """OpenAI Responses API client using OPENAI_API_KEY."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-5.2",
        api_url: str = "https://api.openai.com/v1/responses",
        timeout_seconds: int = 30,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required to use OpenAILLM")

        self.model = model
        self.api_url = api_url
        self.timeout_seconds = timeout_seconds

    def generate(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "instructions": (
                "You are a secure internal company assistant. "
                "Answer only from the provided context."
            ),
            "input": prompt,
        }
        request = Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                response_data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            message = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"OpenAI response request failed: {exc.code} {message}") from exc
        except URLError as exc:
            raise RuntimeError(f"OpenAI response request failed: {exc.reason}") from exc

        if "output_text" in response_data:
            return response_data["output_text"]

        text_parts = []
        for output_item in response_data.get("output", []):
            for content_item in output_item.get("content", []):
                if content_item.get("type") in {"output_text", "text"}:
                    text_parts.append(content_item.get("text", ""))

        return "\n".join(part for part in text_parts if part).strip()


def create_llm_client(provider: str | None = None) -> LLMClient:
    provider = (provider or os.getenv("LLM_PROVIDER", "fake")).lower()

    if provider == "fake":
        return FakeLLM(response="I found relevant company context for your question.")
    if provider == "openai":
        model = os.getenv("OPENAI_MODEL", "gpt-5.2")
        return OpenAILLM(model=model)
    if provider == "groq":
        model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        return GroqLLM(model=model)

    raise ValueError(f"Unsupported LLM provider: {provider}")


def generate_llm_answer(prompt: str, llm_client: LLMClient) -> LLMResponse:
    """Generate an answer using the configured LLM client."""

    answer = llm_client.generate(prompt)
    model_name = llm_client.__class__.__name__
    return LLMResponse(answer=answer, model=model_name)


class RAGChain:
    """Final RAG orchestration: retrieve context, build prompt, call LLM."""

    def __init__(self, retriever: Retriever, llm_client: LLMClient) -> None:
        self.retriever = retriever
        self.llm_client = llm_client

    def answer_question(
        self,
        question: str,
        role: str,
        top_k: int = 3,
    ) -> RAGResponse:
        sources = self.retriever.retrieve(question, role=role, top_k=top_k)

        if not question.strip():
            return RAGResponse(
                answer="Please ask a question.",
                sources=[],
                model=self.llm_client.__class__.__name__,
            )

        if not sources:
            return RAGResponse(
                answer="I could not find relevant information you are allowed to access.",
                sources=[],
                model=self.llm_client.__class__.__name__,
            )

        prompt = build_rag_prompt(question=question, sources=sources)
        llm_response = generate_llm_answer(prompt, self.llm_client)

        return RAGResponse(
            answer=llm_response.answer,
            sources=sources,
            model=llm_response.model,
        )


def build_rag_prompt(question: str, sources: list[dict[str, Any]]) -> str:
    context_blocks = []
    for index, source in enumerate(sources, start=1):
        metadata = source.get("metadata", {})
        filename = metadata.get("filename", "unknown")
        department = metadata.get("department", "unknown")
        content = source.get("content", "")
        context_blocks.append(
            f"Source {index} | department={department} | file={filename}\n{content}"
        )

    context = "\n\n".join(context_blocks)
    return (
        "Use only the context below to answer the employee question. "
        "If the answer is not in the context, say you do not know.\n\n"
        f"Context:\n{context}\n\n"
        f"Question:\n{question}\n\n"
        "Answer:"
    )

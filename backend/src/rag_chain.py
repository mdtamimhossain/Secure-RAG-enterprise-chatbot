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


@dataclass(frozen=True)
class ChatHistoryMessage:
    role: str
    content: str


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
                        "Follow the response policy in the user prompt. "
                        "Do not invent company information."
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
                "User-Agent": "secure-rag-enterprise-chatbot/0.1",
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
                "Follow the response policy in the user prompt. "
                "Do not invent company information."
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
        chat_history: list[ChatHistoryMessage] | None = None,
    ) -> RAGResponse:
        if not question.strip():
            return RAGResponse(
                answer="Please ask a question.",
                sources=[],
                model=self.llm_client.__class__.__name__,
            )

        clean_history = normalize_chat_history(chat_history or [])
        retrieval_query = build_retrieval_query(question, clean_history)
        sources = self.retriever.retrieve(retrieval_query, role=role, top_k=top_k)
        prompt = build_rag_prompt(
            question=question,
            sources=sources,
            chat_history=clean_history,
        )
        llm_response = generate_llm_answer(prompt, self.llm_client)
        answer, should_show_sources = parse_source_usage(llm_response.answer)

        return RAGResponse(
            answer=answer,
            sources=sources if should_show_sources else [],
            model=llm_response.model,
        )


def parse_source_usage(answer: str) -> tuple[str, bool]:
    """Read the LLM source-usage marker and remove it from the visible answer."""

    lines = answer.strip().splitlines()
    if not lines:
        return "", False

    first_line = lines[0].strip()
    marker_prefix = "source_usage:"
    if first_line.lower().startswith(marker_prefix):
        usage = first_line.split(":", 1)[1].strip().lower()
        visible_answer = "\n".join(lines[1:]).strip()
        return visible_answer, usage == "context"

    return answer.strip(), True


def normalize_chat_history(
    chat_history: list[ChatHistoryMessage | dict[str, str]],
    max_messages: int = 8,
    max_chars_per_message: int = 700,
) -> list[ChatHistoryMessage]:
    normalized: list[ChatHistoryMessage] = []
    for message in chat_history[-max_messages:]:
        role = message.role if isinstance(message, ChatHistoryMessage) else message.get("role", "")
        content = message.content if isinstance(message, ChatHistoryMessage) else message.get("content", "")
        clean_role = role.strip().lower()
        clean_content = " ".join(content.strip().split())
        if clean_role not in {"user", "assistant"} or not clean_content:
            continue
        normalized.append(
            ChatHistoryMessage(
                role=clean_role,
                content=clean_content[:max_chars_per_message],
            )
        )
    return normalized


def build_retrieval_query(question: str, chat_history: list[ChatHistoryMessage]) -> str:
    clean_question = question.strip()
    if not clean_question:
        return ""

    if not _is_follow_up_question(clean_question):
        return clean_question

    recent_user_messages = [
        message.content
        for message in chat_history
        if message.role == "user"
    ][-2:]
    recent_assistant_messages = [
        message.content
        for message in chat_history
        if message.role == "assistant"
    ][-1:]
    query_parts = recent_user_messages + recent_assistant_messages + [clean_question]
    return "\n".join(part for part in query_parts if part).strip()


def _is_follow_up_question(question: str) -> bool:
    normalized = question.strip().lower()
    if not normalized:
        return False

    words = normalized.replace("?", "").replace(".", "").split()
    follow_up_phrases = (
        "yes",
        "yeah",
        "yep",
        "no",
        "explain",
        "explain more",
        "tell me more",
        "what about",
        "how about",
        "what does that",
        "what do you mean",
        "i don't understand",
        "dont understand",
        "give me example",
        "give an example",
        "can you explain",
        "and",
        "also",
    )
    if normalized in follow_up_phrases:
        return True
    if any(normalized.startswith(phrase) for phrase in follow_up_phrases):
        return True
    if len(words) <= 4 and any(
        token in words
        for token in {
            "that",
            "this",
            "it",
            "those",
            "them",
            "more",
            "example",
            "examples",
            "days",
            "limit",
            "carry-over",
            "carryover",
        }
    ):
        return True

    return False


def format_chat_history(chat_history: list[ChatHistoryMessage]) -> str:
    if not chat_history:
        return "No previous conversation."

    lines = []
    for message in chat_history:
        speaker = "User" if message.role == "user" else "Assistant"
        lines.append(f"{speaker}: {message.content}")
    return "\n".join(lines)


def build_rag_prompt(
    question: str,
    sources: list[dict[str, Any]],
    chat_history: list[ChatHistoryMessage] | None = None,
) -> str:
    context_blocks = []
    for index, source in enumerate(sources, start=1):
        metadata = source.get("metadata", {})
        filename = metadata.get("filename", "unknown")
        department = metadata.get("department", "unknown")
        content = source.get("content", "")
        context_blocks.append(
            f"Source {index} | department={department} | file={filename}\n{content}"
        )

    context = "\n\n".join(context_blocks) if context_blocks else "No retrieved context."
    conversation = format_chat_history(chat_history or [])
    return (
        "You are Codemars Intranet Assistant.\n\n"
        "Response rules:\n"
        "1. If the user is greeting, thanking, or making casual conversation, "
        "respond naturally and briefly. Do not mention missing documents for casual chat.\n"
        "2. If the user asks about company/internal information, answer only using "
        "the retrieved context below.\n"
        "3. If the user asks about company/internal information but the retrieved "
        "context is empty, irrelevant, or does not contain the answer, say: "
        "\"I could not find specific information about that in your available company documents.\"\n"
        "4. Use the previous conversation only to understand follow-up wording like "
        "\"yes\", \"explain more\", \"what about that\", or \"I don't understand\".\n"
        "5. Do not invent company policies, benefits, finance data, or employee information.\n"
        "6. The context was already filtered by backend RBAC. Never suggest that the "
        "user can access documents outside this context.\n\n"
        "Source display rule:\n"
        "Start your answer with exactly one hidden routing line:\n"
        "- SOURCE_USAGE: casual  -> for greetings, thanks, or casual conversation\n"
        "- SOURCE_USAGE: context -> when your answer uses retrieved company context\n"
        "- SOURCE_USAGE: none    -> when the user asks a company question but the "
        "context does not contain the answer\n"
        "After that first line, write the user-facing answer.\n\n"
        f"Previous conversation:\n{conversation}\n\n"
        f"Retrieved context:\n{context}\n\n"
        f"User message:\n{question}\n\n"
        "Answer:"
    )

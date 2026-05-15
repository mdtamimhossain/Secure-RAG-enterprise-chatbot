from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class LLMClient(Protocol):
    def generate(self, prompt: str) -> str:
        """Generate a text response from a prompt."""


@dataclass(frozen=True)
class LLMResponse:
    answer: str
    model: str


class FakeLLM:
    """Simple local LLM stand-in for tests and early backend wiring."""

    def __init__(self, response: str = "This is a test answer.") -> None:
        self.response = response

    def generate(self, prompt: str) -> str:
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


def generate_llm_answer(prompt: str, llm_client: LLMClient) -> LLMResponse:
    """Generate an answer using the configured LLM client."""

    answer = llm_client.generate(prompt)
    model_name = llm_client.__class__.__name__
    return LLMResponse(answer=answer, model=model_name)

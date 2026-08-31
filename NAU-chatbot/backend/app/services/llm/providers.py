from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence, runtime_checkable


@dataclass(frozen=True, slots=True)
class LLMMessage:
    role: str
    content: str


@runtime_checkable
class LLMProvider(Protocol):
    async def generate(
        self,
        role: str,
        messages: Sequence[LLMMessage],
        *,
        max_new_tokens: int,
    ) -> str: ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    async def embed(
        self,
        texts: Sequence[str],
        *,
        query: bool = False,
    ) -> list[list[float]]: ...


@runtime_checkable
class RerankerProvider(Protocol):
    async def rerank(self, query: str, documents: Sequence[str]) -> list[float]: ...

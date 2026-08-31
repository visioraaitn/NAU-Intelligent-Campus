from __future__ import annotations

from collections.abc import Sequence

import httpx

from app.core.config import Settings
from app.core.exceptions import DependencyUnavailableError
from app.services.llm.providers import LLMMessage


class HttpInferenceClient:
    """Authenticated internal adapter implementing all model provider ports."""

    def __init__(self, settings: Settings) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.inference_base_url.rstrip("/"),
            timeout=httpx.Timeout(settings.inference_timeout_seconds),
            headers={
                "X-Inference-Token": settings.inference_service_token.get_secret_value()
            },
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )

    async def generate(
        self,
        role: str,
        messages: Sequence[LLMMessage],
        *,
        max_new_tokens: int,
    ) -> str:
        response = await self._request(
            "/v1/generate",
            {
                "role": role,
                "messages": [
                    {"role": message.role, "content": message.content}
                    for message in messages
                ],
                "max_new_tokens": max_new_tokens,
            },
        )
        return str(response["text"])

    async def embed(
        self,
        texts: Sequence[str],
        *,
        query: bool = False,
    ) -> list[list[float]]:
        response = await self._request(
            "/v1/embed", {"texts": list(texts), "query": query}
        )
        return [[float(value) for value in vector] for vector in response["embeddings"]]

    async def rerank(self, query: str, documents: Sequence[str]) -> list[float]:
        response = await self._request(
            "/v1/rerank",
            {"query": query, "documents": list(documents)},
        )
        return [float(score) for score in response["scores"]]

    async def health(self) -> bool:
        try:
            response = await self._client.get("/health")
            return response.status_code == 200 and bool(response.json().get("ready"))
        except httpx.HTTPError:
            return False

    async def _request(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        try:
            response = await self._client.post(path, json=payload)
            response.raise_for_status()
            result = response.json()
            if not isinstance(result, dict):
                raise ValueError("unexpected inference response")
            return result
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            raise DependencyUnavailableError("inference") from exc

    async def close(self) -> None:
        await self._client.aclose()

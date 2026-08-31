from __future__ import annotations

from app.core.file_config import prompt_text
from app.services.llm.providers import LLMMessage, LLMProvider


class EspritNluService:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    async def interpret(self, original_message: str) -> str:
        return await self.provider.generate(
            "esprit",
            (
                LLMMessage("system", prompt_text("esprit_nlu")),
                LLMMessage("user", original_message),
            ),
            max_new_tokens=110,
        )


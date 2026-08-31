from __future__ import annotations

import re

from app.core.file_config import dialogue_config


class ResponseLengthGuard:
    def apply(self, answer: str, mode: str) -> str:
        config = dialogue_config()
        limit = config.detail_max_lines if mode == "DETAIL" else config.default_max_lines
        lines = [line.strip() for line in answer.splitlines() if line.strip()]
        if len(lines) <= 1:
            sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+", answer) if item.strip()]
            lines = sentences
        return "\n".join(lines[:limit]).strip()


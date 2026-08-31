from __future__ import annotations

from app.services.dialogue.normalizer import token_set


class AntiRepetitionGuard:
    def apply(self, answer: str, previous: str) -> str:
        current_tokens = token_set(answer)
        previous_tokens = token_set(previous)
        if len(current_tokens) < 6 or not previous_tokens:
            return answer
        overlap = len(current_tokens & previous_tokens) / max(1, len(current_tokens | previous_tokens))
        if overlap < 0.88:
            return answer
        lines = [line.strip() for line in answer.splitlines() if line.strip()]
        return "\n".join(lines[1:] or lines)


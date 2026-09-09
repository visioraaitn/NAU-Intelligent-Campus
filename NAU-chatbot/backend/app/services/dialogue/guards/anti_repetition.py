from __future__ import annotations

from collections.abc import Sequence

from app.services.dialogue.normalizer import token_set


class AntiRepetitionGuard:
    def apply(
        self,
        answer: str,
        previous: str,
        recent: Sequence[str] = (),
    ) -> str:
        current_tokens = token_set(answer)
        candidates = (previous, *recent)
        if len(current_tokens) < 6 or not any(candidates):
            return answer
        for candidate in candidates:
            candidate_tokens = token_set(candidate)
            overlap = len(current_tokens & candidate_tokens) / max(
                1, len(current_tokens | candidate_tokens)
            )
            if overlap >= 0.88:
                lines = [line.strip() for line in answer.splitlines() if line.strip()]
                return "\n".join(lines[1:] or lines)
        return answer


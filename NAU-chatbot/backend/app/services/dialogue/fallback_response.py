from __future__ import annotations

from collections.abc import Sequence

from app.domain.rag.schemas import RagFact
from app.domain.recommendation.schemas import EligibilityDecision, EligibilityStatus, RecommendationDecision
from app.services.dialogue.human_labels import humanize_text


class FallbackResponseBuilder:
    def build(
        self,
        intents: Sequence[str],
        facts: Sequence[RagFact],
        recommendation: RecommendationDecision | None,
        eligibility: EligibilityDecision | None,
    ) -> str:
        if eligibility and eligibility.status is EligibilityStatus.NOT_ELIGIBLE:
            evidence = eligibility.failed_rules[0] if eligibility.failed_rules else None
            reason = (
                self._public_reason(evidence.reason)
                if evidence
                else "les critères publiés ne correspondent pas"
            )
            answer = (
                "Les conditions d'admission actuelles ne correspondent pas à ce profil : "
                f"{reason} Je ne peux donc pas proposer une pré-inscription "
                "pour cette formation."
            )
            if recommendation and recommendation.primary:
                option = recommendation.primary
                label = option.specialisation_name or option.formation_name
                answer += (
                    f" En revanche, {label} est une piste IIT compatible avec les informations fournies. "
                    "Veux-tu que je t'explique son programme et ses débouchés ?"
                )
            return answer
        if recommendation and recommendation.primary:
            option = recommendation.primary
            label = option.specialisation_name or option.formation_name
            parts = [f"La piste la plus cohérente est {label}."]
            parts.extend(recommendation.reasoning[:1])
            if recommendation.challenge:
                parts.append(recommendation.challenge)
            return "\n".join(parts)
        if facts:
            return "\n".join(fact.text for fact in facts[:3])
        if "ORIENTATION" in intents:
            return "Je peux t'orienter progressivement, mais il me manque encore une information fiable sur ton profil ou tes intérêts."
        return "Je n'ai pas trouvé de fait académique suffisamment précis pour répondre sans inventer. Tu peux préciser la formation concernée ?"

    @staticmethod
    def _public_reason(reason: str) -> str:
        folded = reason.casefold()
        if "diplôme requis" in folded:
            return "le diplôme actuel ne correspond pas au niveau d'entrée requis."
        if "ne figure pas dans la liste acceptée" in folded:
            return "la section de bac indiquée n'est pas acceptée pour cette formation."
        return humanize_text(reason)

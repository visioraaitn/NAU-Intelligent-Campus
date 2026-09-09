from __future__ import annotations

from app.domain.conversation.models import SubjectState
from app.services.dialogue.human_labels import profile_label, value_label


class KnownFactsBuilder:
    def build(
        self,
        subject: SubjectState,
        *,
        include_profile: bool = True,
    ) -> tuple[str, str]:
        known: list[str] = []
        if include_profile:
            known.append(f"Situation actuelle : {profile_label(subject.profile)}")
            if subject.bac_specialty:
                known.append(f"Section du bac : {value_label(subject.bac_specialty)}")
            if subject.bac_average is not None:
                known.append(f"Moyenne au bac : {subject.bac_average:g}/20")
            if subject.math_grade is not None:
                known.append(f"Note en mathématiques : {subject.math_grade:g}/20")
            if subject.math_comfort:
                known.append(f"Aisance en mathématiques : {value_label(subject.math_comfort)}")
        if subject.licence_specialty:
            known.append(f"Spécialité de licence : {value_label(subject.licence_specialty)}")
        if subject.target:
            known.append(f"Objectif d'études : {value_label(subject.target)}")
        if subject.interests:
            known.append("Centres d'intérêt : " + ", ".join(value_label(item) for item in subject.interests))
        if subject.rejected_offers:
            known.append("Formations refusées : " + ", ".join(value_label(item) for item in subject.rejected_offers))
        if subject.rejected_domains:
            known.append("Domaines refusés : " + ", ".join(value_label(item) for item in subject.rejected_domains))
        forbidden = [
            "ne pas garantir l'admission",
            "ne pas garantir un emploi ou un salaire",
            "ne pas inventer un bac, une note, un intérêt, une certification, une mobilité ou un partenariat",
            "ne pas traiter une hypothèse comme le profil réel",
            "ne jamais afficher de code interne, de statut technique ou de valeur écrite en majuscules avec des underscores",
            "ne jamais dire que l'IIT propose des métiers : l'IIT propose des formations qui ouvrent vers des débouchés",
        ]
        if subject.math_grade is None:
            forbidden.append("ne pas affirmer que l'utilisateur est fort ou faible en maths")
        if not subject.interests:
            forbidden.append("ne pas supposer un intérêt technique")
        return "\n".join(f"- {item}" for item in known), "\n".join(f"- {item}" for item in forbidden)

from __future__ import annotations

import re
from collections.abc import Sequence

from app.domain.rag.schemas import RagFact
from app.domain.recommendation.schemas import EligibilityStatus
from app.services.dialogue.human_labels import humanize_text
from app.services.dialogue.normalizer import fold_text


class FactualGuard:
    FORBIDDEN = (
        re.compile(r"\badmission (est )?garantie\b", re.I),
        re.compile(r"\bemploi (est )?garanti\b", re.I),
        re.compile(r"\b100\s*%\b", re.I),
        re.compile(r"\bsalaire garanti\b", re.I),
        re.compile(r"\btu (?:seras|es) (?:automatiquement )?(?:admis|admissible|accepté)\b", re.I),
        re.compile(r"\btravail (?:est )?(?:assuré|garanti)\b", re.I),
    )
    LEAKS = ("system policy", "forbidden assumptions", "academic facts", "system prompt")
    MONEY = re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:dt|tnd|dinar(?:s)?)\b", re.I)
    DURATION = re.compile(
        r"\b\d+(?:[.,]\d+)?\s*(?:an(?:s|née|nées)?|semestre(?:s)?)\b",
        re.I,
    )
    ACCREDITATION = re.compile(r"\b(?:accrédit\w*|euro[ -]?inf|asiin)\b", re.I)
    CERTIFICATION = re.compile(r"\bcertifi(?:cation|é|ée|és|ées)\w*\b", re.I)
    MOBILITY = re.compile(r"\b(?:mobilité|international(?:e|es)?|échange(?:s)?)\b", re.I)
    CAREER = re.compile(r"\b(?:métier(?:s)?|carrière(?:s)?|débouché(?:s)?)\b", re.I)
    POSITIVE_ADMISSION = re.compile(r"\b(?:éligible|admissible|admis|accepté)\b", re.I)
    INTERNAL_REPLACEMENTS = {
        "NEW_BAC": "nouveau bachelier",
        "PREPA_STUDENT": "étudiant en cycle préparatoire",
        "PREPA_HOLDER": "cycle préparatoire validé",
        "LICENCE_STUDENT": "étudiant en licence",
        "LICENCE_HOLDER": "titulaire d'une licence",
        "MASTER_HOLDER": "titulaire d'un mastère",
        "ECONOMIE_GESTION": "Économie et Gestion",
        "CYBER_NETWORKS": "cybersécurité et réseaux",
        "EMBEDDED_IOT": "systèmes embarqués et IoT",
        "DATA_AI": "Data et intelligence artificielle",
        "PROJECT_INSTITUTIONAL_RULES": "les règles d'admission de l'IIT",
    }

    def validate(
        self,
        answer: str,
        facts: Sequence[RagFact],
        *,
        eligibility_status: EligibilityStatus | None,
    ) -> str:
        cleaned = answer.strip()
        cleaned = humanize_text(cleaned)
        for internal, readable in self.INTERNAL_REPLACEMENTS.items():
            cleaned = re.sub(rf"\b{re.escape(internal)}\b", readable, cleaned, flags=re.I)
        cleaned = re.sub(
            r"\b(?:FLYER|SRC)_[A-Z0-9_]+\b",
            "documentation académique de l'IIT",
            cleaned,
            flags=re.I,
        )
        cleaned = re.sub(
            r"\b(?:ADMISSION|RECOMMANDATION)_[A-Z0-9_]+\b",
            "règle académique",
            cleaned,
            flags=re.I,
        )
        cleaned = re.sub(r"\b[A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+\b", "", cleaned)
        cleaned = re.sub(
            r"\bL['’]IIT propose des métiers(?:\s+comme)?\b",
            "Les formations de l'IIT ouvrent vers des débouchés comme",
            cleaned,
            flags=re.I,
        )
        if any(term in fold_text(cleaned) for term in self.LEAKS):
            return ""
        for pattern in self.FORBIDDEN:
            cleaned = pattern.sub("ce résultat ne peut pas être garanti", cleaned)
        cleaned = self._remove_unsupported_claims(
            cleaned,
            facts,
            eligibility_status=eligibility_status,
        )
        if eligibility_status is EligibilityStatus.NOT_ELIGIBLE:
            cleaned = "\n".join(
                line for line in cleaned.splitlines()
                if "inscri" not in fold_text(line) and "postul" not in fold_text(line)
            )
        return cleaned.strip()

    def _remove_unsupported_claims(
        self,
        answer: str,
        facts: Sequence[RagFact],
        *,
        eligibility_status: EligibilityStatus | None,
    ) -> str:
        entity_types = {fact.entity_type for fact in facts}
        element_types = {fact.element_type for fact in facts if fact.element_type}
        kept: list[str] = []
        for line in answer.splitlines():
            sentences = [
                item.strip()
                for item in re.split(r"(?<=[.!?])\s+", line)
                if item.strip()
            ]
            safe_sentences = [
                sentence
                for sentence in sentences
                if self._claim_is_supported(
                    sentence,
                    entity_types=entity_types,
                    element_types=element_types,
                    eligibility_status=eligibility_status,
                )
            ]
            if safe_sentences:
                kept.append(" ".join(safe_sentences))
        return "\n".join(kept)

    def _claim_is_supported(
        self,
        sentence: str,
        *,
        entity_types: set[str],
        element_types: set[str],
        eligibility_status: EligibilityStatus | None,
    ) -> bool:
        folded = fold_text(sentence)
        uncertainty = any(
            marker in folded
            for marker in ("pas de", "aucun", "inconnu", "non disponible", "a confirmer")
        )
        if self.MONEY.search(sentence) and "TARIF" not in entity_types:
            return False
        if self.DURATION.search(sentence) and "FORMATION" not in entity_types:
            return False
        if (
            self.ACCREDITATION.search(sentence)
            and "ACCREDITATION" not in entity_types
            and not uncertainty
        ):
            return False
        if (
            self.CERTIFICATION.search(sentence)
            and "CERTIFICATION" not in element_types
            and not uncertainty
        ):
            return False
        if self.MOBILITY.search(sentence) and "MOBILITE" not in element_types and not uncertainty:
            return False
        if self.CAREER.search(sentence) and "METIER" not in element_types and not uncertainty:
            return False
        if (
            self.POSITIVE_ADMISSION.search(sentence)
            and eligibility_status in {None, EligibilityStatus.UNKNOWN}
            and not uncertainty
        ):
            return False
        return True

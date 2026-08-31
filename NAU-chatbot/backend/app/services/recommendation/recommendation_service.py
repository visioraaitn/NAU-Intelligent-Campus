from __future__ import annotations

from dataclasses import dataclass

from app.core.file_config import dialogue_config
from app.domain.conversation.models import AcademicProfile, SubjectState
from app.domain.recommendation.schemas import (
    EligibilityStatus,
    RecommendationDecision,
    RecommendationOption,
)
from app.models.sqlalchemy import Formation, Specialisation
from app.repositories.academic import PageRequest, ParcoursRepository
from app.services.academic.catalog_service import AcademicCatalogService
from app.services.dialogue.normalizer import contains_phrase, fold_text
from app.services.eligibility import EligibilityService


PROFILE_PARCOURS = {
    AcademicProfile.PREPA_STUDENT: {"INGENIEUR"},
    AcademicProfile.PREPA_HOLDER: {"INGENIEUR"},
    AcademicProfile.LICENCE_STUDENT: {"INGENIEUR"},
    AcademicProfile.LICENCE_HOLDER: {"INGENIEUR"},
    AcademicProfile.MASTER_HOLDER: {"INGENIEUR"},
}


class RecommendationService:
    def __init__(self, catalogue: AcademicCatalogService, eligibility: EligibilityService) -> None:
        self.catalogue = catalogue
        self.eligibility = eligibility
        self.interest_keywords = dialogue_config().interest_keywords

    async def recommend(self, subject: SubjectState) -> RecommendationDecision:
        allowed_parcours = self._allowed_parcours(subject)
        if not allowed_parcours:
            return RecommendationDecision(None, None)
        parcours_page = await self.catalogue.parcours.list(PageRequest(page_size=100))
        parcours_codes = {item.id: item.code for item in parcours_page.items}
        formations_page = await self.catalogue.formations.list(PageRequest(page_size=100))
        candidates: list[RecommendationOption] = []
        has_specific_interests = any(
            interest != "GENERAL_INFO" for interest in subject.interests
        )
        for formation in formations_page.items:
            parcours_code = parcours_codes.get(formation.parcours_id)
            if parcours_code not in allowed_parcours:
                continue
            if not self._formation_matches_academic_domain(subject, formation.code):
                continue
            formation_identity = fold_text(
                " ".join(
                    filter(
                        None,
                        (
                            formation.code,
                            formation.nom,
                            getattr(formation, "intitule_diplome", None),
                        ),
                    )
                )
            )
            if (
                "INFORMATIQUE" in subject.rejected_domains
                and (
                    "INFO" in formation.code.upper().split("_")
                    or contains_phrase(formation_identity, "informatique")
                )
            ):
                continue
            specs = (
                await self.catalogue.specialisations.list(
                    PageRequest(page_size=100, filters={"formation_id": formation.id})
                )
            ).items
            options: list[Specialisation | None] = list(specs) if has_specific_interests else [None]
            elements = (
                await self.catalogue.elements.list(
                    PageRequest(page_size=100, filters={"formation_id": formation.id})
                )
            ).items
            for spec in options:
                if formation.code in subject.rejected_offers or (spec and spec.code in subject.rejected_offers):
                    continue
                decision = await self.eligibility.evaluate(subject, formation, spec)
                if decision.status is EligibilityStatus.NOT_ELIGIBLE:
                    continue
                relevant = [item for item in elements if item.specialisation_id in (None, spec.id if spec else None)]
                corpus = fold_text(" ".join(filter(None, [formation.nom, formation.description, spec.nom if spec else None, spec.description if spec else None, *(item.nom for item in relevant), *(item.description or "" for item in relevant)])))
                score = 1.0 if decision.status is EligibilityStatus.ELIGIBLE else 0.0
                for interest in subject.interests:
                    score += sum(
                        1.0
                        for term in self.interest_keywords.get(interest, [])
                        if contains_phrase(corpus, term)
                    )
                normalized_target = {
                    "ENGINEERING": "INGENIEUR",
                    "PREPA": "PREPA",
                    "LICENCE": "LICENCE",
                }.get(subject.target or "")
                if normalized_target and parcours_code == normalized_target:
                    score += 2.0
                if (
                    subject.profile is AcademicProfile.NEW_BAC
                    and subject.bac_specialty in {"MATH", "SCIENCES"}
                    and subject.target != "LICENCE"
                    and parcours_code == "PREPA"
                ):
                    score += 3.0
                candidates.append(
                    RecommendationOption(
                        formation.id,
                        formation.code,
                        formation.nom,
                        spec.id if spec else None,
                        spec.code if spec else None,
                        spec.nom if spec else None,
                        score,
                        decision,
                        tuple(item.id for item in relevant[:12]),
                    )
                )
        eligible_candidates = [
            item
            for item in candidates
            if item.eligibility.status is EligibilityStatus.ELIGIBLE
        ]
        if eligible_candidates:
            candidates = eligible_candidates
        elif subject.profile is AcademicProfile.NEW_BAC:
            return RecommendationDecision(None, None)
        candidates.sort(
            key=lambda item: (
                -item.score,
                item.formation_code,
                item.specialisation_code or "",
            )
        )
        if not candidates:
            return RecommendationDecision(None, None)
        primary = candidates[0]
        if has_specific_interests:
            secondary = next(
                (
                    item
                    for item in candidates[1:]
                    if (item.formation_id, item.specialisation_id)
                    != (primary.formation_id, primary.specialisation_id)
                ),
                None,
            )
        else:
            secondary = next(
                (item for item in candidates[1:] if item.formation_id != primary.formation_id),
                None,
            )
        alternatives = tuple(
            item
            for index, item in enumerate(candidates[1:])
            if item.formation_id != primary.formation_id
            and item.formation_id
            not in {candidate.formation_id for candidate in candidates[1:index + 1]}
        )
        label = primary.specialisation_name or primary.formation_name
        if subject.profile is AcademicProfile.NEW_BAC and subject.bac_specialty in {"MATH", "SCIENCES"}:
            reasons = [
                f"Avec ce bac scientifique, {label} est la voie prioritaire vers un cycle ingénieur; les licences admissibles restent des alternatives à comparer."
            ]
        elif subject.profile is AcademicProfile.NEW_BAC:
            reasons = [
                f"Avec cette section de bac, {label} est une formation de niveau licence compatible avec les règles d'admission connues."
            ]
        elif has_specific_interests:
            reasons = [f"{label} correspond le mieux aux intérêts et au profil explicitement connus."]
        else:
            reasons = [f"{label} correspond au niveau d'études actuellement connu."]
        if primary.eligibility.status is EligibilityStatus.UNKNOWN:
            reasons.append("L'éligibilité doit encore être confirmée à partir des informations manquantes.")
        challenge = None
        if primary.formation_code == "PREPA_GENERAL" and subject.math_comfort == "LOW":
            challenge = "La Prépa est exigeante en mathématiques; un travail régulier et un accompagnement seront importants."
        return RecommendationDecision(
            primary,
            secondary,
            tuple(reasons),
            challenge,
            provisional=not has_specific_interests,
            alternatives=alternatives,
        )

    @staticmethod
    def _allowed_parcours(subject: SubjectState) -> set[str] | None:
        if subject.profile is AcademicProfile.NEW_BAC:
            if subject.bac_specialty in {"MATH", "SCIENCES"}:
                return {"PREPA", "LICENCE"}
            if subject.bac_specialty:
                return {"LICENCE"}
            return set()
        return PROFILE_PARCOURS.get(subject.profile)

    @staticmethod
    def _formation_matches_academic_domain(
        subject: SubjectState,
        formation_code: str,
    ) -> bool:
        if (
            subject.profile is AcademicProfile.NEW_BAC
            and subject.bac_specialty == "ECONOMIE_GESTION"
        ):
            return formation_code == "LICENCE_INFO"
        if subject.profile not in {
            AcademicProfile.LICENCE_STUDENT,
            AcademicProfile.LICENCE_HOLDER,
        }:
            return True
        specialty = fold_text(subject.licence_specialty or "")
        if any(term in specialty for term in ("info", "logiciel", "reseau", "data", "cyber")):
            return formation_code == "INGENIEUR_INFO"
        if any(term in specialty for term in ("civil", "batiment", "construction")):
            return formation_code == "INGENIEUR_CIVIL"
        if any(term in specialty for term in ("mecan", "maintenance", "industri", "logistique")):
            return formation_code in {"INGENIEUR_MECANIQUE", "INGENIEUR_INDUSTRIEL"}
        if any(term in specialty for term in ("chim", "procede", "energie")):
            return formation_code == "INGENIEUR_PROCEDES"
        return True

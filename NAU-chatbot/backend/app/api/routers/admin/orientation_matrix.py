from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import enforce_admin_rate_limit, require_admin
from app.domain.conversation.models import AcademicProfile, SubjectState
from app.domain.recommendation.schemas import EligibilityStatus
from app.infrastructure.db import get_session
from app.models.schemas.admin import OrientationMatrixResponse
from app.repositories.academic import OrientationRuleRepository, PageRequest
from app.services.academic.catalog_service import AcademicCatalogService
from app.services.dialogue.human_labels import humanize_text
from app.services.eligibility import EligibilityService
from app.services.recommendation import RecommendationService


router = APIRouter(
    prefix="/admin/orientation-matrix",
    tags=["admin:orientation-matrix"],
    dependencies=[Depends(require_admin), Depends(enforce_admin_rate_limit)],
)

BAC_PROFILES = (
    ("BAC_MATH", "Bac Mathématiques", "MATH"),
    ("BAC_SCIENCES", "Bac Sciences expérimentales", "SCIENCES"),
    ("BAC_INFO", "Bac Informatique", "INFORMATIQUE"),
    ("BAC_TECHNIQUE", "Bac Sciences techniques", "TECHNIQUE"),
    ("BAC_ECO", "Bac Économie et Gestion", "ECONOMIE_GESTION"),
    ("BAC_SPORT", "Bac Sport", "SPORT"),
)


@router.get("", response_model=OrientationMatrixResponse)
async def orientation_matrix(
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    catalogue = AcademicCatalogService(session)
    eligibility = EligibilityService(OrientationRuleRepository(session))
    recommender = RecommendationService(catalogue, eligibility)
    formations = (
        await catalogue.formations.list(PageRequest(page_size=100))
    ).items
    parcours = (
        await catalogue.parcours.list(PageRequest(page_size=100))
    ).items
    parcours_names = {item.id: item.nom for item in parcours}
    snapshots = {
        formation.id: await catalogue.formation_snapshot(formation.id)
        for formation in formations
    }

    profiles: list[dict[str, object]] = []
    for code, label, bac_specialty in BAC_PROFILES:
        subject = SubjectState(
            profile=AcademicProfile.NEW_BAC,
            bac_specialty=bac_specialty,
        )
        recommendation = await recommender.recommend(subject)
        recommended_ids = {
            option.formation_id
            for option in (
                recommendation.primary,
                recommendation.secondary,
                *recommendation.alternatives,
            )
            if option is not None
        }
        matrix_formations: list[dict[str, object]] = []
        for formation in formations:
            decision = await eligibility.evaluate(subject, formation)
            evidence = (
                decision.matched_rules
                or decision.failed_rules
            )
            explanation = _explanation(decision.status, evidence, decision.unknown_reasons)
            matrix_formations.append(
                {
                    "formation_id": formation.id,
                    "formation_code": formation.code,
                    "formation_name": formation.nom,
                    "parcours_name": parcours_names.get(formation.parcours_id, "Parcours"),
                    "eligibility": decision.status.value,
                    "explanation": explanation,
                    "rule_codes": [item.rule_code for item in evidence],
                    "source_refs": list(decision.source_refs),
                    "recommended": formation.id in recommended_ids,
                }
            )
        recommendation_label = None
        if recommendation.primary:
            recommendation_label = recommendation.primary.formation_name
            alternative_names = list(
                dict.fromkeys(
                    option.formation_name for option in recommendation.alternatives
                )
            )
            if alternative_names:
                recommendation_label += " ; alternatives : " + ", ".join(
                    alternative_names
                )
        profiles.append(
            {
                "code": code,
                "label": label,
                "policy": (
                    "Le chatbot privilégie le Cycle Préparatoire et affiche aussi les licences admissibles à comparer; jamais de cycle ingénieur direct après le bac."
                    if bac_specialty in {"MATH", "SCIENCES"}
                    else "Le chatbot propose uniquement les licences dont l'admission est confirmée."
                ),
                "recommendation": recommendation_label,
                "formations": matrix_formations,
            }
        )

    diagnostics: list[dict[str, object]] = []
    for formation in formations:
        snapshot = snapshots[formation.id]
        has_rule = any(
            item.type_regle == "ADMISSION" for item in snapshot.orientation_rules
        )
        issues: list[str] = []
        if not has_rule:
            issues.append("Aucune règle d'admission active : le chatbot ne peut pas confirmer l'accès.")
        if not snapshot.tarifs:
            issues.append("Aucun tarif actif : le chatbot doit demander une confirmation à l'IIT.")
        if not snapshot.elements:
            issues.append("Aucun contenu académique actif pour présenter cette formation.")
        diagnostics.append(
            {
                "formation_id": formation.id,
                "formation_name": formation.nom,
                "has_admission_rule": has_rule,
                "has_tariff": bool(snapshot.tarifs),
                "specialisation_count": len(snapshot.specialisations),
                "element_count": len(snapshot.elements),
                "issues": issues,
            }
        )
    return {"profiles": profiles, "diagnostics": diagnostics}


def _explanation(
    status: EligibilityStatus,
    evidence: tuple[object, ...],
    unknown_reasons: tuple[str, ...],
) -> str:
    if status is EligibilityStatus.ELIGIBLE:
        return "Admission compatible avec les règles actives."
    if status is EligibilityStatus.NOT_ELIGIBLE:
        return "Profil non compatible avec les critères actifs."
    if unknown_reasons:
        return humanize_text(unknown_reasons[0])
    if evidence:
        return "Règle à vérifier."
    return "Aucune règle active ne permet de conclure."

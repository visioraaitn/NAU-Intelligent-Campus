from __future__ import annotations

from typing import Any

from app.domain.conversation.models import AcademicProfile, SubjectState
from app.domain.recommendation.schemas import (
    EligibilityDecision,
    EligibilityStatus,
    RuleEvidence,
)
from app.models.sqlalchemy import Formation, RegleOrientation, Specialisation
from app.repositories.academic import OrientationRuleRepository, PageRequest
from app.services.dialogue.normalizer import fold_text


DIPLOMA_BY_PROFILE = {
    AcademicProfile.NEW_BAC: "BAC",
    AcademicProfile.PREPA_STUDENT: "PREPA",
    AcademicProfile.PREPA_HOLDER: "PREPA",
    AcademicProfile.LICENCE_STUDENT: "LICENCE",
    AcademicProfile.LICENCE_HOLDER: "LICENCE",
    AcademicProfile.MASTER_HOLDER: "MASTER",
}

BAC_FAMILIES = {
    "MATH": {"MATH", "SCIENTIFIQUE"},
    "SCIENCES": {"SCIENCES", "SCIENCES_EXPERIMENTALES", "SCIENTIFIQUE"},
    "INFORMATIQUE": {"INFORMATIQUE", "SCIENTIFIQUE"},
    "TECHNIQUE": {"TECHNIQUE"},
    "ECONOMIE_GESTION": {"ECONOMIE_GESTION", "ECONOMIQUE"},
    "LETTERS": {"LETTERS", "LETTRES", "LITTERAIRE"},
    "SPORT": {"SPORT"},
}


class EligibilityService:
    def __init__(self, rules: OrientationRuleRepository) -> None:
        self.rules = rules

    async def evaluate(
        self,
        subject: SubjectState,
        formation: Formation,
        specialisation: Specialisation | None = None,
    ) -> EligibilityDecision:
        page = await self.rules.list(
            PageRequest(
                page_size=100,
                filters={"formation_id": formation.id, "type_regle": "ADMISSION"},
            )
        )
        generic = [
            rule
            for rule in page.items
            if rule.specialisation_id is None
        ]
        specific = (
            [rule for rule in page.items if rule.specialisation_id == specialisation.id]
            if specialisation is not None
            else []
        )
        # A specialization-specific admission policy overrides its formation-level
        # fallback; otherwise a permissive generic rule could mask a scoped failure.
        applicable = specific or generic
        if not applicable:
            return EligibilityDecision(
                EligibilityStatus.UNKNOWN,
                formation.id,
                formation.code,
                specialisation.id if specialisation else None,
                specialisation.code if specialisation else None,
                unknown_reasons=("Aucune règle d'admission active ne couvre ce cas.",),
            )

        matches: list[RuleEvidence] = []
        failures: list[RuleEvidence] = []
        unknown: list[str] = []
        for rule in applicable:
            result, reason = self._evaluate_rule(rule, subject)
            evidence = RuleEvidence(rule.id, rule.code, rule.source_ref, reason)
            if result is True:
                matches.append(evidence)
            elif result is False:
                failures.append(evidence)
            else:
                unknown.append(reason)
        if matches:
            status = EligibilityStatus.ELIGIBLE
        elif failures and not unknown:
            status = EligibilityStatus.NOT_ELIGIBLE
        else:
            status = EligibilityStatus.UNKNOWN
        return EligibilityDecision(
            status,
            formation.id,
            formation.code,
            specialisation.id if specialisation else None,
            specialisation.code if specialisation else None,
            tuple(matches),
            tuple(failures),
            tuple(dict.fromkeys(unknown)),
        )

    def _evaluate_rule(
        self,
        rule: RegleOrientation,
        subject: SubjectState,
    ) -> tuple[bool | None, str]:
        criteria = rule.criteres or {}
        supported = {"diplome", "type_bac", "diplome_origine"}
        unsupported = sorted(set(criteria).difference(supported))
        if unsupported:
            return None, (
                "La règle contient des critères non pris en charge: "
                + ", ".join(unsupported)
                + "."
            )
        if not criteria:
            return None, "La règle d'admission ne contient aucun critère exploitable."
        diploma = DIPLOMA_BY_PROFILE.get(subject.profile)
        if subject.profile in {AcademicProfile.LICENCE_STUDENT, AcademicProfile.PREPA_STUDENT} and not subject.finishing_current_degree:
            return None, "Le diplôme en cours doit être terminé ou validé avant de conclure."
        for key, expected in criteria.items():
            if key == "diplome":
                result = _matches_expected(diploma, expected)
                if result is not True:
                    return result, f"Diplôme requis par {rule.code}: {expected}."
            elif key == "type_bac":
                if subject.bac_specialty is None:
                    return None, "La section du bac est inconnue."
                allowed = _allowed(expected)
                aliases = BAC_FAMILIES.get(subject.bac_specialty, {subject.bac_specialty})
                if not aliases.intersection(allowed):
                    return False, f"Le bac {subject.bac_specialty} ne figure pas dans la liste acceptée."
            elif key == "diplome_origine":
                if not subject.licence_specialty:
                    return None, "La spécialité du diplôme d'origine est inconnue."
                if _credential_label(subject.licence_specialty) not in {_credential_label(item) for item in _allowed(expected)}:
                    return False, "Le diplôme d'origine ne correspond pas à la règle publiée."
        return True, rule.description or f"La règle {rule.code} est satisfaite."


def _allowed(expected: Any) -> set[str]:
    if isinstance(expected, dict) and "in" in expected:
        expected = expected["in"]
    if isinstance(expected, list):
        return {str(item).upper() for item in expected}
    return {str(expected).upper()}


def _credential_label(value: str) -> str:
    """Compare the same title with/without a redundant degree prefix, exactly."""
    words = fold_text(value.replace('_', ' ')).split()
    if len(words) > 1 and words[0] == 'licence':
        words.pop(0)
        if words and words[0] == 'en':
            words.pop(0)
    return ' '.join(words)


def _matches_expected(actual: str | None, expected: Any) -> bool | None:
    if actual is None:
        return None
    return actual.upper() in _allowed(expected)

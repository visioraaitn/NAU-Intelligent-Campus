"""Stable academic-domain values shared across persistence and services."""

from __future__ import annotations

from enum import Enum


class _StringEnum(str, Enum):
    """Enum whose members serialize to their stable string values."""

    def __str__(self) -> str:
        return self.value


class FormationElementType(_StringEnum):
    """Kinds of atomic academic facts supported by the official schema."""

    MODULE = "MODULE"
    COURS = "COURS"
    CONTENU_PROGRAMME = "CONTENU_PROGRAMME"
    COMPETENCE = "COMPETENCE"
    METIER = "METIER"
    DOMAINE_ACTIVITE = "DOMAINE_ACTIVITE"
    CERTIFICATION = "CERTIFICATION"
    LANGUE = "LANGUE"
    MOBILITE = "MOBILITE"
    OUTIL = "OUTIL"
    OPPORTUNITE = "OPPORTUNITE"
    INFORMATION = "INFORMATION"


class OrientationRuleType(_StringEnum):
    """Known rule families; the database column remains forward-compatible text."""

    ADMISSION = "ADMISSION"
    RECOMMANDATION = "RECOMMANDATION"


class TarifStatus(_StringEnum):
    """Known provenance levels for published tariffs."""

    INDICATIF = "INDICATIF"
    CONFIRME = "CONFIRME"



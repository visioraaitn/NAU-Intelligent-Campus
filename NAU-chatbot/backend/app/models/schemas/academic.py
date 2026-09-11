"""Validated academic CRUD contracts shared by the API and administration UI."""
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.domain.academic.enums import FormationElementType

T = TypeVar("T")

class AcademicSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True, str_strip_whitespace=True)

    @field_validator("langues_enseignement", mode="before", check_fields=False)
    @classmethod
    def normalize_languages(cls, value):
        if not isinstance(value, list) or not value:
            raise ValueError("Au moins une langue est requise")
        return list(dict.fromkeys(cls.normalize_language(item) for item in value))

    @field_validator("langue_enseignement", mode="before", check_fields=False)
    @classmethod
    def normalize_language(cls, value):
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Code langue invalide")
        value = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{0,49}", value):
            raise ValueError("Code langue invalide")
        return value

    @model_validator(mode="after")
    def validate_scope_and_dates(self):
        if getattr(self, "parcours_id", None) is not None and hasattr(self, "specialisation_id"):
            if getattr(self, "formation_id", None) is not None or self.specialisation_id is not None:
                raise ValueError("Les portées parcours et formation sont exclusives")
        start, end = getattr(self, "date_debut", None), getattr(self, "date_fin", None)
        if start is not None and end is not None and end < start:
            raise ValueError("La date de fin précède la date de début")
        return self

class AcademicPage(AcademicSchema, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class ParcoursCreate(AcademicSchema):
    code: str = Field(max_length=50, min_length=1)
    nom: str = Field(max_length=255, min_length=1)
    duree_annees: int | None = Field(default=None, gt=0)
    description: str | None = Field(default=None)
    actif: bool = Field(default=True)

class ParcoursUpdate(AcademicSchema):
    code: str | None = Field(default=None, max_length=50, min_length=1)
    nom: str | None = Field(default=None, max_length=255, min_length=1)
    duree_annees: int | None = Field(default=None, gt=0)
    description: str | None = Field(default=None)
    actif: bool | None = Field(default=None)

class ParcoursRead(AcademicSchema):
    id: int
    code: str = Field(max_length=50, min_length=1)
    nom: str = Field(max_length=255, min_length=1)
    duree_annees: int | None = Field(default=None, gt=0)
    description: str | None = Field(default=None)
    actif: bool
    created_at: datetime
    updated_at: datetime

class FormationCreate(AcademicSchema):
    parcours_id: int = Field(gt=0)
    code: str = Field(max_length=100, min_length=1)
    nom: str = Field(max_length=255, min_length=1)
    intitule_diplome: str | None = Field(default=None, max_length=255)
    duree_annees: int | None = Field(default=None, gt=0)
    nb_semestres: int | None = Field(default=None, gt=0)
    credits_total: int | None = Field(default=None, gt=0)
    description: str | None = Field(default=None)
    source_ref: str | None = Field(default=None)
    actif: bool = Field(default=True)
    langues_enseignement: list[str] = Field(min_length=1)

class FormationUpdate(AcademicSchema):
    parcours_id: int | None = Field(default=None, gt=0)
    code: str | None = Field(default=None, max_length=100, min_length=1)
    nom: str | None = Field(default=None, max_length=255, min_length=1)
    intitule_diplome: str | None = Field(default=None, max_length=255)
    duree_annees: int | None = Field(default=None, gt=0)
    nb_semestres: int | None = Field(default=None, gt=0)
    credits_total: int | None = Field(default=None, gt=0)
    description: str | None = Field(default=None)
    source_ref: str | None = Field(default=None)
    actif: bool | None = Field(default=None)
    langues_enseignement: list[str] | None = Field(default=None, min_length=1)

class FormationRead(AcademicSchema):
    id: int
    parcours_id: int = Field(gt=0)
    code: str = Field(max_length=100, min_length=1)
    nom: str = Field(max_length=255, min_length=1)
    intitule_diplome: str | None = Field(default=None, max_length=255)
    duree_annees: int | None = Field(default=None, gt=0)
    nb_semestres: int | None = Field(default=None, gt=0)
    credits_total: int | None = Field(default=None, gt=0)
    description: str | None = Field(default=None)
    source_ref: str | None = Field(default=None)
    actif: bool
    created_at: datetime
    updated_at: datetime
    langues_enseignement: list[str] = Field(min_length=1)

class SpecialisationCreate(AcademicSchema):
    formation_id: int = Field(gt=0)
    code: str = Field(max_length=100, min_length=1)
    nom: str = Field(max_length=255, min_length=1)
    description: str | None = Field(default=None)
    ordre_affichage: int | None = Field(default=None, ge=0)
    source_ref: str | None = Field(default=None)
    actif: bool = Field(default=True)

class SpecialisationUpdate(AcademicSchema):
    formation_id: int | None = Field(default=None, gt=0)
    code: str | None = Field(default=None, max_length=100, min_length=1)
    nom: str | None = Field(default=None, max_length=255, min_length=1)
    description: str | None = Field(default=None)
    ordre_affichage: int | None = Field(default=None, ge=0)
    source_ref: str | None = Field(default=None)
    actif: bool | None = Field(default=None)

class SpecialisationRead(AcademicSchema):
    id: int
    formation_id: int = Field(gt=0)
    code: str = Field(max_length=100, min_length=1)
    nom: str = Field(max_length=255, min_length=1)
    description: str | None = Field(default=None)
    ordre_affichage: int | None = Field(default=None, ge=0)
    source_ref: str | None = Field(default=None)
    actif: bool
    created_at: datetime
    updated_at: datetime

class FormationElementCreate(AcademicSchema):
    formation_id: int | None = Field(default=None, gt=0)
    specialisation_id: int | None = Field(default=None, gt=0)
    parent_id: int | None = Field(default=None, gt=0)
    type_element: FormationElementType
    code: str | None = Field(default=None, max_length=120)
    nom: str = Field(max_length=255, min_length=1)
    description: str | None = Field(default=None)
    organisme: str | None = Field(default=None, max_length=255)
    ordre_affichage: int | None = Field(default=None, ge=0)
    source_ref: str | None = Field(default=None)
    actif: bool = Field(default=True)
    parcours_id: int | None = Field(default=None, gt=0)
    valeur: str | None = Field(default=None)

class FormationElementUpdate(AcademicSchema):
    formation_id: int | None = Field(default=None, gt=0)
    specialisation_id: int | None = Field(default=None, gt=0)
    parent_id: int | None = Field(default=None, gt=0)
    type_element: FormationElementType | None = Field(default=None)
    code: str | None = Field(default=None, max_length=120)
    nom: str | None = Field(default=None, max_length=255, min_length=1)
    description: str | None = Field(default=None)
    organisme: str | None = Field(default=None, max_length=255)
    ordre_affichage: int | None = Field(default=None, ge=0)
    source_ref: str | None = Field(default=None)
    actif: bool | None = Field(default=None)
    parcours_id: int | None = Field(default=None, gt=0)
    valeur: str | None = Field(default=None)

class FormationElementRead(AcademicSchema):
    id: int
    formation_id: int | None = Field(default=None, gt=0)
    specialisation_id: int | None = Field(default=None, gt=0)
    parent_id: int | None = Field(default=None, gt=0)
    type_element: FormationElementType
    code: str | None = Field(default=None, max_length=120)
    nom: str = Field(max_length=255, min_length=1)
    description: str | None = Field(default=None)
    organisme: str | None = Field(default=None, max_length=255)
    ordre_affichage: int | None = Field(default=None, ge=0)
    source_ref: str | None = Field(default=None)
    actif: bool
    created_at: datetime
    updated_at: datetime
    parcours_id: int | None = Field(default=None, gt=0)
    valeur: str | None = Field(default=None)

class TarifCreate(AcademicSchema):
    formation_id: int | None = Field(default=None, gt=0)
    specialisation_id: int | None = Field(default=None, gt=0)
    frais_inscription: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    mensualite: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    nb_mensualites: int | None = Field(default=None, gt=0)
    devise: str = Field(default="TND", max_length=10, min_length=1)
    annee_universitaire: str | None = Field(default=None, max_length=50)
    statut: str = Field(default="INDICATIF", max_length=50, min_length=1)
    remarque: str | None = Field(default=None)
    source_ref: str | None = Field(default=None)
    actif: bool = Field(default=True)
    langue_enseignement: str | None = Field(default=None, max_length=50)
    parcours_id: int | None = Field(default=None, gt=0)

class TarifUpdate(AcademicSchema):
    formation_id: int | None = Field(default=None, gt=0)
    specialisation_id: int | None = Field(default=None, gt=0)
    frais_inscription: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    mensualite: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    nb_mensualites: int | None = Field(default=None, gt=0)
    devise: str | None = Field(default=None, max_length=10, min_length=1)
    annee_universitaire: str | None = Field(default=None, max_length=50)
    statut: str | None = Field(default=None, max_length=50, min_length=1)
    remarque: str | None = Field(default=None)
    source_ref: str | None = Field(default=None)
    actif: bool | None = Field(default=None)
    langue_enseignement: str | None = Field(default=None, max_length=50)
    parcours_id: int | None = Field(default=None, gt=0)

class TarifRead(AcademicSchema):
    id: int
    formation_id: int | None = Field(default=None, gt=0)
    specialisation_id: int | None = Field(default=None, gt=0)
    frais_inscription: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    mensualite: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    nb_mensualites: int | None = Field(default=None, gt=0)
    devise: str = Field(max_length=10, min_length=1)
    annee_universitaire: str | None = Field(default=None, max_length=50)
    statut: str = Field(max_length=50, min_length=1)
    remarque: str | None = Field(default=None)
    source_ref: str | None = Field(default=None)
    actif: bool
    created_at: datetime
    updated_at: datetime
    langue_enseignement: str | None = Field(default=None, max_length=50)
    parcours_id: int | None = Field(default=None, gt=0)

class RegleOrientationCreate(AcademicSchema):
    formation_id: int = Field(gt=0)
    specialisation_id: int | None = Field(default=None, gt=0)
    code: str = Field(max_length=100, min_length=1)
    nom: str = Field(max_length=255, min_length=1)
    type_regle: str = Field(max_length=50, min_length=1)
    criteres: dict[str, Any] = Field(default_factory=dict)
    description: str | None = Field(default=None)
    priorite: int = Field(default=1, gt=0)
    source_ref: str | None = Field(default=None)
    actif: bool = Field(default=True)

class RegleOrientationUpdate(AcademicSchema):
    formation_id: int | None = Field(default=None, gt=0)
    specialisation_id: int | None = Field(default=None, gt=0)
    code: str | None = Field(default=None, max_length=100, min_length=1)
    nom: str | None = Field(default=None, max_length=255, min_length=1)
    type_regle: str | None = Field(default=None, max_length=50, min_length=1)
    criteres: dict[str, Any] | None = Field(default=None)
    description: str | None = Field(default=None)
    priorite: int | None = Field(default=None, gt=0)
    source_ref: str | None = Field(default=None)
    actif: bool | None = Field(default=None)

class RegleOrientationRead(AcademicSchema):
    id: int
    formation_id: int = Field(gt=0)
    specialisation_id: int | None = Field(default=None, gt=0)
    code: str = Field(max_length=100, min_length=1)
    nom: str = Field(max_length=255, min_length=1)
    type_regle: str = Field(max_length=50, min_length=1)
    criteres: dict[str, Any]
    description: str | None = Field(default=None)
    priorite: int = Field(gt=0)
    source_ref: str | None = Field(default=None)
    actif: bool
    created_at: datetime
    updated_at: datetime

class AccreditationCreate(AcademicSchema):
    formation_id: int = Field(gt=0)
    code: str = Field(max_length=100, min_length=1)
    nom: str = Field(max_length=255, min_length=1)
    organisme: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None)
    date_debut: date | None = Field(default=None)
    date_fin: date | None = Field(default=None)
    source_ref: str | None = Field(default=None)
    actif: bool = Field(default=True)

class AccreditationUpdate(AcademicSchema):
    formation_id: int | None = Field(default=None, gt=0)
    code: str | None = Field(default=None, max_length=100, min_length=1)
    nom: str | None = Field(default=None, max_length=255, min_length=1)
    organisme: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None)
    date_debut: date | None = Field(default=None)
    date_fin: date | None = Field(default=None)
    source_ref: str | None = Field(default=None)
    actif: bool | None = Field(default=None)

class AccreditationRead(AcademicSchema):
    id: int
    formation_id: int = Field(gt=0)
    code: str = Field(max_length=100, min_length=1)
    nom: str = Field(max_length=255, min_length=1)
    organisme: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None)
    date_debut: date | None = Field(default=None)
    date_fin: date | None = Field(default=None)
    source_ref: str | None = Field(default=None)
    actif: bool
    created_at: datetime
    updated_at: datetime

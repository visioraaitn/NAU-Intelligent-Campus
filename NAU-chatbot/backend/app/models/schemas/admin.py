"""Administration response contracts, including resolved catalogue views."""
from datetime import datetime
from decimal import Decimal
from typing import Any, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from app.models.schemas.academic import (
    AccreditationRead, FormationElementRead, FormationRead, RegleOrientationRead,
    ParcoursRead, SpecialisationRead, TarifRead,
)

T = TypeVar('T')


class AdminSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MutationResponse(AdminSchema, Generic[T]):
    entity: T | None
    action: str
    indexing_status: str
    event_ids: list[UUID]


class RagQueueResponse(AdminSchema):
    queued: int
    event_ids: list[UUID]


class RagJob(AdminSchema):
    event_id: UUID
    entity_type: str
    entity_id: int
    formation_id: int | None
    action: str
    occurred_at: datetime
    updated_at: datetime
    attempt: int
    state: str
    detail: str | None = None


class RagStatusResponse(AdminSchema):
    jobs: list[RagJob]


class EffectiveFormationElement(AdminSchema):
    element: FormationElementRead
    scope: Literal['GLOBAL', 'PARCOURS', 'FORMATION', 'SPECIALISATION']


class EffectiveTarifRead(AdminSchema):
    parcours_id: int
    formation_id: int
    specialisation_id: int | None
    langue_enseignement: str | None
    frais_inscription: Decimal | None
    mensualite: Decimal | None
    nb_mensualites: int | None
    devise: str
    annee_universitaire: str | None
    statut: str
    remarque: str | None
    source_ref: str | None
    field_origins: dict[str, str]
    source_tarif_ids: list[int]


class RagDocumentPreview(AdminSchema):
    document_id: str
    content: str
    metadata: dict[str, Any]


class AcademicFormationOverview(AdminSchema):
    parcours: ParcoursRead
    formation: FormationRead
    specialisations: list[SpecialisationRead]
    elements: list[FormationElementRead]
    effective_elements: list[EffectiveFormationElement]
    tarifs: list[TarifRead]
    effective_tarifs: list[EffectiveTarifRead]
    orientation_rules: list[RegleOrientationRead]
    accreditations: list[AccreditationRead]
    rag_documents: list[RagDocumentPreview]


class AcademicOverviewResponse(AdminSchema):
    formations: list[AcademicFormationOverview]
    global_elements: list[FormationElementRead]
    global_rag_documents: list[RagDocumentPreview]


class AcademicCycleOverviewResponse(AdminSchema):
    parcours: ParcoursRead
    formations: list[FormationRead]
    effective_elements: list[EffectiveFormationElement]
    tarifs: list[TarifRead]


class OrientationMatrixFormation(AdminSchema):
    formation_id: int
    formation_code: str
    formation_name: str
    parcours_name: str
    eligibility: Literal['ELIGIBLE', 'NOT_ELIGIBLE', 'UNKNOWN']
    explanation: str
    rule_codes: list[str]
    source_refs: list[str]
    recommended: bool


class OrientationMatrixProfile(AdminSchema):
    code: str
    label: str
    policy: str
    recommendation: str | None
    formations: list[OrientationMatrixFormation]


class FormationDataDiagnostic(AdminSchema):
    formation_id: int
    formation_name: str
    has_admission_rule: bool
    has_tariff: bool
    specialisation_count: int
    element_count: int
    issues: list[str]


class OrientationMatrixResponse(AdminSchema):
    profiles: list[OrientationMatrixProfile]
    diagnostics: list[FormationDataDiagnostic]

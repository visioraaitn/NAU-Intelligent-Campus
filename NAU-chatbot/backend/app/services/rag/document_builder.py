from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal

from app.core.file_config import RagFileConfig, rag_config
from app.domain.rag.schemas import RagDocument, Scalar
from app.models.sqlalchemy import (
    Accreditation,
    Formation,
    FormationElement,
    RegleOrientation,
    Specialisation,
    Tarif,
)
from app.services.academic.catalog_service import FormationCatalogSnapshot


def _clean(*parts: object) -> str:
    return " ".join(str(part).strip() for part in parts if part not in (None, ""))


def _hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _value(value: object | None) -> Scalar:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


class AcademicDocumentBuilder:
    """Build small, deterministic reference documents from academic rows."""

    def __init__(self, config: RagFileConfig | None = None) -> None:
        self.max_chars = (config or rag_config()).chunk_max_chars

    def build_snapshot(self, snapshot: FormationCatalogSnapshot) -> list[RagDocument]:
        formation = snapshot.formation
        spec_codes = {item.id: item.code for item in snapshot.specialisations}
        documents = [self.formation(formation)]
        documents.extend(self.specialisation(item, formation) for item in snapshot.specialisations)
        documents.extend(self.element(item, formation, spec_codes.get(item.specialisation_id)) for item in snapshot.elements)
        documents.extend(self.tarif(item, formation, spec_codes.get(item.specialisation_id)) for item in snapshot.tarifs)
        documents.extend(self.orientation(item, formation, spec_codes.get(item.specialisation_id)) for item in snapshot.orientation_rules)
        documents.extend(self.accreditation(item, formation) for item in snapshot.accreditations)
        return [document for document in documents if document.metadata["active"] is True]

    def _document(
        self,
        *,
        document_id: str,
        entity_type: str,
        entity_id: int,
        content: str,
        formation_id: int | None,
        formation_code: str | None,
        specialisation_id: int | None = None,
        specialisation_code: str | None = None,
        element_type: str | None = None,
        source_ref: str | None = None,
        active: bool = True,
        updated_at: datetime | None = None,
    ) -> RagDocument:
        if len(content) > self.max_chars:
            raise ValueError(
                f"RAG document {document_id} exceeds {self.max_chars} characters; "
                "keep the source row concise or split details into atomic formation elements"
            )
        metadata: dict[str, Scalar] = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "formation_id": _value(formation_id),
            "formation_code": _value(formation_code),
            "specialisation_id": _value(specialisation_id),
            "specialisation_code": _value(specialisation_code),
            "element_type": _value(element_type),
            "source_ref": _value(source_ref),
            "active": active,
            "updated_at": _value(updated_at),
        }
        metadata["content_hash"] = _hash(
            content
            + "\n"
            + json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        )
        return RagDocument(document_id, content, metadata)

    def formation(self, row: Formation) -> RagDocument:
        content = _clean("Formation:", row.nom + ".", row.intitule_diplome, row.description, f"Durée: {row.duree_annees} ans." if row.duree_annees else None, f"Semestres: {row.nb_semestres}." if row.nb_semestres else None)
        return self._document(document_id=f"formation:{row.id}", entity_type="FORMATION", entity_id=row.id, content=content, formation_id=row.id, formation_code=row.code, source_ref=row.source_ref, active=row.actif, updated_at=row.updated_at)

    def specialisation(self, row: Specialisation, formation: Formation) -> RagDocument:
        content = _clean(f"Spécialisation {row.nom} de {formation.nom}.", row.description)
        return self._document(document_id=f"specialisation:{row.id}", entity_type="SPECIALISATION", entity_id=row.id, content=content, formation_id=formation.id, formation_code=formation.code, specialisation_id=row.id, specialisation_code=row.code, source_ref=row.source_ref, active=row.actif, updated_at=row.updated_at)

    def element(self, row: FormationElement, formation: Formation | None, spec_code: str | None) -> RagDocument:
        labels = {
            "MODULE": "Module",
            "COURS": "Cours",
            "CONTENU_PROGRAMME": "Contenu étudié",
            "COMPETENCE": "Compétence développée",
            "METIER": "Débouché possible",
            "DOMAINE_ACTIVITE": "Secteur d'activité",
            "CERTIFICATION": "Certification préparée",
            "LANGUE": "Langue d'enseignement",
            "MOBILITE": "Possibilité de mobilité",
            "OUTIL": "Outil étudié",
            "OPPORTUNITE": "Perspective",
            "INFORMATION": "Information académique",
            "LIEN_PREINSCRIPTION": "Lien de pré-inscription",
            "DOCUMENT_INSCRIPTION": "Document d'inscription",
        }
        content = _clean(f"{labels[row.type_element.value]} : {row.nom}.", row.description, f"Organisme: {row.organisme}." if row.organisme else None)
        return self._document(document_id=f"element:{row.id}", entity_type="FORMATION_ELEMENT", entity_id=row.id, content=content, formation_id=row.formation_id, formation_code=formation.code if formation else None, specialisation_id=row.specialisation_id, specialisation_code=spec_code, element_type=row.type_element.value, source_ref=row.source_ref, active=row.actif, updated_at=row.updated_at)

    def tarif(self, row: Tarif, formation: Formation, spec_code: str | None) -> RagDocument:
        content = _clean(f"Tarif {formation.nom}.", f"Inscription: {row.frais_inscription} {row.devise}." if row.frais_inscription is not None else None, f"Mensualité: {row.mensualite} {row.devise} pendant {row.nb_mensualites} mois." if row.mensualite is not None else None, f"Statut: {row.statut}.", row.remarque)
        return self._document(document_id=f"tarif:{row.id}", entity_type="TARIF", entity_id=row.id, content=content, formation_id=formation.id, formation_code=formation.code, specialisation_id=row.specialisation_id, specialisation_code=spec_code, source_ref=row.source_ref, active=row.actif, updated_at=row.updated_at)

    def orientation(self, row: RegleOrientation, formation: Formation, spec_code: str | None) -> RagDocument:
        content = _clean(f"Conditions d'admission pour {formation.nom}.", row.description)
        return self._document(document_id=f"orientation:{row.id}", entity_type="ORIENTATION_RULE", entity_id=row.id, content=content, formation_id=formation.id, formation_code=formation.code, specialisation_id=row.specialisation_id, specialisation_code=spec_code, source_ref=row.source_ref, active=row.actif, updated_at=row.updated_at)

    def accreditation(self, row: Accreditation, formation: Formation) -> RagDocument:
        content = _clean(f"Accréditation {row.nom} pour {formation.nom}.", f"Organisme: {row.organisme}." if row.organisme else None, row.description)
        return self._document(document_id=f"accreditation:{row.id}", entity_type="ACCREDITATION", entity_id=row.id, content=content, formation_id=formation.id, formation_code=formation.code, source_ref=row.source_ref, active=row.actif, updated_at=row.updated_at)

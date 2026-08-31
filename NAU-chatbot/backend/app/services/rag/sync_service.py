from __future__ import annotations

from app.domain.academic.events import (
    AcademicChangeAction,
    AcademicEntityChanged,
    AcademicEntityType,
)
from app.core.exceptions import NotFoundError
from app.models.sqlalchemy import FormationElement
from app.repositories.academic import PageRequest
from app.repositories.chroma import ChromaRepository
from app.services.academic.catalog_service import AcademicCatalogService
from app.services.rag.document_builder import AcademicDocumentBuilder
from app.services.rag.indexer import IndexResult, RagIndexer


ID_PREFIX = {
    AcademicEntityType.FORMATION: "formation",
    AcademicEntityType.SPECIALISATION: "specialisation",
    AcademicEntityType.FORMATION_ELEMENT: "element",
    AcademicEntityType.TARIF: "tarif",
    AcademicEntityType.ORIENTATION_RULE: "orientation",
    AcademicEntityType.ACCREDITATION: "accreditation",
}


class RagSyncService:
    def __init__(
        self,
        catalogue: AcademicCatalogService,
        indexer: RagIndexer,
        repository: ChromaRepository,
    ) -> None:
        self.catalogue = catalogue
        self.indexer = indexer
        self.repository = repository
        self.builder = AcademicDocumentBuilder()

    async def process(self, event: AcademicEntityChanged) -> IndexResult:
        if event.entity_type is AcademicEntityType.CATALOGUE:
            return await self._reconcile_catalogue()
        if event.action in {
            AcademicChangeAction.DELETED,
            AcademicChangeAction.DEACTIVATED,
        }:
            await self._remove(event)
            return IndexResult(considered=1, upserted=0, skipped=0, deleted=1)

        if event.formation_id is not None:
            try:
                snapshot = await self.catalogue.formation_snapshot(event.formation_id)
            except NotFoundError:
                await self.repository.delete_where(
                    {"formation_id": {"$eq": event.formation_id}}
                )
                return IndexResult(considered=0, upserted=0, skipped=0, deleted=1)
            return await self.indexer.reconcile(
                self.builder.build_snapshot(snapshot),
                where={"formation_id": {"$eq": event.formation_id}},
            )

        if event.entity_type is AcademicEntityType.FORMATION_ELEMENT:
            element = await self.catalogue.elements.require(
                event.entity_id,
                include_inactive=True,
            )
            document = self.builder.element(element, None, None)
            return await self.indexer.index([document])

        # A parcours with no active formation has no derived document of its own.
        return IndexResult(considered=0, upserted=0, skipped=0, deleted=0)

    async def _reconcile_catalogue(self) -> IndexResult:
        documents = []
        page_number = 1
        while True:
            page = await self.catalogue.formations.list(
                PageRequest(page=page_number, page_size=100)
            )
            for formation in page.items:
                snapshot = await self.catalogue.formation_snapshot(formation.id)
                documents.extend(self.builder.build_snapshot(snapshot))
            if page_number >= page.pages:
                break
            page_number += 1

        page_number = 1
        while True:
            page = await self.catalogue.elements.list(
                PageRequest(
                    page=page_number,
                    page_size=100,
                    filters={"formation_id": None},
                )
            )
            documents.extend(
                self.builder.element(element, None, None) for element in page.items
            )
            if page_number >= page.pages:
                break
            page_number += 1
        return await self.indexer.reconcile(documents)

    async def _remove(self, event: AcademicEntityChanged) -> None:
        if (
            event.entity_type is AcademicEntityType.PARCOURS
            and event.formation_id is not None
        ):
            await self.repository.delete_where(
                {"formation_id": {"$eq": event.formation_id}}
            )
            return
        if event.entity_type is AcademicEntityType.FORMATION:
            await self.repository.delete_where({"formation_id": {"$eq": event.entity_id}})
            return
        if event.entity_type is AcademicEntityType.SPECIALISATION:
            await self.repository.delete_where(
                {"specialisation_id": {"$eq": event.entity_id}}
            )
            return
        prefix = ID_PREFIX.get(event.entity_type)
        if prefix:
            await self.repository.delete_ids([f"{prefix}:{event.entity_id}"])

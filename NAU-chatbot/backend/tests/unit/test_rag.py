from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.domain.academic.events import (
    AcademicChangeAction,
    AcademicEntityChanged,
    AcademicEntityType,
)
from app.domain.rag.schemas import RagDocument, RagQueryPlan, RetrievedChunk
from app.services.academic.catalog_service import FormationCatalogSnapshot
from app.services.rag.indexer import IndexResult, RagIndexer
from app.services.rag.metadata_filters import MetadataFilterBuilder
from app.services.rag.query_planner import RagQueryPlanner
from app.services.rag.retriever import RagRetriever
from app.services.rag.sync_service import RagSyncService


pytestmark = pytest.mark.unit


def test_metadata_filter_always_excludes_inactive_documents() -> None:
    assert MetadataFilterBuilder.build(RagQueryPlan(query="formations")) == {
        "active": {"$eq": True}
    }


def test_metadata_filter_combines_all_academic_scopes() -> None:
    plan = RagQueryPlan(
        query="modules SDIA",
        formation_code="INGENIEUR_INFO",
        specialisation_code="SDIA",
        entity_type="FORMATION_ELEMENT",
        element_type="CONTENU_PROGRAMME",
    )

    assert MetadataFilterBuilder.build(plan) == {
        "$and": [
            {"active": {"$eq": True}},
            {"formation_code": {"$eq": "INGENIEUR_INFO"}},
            {"entity_type": {"$eq": "FORMATION_ELEMENT"}},
            {"element_type": {"$eq": "CONTENU_PROGRAMME"}},
            {
                "$or": [
                    {"specialisation_code": {"$eq": "SDIA"}},
                    {"specialisation_code": {"$eq": ""}},
                ]
            },
        ]
    }


@pytest.mark.parametrize(
    ("intent", "entity_type", "element_type"),
    [
        ("FEES", "TARIF", None),
        ("ACCREDITATION", "ACCREDITATION", None),
        ("ADMISSION", "ORIENTATION_RULE", None),
        ("CAREERS", "FORMATION_ELEMENT", "METIER"),
        ("PROGRAMME", "FORMATION_ELEMENT", "CONTENU_PROGRAMME"),
        ("CERTIFICATIONS", "FORMATION_ELEMENT", "CERTIFICATION"),
        ("INTERNATIONAL", "FORMATION_ELEMENT", "MOBILITE"),
    ],
)
def test_query_planner_maps_intents_to_allowlisted_metadata(
    intent: str,
    entity_type: str,
    element_type: str | None,
) -> None:
    plan = RagQueryPlanner().plan(
        "question",
        [intent],
        formation_code="INGENIEUR_INFO",
        specialisation_code="SDIA",
    )

    assert plan.entity_type == entity_type
    assert plan.element_type == element_type
    assert plan.formation_code == "INGENIEUR_INFO"
    assert plan.specialisation_code == "SDIA"


class RecordingEmbeddings:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], bool]] = []

    async def embed(self, texts, *, query=False):
        values = list(texts)
        self.calls.append((values, query))
        return [[float(index + 1), 0.5] for index, _ in enumerate(values)]


class RecordingVectorRepository:
    def __init__(self) -> None:
        self.hashes: dict[str, str] = {}
        self.upserts: list[tuple[list[RagDocument], list[list[float]]]] = []
        self.deleted_ids: list[list[str]] = []
        self.deleted_where: list[dict[str, object]] = []
        self.query_where = None
        self.query_limit = None
        self.query_results: list[RetrievedChunk] = []

    async def ids_where(self, where=None):
        del where
        return list(self.hashes)

    async def existing_hashes(self, ids):
        return {item: self.hashes[item] for item in ids if item in self.hashes}

    async def upsert(self, documents, vectors):
        self.upserts.append((list(documents), list(vectors)))

    async def delete_ids(self, ids):
        self.deleted_ids.append(list(ids))

    async def delete_where(self, where):
        self.deleted_where.append(dict(where))

    async def query(self, vector, *, where, limit):
        assert vector
        self.query_where = where
        self.query_limit = limit
        return list(self.query_results)


@pytest.mark.asyncio
async def test_indexer_embeds_only_changed_documents_and_deletes_inactive_ids() -> None:
    repository = RecordingVectorRepository()
    repository.hashes["formation:1"] = "same"
    embeddings = RecordingEmbeddings()
    documents = [
        RagDocument(
            "formation:1",
            "unchanged",
            {"active": True, "content_hash": "same"},
        ),
        RagDocument(
            "tarif:2",
            "new tariff",
            {"active": True, "content_hash": "new"},
        ),
        RagDocument(
            "element:3",
            "inactive module",
            {"active": False, "content_hash": "inactive"},
        ),
    ]

    result = await RagIndexer(repository, embeddings).index(documents)

    assert result == IndexResult(considered=3, upserted=1, skipped=1, deleted=1)
    assert embeddings.calls == [(["new tariff"], False)]
    assert [doc.id for doc in repository.upserts[0][0]] == ["tarif:2"]
    assert repository.deleted_ids == [["element:3"]]


@pytest.mark.asyncio
async def test_full_reconciliation_removes_vectors_absent_from_postgresql_projection() -> None:
    repository = RecordingVectorRepository()
    repository.hashes = {
        "formation:1": "same",
        "element:999": "stale",
    }
    embeddings = RecordingEmbeddings()
    documents = [
        RagDocument(
            "formation:1",
            "unchanged",
            {"active": True, "content_hash": "same"},
        )
    ]

    result = await RagIndexer(repository, embeddings).reconcile(documents)

    assert result == IndexResult(considered=1, upserted=0, skipped=1, deleted=1)
    assert repository.deleted_ids == [["element:999"]]


class FixedReranker:
    async def rerank(self, query, documents):
        del query
        return [float(index) for index, _ in enumerate(documents, start=1)]


@pytest.mark.asyncio
async def test_retriever_passes_active_scoped_filter_and_uses_query_embedding() -> None:
    repository = RecordingVectorRepository()
    repository.query_results = [
        RetrievedChunk(
            id="tarif:3",
            content="Mensualité indicative.",
            metadata={
                "entity_type": "TARIF",
                "entity_id": 3,
                "formation_code": "PREPA_GENERAL",
                "active": True,
            },
            dense_score=0.9,
        )
    ]
    embeddings = RecordingEmbeddings()
    plan = RagQueryPlan(
        query="prix prépa",
        formation_code="PREPA_GENERAL",
        entity_type="TARIF",
    )

    result = await RagRetriever(repository, embeddings, FixedReranker()).retrieve(plan)

    assert embeddings.calls == [(["prix prépa"], True)]
    assert repository.query_where == {
        "$and": [
            {"active": {"$eq": True}},
            {"formation_code": {"$eq": "PREPA_GENERAL"}},
            {"entity_type": {"$eq": "TARIF"}},
        ]
    }
    assert result.facts[0].supporting_chunk_id == "tarif:3"


class SnapshotCatalogue:
    def __init__(self, snapshot: FormationCatalogSnapshot) -> None:
        self.snapshot = snapshot
        self.requested: list[int] = []

    async def formation_snapshot(self, formation_id: int) -> FormationCatalogSnapshot:
        self.requested.append(formation_id)
        return self.snapshot


class CapturingIndexer:
    def __init__(self) -> None:
        self.batches: list[list[RagDocument]] = []

    async def index(self, documents):
        batch = list(documents)
        self.batches.append(batch)
        return IndexResult(len(batch), len(batch), 0, 0)

    async def reconcile(self, documents, *, where=None):
        del where
        return await self.index(documents)


def _snapshot() -> FormationCatalogSnapshot:
    formation = SimpleNamespace(
        id=7,
        code="PREPA_GENERAL",
        nom="Cycle Préparatoire",
        intitule_diplome=None,
        description="Prépa MP",
        duree_annees=2,
        nb_semestres=None,
        source_ref="SRC_PREPA",
        actif=True,
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    tariff = SimpleNamespace(
        id=44,
        formation_id=7,
        specialisation_id=None,
        frais_inscription=Decimal("800.00"),
        mensualite=Decimal("556.00"),
        nb_mensualites=9,
        devise="TND",
        statut="INDICATIF",
        remarque="Tarif public indicatif.",
        source_ref="SRC_PREPA",
        actif=True,
        updated_at=datetime(2026, 1, 2, tzinfo=UTC),
    )
    return FormationCatalogSnapshot(formation, (), (), (tariff,), (), ())


@pytest.mark.asyncio
async def test_incremental_update_reindexes_only_the_affected_formation_snapshot() -> None:
    catalogue = SnapshotCatalogue(_snapshot())
    indexer = CapturingIndexer()
    repository = RecordingVectorRepository()
    sync = RagSyncService(catalogue, indexer, repository)
    event = AcademicEntityChanged(
        entity_type=AcademicEntityType.TARIF,
        entity_id=44,
        formation_id=7,
        action=AcademicChangeAction.UPDATED,
    )

    result = await sync.process(event)

    assert catalogue.requested == [7]
    assert [[doc.id for doc in batch] for batch in indexer.batches] == [
        ["formation:7", "tarif:44"]
    ]
    assert repository.deleted_where == []
    assert result == IndexResult(2, 2, 0, 0)


@pytest.mark.asyncio
async def test_incremental_deactivation_deletes_only_the_entity_scope() -> None:
    catalogue = SnapshotCatalogue(_snapshot())
    indexer = CapturingIndexer()
    repository = RecordingVectorRepository()
    sync = RagSyncService(catalogue, indexer, repository)
    event = AcademicEntityChanged(
        entity_type=AcademicEntityType.SPECIALISATION,
        entity_id=101,
        formation_id=7,
        action=AcademicChangeAction.DEACTIVATED,
    )

    result = await sync.process(event)

    assert catalogue.requested == []
    assert indexer.batches == []
    assert repository.deleted_where == [{"specialisation_id": {"$eq": 101}}]
    assert result == IndexResult(considered=1, upserted=0, skipped=0, deleted=1)


@pytest.mark.asyncio
async def test_parcours_deactivation_removes_each_affected_formation_scope() -> None:
    catalogue = SnapshotCatalogue(_snapshot())
    indexer = CapturingIndexer()
    repository = RecordingVectorRepository()
    sync = RagSyncService(catalogue, indexer, repository)
    event = AcademicEntityChanged(
        entity_type=AcademicEntityType.PARCOURS,
        entity_id=2,
        formation_id=7,
        action=AcademicChangeAction.DEACTIVATED,
    )

    result = await sync.process(event)

    assert catalogue.requested == []
    assert indexer.batches == []
    assert repository.deleted_where == [{"formation_id": {"$eq": 7}}]
    assert result == IndexResult(considered=1, upserted=0, skipped=0, deleted=1)

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.academic.base import AcademicRepository


pytestmark = pytest.mark.unit


class ExampleEntity:
    def __init__(self, **values: object) -> None:
        for name, value in values.items():
            setattr(self, name, value)


class ExampleRepository(AcademicRepository[ExampleEntity]):
    model = ExampleEntity
    writable_fields = frozenset({"code", "actif"})


@pytest.fixture
def session() -> MagicMock:
    return MagicMock(spec=AsyncSession)


@pytest.fixture
def repository(session: MagicMock) -> ExampleRepository:
    return ExampleRepository(session)


async def test_create_refreshes_server_generated_values(
    repository: ExampleRepository,
    session: MagicMock,
) -> None:
    entity = await repository.create({"code": "LICENCE", "actif": True})

    session.add.assert_called_once_with(entity)
    session.flush.assert_awaited_once_with()
    session.refresh.assert_awaited_once_with(entity)


async def test_update_refreshes_server_generated_values(
    repository: ExampleRepository,
    session: MagicMock,
) -> None:
    entity = ExampleEntity(code="OLD", actif=True)

    result = await repository.update(entity, {"code": "NEW"})

    assert result is entity
    assert entity.code == "NEW"
    session.flush.assert_awaited_once_with()
    session.refresh.assert_awaited_once_with(entity)


async def test_set_active_refreshes_server_generated_values(
    repository: ExampleRepository,
    session: MagicMock,
) -> None:
    entity = ExampleEntity(code="LICENCE", actif=True)

    result = await repository.set_active(entity, False)

    assert result is entity
    assert entity.actif is False
    session.flush.assert_awaited_once_with()
    session.refresh.assert_awaited_once_with(entity)

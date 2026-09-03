from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import ConflictError
from app.domain.academic.events import AcademicEntityType
from app.services.admin.academic_service import AcademicAdminService


pytestmark = pytest.mark.unit


async def test_cycle_and_formation_scope_is_rejected() -> None:
    service = AcademicAdminService(AsyncMock(), AsyncMock())

    with pytest.raises(ConflictError, match="simultanément"):
        await service._validate_scoped_values(
            AcademicEntityType.FORMATION_ELEMENT,
            {"parcours_id": 3, "formation_id": 30, "specialisation_id": None},
        )


async def test_specialisation_from_another_formation_is_rejected() -> None:
    session = AsyncMock()
    session.scalar.return_value = 31
    service = AcademicAdminService(session, AsyncMock())

    with pytest.raises(ConflictError, match="n’appartient pas"):
        await service._validate_scoped_values(
            AcademicEntityType.TARIF,
            {"parcours_id": None, "formation_id": 30, "specialisation_id": 301},
        )

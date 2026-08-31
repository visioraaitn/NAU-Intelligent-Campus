from __future__ import annotations

import pytest

from app.api.routers.admin import (
    accreditations_router,
    elements_router,
    formations_router,
    orientation_rules_router,
    parcours_router,
    rag_router,
    specialisations_router,
    tarifs_router,
)
from app.core.dependencies import enforce_admin_rate_limit, require_admin


pytestmark = pytest.mark.unit


ADMIN_ROUTERS = (
    parcours_router,
    formations_router,
    specialisations_router,
    elements_router,
    tarifs_router,
    orientation_rules_router,
    accreditations_router,
    rag_router,
)


@pytest.mark.parametrize("router", ADMIN_ROUTERS)
def test_every_admin_endpoint_requires_access_token_and_admin_rate_limit(router) -> None:
    assert router.routes, f"{router.prefix} unexpectedly has no routes"

    for route in router.routes:
        dependency_calls = {dependency.call for dependency in route.dependant.dependencies}
        assert require_admin in dependency_calls, f"{route.path} is not authentication protected"
        assert enforce_admin_rate_limit in dependency_calls, f"{route.path} has no admin rate limit"


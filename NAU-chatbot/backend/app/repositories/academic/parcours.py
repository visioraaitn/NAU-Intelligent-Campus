from __future__ import annotations

from sqlalchemy import func, select

from app.models.sqlalchemy import Formation, Parcours
from app.repositories.academic.base import AcademicRepository


class ParcoursRepository(AcademicRepository[Parcours]):
    model = Parcours
    resource_name = "parcours"
    writable_fields = frozenset(
        {"code", "nom", "duree_annees", "description", "actif"}
    )
    filter_fields = {
        "code": Parcours.code,
        "duree_annees": Parcours.duree_annees,
        "actif": Parcours.actif,
    }
    search_fields = (Parcours.code, Parcours.nom, Parcours.description)
    order_by = (Parcours.nom.asc(), Parcours.id.asc())

    async def formation_ids(self, parcours_id: int) -> list[int]:
        result = await self.session.scalars(
            select(Formation.id)
            .where(Formation.parcours_id == parcours_id)
            .order_by(Formation.id.asc())
        )
        return list(result.all())

    async def dependency_counts(self, entity_id: int) -> dict[str, int]:
        count = int(
            (
                await self.session.scalar(
                    select(func.count(Formation.id)).where(
                        Formation.parcours_id == entity_id
                    )
                )
            )
            or 0
        )
        return {"formations": count} if count else {}


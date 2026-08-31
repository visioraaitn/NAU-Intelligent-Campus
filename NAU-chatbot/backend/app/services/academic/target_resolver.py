from __future__ import annotations

from dataclasses import dataclass

from app.models.sqlalchemy import Formation, Specialisation
from app.repositories.academic import PageRequest
from app.services.academic.catalog_service import AcademicCatalogService
from app.services.dialogue.normalizer import contains_phrase, fold_text


@dataclass(frozen=True, slots=True)
class AcademicTarget:
    formation: Formation
    specialisation: Specialisation | None = None


class AcademicTargetResolver:
    def __init__(self, catalogue: AcademicCatalogService) -> None:
        self.catalogue = catalogue

    async def resolve(self, message: str) -> AcademicTarget | None:
        text = fold_text(message)
        specs = (await self.catalogue.specialisations.list(PageRequest(page_size=100))).items
        spec_aliases = {
            "licence cyber": "LIC_INFO_CYBER",
            "licrnce cyber": "LIC_INFO_CYBER",
            "cybersecurite": "LIC_INFO_CYBER",
            "big data": "LIC_INFO_BIG_DATA",
            "licence glsi": "LIC_INFO_GLSI",
            "licence iot": "LIC_INFO_IOT",
            "systemes embarques": "LIC_INFO_IOT",
        }
        alias_code = next(
            (code for alias, code in spec_aliases.items() if contains_phrase(text, alias)),
            None,
        )
        if alias_code:
            spec = next((item for item in specs if item.code == alias_code), None)
            if spec:
                return AcademicTarget(
                    await self.catalogue.get_formation(spec.formation_id),
                    spec,
                )
        for spec in specs:
            code = fold_text(spec.code)
            name = fold_text(spec.nom)
            if contains_phrase(text, code) or (
                len(name.split()) > 1 and contains_phrase(text, name)
            ):
                formation = await self.catalogue.get_formation(spec.formation_id)
                return AcademicTarget(formation, spec)
        formations = (await self.catalogue.formations.list(PageRequest(page_size=100))).items
        aliases = {
            "prepa": "PREPA_GENERAL",
            "preparatoire": "PREPA_GENERAL",
            "licence info": "LICENCE_INFO",
            "licence informatique": "LICENCE_INFO",
            "licrnce informatique": "LICENCE_INFO",
            "genie informatique": "INGENIEUR_INFO",
            "cycle ingenieur informatique": "INGENIEUR_INFO",
            "architecture": "ARCHITECTURE_DNA",
            "genie civil": "INGENIEUR_CIVIL",
            "genie industriel": "INGENIEUR_INDUSTRIEL",
            "genie mecanique": "INGENIEUR_MECANIQUE",
            "genie des procedes": "INGENIEUR_PROCEDES",
            "mecatronique": "LICENCE_MECATRONIQUE_SI",
            "electrique": "LICENCE_ELEC_SEIER",
            "informatique": "LICENCE_INFO",
        }
        code = next(
            (value for key, value in aliases.items() if contains_phrase(text, key)),
            None,
        )
        if code:
            match = next((item for item in formations if item.code == code), None)
            if match:
                return AcademicTarget(match)
        for formation in formations:
            name = fold_text(formation.nom)
            if len(name.split()) > 1 and contains_phrase(text, name):
                return AcademicTarget(formation)
        return None

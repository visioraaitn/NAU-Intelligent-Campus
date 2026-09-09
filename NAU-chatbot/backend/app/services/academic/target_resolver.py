from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.models.sqlalchemy import Formation, Specialisation
from app.repositories.academic import PageRequest
from app.services.academic.catalog_service import AcademicCatalogService
from app.services.dialogue.normalizer import contains_phrase, fold_text


@dataclass(frozen=True, slots=True)
class AcademicTarget:
    formation: Formation
    specialisation: Specialisation | None = None


@dataclass(frozen=True, slots=True)
class AcademicTargetResolution:
    target: AcademicTarget | None = None
    unavailable_label: str | None = None


class AcademicTargetResolver:
    def __init__(self, catalogue: AcademicCatalogService) -> None:
        self.catalogue = catalogue

    async def resolve(self, message: str) -> AcademicTarget | None:
        return (await self.resolve_request(message)).target

    @staticmethod
    def is_current_reference(message: str) -> bool:
        text = fold_text(message).strip()
        return bool(re.search(
            r"\b(?:cette|cette?\s+formation|cette?\s+licence|licence\s+hedhi|formation\s+hedhi|"
            r"hedhi\s+licence|hedhi|option|hal\s+option|ce\s+parcours|el\s+formation\s+hedhi|el\s+parcours\s+hedha)\b",
            text,
        ))

    async def resolve_request(self, message: str) -> AcademicTargetResolution:
        text = fold_text(message)
        owned_licence = self._describes_owned_licence(text)
        specs = (await self.catalogue.specialisations.list(PageRequest(page_size=100))).items
        spec_aliases = {
            "cyber": "LIC_INFO_CYBER",
            "licence cyber": "LIC_INFO_CYBER",
            "licrnce cyber": "LIC_INFO_CYBER",
            "cybersecurite": "LIC_INFO_CYBER",
            "big data": "LIC_INFO_BIG_DATA",
            "licence glsi": "LIC_INFO_GLSI",
            "licence genie logiciel": "LIC_INFO_GLSI",
            "genie logiciel": "LIC_INFO_GLSI",
            "licence iot": "LIC_INFO_IOT",
            "systemes embarques": "LIC_INFO_IOT",
            "glsi": "LIC_INFO_GLSI",
            "sdia": "SDIA",
            "arsi": "ARSI",
        }
        alias_code = None if owned_licence else next(
            (code for alias, code in spec_aliases.items() if contains_phrase(text, alias)),
            None,
        )
        if alias_code:
            spec = next((item for item in specs if item.code == alias_code), None)
            if spec:
                return AcademicTargetResolution(
                    AcademicTarget(
                        await self.catalogue.get_formation(spec.formation_id),
                        spec,
                    )
                )
        fuzzy_spec_code = None if owned_licence else self._fuzzy_alias_code(text, spec_aliases)
        if fuzzy_spec_code:
            spec = next((item for item in specs if item.code == fuzzy_spec_code), None)
            if spec:
                return AcademicTargetResolution(
                    AcademicTarget(
                        await self.catalogue.get_formation(spec.formation_id),
                        spec,
                    )
                )
        for spec in (() if owned_licence else specs):
            code = fold_text(spec.code)
            name = fold_text(spec.nom)
            if contains_phrase(text, code) or (
                len(name.split()) > 1 and contains_phrase(text, name)
            ):
                formation = await self.catalogue.get_formation(spec.formation_id)
                return AcademicTargetResolution(AcademicTarget(formation, spec))
        formations = (await self.catalogue.formations.list(PageRequest(page_size=100))).items
        aliases = {
            "prepa": "PREPA_GENERAL",
            "preparatoire": "PREPA_GENERAL",
            "licence info": "LICENCE_INFO",
            "licence informatique": "LICENCE_INFO",
            "licrnce informatique": "LICENCE_INFO",
            "genie informatique": "INGENIEUR_INFO",
            "genie info": "INGENIEUR_INFO",
            "genie inf": "INGENIEUR_INFO",
            "cycle ingenieur informatique": "INGENIEUR_INFO",
            "architecture": "ARCHITECTURE_DNA",
            "genie civil": "INGENIEUR_CIVIL",
            "genie industriel": "INGENIEUR_INDUSTRIEL",
            "genie indus": "INGENIEUR_INDUSTRIEL",
            "genie ind": "INGENIEUR_INDUSTRIEL",
            "genie mecanique": "INGENIEUR_MECANIQUE",
            "genie des procedes": "INGENIEUR_PROCEDES",
            "mecatronique": "LICENCE_MECATRONIQUE_SI",
            "electrique": "LICENCE_ELEC_SEIER",
            "informatique": "LICENCE_INFO",
        }
        if owned_licence:
            aliases = {
                alias: code
                for alias, code in aliases.items()
                if not code.startswith("LICENCE_")
            }
        code = next(
            (value for key, value in aliases.items() if contains_phrase(text, key)),
            None,
        )
        code = code or self._fuzzy_alias_code(text, aliases)
        if code:
            match = next((item for item in formations if item.code == code), None)
            if match:
                return AcademicTargetResolution(AcademicTarget(match))
        for formation in formations:
            if owned_licence and formation.code.startswith("LICENCE_"):
                continue
            name = fold_text(formation.nom)
            if len(name.split()) > 1 and contains_phrase(text, name):
                return AcademicTargetResolution(AcademicTarget(formation))
        return AcademicTargetResolution(
            unavailable_label=(
                None if owned_licence else self._requested_unavailable_offer(text)
            )
        )

    @staticmethod
    def _fuzzy_alias_code(text: str, aliases: dict[str, str]) -> str | None:
        """Resolve a short, slightly misspelled catalogue choice conservatively."""

        candidate = re.sub(r"[^a-z0-9 ]+", " ", text)
        candidate = re.sub(r"\s+", " ", candidate).strip()
        if not 4 <= len(candidate) <= 45 or len(candidate.split()) > 5:
            return None
        scored = sorted(
            (
                (SequenceMatcher(None, candidate, alias).ratio(), code)
                for alias, code in aliases.items()
                if len(alias) >= 4
            ),
            reverse=True,
        )
        if not scored or scored[0][0] < 0.84:
            return None
        if len(scored) > 1 and scored[0][0] - scored[1][0] < 0.04:
            return None
        return scored[0][1]

    @staticmethod
    def _describes_owned_licence(text: str) -> bool:
        return bool(
            re.search(
                r"\b(?:j(?:'|\s)+ai|je\s+suis\s+en|ena|andi|3andi|na9ra)\b"
                r".{0,24}\blicen[cs]e\b",
                text,
            )
            or re.search(
                r"\b(?:titulaire|diplome)\b.{0,24}\blicen[cs]e\b",
                text,
            )
        )

    @staticmethod
    def _requested_unavailable_offer(text: str) -> str | None:
        patterns = (
            re.compile(r"\b(?P<kind>licence|mastere?)\b(?:\s+(?:en|de|d))?\s+(?P<label>[a-z0-9][a-z0-9' ]*)"),
            re.compile(r"\b(?P<kind>cycle ingenieur|genie|ingenierie)\b(?:\s+(?:en|de|d))?\s+(?P<label>[a-z0-9][a-z0-9' ]*)"),
        )
        ownership_cues = (
            "j ai",
            "je suis en",
            "titulaire",
            "diplome en",
            "ena licence",
            "andi licence",
            "3andi licence",
            "na9ra licence",
            "ena njaht fel licence",
            "j ai reussi ma licence",
            "j ai valide ma licence",
            "j ai obtenu ma licence",
        )
        stop_words = {
            "a", "au", "avec", "car", "chez", "dans", "de", "des", "du", "elle",
            "en", "est", "et", "iit", "la", "le", "les", "ou", "par", "pour",
            "propose", "proposee", "proposees", "possible", "que", "qui", "sur", "une",
        }

        for pattern in patterns:
            for match in pattern.finditer(text):
                prefix = text[: match.start()].strip()
                if any(contains_phrase(prefix, cue) for cue in ownership_cues):
                    continue
                words: list[str] = []
                for word in match.group("label").split():
                    if word in stop_words or len(words) == 5:
                        break
                    words.append(word)
                if words:
                    return f"{match.group('kind')} {' '.join(words)}"
        return None

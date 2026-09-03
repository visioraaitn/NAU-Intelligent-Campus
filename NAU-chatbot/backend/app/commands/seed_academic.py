"""Idempotently load the versioned academic catalogue into PostgreSQL."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, TypeVar

import yaml
from sqlalchemy import Select, and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.session import close_database, get_session_factory
from app.models.sqlalchemy.academic import (
    Accreditation,
    Formation,
    FormationElement,
    Parcours,
    RegleOrientation,
    Specialisation,
    Tarif,
)


ModelT = TypeVar("ModelT")
SEED_PATH = Path(__file__).resolve().parents[1] / "data" / "academic_seed.yaml"


def load_seed(path: Path = SEED_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        payload = yaml.safe_load(stream)
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise ValueError("Unsupported or malformed academic seed")
    return payload


async def _one(session: AsyncSession, statement: Select[tuple[ModelT]]) -> ModelT | None:
    return (await session.execute(statement.limit(1))).scalar_one_or_none()


async def _upsert(
    session: AsyncSession,
    model: type[ModelT],
    identity: Mapping[str, Any],
    values: Mapping[str, Any],
) -> ModelT:
    predicates = [getattr(model, key) == value for key, value in identity.items()]
    entity = await _one(session, select(model).where(and_(*predicates)))
    if entity is None:
        entity = model(**identity, **values)
        session.add(entity)
    else:
        for key, value in values.items():
            setattr(entity, key, value)
    await session.flush()
    return entity


def _values(row: Mapping[str, Any], *, omit: set[str]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key not in omit}


async def seed_academic(session: AsyncSession, payload: Mapping[str, Any]) -> dict[str, int]:
    """Seed all entities in dependency order inside the caller's transaction."""

    counts: dict[str, int] = {}
    parcours_by_code: dict[str, Parcours] = {}
    formations_by_code: dict[str, Formation] = {}
    specs_by_key: dict[tuple[str, str], Specialisation] = {}

    for row in payload.get("parcours", []):
        entity = await _upsert(
            session,
            Parcours,
            {"code": row["code"]},
            _values(row, omit={"code"}),
        )
        parcours_by_code[row["code"]] = entity
    counts["parcours"] = len(parcours_by_code)

    for row in payload.get("formations", []):
        parcours = parcours_by_code[row["parcours_code"]]
        values = _values(row, omit={"code", "parcours_code"})
        values["parcours_id"] = parcours.id
        entity = await _upsert(session, Formation, {"code": row["code"]}, values)
        formations_by_code[row["code"]] = entity
    counts["formations"] = len(formations_by_code)

    for row in payload.get("specialisations", []):
        formation = formations_by_code[row["formation_code"]]
        identity = {"formation_id": formation.id, "code": row["code"]}
        values = _values(row, omit={"formation_code", "code"})
        entity = await _upsert(session, Specialisation, identity, values)
        specs_by_key[(row["formation_code"], row["code"])] = entity
    counts["specialisations"] = len(specs_by_key)

    element_count = 0
    for row in payload.get("formation_elements", []):
        parcours_code = row.get("parcours_code")
        parcours = parcours_by_code.get(parcours_code) if parcours_code else None
        if parcours_code and parcours is None:
            raise ValueError(f"unknown parcours code for formation element: {parcours_code}")
        formation_code = row.get("formation_code")
        formation = formations_by_code.get(formation_code) if formation_code else None
        if parcours is not None and formation is not None:
            raise ValueError("a formation element cannot target a parcours and a formation")
        spec_code = row.get("specialisation_code")
        spec = specs_by_key.get((formation_code, spec_code)) if spec_code else None
        code = row.get("code")
        identity: dict[str, Any] = {
            "parcours_id": parcours.id if parcours else None,
            "formation_id": formation.id if formation else None,
            "specialisation_id": spec.id if spec else None,
            "type_element": row["type_element"],
        }
        if code:
            identity["code"] = code
        else:
            identity["code"] = None
            identity["nom"] = row["nom"]
        values = _values(
            row,
            omit={
                "parcours_code",
                "formation_code",
                "specialisation_code",
                *identity.keys(),
            },
        )
        await _upsert(session, FormationElement, identity, values)
        element_count += 1
    counts["formation_elements"] = element_count

    tariff_count = 0
    for row in payload.get("tarifs", []):
        parcours_code = row.get("parcours_code")
        parcours = parcours_by_code.get(parcours_code) if parcours_code else None
        formation_code = row.get("formation_code")
        formation = formations_by_code.get(formation_code) if formation_code else None
        if parcours_code and parcours is None:
            raise ValueError(f"unknown parcours code for tariff: {parcours_code}")
        if parcours is not None and formation is not None:
            raise ValueError("a tariff cannot target a parcours and a formation")
        if parcours is None and formation is None:
            raise ValueError("a tariff must target a parcours or a formation")
        spec_code = row.get("specialisation_code")
        spec = specs_by_key.get((formation_code, spec_code)) if spec_code else None
        identity = {
            "parcours_id": parcours.id if parcours else None,
            "formation_id": formation.id if formation else None,
            "specialisation_id": spec.id if spec else None,
            "langue_enseignement": row.get("langue_enseignement"),
            "source_ref": row.get("source_ref"),
            "statut": row.get("statut", "INDICATIF"),
            "annee_universitaire": row.get("annee_universitaire"),
        }
        values = _values(
            row,
            omit={
                "code",
                "parcours_code",
                "formation_code",
                "specialisation_code",
                *identity.keys(),
            },
        )
        for money_field in ("frais_inscription", "mensualite"):
            if values.get(money_field) is not None:
                values[money_field] = Decimal(str(values[money_field]))
        await _upsert(session, Tarif, identity, values)
        tariff_count += 1
    counts["tarifs"] = tariff_count

    rule_count = 0
    for row in payload.get("orientation_rules", []):
        formation = formations_by_code[row["formation_code"]]
        spec_code = row.get("specialisation_code")
        spec = specs_by_key.get((row["formation_code"], spec_code)) if spec_code else None
        values = _values(
            row,
            omit={"code", "formation_code", "specialisation_code"},
        )
        values.update(
            formation_id=formation.id,
            specialisation_id=spec.id if spec else None,
        )
        await _upsert(session, RegleOrientation, {"code": row["code"]}, values)
        rule_count += 1
    counts["orientation_rules"] = rule_count

    accreditation_count = 0
    for row in payload.get("accreditations", []):
        formation = formations_by_code[row["formation_code"]]
        values = _values(row, omit={"code", "formation_code"})
        for date_field in ("date_debut", "date_fin"):
            if isinstance(values.get(date_field), str):
                values[date_field] = date.fromisoformat(values[date_field])
        await _upsert(
            session,
            Accreditation,
            {"formation_id": formation.id, "code": row["code"]},
            values,
        )
        accreditation_count += 1
    counts["accreditations"] = accreditation_count

    # Reassert prompt-authoritative corrections after every seed operation.
    prepa_rule = await _one(
        session,
        select(RegleOrientation).where(RegleOrientation.code == "ADMISSION_PREPA"),
    )
    if prepa_rule is None:
        raise RuntimeError("ADMISSION_PREPA missing from the academic seed")
    prepa_rule.criteres = {
        "diplome": "BAC",
        "type_bac": {"in": ["MATH", "SCIENCES"]},
    }
    prepa_rule.source_ref = "PROJECT_INSTITUTIONAL_RULES"
    prepa_rule.actif = True

    legacy_rule = await _one(
        session,
        select(RegleOrientation).where(
            RegleOrientation.code == "ADMISSION_LICENCE_GLSI"
        ),
    )
    if legacy_rule is not None:
        legacy_rule.actif = False

    await session.flush()
    return counts


async def async_main() -> None:
    payload = load_seed()
    factory = get_session_factory()
    try:
        async with factory() as session:
            async with session.begin():
                counts = await seed_academic(session, payload)
        print("Academic seed committed: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    finally:
        await close_database()


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()

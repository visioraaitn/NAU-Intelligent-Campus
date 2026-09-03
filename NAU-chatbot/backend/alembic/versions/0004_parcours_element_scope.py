"""Allow parcours-scoped academic elements and consolidate enrollment facts.

Revision ID: 0004_parcours_element_scope
Revises: 0003_teaching_languages
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0004_parcours_element_scope"
down_revision: str | None = "0003_teaching_languages"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SOURCE_REF = "PROJECT_ENROLLMENT_SCOPE_V1"


def upgrade() -> None:
    op.add_column("formation_element", sa.Column("parcours_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_formation_element_parcours_id_parcours",
        "formation_element",
        "parcours",
        ["parcours_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_check_constraint(
        "ck_formation_element_parcours_scope_exclusive",
        "formation_element",
        "parcours_id IS NULL OR (formation_id IS NULL AND specialisation_id IS NULL)",
    )
    op.create_index("ix_fe_parcours", "formation_element", ["parcours_id"])

    op.drop_index("uq_fe_global_code", table_name="formation_element")
    op.drop_index("uq_fe_global_nom", table_name="formation_element")
    _create_scope_indexes()

    op.execute(
        """
        DELETE FROM formation_element
        WHERE type_element = 'INFORMATION'
          AND (
            code = 'INFO_PREINSCRIPTION'
            OR code LIKE 'INFO_%_PREINSCRIPTION'
            OR code LIKE 'INFO_%_PIECES'
            OR lower(nom) LIKE '%pièces d''inscription%'
          )
        """
    )
    op.execute(
        f"""
        INSERT INTO formation_element (
            parcours_id, formation_id, specialisation_id, parent_id,
            type_element, code, nom, description, organisme,
            ordre_affichage, source_ref, actif
        )
        SELECT NULL, NULL, NULL, NULL,
               'INFORMATION', 'INFO_PREINSCRIPTION', 'Préinscription',
               'La préinscription s’effectue via le lien officiel : '
               'https://pre-inscription.iitadmin.com//?fbclid=IwAR1CfciROXUxaOBiXCcmv7DikLDQjD-8cKzEzuVLS9bEsnnZncSTAy96nzY',
               NULL, 1, '{SOURCE_REF}', true
        WHERE NOT EXISTS (
            SELECT 1 FROM formation_element
            WHERE parcours_id IS NULL AND formation_id IS NULL
              AND specialisation_id IS NULL
              AND type_element = 'INFORMATION' AND code = 'INFO_PREINSCRIPTION'
        )
        """
    )
    op.execute(
        f"""
        INSERT INTO formation_element (
            parcours_id, formation_id, specialisation_id, parent_id,
            type_element, code, nom, description, organisme,
            ordre_affichage, source_ref, actif
        )
        SELECT p.id, NULL, NULL, NULL,
               'INFORMATION', 'INFO_PIECES_INSCRIPTION', 'Pièces d’inscription',
               CASE WHEN p.code = 'INGENIEUR' THEN
                 'Pièces demandées : copie conforme du diplôme du Baccalauréat ; '
                 'relevé de notes du Baccalauréat ; copie conforme du diplôme de Licence ; '
                 '3 relevés de notes de Licence ; 3 photos ; règlement intérieur avec '
                 'signature légalisée à la Municipalité ; copie CIN ; pré-inscription.'
               ELSE
                 'Pièces demandées : copie conforme du diplôme du Baccalauréat ; '
                 'relevé de notes du Baccalauréat ; 3 photos ; règlement intérieur avec '
                 'signature légalisée à la Municipalité ; copie CIN ; pré-inscription.'
               END,
               NULL, 2, '{SOURCE_REF}', true
        FROM parcours p
        WHERE p.code IN ('PREPA', 'LICENCE', 'INGENIEUR', 'ARCHITECTURE')
          AND NOT EXISTS (
            SELECT 1 FROM formation_element fe
            WHERE fe.parcours_id = p.id
              AND fe.type_element = 'INFORMATION'
              AND fe.code = 'INFO_PIECES_INSCRIPTION'
          )
        """
    )


def downgrade() -> None:
    op.execute(
        f"DELETE FROM formation_element WHERE source_ref = '{SOURCE_REF}'"
    )
    _drop_scope_indexes()
    op.create_index(
        "uq_fe_global_code",
        "formation_element",
        ["formation_id", "type_element", "code"],
        unique=True,
        postgresql_where=sa.text("specialisation_id IS NULL AND code IS NOT NULL"),
    )
    op.create_index(
        "uq_fe_global_nom",
        "formation_element",
        ["formation_id", "type_element", "nom"],
        unique=True,
        postgresql_where=sa.text("specialisation_id IS NULL AND code IS NULL"),
    )
    op.drop_index("ix_fe_parcours", table_name="formation_element")
    op.drop_constraint(
        "ck_formation_element_parcours_scope_exclusive",
        "formation_element",
        type_="check",
    )
    op.drop_constraint(
        "fk_formation_element_parcours_id_parcours",
        "formation_element",
        type_="foreignkey",
    )
    op.drop_column("formation_element", "parcours_id")


def _create_scope_indexes() -> None:
    op.create_index(
        "uq_fe_global_code",
        "formation_element",
        ["type_element", "code"],
        unique=True,
        postgresql_where=sa.text(
            "parcours_id IS NULL AND formation_id IS NULL "
            "AND specialisation_id IS NULL AND code IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_fe_parcours_code",
        "formation_element",
        ["parcours_id", "type_element", "code"],
        unique=True,
        postgresql_where=sa.text("parcours_id IS NOT NULL AND code IS NOT NULL"),
    )
    op.create_index(
        "uq_fe_formation_code",
        "formation_element",
        ["formation_id", "type_element", "code"],
        unique=True,
        postgresql_where=sa.text(
            "parcours_id IS NULL AND formation_id IS NOT NULL "
            "AND specialisation_id IS NULL AND code IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_fe_global_nom",
        "formation_element",
        ["type_element", "nom"],
        unique=True,
        postgresql_where=sa.text(
            "parcours_id IS NULL AND formation_id IS NULL "
            "AND specialisation_id IS NULL AND code IS NULL"
        ),
    )
    op.create_index(
        "uq_fe_parcours_nom",
        "formation_element",
        ["parcours_id", "type_element", "nom"],
        unique=True,
        postgresql_where=sa.text("parcours_id IS NOT NULL AND code IS NULL"),
    )
    op.create_index(
        "uq_fe_formation_nom",
        "formation_element",
        ["formation_id", "type_element", "nom"],
        unique=True,
        postgresql_where=sa.text(
            "parcours_id IS NULL AND formation_id IS NOT NULL "
            "AND specialisation_id IS NULL AND code IS NULL"
        ),
    )


def _drop_scope_indexes() -> None:
    for name in (
        "uq_fe_global_code",
        "uq_fe_parcours_code",
        "uq_fe_formation_code",
        "uq_fe_global_nom",
        "uq_fe_parcours_nom",
        "uq_fe_formation_nom",
    ):
        op.drop_index(name, table_name="formation_element")

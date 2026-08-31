"""Add teaching languages to formations and tariffs.

Revision ID: 0003_teaching_languages
Revises: 0002_institutional_corrections
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0003_teaching_languages"
down_revision: str | None = "0002_institutional_corrections"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "formation",
        sa.Column(
            "langues_enseignement",
            postgresql.ARRAY(sa.String(length=50)),
            server_default=sa.text("ARRAY['FRANCAIS']::varchar[]"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_formation_langues_enseignement_nonempty",
        "formation",
        "cardinality(langues_enseignement) > 0",
    )
    op.execute(
        """
        UPDATE formation
        SET langues_enseignement = ARRAY['FRANCAIS', 'ANGLAIS']::varchar[]
        WHERE code IN (
            'LICENCE_INFO',
            'LICENCE_ELEC_SEIER',
            'LICENCE_MECATRONIQUE_SI'
        )
        """
    )

    op.add_column(
        "tarif",
        sa.Column(
            "langue_enseignement",
            sa.String(length=50),
            server_default=sa.text("'FRANCAIS'"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_tarif_langue_enseignement_code",
        "tarif",
        "langue_enseignement ~ '^[A-Z0-9][A-Z0-9_-]*$'",
    )
    op.create_index(
        "ix_tarif_formation_langue",
        "tarif",
        ["formation_id", "langue_enseignement"],
    )


def downgrade() -> None:
    op.drop_index("ix_tarif_formation_langue", table_name="tarif")
    op.drop_constraint(
        "ck_tarif_langue_enseignement_code",
        "tarif",
        type_="check",
    )
    op.drop_column("tarif", "langue_enseignement")
    op.drop_constraint(
        "ck_formation_langues_enseignement_nonempty",
        "formation",
        type_="check",
    )
    op.drop_column("formation", "langues_enseignement")

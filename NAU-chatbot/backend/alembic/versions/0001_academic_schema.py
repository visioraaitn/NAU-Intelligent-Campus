"""Create the clean seven-table academic schema.

Revision ID: 0001_academic_schema
Revises: None
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0001_academic_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ELEMENT_TYPES = (
    "'MODULE','COURS','CONTENU_PROGRAMME','COMPETENCE','METIER',"
    "'DOMAINE_ACTIVITE','CERTIFICATION','LANGUE','MOBILITE','OUTIL',"
    "'OPPORTUNITE','INFORMATION'"
)


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "parcours",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("nom", sa.String(255), nullable=False),
        sa.Column("duree_annees", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("actif", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("duree_annees IS NULL OR duree_annees > 0", name="ck_parcours_duree_positive"),
        sa.PrimaryKeyConstraint("id", name="pk_parcours"),
        sa.UniqueConstraint("code", name="uq_parcours_code"),
    )
    op.create_table(
        "formation",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("parcours_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("nom", sa.String(255), nullable=False),
        sa.Column("intitule_diplome", sa.String(255), nullable=True),
        sa.Column("duree_annees", sa.Integer(), nullable=True),
        sa.Column("nb_semestres", sa.Integer(), nullable=True),
        sa.Column("credits_total", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("actif", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("duree_annees IS NULL OR duree_annees > 0", name="ck_formation_duree_positive"),
        sa.CheckConstraint("nb_semestres IS NULL OR nb_semestres > 0", name="ck_formation_semestres_positive"),
        sa.CheckConstraint("credits_total IS NULL OR credits_total > 0", name="ck_formation_credits_positive"),
        sa.ForeignKeyConstraint(["parcours_id"], ["parcours.id"], name="fk_formation_parcours_id_parcours"),
        sa.PrimaryKeyConstraint("id", name="pk_formation"),
        sa.UniqueConstraint("code", name="uq_formation_code"),
    )
    op.create_index("ix_formation_parcours", "formation", ["parcours_id"])
    op.create_table(
        "specialisation",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("formation_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("nom", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("ordre_affichage", sa.Integer(), nullable=True),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("actif", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("ordre_affichage IS NULL OR ordre_affichage >= 0", name="ck_specialisation_ordre_nonnegative"),
        sa.ForeignKeyConstraint(["formation_id"], ["formation.id"], name="fk_specialisation_formation_id_formation", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_specialisation"),
        sa.UniqueConstraint("formation_id", "code", name="uq_specialisation_formation_code"),
        sa.UniqueConstraint("formation_id", "id", name="uq_specialisation_formation_id_id"),
    )
    op.create_index("ix_specialisation_s_formation", "specialisation", ["formation_id"])
    op.create_table(
        "formation_element",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("formation_id", sa.Integer(), nullable=True),
        sa.Column("specialisation_id", sa.Integer(), nullable=True),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("type_element", sa.String(30), nullable=False),
        sa.Column("code", sa.String(120), nullable=True),
        sa.Column("nom", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("organisme", sa.String(255), nullable=True),
        sa.Column("ordre_affichage", sa.Integer(), nullable=True),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("actif", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(f"type_element IN ({ELEMENT_TYPES})", name="ck_formation_element_type_element_values"),
        sa.CheckConstraint("specialisation_id IS NULL OR formation_id IS NOT NULL", name="ck_formation_element_specialisation_requires_formation"),
        sa.CheckConstraint("ordre_affichage IS NULL OR ordre_affichage >= 0", name="ck_formation_element_ordre_nonnegative"),
        sa.ForeignKeyConstraint(["formation_id"], ["formation.id"], name="fk_formation_element_formation_id_formation", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["formation_id", "specialisation_id"], ["specialisation.formation_id", "specialisation.id"], name="fk_fe_formation_specialisation", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["formation_element.id"], name="fk_formation_element_parent_id_formation_element", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_formation_element"),
    )
    op.create_index("ix_fe_formation", "formation_element", ["formation_id"])
    op.create_index("ix_fe_specialisation", "formation_element", ["specialisation_id"])
    op.create_index("ix_fe_parent", "formation_element", ["parent_id"])
    op.create_index("uq_fe_global_code", "formation_element", ["formation_id", "type_element", "code"], unique=True, postgresql_where=sa.text("specialisation_id IS NULL AND code IS NOT NULL"))
    op.create_index("uq_fe_specialisation_code", "formation_element", ["formation_id", "specialisation_id", "type_element", "code"], unique=True, postgresql_where=sa.text("specialisation_id IS NOT NULL AND code IS NOT NULL"))
    op.create_index("uq_fe_global_nom", "formation_element", ["formation_id", "type_element", "nom"], unique=True, postgresql_where=sa.text("specialisation_id IS NULL AND code IS NULL"))
    op.create_index("uq_fe_specialisation_nom", "formation_element", ["formation_id", "specialisation_id", "type_element", "nom"], unique=True, postgresql_where=sa.text("specialisation_id IS NOT NULL AND code IS NULL"))
    op.create_table(
        "tarif",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("formation_id", sa.Integer(), nullable=False),
        sa.Column("specialisation_id", sa.Integer(), nullable=True),
        sa.Column("frais_inscription", sa.Numeric(10, 2), nullable=True),
        sa.Column("mensualite", sa.Numeric(10, 2), nullable=True),
        sa.Column("nb_mensualites", sa.Integer(), nullable=True),
        sa.Column("devise", sa.String(10), server_default=sa.text("'TND'"), nullable=False),
        sa.Column("annee_universitaire", sa.String(50), nullable=True),
        sa.Column("statut", sa.String(50), server_default=sa.text("'INDICATIF'"), nullable=False),
        sa.Column("remarque", sa.Text(), nullable=True),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("actif", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("frais_inscription IS NULL OR frais_inscription >= 0", name="ck_tarif_frais_nonnegative"),
        sa.CheckConstraint("mensualite IS NULL OR mensualite >= 0", name="ck_tarif_mensualite_nonnegative"),
        sa.CheckConstraint("nb_mensualites IS NULL OR nb_mensualites > 0", name="ck_tarif_mensualites_positive"),
        sa.ForeignKeyConstraint(["formation_id"], ["formation.id"], name="fk_tarif_formation_id_formation", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["formation_id", "specialisation_id"], ["specialisation.formation_id", "specialisation.id"], name="fk_tarif_formation_specialisation", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_tarif"),
    )
    op.create_index("ix_tarif_formation", "tarif", ["formation_id"])
    op.create_index("ix_tarif_specialisation", "tarif", ["specialisation_id"])
    op.create_table(
        "regle_orientation",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("formation_id", sa.Integer(), nullable=False),
        sa.Column("specialisation_id", sa.Integer(), nullable=True),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("nom", sa.String(255), nullable=False),
        sa.Column("type_regle", sa.String(50), nullable=False),
        sa.Column("criteres", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priorite", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("actif", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("priorite > 0", name="ck_regle_orientation_priorite_positive"),
        sa.ForeignKeyConstraint(["formation_id"], ["formation.id"], name="fk_regle_orientation_formation_id_formation", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["formation_id", "specialisation_id"], ["specialisation.formation_id", "specialisation.id"], name="fk_regle_formation_specialisation", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_regle_orientation"),
        sa.UniqueConstraint("code", name="uq_regle_orientation_code"),
    )
    op.create_index("ix_regle_orientation_formation", "regle_orientation", ["formation_id"])
    op.create_index("ix_regle_orientation_specialisation", "regle_orientation", ["specialisation_id"])
    op.create_table(
        "accreditation",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("formation_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("nom", sa.String(255), nullable=False),
        sa.Column("organisme", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("date_debut", sa.Date(), nullable=True),
        sa.Column("date_fin", sa.Date(), nullable=True),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("actif", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("date_debut IS NULL OR date_fin IS NULL OR date_fin >= date_debut", name="ck_accreditation_dates_ordered"),
        sa.ForeignKeyConstraint(["formation_id"], ["formation.id"], name="fk_accreditation_formation_id_formation", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_accreditation"),
        sa.UniqueConstraint("formation_id", "code", name="uq_accreditation_formation_code"),
    )
    op.create_index("ix_accreditation_formation", "accreditation", ["formation_id"])


def downgrade() -> None:
    op.drop_table("accreditation")
    op.drop_table("regle_orientation")
    op.drop_table("tarif")
    op.drop_table("formation_element")
    op.drop_table("specialisation")
    op.drop_table("formation")
    op.drop_table("parcours")


"""Structure cycle registration facts and support scoped tariff components.

Revision ID: 0005_cycle_registration_tariffs
Revises: 0004_parcours_element_scope
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0005_cycle_registration_tariffs"
down_revision: str | None = "0004_parcours_element_scope"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ENROLLMENT_SOURCE = "PROJECT_ENROLLMENT_SCOPE_V2"
COMMON_FEE_MARKER = "PROJECT_COMMON_REGISTRATION_FEE_V1"


def upgrade() -> None:
    op.add_column("formation_element", sa.Column("valeur", sa.Text(), nullable=True))
    op.execute(
        "ALTER TABLE formation_element DROP CONSTRAINT "
        "ck_formation_element_ck_formation_element_type_element_values"
    )
    op.execute(
        "ALTER TABLE formation_element ADD CONSTRAINT "
        "ck_formation_element_ck_formation_element_type_element_values CHECK ("
        "type_element IN ('MODULE','COURS','CONTENU_PROGRAMME','COMPETENCE',"
        "'METIER','DOMAINE_ACTIVITE','CERTIFICATION','LANGUE','MOBILITE',"
        "'OUTIL','OPPORTUNITE','INFORMATION','DOCUMENT_INSCRIPTION',"
        "'LIEN_PREINSCRIPTION'))"
    )

    op.add_column("tarif", sa.Column("parcours_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_tarif_parcours_id_parcours",
        "tarif",
        "parcours",
        ["parcours_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_tarif_parcours", "tarif", ["parcours_id"])
    op.alter_column("tarif", "formation_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column(
        "tarif",
        "langue_enseignement",
        existing_type=sa.String(length=50),
        nullable=True,
        server_default=None,
    )
    op.execute(
        "ALTER TABLE tarif DROP CONSTRAINT ck_tarif_ck_tarif_langue_enseignement_code"
    )
    op.execute(
        "ALTER TABLE tarif ADD CONSTRAINT ck_tarif_ck_tarif_langue_enseignement_code "
        "CHECK (langue_enseignement IS NULL OR "
        "langue_enseignement ~ '^[A-Z0-9][A-Z0-9_-]*$')"
    )
    op.create_check_constraint(
        "ck_tarif_parcours_scope_exclusive",
        "tarif",
        "parcours_id IS NULL OR "
        "(formation_id IS NULL AND specialisation_id IS NULL)",
    )
    op.create_check_constraint(
        "ck_tarif_specialisation_requires_formation",
        "tarif",
        "specialisation_id IS NULL OR formation_id IS NOT NULL",
    )
    op.create_check_constraint(
        "ck_tarif_scope_required",
        "tarif",
        "parcours_id IS NOT NULL OR formation_id IS NOT NULL",
    )

    _migrate_registration_elements()
    _migrate_common_registration_fees()


def downgrade() -> None:
    _restore_formation_fees()
    _restore_legacy_registration_elements()

    op.drop_constraint("ck_tarif_scope_required", "tarif", type_="check")
    op.drop_constraint(
        "ck_tarif_specialisation_requires_formation",
        "tarif",
        type_="check",
    )
    op.drop_constraint("ck_tarif_parcours_scope_exclusive", "tarif", type_="check")
    op.execute(
        "ALTER TABLE tarif DROP CONSTRAINT ck_tarif_ck_tarif_langue_enseignement_code"
    )
    op.execute(
        "ALTER TABLE tarif ADD CONSTRAINT ck_tarif_ck_tarif_langue_enseignement_code "
        "CHECK (langue_enseignement ~ '^[A-Z0-9][A-Z0-9_-]*$')"
    )
    op.execute(
        "UPDATE tarif SET langue_enseignement = 'FRANCAIS' "
        "WHERE langue_enseignement IS NULL"
    )
    op.alter_column(
        "tarif",
        "langue_enseignement",
        existing_type=sa.String(length=50),
        nullable=False,
        server_default=sa.text("'FRANCAIS'"),
    )
    op.alter_column("tarif", "formation_id", existing_type=sa.Integer(), nullable=False)
    op.drop_index("ix_tarif_parcours", table_name="tarif")
    op.drop_constraint(
        "fk_tarif_parcours_id_parcours",
        "tarif",
        type_="foreignkey",
    )
    op.drop_column("tarif", "parcours_id")

    op.execute(
        "ALTER TABLE formation_element DROP CONSTRAINT "
        "ck_formation_element_ck_formation_element_type_element_values"
    )
    op.execute(
        "ALTER TABLE formation_element ADD CONSTRAINT "
        "ck_formation_element_ck_formation_element_type_element_values CHECK ("
        "type_element IN ('MODULE','COURS','CONTENU_PROGRAMME','COMPETENCE',"
        "'METIER','DOMAINE_ACTIVITE','CERTIFICATION','LANGUE','MOBILITE',"
        "'OUTIL','OPPORTUNITE','INFORMATION'))"
    )
    op.drop_column("formation_element", "valeur")


def _migrate_registration_elements() -> None:
    op.execute(
        """
        DELETE FROM formation_element
        WHERE source_ref IN ('PROJECT_ENROLLMENT_SCOPE_V1', 'PROJECT_ENROLLMENT_SCOPE_V2')
           OR code = 'INFO_PREINSCRIPTION'
           OR code = 'INFO_PIECES_INSCRIPTION'
        """
    )
    op.execute(
        f"""
        INSERT INTO formation_element (
            parcours_id, formation_id, specialisation_id, parent_id,
            type_element, code, nom, valeur, ordre_affichage, source_ref, actif
        ) VALUES (
            NULL, NULL, NULL, NULL,
            'LIEN_PREINSCRIPTION', 'PREINSCRIPTION_URL', 'Préinscription IIT',
            'https://pre-inscription.iitadmin.com//?fbclid=IwAR1CfciROXUxaOBiXCcmv7DikLDQjD-8cKzEzuVLS9bEsnnZncSTAy96nzY',
            1, '{ENROLLMENT_SOURCE}', true
        )
        """
    )
    op.execute(
        f"""
        INSERT INTO formation_element (
            parcours_id, formation_id, specialisation_id, parent_id,
            type_element, code, nom, ordre_affichage, source_ref, actif
        )
        SELECT p.id, NULL, NULL, NULL, 'DOCUMENT_INSCRIPTION', document.code,
               document.nom, document.ordre, '{ENROLLMENT_SOURCE}', true
        FROM parcours p
        CROSS JOIN (
            VALUES
                ('DOC_BAC', 'Copie conforme du diplôme du Baccalauréat', 10),
                ('DOC_RELEVE_BAC', 'Relevé de notes du Baccalauréat', 20),
                ('DOC_PHOTOS', '3 photos', 50),
                ('DOC_REGLEMENT', 'Règlement intérieur avec signature légalisée à la Municipalité', 60),
                ('DOC_CIN', 'Copie CIN', 70),
                ('DOC_PREINSCRIPTION', 'Pré-inscription', 80)
        ) AS document(code, nom, ordre)
        WHERE p.code IN ('PREPA', 'LICENCE', 'INGENIEUR', 'ARCHITECTURE')
        """
    )
    op.execute(
        f"""
        INSERT INTO formation_element (
            parcours_id, formation_id, specialisation_id, parent_id,
            type_element, code, nom, ordre_affichage, source_ref, actif
        )
        SELECT p.id, NULL, NULL, NULL, 'DOCUMENT_INSCRIPTION', document.code,
               document.nom, document.ordre, '{ENROLLMENT_SOURCE}', true
        FROM parcours p
        CROSS JOIN (
            VALUES
                ('DOC_LICENCE', 'Copie conforme du diplôme de Licence', 30),
                ('DOC_RELEVES_LICENCE', '3 relevés de notes de Licence', 40)
        ) AS document(code, nom, ordre)
        WHERE p.code = 'INGENIEUR'
        """
    )


def _migrate_common_registration_fees() -> None:
    op.execute(
        f"""
        WITH supported AS (
            SELECT DISTINCT ON (f.parcours_id)
                   f.parcours_id, t.frais_inscription, t.devise, t.statut,
                   t.source_ref
            FROM tarif t
            JOIN formation f ON f.id = t.formation_id
            WHERE t.frais_inscription IS NOT NULL
              AND t.source_ref IS NOT NULL
              AND lower(coalesce(t.remarque, '')) LIKE '%droit d''inscription%'
            ORDER BY f.parcours_id, t.id
        )
        INSERT INTO tarif (
            parcours_id, formation_id, specialisation_id, frais_inscription,
            mensualite, nb_mensualites, langue_enseignement, devise,
            annee_universitaire, statut, remarque, source_ref, actif
        )
        SELECT parcours_id, NULL, NULL, frais_inscription, NULL, NULL, NULL,
               devise, NULL, statut, 'Frais d’inscription commun au cycle',
               '{COMMON_FEE_MARKER}:' || source_ref, true
        FROM supported
        """
    )
    op.execute(
        f"""
        WITH common_fee AS (
            SELECT parcours_id, frais_inscription
            FROM tarif
            WHERE source_ref LIKE '{COMMON_FEE_MARKER}:%'
        )
        UPDATE tarif t
        SET frais_inscription = NULL
        FROM formation f, common_fee common
        WHERE t.formation_id = f.id
          AND f.parcours_id = common.parcours_id
          AND t.frais_inscription = common.frais_inscription
          AND coalesce(t.source_ref, '') NOT LIKE '{COMMON_FEE_MARKER}:%'
        """
    )


def _restore_formation_fees() -> None:
    op.execute(
        f"""
        UPDATE tarif t
        SET frais_inscription = common.frais_inscription
        FROM formation f
        JOIN tarif common ON common.parcours_id = f.parcours_id
        WHERE t.formation_id = f.id
          AND t.frais_inscription IS NULL
          AND common.source_ref LIKE '{COMMON_FEE_MARKER}:%'
        """
    )
    op.execute(
        f"DELETE FROM tarif WHERE source_ref LIKE '{COMMON_FEE_MARKER}:%'"
    )


def _restore_legacy_registration_elements() -> None:
    op.execute(
        f"""
        DELETE FROM formation_element WHERE source_ref = '{ENROLLMENT_SOURCE}'
        """
    )
    op.execute(
        """
        INSERT INTO formation_element (
            parcours_id, formation_id, specialisation_id, parent_id,
            type_element, code, nom, description, ordre_affichage, source_ref, actif
        ) VALUES (
            NULL, NULL, NULL, NULL, 'INFORMATION', 'INFO_PREINSCRIPTION',
            'Préinscription',
            'La préinscription s’effectue via le lien officiel IIT.',
            1, 'PROJECT_ENROLLMENT_SCOPE_V1', true
        )
        """
    )

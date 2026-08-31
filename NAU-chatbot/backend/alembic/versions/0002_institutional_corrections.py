"""Apply authoritative Prépa and legacy Licence corrections.

Revision ID: 0002_institutional_corrections
Revises: 0001_academic_schema
"""

from typing import Sequence

from alembic import op


revision: str = "0002_institutional_corrections"
down_revision: str | None = "0001_academic_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # These upserts intentionally work before the full official seed is loaded.
    op.execute(
        """
        INSERT INTO parcours (code, nom, duree_annees, description, actif)
        VALUES ('PREPA', 'Cycle Préparatoire', 2,
                'Cycle préparatoire aux études d’ingénieurs.', true)
        ON CONFLICT (code) DO UPDATE
        SET actif = true, updated_at = now()
        """
    )
    op.execute(
        """
        INSERT INTO formation
            (parcours_id, code, nom, intitule_diplome, duree_annees,
             nb_semestres, description, source_ref, actif)
        SELECT id, 'PREPA_GENERAL', 'Cycle Préparatoire',
               'Cycle Préparatoire aux Études d’Ingénieurs', 2, 4,
               'Cycle préparatoire général.', 'SRC_PREPA', true
        FROM parcours WHERE code = 'PREPA'
        ON CONFLICT (code) DO UPDATE
        SET parcours_id = EXCLUDED.parcours_id,
            source_ref = 'SRC_PREPA', actif = true, updated_at = now()
        """
    )
    op.execute(
        """
        INSERT INTO specialisation
            (formation_id, code, nom, description, ordre_affichage,
             source_ref, actif)
        SELECT id, 'MP', 'Mathématiques-Physique',
               'Spécialisation préparatoire MP validée par la règle institutionnelle du projet.',
               1, 'PROJECT_INSTITUTIONAL_RULES', true
        FROM formation WHERE code = 'PREPA_GENERAL'
        ON CONFLICT (formation_id, code) DO UPDATE
        SET nom = EXCLUDED.nom, description = EXCLUDED.description,
            ordre_affichage = EXCLUDED.ordre_affichage,
            source_ref = 'PROJECT_INSTITUTIONAL_RULES', actif = true,
            updated_at = now()
        """
    )
    op.execute(
        """
        INSERT INTO regle_orientation
            (formation_id, specialisation_id, code, nom, type_regle,
             criteres, description, priorite, source_ref, actif)
        SELECT id, NULL, 'ADMISSION_PREPA', 'Admission Cycle Préparatoire',
               'ADMISSION',
               '{"diplome":"BAC","type_bac":{"in":["MATH","SCIENCES"]}}'::jsonb,
               'Admission réservée aux titulaires d’un bac Math ou Sciences.',
               1, 'PROJECT_INSTITUTIONAL_RULES', true
        FROM formation WHERE code = 'PREPA_GENERAL'
        ON CONFLICT (code) DO UPDATE
        SET formation_id = EXCLUDED.formation_id,
            specialisation_id = NULL,
            nom = EXCLUDED.nom,
            type_regle = 'ADMISSION',
            criteres = EXCLUDED.criteres,
            description = EXCLUDED.description,
            priorite = 1,
            source_ref = 'PROJECT_INSTITUTIONAL_RULES',
            actif = true,
            updated_at = now()
        """
    )
    # If a legacy catalogue was imported first, it cannot override the current rule.
    op.execute(
        """
        UPDATE regle_orientation
        SET actif = false, updated_at = now()
        WHERE code = 'ADMISSION_LICENCE_GLSI' AND actif = true
        """
    )


def downgrade() -> None:
    # Soft reversal avoids cascading deletion of catalogue data added after upgrade.
    op.execute(
        """
        UPDATE regle_orientation
        SET actif = false, updated_at = now()
        WHERE code = 'ADMISSION_PREPA'
          AND source_ref = 'PROJECT_INSTITUTIONAL_RULES'
          AND criteres =
              '{"diplome":"BAC","type_bac":{"in":["MATH","SCIENCES"]}}'::jsonb
        """
    )
    op.execute(
        """
        UPDATE specialisation
        SET actif = false, updated_at = now()
        WHERE code = 'MP'
          AND source_ref = 'PROJECT_INSTITUTIONAL_RULES'
          AND formation_id = (
              SELECT id FROM formation WHERE code = 'PREPA_GENERAL'
          )
        """
    )
    # PREPA/PREPA_GENERAL and any legacy rule are retained: their pre-migration
    # existence and state cannot be inferred safely without an audit table.


"""Academic mappings matching the versioned PostgreSQL schema."""

from typing import Optional

from sqlalchemy import Enum, ARRAY, Boolean, CheckConstraint, Date, DateTime, ForeignKeyConstraint, Index, Integer, Numeric, PrimaryKeyConstraint, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.schema import conv
from sqlalchemy.orm import Mapped, mapped_column
import datetime
import decimal

from app.models.sqlalchemy.base import Base, TimestampMixin
from app.domain.academic.enums import FormationElementType


class Parcours(TimestampMixin, Base):
    __tablename__ = 'parcours'
    __table_args__ = (
        CheckConstraint('duree_annees IS NULL OR duree_annees > 0', name=conv('ck_parcours_ck_parcours_duree_positive')),
        PrimaryKeyConstraint('id', name=conv('pk_parcours')),
        UniqueConstraint('code', name=conv('uq_parcours_code'))
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50))
    nom: Mapped[str] = mapped_column(String(255))
    actif: Mapped[bool] = mapped_column(Boolean, server_default=text('true'))
    duree_annees: Mapped[Optional[int]] = mapped_column(Integer)
    description: Mapped[Optional[str]] = mapped_column(Text)


class Formation(TimestampMixin, Base):
    __tablename__ = 'formation'
    __table_args__ = (
        CheckConstraint('cardinality(langues_enseignement) > 0', name=conv('ck_formation_ck_formation_langues_enseignement_nonempty')),
        CheckConstraint('credits_total IS NULL OR credits_total > 0', name=conv('ck_formation_ck_formation_credits_positive')),
        CheckConstraint('duree_annees IS NULL OR duree_annees > 0', name=conv('ck_formation_ck_formation_duree_positive')),
        CheckConstraint('nb_semestres IS NULL OR nb_semestres > 0', name=conv('ck_formation_ck_formation_semestres_positive')),
        ForeignKeyConstraint(['parcours_id'], ['parcours.id'], name=conv('fk_formation_parcours_id_parcours')),
        PrimaryKeyConstraint('id', name=conv('pk_formation')),
        UniqueConstraint('code', name=conv('uq_formation_code')),
        Index('ix_formation_parcours', 'parcours_id')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parcours_id: Mapped[int] = mapped_column(Integer)
    code: Mapped[str] = mapped_column(String(100))
    nom: Mapped[str] = mapped_column(String(255))
    actif: Mapped[bool] = mapped_column(Boolean, server_default=text('true'))
    langues_enseignement: Mapped[list] = mapped_column(ARRAY(String(length=50)), server_default=text("ARRAY['FRANCAIS'::character varying]"))
    intitule_diplome: Mapped[Optional[str]] = mapped_column(String(255))
    duree_annees: Mapped[Optional[int]] = mapped_column(Integer)
    nb_semestres: Mapped[Optional[int]] = mapped_column(Integer)
    credits_total: Mapped[Optional[int]] = mapped_column(Integer)
    description: Mapped[Optional[str]] = mapped_column(Text)
    source_ref: Mapped[Optional[str]] = mapped_column(Text)



class Accreditation(TimestampMixin, Base):
    __tablename__ = 'accreditation'
    __table_args__ = (
        CheckConstraint('date_debut IS NULL OR date_fin IS NULL OR date_fin >= date_debut', name=conv('ck_accreditation_ck_accreditation_dates_ordered')),
        ForeignKeyConstraint(['formation_id'], ['formation.id'], ondelete='CASCADE', name=conv('fk_accreditation_formation_id_formation')),
        PrimaryKeyConstraint('id', name=conv('pk_accreditation')),
        UniqueConstraint('formation_id', 'code', name=conv('uq_accreditation_formation_code')),
        Index('ix_accreditation_formation', 'formation_id')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    formation_id: Mapped[int] = mapped_column(Integer)
    code: Mapped[str] = mapped_column(String(100))
    nom: Mapped[str] = mapped_column(String(255))
    actif: Mapped[bool] = mapped_column(Boolean, server_default=text('true'))
    organisme: Mapped[Optional[str]] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    date_debut: Mapped[Optional[datetime.date]] = mapped_column(Date)
    date_fin: Mapped[Optional[datetime.date]] = mapped_column(Date)
    source_ref: Mapped[Optional[str]] = mapped_column(Text)



class Specialisation(TimestampMixin, Base):
    __tablename__ = 'specialisation'
    __table_args__ = (
        CheckConstraint('ordre_affichage IS NULL OR ordre_affichage >= 0', name=conv('ck_specialisation_ck_specialisation_ordre_nonnegative')),
        ForeignKeyConstraint(['formation_id'], ['formation.id'], ondelete='CASCADE', name=conv('fk_specialisation_formation_id_formation')),
        PrimaryKeyConstraint('id', name=conv('pk_specialisation')),
        UniqueConstraint('formation_id', 'code', name=conv('uq_specialisation_formation_code')),
        UniqueConstraint('formation_id', 'id', name=conv('uq_specialisation_formation_id_id')),
        Index('ix_specialisation_s_formation', 'formation_id')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    formation_id: Mapped[int] = mapped_column(Integer)
    code: Mapped[str] = mapped_column(String(100))
    nom: Mapped[str] = mapped_column(String(255))
    actif: Mapped[bool] = mapped_column(Boolean, server_default=text('true'))
    description: Mapped[Optional[str]] = mapped_column(Text)
    ordre_affichage: Mapped[Optional[int]] = mapped_column(Integer)
    source_ref: Mapped[Optional[str]] = mapped_column(Text)



class FormationElement(TimestampMixin, Base):
    __tablename__ = 'formation_element'
    __table_args__ = (
        CheckConstraint('ordre_affichage IS NULL OR ordre_affichage >= 0', name=conv('ck_formation_element_ck_formation_element_ordre_nonnegative')),
        CheckConstraint('parcours_id IS NULL OR formation_id IS NULL AND specialisation_id IS NULL', name=conv('ck_formation_element_ck_formation_element_parcours_scop_99e1')),
        CheckConstraint('specialisation_id IS NULL OR formation_id IS NOT NULL', name=conv('ck_formation_element_ck_formation_element_specialisatio_da1e')),
        CheckConstraint("type_element::text = ANY (ARRAY['MODULE'::character varying::text, 'COURS'::character varying::text, 'CONTENU_PROGRAMME'::character varying::text, 'COMPETENCE'::character varying::text, 'METIER'::character varying::text, 'DOMAINE_ACTIVITE'::character varying::text, 'CERTIFICATION'::character varying::text, 'LANGUE'::character varying::text, 'MOBILITE'::character varying::text, 'OUTIL'::character varying::text, 'OPPORTUNITE'::character varying::text, 'INFORMATION'::character varying::text, 'DOCUMENT_INSCRIPTION'::character varying::text, 'LIEN_PREINSCRIPTION'::character varying::text])", name=conv('ck_formation_element_ck_formation_element_type_element_values')),
        ForeignKeyConstraint(['formation_id', 'specialisation_id'], ['specialisation.formation_id', 'specialisation.id'], ondelete='CASCADE', name=conv('fk_fe_formation_specialisation')),
        ForeignKeyConstraint(['formation_id'], ['formation.id'], ondelete='CASCADE', name=conv('fk_formation_element_formation_id_formation')),
        ForeignKeyConstraint(['parcours_id'], ['parcours.id'], ondelete='CASCADE', name=conv('fk_formation_element_parcours_id_parcours')),
        ForeignKeyConstraint(['parent_id'], ['formation_element.id'], ondelete='CASCADE', name=conv('fk_formation_element_parent_id_formation_element')),
        PrimaryKeyConstraint('id', name=conv('pk_formation_element')),
        Index('ix_fe_formation', 'formation_id'),
        Index('ix_fe_parcours', 'parcours_id'),
        Index('ix_fe_parent', 'parent_id'),
        Index('ix_fe_specialisation', 'specialisation_id'),
        Index('uq_fe_formation_code', 'formation_id', 'type_element', 'code', unique=True, postgresql_where=text('((parcours_id IS NULL) AND (formation_id IS NOT NULL) AND (specialisation_id IS NULL) AND (code IS NOT NULL))')),
        Index('uq_fe_formation_nom', 'formation_id', 'type_element', 'nom', unique=True, postgresql_where=text('((parcours_id IS NULL) AND (formation_id IS NOT NULL) AND (specialisation_id IS NULL) AND (code IS NULL))')),
        Index('uq_fe_global_code', 'type_element', 'code', unique=True, postgresql_where=text('((parcours_id IS NULL) AND (formation_id IS NULL) AND (specialisation_id IS NULL) AND (code IS NOT NULL))')),
        Index('uq_fe_global_nom', 'type_element', 'nom', unique=True, postgresql_where=text('((parcours_id IS NULL) AND (formation_id IS NULL) AND (specialisation_id IS NULL) AND (code IS NULL))')),
        Index('uq_fe_parcours_code', 'parcours_id', 'type_element', 'code', unique=True, postgresql_where=text('((parcours_id IS NOT NULL) AND (code IS NOT NULL))')),
        Index('uq_fe_parcours_nom', 'parcours_id', 'type_element', 'nom', unique=True, postgresql_where=text('((parcours_id IS NOT NULL) AND (code IS NULL))')),
        Index('uq_fe_specialisation_code', 'formation_id', 'specialisation_id', 'type_element', 'code', unique=True, postgresql_where=text('((specialisation_id IS NOT NULL) AND (code IS NOT NULL))')),
        Index('uq_fe_specialisation_nom', 'formation_id', 'specialisation_id', 'type_element', 'nom', unique=True, postgresql_where=text('((specialisation_id IS NOT NULL) AND (code IS NULL))'))
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type_element: Mapped[FormationElementType] = mapped_column(Enum(FormationElementType, native_enum=False, length=30, create_constraint=False))
    nom: Mapped[str] = mapped_column(String(255))
    actif: Mapped[bool] = mapped_column(Boolean, server_default=text('true'))
    formation_id: Mapped[Optional[int]] = mapped_column(Integer)
    specialisation_id: Mapped[Optional[int]] = mapped_column(Integer)
    parent_id: Mapped[Optional[int]] = mapped_column(Integer)
    code: Mapped[Optional[str]] = mapped_column(String(120))
    description: Mapped[Optional[str]] = mapped_column(Text)
    organisme: Mapped[Optional[str]] = mapped_column(String(255))
    ordre_affichage: Mapped[Optional[int]] = mapped_column(Integer)
    source_ref: Mapped[Optional[str]] = mapped_column(Text)
    parcours_id: Mapped[Optional[int]] = mapped_column(Integer)
    valeur: Mapped[Optional[str]] = mapped_column(Text)



class RegleOrientation(TimestampMixin, Base):
    __tablename__ = 'regle_orientation'
    __table_args__ = (
        CheckConstraint('priorite > 0', name=conv('ck_regle_orientation_ck_regle_orientation_priorite_positive')),
        ForeignKeyConstraint(['formation_id', 'specialisation_id'], ['specialisation.formation_id', 'specialisation.id'], ondelete='CASCADE', name=conv('fk_regle_formation_specialisation')),
        ForeignKeyConstraint(['formation_id'], ['formation.id'], ondelete='CASCADE', name=conv('fk_regle_orientation_formation_id_formation')),
        PrimaryKeyConstraint('id', name=conv('pk_regle_orientation')),
        UniqueConstraint('code', name=conv('uq_regle_orientation_code')),
        Index('ix_regle_orientation_formation', 'formation_id'),
        Index('ix_regle_orientation_specialisation', 'specialisation_id')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    formation_id: Mapped[int] = mapped_column(Integer)
    code: Mapped[str] = mapped_column(String(100))
    nom: Mapped[str] = mapped_column(String(255))
    type_regle: Mapped[str] = mapped_column(String(50))
    criteres: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    priorite: Mapped[int] = mapped_column(Integer, server_default=text('1'))
    actif: Mapped[bool] = mapped_column(Boolean, server_default=text('true'))
    specialisation_id: Mapped[Optional[int]] = mapped_column(Integer)
    description: Mapped[Optional[str]] = mapped_column(Text)
    source_ref: Mapped[Optional[str]] = mapped_column(Text)



class Tarif(TimestampMixin, Base):
    __tablename__ = 'tarif'
    __table_args__ = (
        CheckConstraint('frais_inscription IS NULL OR frais_inscription >= 0::numeric', name=conv('ck_tarif_ck_tarif_frais_nonnegative')),
        CheckConstraint("langue_enseignement IS NULL OR langue_enseignement::text ~ '^[A-Z0-9][A-Z0-9_-]*$'::text", name=conv('ck_tarif_ck_tarif_langue_enseignement_code')),
        CheckConstraint('mensualite IS NULL OR mensualite >= 0::numeric', name=conv('ck_tarif_ck_tarif_mensualite_nonnegative')),
        CheckConstraint('nb_mensualites IS NULL OR nb_mensualites > 0', name=conv('ck_tarif_ck_tarif_mensualites_positive')),
        CheckConstraint('parcours_id IS NOT NULL OR formation_id IS NOT NULL', name=conv('ck_tarif_ck_tarif_scope_required')),
        CheckConstraint('parcours_id IS NULL OR formation_id IS NULL AND specialisation_id IS NULL', name=conv('ck_tarif_ck_tarif_parcours_scope_exclusive')),
        CheckConstraint('specialisation_id IS NULL OR formation_id IS NOT NULL', name=conv('ck_tarif_ck_tarif_specialisation_requires_formation')),
        ForeignKeyConstraint(['formation_id', 'specialisation_id'], ['specialisation.formation_id', 'specialisation.id'], ondelete='CASCADE', name=conv('fk_tarif_formation_specialisation')),
        ForeignKeyConstraint(['formation_id'], ['formation.id'], ondelete='CASCADE', name=conv('fk_tarif_formation_id_formation')),
        ForeignKeyConstraint(['parcours_id'], ['parcours.id'], ondelete='CASCADE', name=conv('fk_tarif_parcours_id_parcours')),
        PrimaryKeyConstraint('id', name=conv('pk_tarif')),
        Index('ix_tarif_formation', 'formation_id'),
        Index('ix_tarif_formation_langue', 'formation_id', 'langue_enseignement'),
        Index('ix_tarif_parcours', 'parcours_id'),
        Index('ix_tarif_specialisation', 'specialisation_id')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    devise: Mapped[str] = mapped_column(String(10), server_default=text("'TND'::character varying"))
    statut: Mapped[str] = mapped_column(String(50), server_default=text("'INDICATIF'::character varying"))
    actif: Mapped[bool] = mapped_column(Boolean, server_default=text('true'))
    formation_id: Mapped[Optional[int]] = mapped_column(Integer)
    specialisation_id: Mapped[Optional[int]] = mapped_column(Integer)
    frais_inscription: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(10, 2))
    mensualite: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(10, 2))
    nb_mensualites: Mapped[Optional[int]] = mapped_column(Integer)
    annee_universitaire: Mapped[Optional[str]] = mapped_column(String(50))
    remarque: Mapped[Optional[str]] = mapped_column(Text)
    source_ref: Mapped[Optional[str]] = mapped_column(Text)
    langue_enseignement: Mapped[Optional[str]] = mapped_column(String(50))
    parcours_id: Mapped[Optional[int]] = mapped_column(Integer)


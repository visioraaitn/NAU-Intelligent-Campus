-- ============================================================================
-- IIT ACADEMIC ASSISTANT — SEED PORTABLE COMPLET DU REPOSITORY
-- Snapshot PostgreSQL généré le 2026-09-09 depuis la base locale de référence.
-- Cible : PostgreSQL 16 (compatible avec l'image postgres:16.6 du Compose).
-- ============================================================================
--
-- CONTENU
--   * Schéma PostgreSQL complet de l'application : 11 tables, types de
--     colonnes, valeurs par défaut, contraintes, clés étrangères, index et
--     séquences.
--   * Version Alembic : 0006_user_conversation_history.
--   * Toutes les données académiques/RAG : parcours, formations,
--     spécialisations, éléments RAG, tarifs, règles et accréditations.
--   * Les tables user_account, conversation et message sont créées VIDES :
--     aucune identité, aucun hash de mot de passe et aucune conversation
--     réelle ne doit être publiée dans Git.
--
-- MANIFESTE DES DONNÉES DU SNAPSHOT
--   parcours=4, formation=10, specialisation=8, formation_element=268,
--   tarif=15, regle_orientation=14, accreditation=10, alembic_version=1,
--   user_account=0, conversation=0, message=0.
--
-- STOCKAGES NON INCLUS DANS UN SEED SQL
--   * Redis : état opérationnel temporaire (sessions, verrous, rate limits,
--     files RAG). Il doit démarrer vide sur une nouvelle machine.
--   * Chroma : index vectoriel reconstruisible depuis PostgreSQL.
--   * Modèles Hugging Face : fichiers volumineux à placer dans le volume
--     iit_academic_model_data selon VM_SETUP.md.
--
-- RESTAURATION SUR UNE NOUVELLE MACHINE (base cible déjà créée)
--   psql -v ON_ERROR_STOP=1 \
--     -h "$POSTGRES_HOST" -p "${POSTGRES_PORT:-5432}" \
--     -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
--     -f iit_repository_seed.sql
--
-- AVEC DOCKER COMPOSE
--   docker compose up -d postgres redis chroma
--   docker compose exec -T postgres psql -v ON_ERROR_STOP=1 \
--     -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
--     < iit_repository_seed.sql
--   docker compose up -d inference rag-worker
--   docker compose run --rm --no-deps backend \
--     python -m app.commands.reindex_rag
--
-- ATTENTION
--   Ce script nettoie puis recrée les objets PostgreSQL de l'application dans
--   la base cible. Ne pas l'exécuter sur une base contenant des données à
--   conserver sans avoir fait un backup préalable.
-- ============================================================================

--
-- PostgreSQL database dump
--


-- Dumped from database version 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

ALTER TABLE IF EXISTS ONLY public.tarif DROP CONSTRAINT IF EXISTS fk_tarif_parcours_id_parcours;
ALTER TABLE IF EXISTS ONLY public.tarif DROP CONSTRAINT IF EXISTS fk_tarif_formation_specialisation;
ALTER TABLE IF EXISTS ONLY public.tarif DROP CONSTRAINT IF EXISTS fk_tarif_formation_id_formation;
ALTER TABLE IF EXISTS ONLY public.specialisation DROP CONSTRAINT IF EXISTS fk_specialisation_formation_id_formation;
ALTER TABLE IF EXISTS ONLY public.regle_orientation DROP CONSTRAINT IF EXISTS fk_regle_orientation_formation_id_formation;
ALTER TABLE IF EXISTS ONLY public.regle_orientation DROP CONSTRAINT IF EXISTS fk_regle_formation_specialisation;
ALTER TABLE IF EXISTS ONLY public.message DROP CONSTRAINT IF EXISTS fk_message_conversation_id_conversation;
ALTER TABLE IF EXISTS ONLY public.formation DROP CONSTRAINT IF EXISTS fk_formation_parcours_id_parcours;
ALTER TABLE IF EXISTS ONLY public.formation_element DROP CONSTRAINT IF EXISTS fk_formation_element_parent_id_formation_element;
ALTER TABLE IF EXISTS ONLY public.formation_element DROP CONSTRAINT IF EXISTS fk_formation_element_parcours_id_parcours;
ALTER TABLE IF EXISTS ONLY public.formation_element DROP CONSTRAINT IF EXISTS fk_formation_element_formation_id_formation;
ALTER TABLE IF EXISTS ONLY public.formation_element DROP CONSTRAINT IF EXISTS fk_fe_formation_specialisation;
ALTER TABLE IF EXISTS ONLY public.conversation DROP CONSTRAINT IF EXISTS fk_conversation_user_id_user_account;
ALTER TABLE IF EXISTS ONLY public.accreditation DROP CONSTRAINT IF EXISTS fk_accreditation_formation_id_formation;
DROP INDEX IF EXISTS public.uq_fe_specialisation_nom;
DROP INDEX IF EXISTS public.uq_fe_specialisation_code;
DROP INDEX IF EXISTS public.uq_fe_parcours_nom;
DROP INDEX IF EXISTS public.uq_fe_parcours_code;
DROP INDEX IF EXISTS public.uq_fe_global_nom;
DROP INDEX IF EXISTS public.uq_fe_global_code;
DROP INDEX IF EXISTS public.uq_fe_formation_nom;
DROP INDEX IF EXISTS public.uq_fe_formation_code;
DROP INDEX IF EXISTS public.ix_tarif_specialisation;
DROP INDEX IF EXISTS public.ix_tarif_parcours;
DROP INDEX IF EXISTS public.ix_tarif_formation_langue;
DROP INDEX IF EXISTS public.ix_tarif_formation;
DROP INDEX IF EXISTS public.ix_specialisation_s_formation;
DROP INDEX IF EXISTS public.ix_regle_orientation_specialisation;
DROP INDEX IF EXISTS public.ix_regle_orientation_formation;
DROP INDEX IF EXISTS public.ix_message_conversation_id;
DROP INDEX IF EXISTS public.ix_message_conversation_created;
DROP INDEX IF EXISTS public.ix_formation_parcours;
DROP INDEX IF EXISTS public.ix_fe_specialisation;
DROP INDEX IF EXISTS public.ix_fe_parent;
DROP INDEX IF EXISTS public.ix_fe_parcours;
DROP INDEX IF EXISTS public.ix_fe_formation;
DROP INDEX IF EXISTS public.ix_conversation_user_updated;
DROP INDEX IF EXISTS public.ix_conversation_user_id;
DROP INDEX IF EXISTS public.ix_accreditation_formation;
ALTER TABLE IF EXISTS ONLY public.user_account DROP CONSTRAINT IF EXISTS uq_user_account_email;
ALTER TABLE IF EXISTS ONLY public.specialisation DROP CONSTRAINT IF EXISTS uq_specialisation_formation_id_id;
ALTER TABLE IF EXISTS ONLY public.specialisation DROP CONSTRAINT IF EXISTS uq_specialisation_formation_code;
ALTER TABLE IF EXISTS ONLY public.regle_orientation DROP CONSTRAINT IF EXISTS uq_regle_orientation_code;
ALTER TABLE IF EXISTS ONLY public.parcours DROP CONSTRAINT IF EXISTS uq_parcours_code;
ALTER TABLE IF EXISTS ONLY public.message DROP CONSTRAINT IF EXISTS uq_message_conversation_role_request;
ALTER TABLE IF EXISTS ONLY public.formation DROP CONSTRAINT IF EXISTS uq_formation_code;
ALTER TABLE IF EXISTS ONLY public.accreditation DROP CONSTRAINT IF EXISTS uq_accreditation_formation_code;
ALTER TABLE IF EXISTS ONLY public.user_account DROP CONSTRAINT IF EXISTS pk_user_account;
ALTER TABLE IF EXISTS ONLY public.tarif DROP CONSTRAINT IF EXISTS pk_tarif;
ALTER TABLE IF EXISTS ONLY public.specialisation DROP CONSTRAINT IF EXISTS pk_specialisation;
ALTER TABLE IF EXISTS ONLY public.regle_orientation DROP CONSTRAINT IF EXISTS pk_regle_orientation;
ALTER TABLE IF EXISTS ONLY public.parcours DROP CONSTRAINT IF EXISTS pk_parcours;
ALTER TABLE IF EXISTS ONLY public.message DROP CONSTRAINT IF EXISTS pk_message;
ALTER TABLE IF EXISTS ONLY public.formation_element DROP CONSTRAINT IF EXISTS pk_formation_element;
ALTER TABLE IF EXISTS ONLY public.formation DROP CONSTRAINT IF EXISTS pk_formation;
ALTER TABLE IF EXISTS ONLY public.conversation DROP CONSTRAINT IF EXISTS pk_conversation;
ALTER TABLE IF EXISTS ONLY public.accreditation DROP CONSTRAINT IF EXISTS pk_accreditation;
ALTER TABLE IF EXISTS ONLY public.alembic_version DROP CONSTRAINT IF EXISTS alembic_version_pkc;
ALTER TABLE IF EXISTS public.tarif ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.specialisation ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.regle_orientation ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.parcours ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.formation_element ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.formation ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.accreditation ALTER COLUMN id DROP DEFAULT;
DROP TABLE IF EXISTS public.user_account;
DROP SEQUENCE IF EXISTS public.tarif_id_seq;
DROP TABLE IF EXISTS public.tarif;
DROP SEQUENCE IF EXISTS public.specialisation_id_seq;
DROP TABLE IF EXISTS public.specialisation;
DROP SEQUENCE IF EXISTS public.regle_orientation_id_seq;
DROP TABLE IF EXISTS public.regle_orientation;
DROP SEQUENCE IF EXISTS public.parcours_id_seq;
DROP TABLE IF EXISTS public.parcours;
DROP TABLE IF EXISTS public.message;
DROP SEQUENCE IF EXISTS public.formation_id_seq;
DROP SEQUENCE IF EXISTS public.formation_element_id_seq;
DROP TABLE IF EXISTS public.formation_element;
DROP TABLE IF EXISTS public.formation;
DROP TABLE IF EXISTS public.conversation;
DROP TABLE IF EXISTS public.alembic_version;
DROP SEQUENCE IF EXISTS public.accreditation_id_seq;
DROP TABLE IF EXISTS public.accreditation;
SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: accreditation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.accreditation (
    id integer NOT NULL,
    formation_id integer NOT NULL,
    code character varying(100) NOT NULL,
    nom character varying(255) NOT NULL,
    organisme character varying(255),
    description text,
    date_debut date,
    date_fin date,
    source_ref text,
    actif boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_accreditation_ck_accreditation_dates_ordered CHECK (((date_debut IS NULL) OR (date_fin IS NULL) OR (date_fin >= date_debut)))
);


--
-- Name: accreditation_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.accreditation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: accreditation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.accreditation_id_seq OWNED BY public.accreditation.id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: conversation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.conversation (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    title character varying(160) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: formation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.formation (
    id integer NOT NULL,
    parcours_id integer NOT NULL,
    code character varying(100) NOT NULL,
    nom character varying(255) NOT NULL,
    intitule_diplome character varying(255),
    duree_annees integer,
    nb_semestres integer,
    credits_total integer,
    description text,
    source_ref text,
    actif boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    langues_enseignement character varying(50)[] DEFAULT ARRAY['FRANCAIS'::character varying] NOT NULL,
    CONSTRAINT ck_formation_ck_formation_credits_positive CHECK (((credits_total IS NULL) OR (credits_total > 0))),
    CONSTRAINT ck_formation_ck_formation_duree_positive CHECK (((duree_annees IS NULL) OR (duree_annees > 0))),
    CONSTRAINT ck_formation_ck_formation_langues_enseignement_nonempty CHECK ((cardinality(langues_enseignement) > 0)),
    CONSTRAINT ck_formation_ck_formation_semestres_positive CHECK (((nb_semestres IS NULL) OR (nb_semestres > 0)))
);


--
-- Name: formation_element; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.formation_element (
    id integer NOT NULL,
    formation_id integer,
    specialisation_id integer,
    parent_id integer,
    type_element character varying(30) NOT NULL,
    code character varying(120),
    nom character varying(255) NOT NULL,
    description text,
    organisme character varying(255),
    ordre_affichage integer,
    source_ref text,
    actif boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    parcours_id integer,
    valeur text,
    CONSTRAINT ck_formation_element_ck_formation_element_ordre_nonnegative CHECK (((ordre_affichage IS NULL) OR (ordre_affichage >= 0))),
    CONSTRAINT ck_formation_element_ck_formation_element_parcours_scop_99e1 CHECK (((parcours_id IS NULL) OR ((formation_id IS NULL) AND (specialisation_id IS NULL)))),
    CONSTRAINT ck_formation_element_ck_formation_element_specialisatio_da1e CHECK (((specialisation_id IS NULL) OR (formation_id IS NOT NULL))),
    CONSTRAINT ck_formation_element_ck_formation_element_type_element_values CHECK (((type_element)::text = ANY ((ARRAY['MODULE'::character varying, 'COURS'::character varying, 'CONTENU_PROGRAMME'::character varying, 'COMPETENCE'::character varying, 'METIER'::character varying, 'DOMAINE_ACTIVITE'::character varying, 'CERTIFICATION'::character varying, 'LANGUE'::character varying, 'MOBILITE'::character varying, 'OUTIL'::character varying, 'OPPORTUNITE'::character varying, 'INFORMATION'::character varying, 'DOCUMENT_INSCRIPTION'::character varying, 'LIEN_PREINSCRIPTION'::character varying])::text[])))
);


--
-- Name: formation_element_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.formation_element_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: formation_element_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.formation_element_id_seq OWNED BY public.formation_element.id;


--
-- Name: formation_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.formation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: formation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.formation_id_seq OWNED BY public.formation.id;


--
-- Name: message; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.message (
    id uuid NOT NULL,
    conversation_id uuid NOT NULL,
    role character varying(20) NOT NULL,
    content text NOT NULL,
    request_key character varying(128),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_message_ck_message_role_values CHECK (((role)::text = ANY ((ARRAY['USER'::character varying, 'ASSISTANT'::character varying])::text[])))
);


--
-- Name: parcours; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.parcours (
    id integer NOT NULL,
    code character varying(50) NOT NULL,
    nom character varying(255) NOT NULL,
    duree_annees integer,
    description text,
    actif boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_parcours_ck_parcours_duree_positive CHECK (((duree_annees IS NULL) OR (duree_annees > 0)))
);


--
-- Name: parcours_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.parcours_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: parcours_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.parcours_id_seq OWNED BY public.parcours.id;


--
-- Name: regle_orientation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.regle_orientation (
    id integer NOT NULL,
    formation_id integer NOT NULL,
    specialisation_id integer,
    code character varying(100) NOT NULL,
    nom character varying(255) NOT NULL,
    type_regle character varying(50) NOT NULL,
    criteres jsonb DEFAULT '{}'::jsonb NOT NULL,
    description text,
    priorite integer DEFAULT 1 NOT NULL,
    source_ref text,
    actif boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_regle_orientation_ck_regle_orientation_priorite_positive CHECK ((priorite > 0))
);


--
-- Name: regle_orientation_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.regle_orientation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: regle_orientation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.regle_orientation_id_seq OWNED BY public.regle_orientation.id;


--
-- Name: specialisation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.specialisation (
    id integer NOT NULL,
    formation_id integer NOT NULL,
    code character varying(100) NOT NULL,
    nom character varying(255) NOT NULL,
    description text,
    ordre_affichage integer,
    source_ref text,
    actif boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_specialisation_ck_specialisation_ordre_nonnegative CHECK (((ordre_affichage IS NULL) OR (ordre_affichage >= 0)))
);


--
-- Name: specialisation_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.specialisation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: specialisation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.specialisation_id_seq OWNED BY public.specialisation.id;


--
-- Name: tarif; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tarif (
    id integer NOT NULL,
    formation_id integer,
    specialisation_id integer,
    frais_inscription numeric(10,2),
    mensualite numeric(10,2),
    nb_mensualites integer,
    devise character varying(10) DEFAULT 'TND'::character varying NOT NULL,
    annee_universitaire character varying(50),
    statut character varying(50) DEFAULT 'INDICATIF'::character varying NOT NULL,
    remarque text,
    source_ref text,
    actif boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    langue_enseignement character varying(50),
    parcours_id integer,
    CONSTRAINT ck_tarif_ck_tarif_frais_nonnegative CHECK (((frais_inscription IS NULL) OR (frais_inscription >= (0)::numeric))),
    CONSTRAINT ck_tarif_ck_tarif_langue_enseignement_code CHECK (((langue_enseignement IS NULL) OR ((langue_enseignement)::text ~ '^[A-Z0-9][A-Z0-9_-]*$'::text))),
    CONSTRAINT ck_tarif_ck_tarif_mensualite_nonnegative CHECK (((mensualite IS NULL) OR (mensualite >= (0)::numeric))),
    CONSTRAINT ck_tarif_ck_tarif_mensualites_positive CHECK (((nb_mensualites IS NULL) OR (nb_mensualites > 0))),
    CONSTRAINT ck_tarif_ck_tarif_parcours_scope_exclusive CHECK (((parcours_id IS NULL) OR ((formation_id IS NULL) AND (specialisation_id IS NULL)))),
    CONSTRAINT ck_tarif_ck_tarif_scope_required CHECK (((parcours_id IS NOT NULL) OR (formation_id IS NOT NULL))),
    CONSTRAINT ck_tarif_ck_tarif_specialisation_requires_formation CHECK (((specialisation_id IS NULL) OR (formation_id IS NOT NULL)))
);


--
-- Name: tarif_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tarif_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tarif_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tarif_id_seq OWNED BY public.tarif.id;


--
-- Name: user_account; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_account (
    id uuid NOT NULL,
    name character varying(120) NOT NULL,
    email character varying(320) NOT NULL,
    password_hash character varying(255) NOT NULL,
    role character varying(20) DEFAULT 'USER'::character varying NOT NULL,
    active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_user_account_ck_user_account_role_values CHECK (((role)::text = ANY ((ARRAY['USER'::character varying, 'ADMIN'::character varying])::text[])))
);


--
-- Name: accreditation id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.accreditation ALTER COLUMN id SET DEFAULT nextval('public.accreditation_id_seq'::regclass);


--
-- Name: formation id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.formation ALTER COLUMN id SET DEFAULT nextval('public.formation_id_seq'::regclass);


--
-- Name: formation_element id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.formation_element ALTER COLUMN id SET DEFAULT nextval('public.formation_element_id_seq'::regclass);


--
-- Name: parcours id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parcours ALTER COLUMN id SET DEFAULT nextval('public.parcours_id_seq'::regclass);


--
-- Name: regle_orientation id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.regle_orientation ALTER COLUMN id SET DEFAULT nextval('public.regle_orientation_id_seq'::regclass);


--
-- Name: specialisation id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.specialisation ALTER COLUMN id SET DEFAULT nextval('public.specialisation_id_seq'::regclass);


--
-- Name: tarif id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tarif ALTER COLUMN id SET DEFAULT nextval('public.tarif_id_seq'::regclass);


--
-- Data for Name: accreditation; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.accreditation (id, formation_id, code, nom, organisme, description, date_debut, date_fin, source_ref, actif, created_at, updated_at) VALUES
	(1, 5, 'EURO-INF', 'EURO-INF', 'ASIIN', 'Le Génie Informatique IIT porte le label EURO-INF attribué par ASIIN selon les pages publiques IIT. Il s''agit d''une accréditation de programme international.', NULL, NULL, 'SRC_ACCREDITATIONS', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01'),
	(8, 2, 'EURO-INF', 'EURO-INF', 'ASIIN', NULL, NULL, NULL, NULL, true, '2026-09-01 09:31:58.735669+01', '2026-09-01 09:31:58.735669+01'),
	(10, 1, 'EUR-ACM', 'EUR-ACMaster', 'ASIIN', NULL, NULL, NULL, NULL, true, '2026-09-01 09:34:10.186771+01', '2026-09-01 09:34:10.186771+01'),
	(9, 3, 'EUR-ACM', 'EUR-ACMaster', 'ASIIN', NULL, NULL, NULL, NULL, true, '2026-09-01 09:33:42.321991+01', '2026-09-01 09:34:17.024542+01'),
	(2, 10, 'EUR-ACM', 'EUR-ACMaster', 'ASIIN', NULL, NULL, NULL, NULL, true, '2026-09-01 09:26:34.039869+01', '2026-09-01 09:34:23.340993+01'),
	(7, 4, 'EUR-ACE', 'EUR-ACMaster', 'ASIIN', NULL, NULL, NULL, NULL, true, '2026-09-01 09:31:33.141995+01', '2026-09-01 09:34:32.641615+01'),
	(6, 9, 'EUR-ACE', 'EUR-ACMaster', 'ASIIN', NULL, NULL, NULL, NULL, true, '2026-09-01 09:31:12.695902+01', '2026-09-01 09:34:45.425513+01'),
	(5, 8, 'EUR-ACE', 'EUR-ACMaster', 'ASIIN', NULL, NULL, NULL, NULL, true, '2026-09-01 09:30:48.999554+01', '2026-09-01 09:34:57.480409+01'),
	(4, 7, 'EUR-ACE', 'EUR-ACMaster', 'ASIIN', NULL, NULL, NULL, NULL, true, '2026-09-01 09:29:24.286944+01', '2026-09-01 09:35:05.313618+01'),
	(3, 6, 'EUR-ACE', 'EUR-ACMaster', 'ASIIN', NULL, NULL, NULL, NULL, true, '2026-09-01 09:28:00.782517+01', '2026-09-01 09:35:15.563881+01');


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.alembic_version (version_num) VALUES
	('0006_user_conversation_history');


--
-- Data for Name: formation; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.formation (id, parcours_id, code, nom, intitule_diplome, duree_annees, nb_semestres, credits_total, description, source_ref, actif, created_at, updated_at, langues_enseignement) VALUES
	(10, 4, 'ARCHITECTURE_DNA', 'Diplôme National d''Architecte', 'Diplôme National d''Architecte', 6, 12, NULL, NULL, 'FLYER_ARCHITECTURE', true, '2026-08-30 13:15:39.565163+01', '2026-08-31 19:58:53.548642+01', '{FRANCAIS}'),
	(6, 3, 'INGENIEUR_CIVIL', 'Génie Civil', 'Diplôme National d''Ingénieur en Génie Civil', 3, 6, 180, NULL, 'FLYER_GENIE_CIVIL', true, '2026-08-30 13:15:39.565163+01', '2026-08-31 19:59:00.386944+01', '{FRANCAIS}'),
	(7, 3, 'INGENIEUR_INDUSTRIEL', 'Génie Industriel', 'Diplôme National d''Ingénieur en Génie Industriel', 3, 6, 180, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-31 19:59:05.045308+01', '{FRANCAIS}'),
	(5, 3, 'INGENIEUR_INFO', 'Génie Informatique', 'Diplôme National d''Ingénieur en Génie Informatique', 3, 6, NULL, NULL, 'FLYER_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-31 19:59:14.485992+01', '{FRANCAIS}'),
	(8, 3, 'INGENIEUR_MECANIQUE', 'Génie Mécanique', 'Diplôme National d''Ingénieur en Génie Mécanique', 3, 6, 180, NULL, 'FLYER_GENIE_MECANIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-31 19:59:19.082825+01', '{FRANCAIS}'),
	(9, 3, 'INGENIEUR_PROCEDES', 'Génie des Procédés', 'Diplôme National d''Ingénieur en Génie des Procédés', 3, 6, 180, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-31 19:59:22.732269+01', '{FRANCAIS}'),
	(1, 1, 'PREPA_GENERAL', 'Cycle Préparatoire', 'Diplôme du cycle préparatoire aux études d’ingénieur', 2, 4, NULL, 'Cycle Préparatoire général', 'SRC_PREPA', true, '2026-08-30 13:15:21.369956+01', '2026-08-31 19:59:30.993369+01', '{FRANCAIS}'),
	(2, 2, 'LICENCE_INFO', 'Licence en Informatique', 'Licence en Informatique', 3, 6, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', '{FRANCAIS,ANGLAIS}'),
	(3, 2, 'LICENCE_MECATRONIQUE_SI', 'Mécatronique & Systèmes Intelligents', 'Licence Nationale en Mécatronique & Systèmes Intelligents', 3, 6, NULL, NULL, 'FLYER_LICENCE_MECATRONIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', '{FRANCAIS,ANGLAIS}'),
	(4, 2, 'LICENCE_ELEC_SEIER', 'Systèmes Électriques Intelligents & Énergies Renouvelables', 'Licence en Génie Électrique', 3, 6, NULL, NULL, 'FLYER_LICENCE_ELECTRIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', '{FRANCAIS,ANGLAIS}');


--
-- Data for Name: formation_element; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.formation_element (id, formation_id, specialisation_id, parent_id, type_element, code, nom, description, organisme, ordre_affichage, source_ref, actif, created_at, updated_at, parcours_id, valeur) VALUES
	(1, 9, NULL, NULL, 'COMPETENCE', 'PROC_SIM', 'Simulation de procédés (Aspen HYSYS, CFD, REVIT…)', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(2, 9, NULL, NULL, 'COMPETENCE', 'PROC_TRANSFERT', 'Phénomènes de transfert et opérations unitaires', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(3, 9, NULL, NULL, 'COMPETENCE', 'PROC_OPT', 'Contrôle et optimisation des procédés', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(4, 9, NULL, NULL, 'COMPETENCE', 'PROC_QHSE', 'Sécurité, QHSE et environnement', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(5, 9, NULL, NULL, 'COMPETENCE', 'PROC_FUTUR', 'Énergies du futur et développement durable', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(6, 9, NULL, NULL, 'COMPETENCE', 'PROC_ACV', 'Bilan carbone, décarbonation industrielle et analyse du cycle de vie (ACV)', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(7, 9, NULL, NULL, 'METIER', 'PROC_M_PROD', 'Ingénieur de production', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(8, 9, NULL, NULL, 'METIER', 'PROC_M_PROC', 'Ingénieur procédés', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(9, 9, NULL, NULL, 'METIER', 'M_QHSE', 'Responsable QHSE', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(10, 9, NULL, NULL, 'METIER', 'M_BUREAU', 'Responsable bureau d''études', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(11, 9, NULL, NULL, 'METIER', 'M_CHEF_PROJET_IND', 'Chef de projet industriel', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(12, 9, NULL, NULL, 'METIER', 'M_RD', 'Ingénieur R&D', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(13, 9, NULL, NULL, 'METIER', 'M_TECH_COM', 'Ingénieur technico-commercial', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(14, 9, NULL, NULL, 'METIER', 'M_BILAN_C', 'Ingénieur bilan carbone', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(15, 9, NULL, NULL, 'METIER', 'M_TRANSITION', 'Consultant transition énergétique & climat', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(16, 9, NULL, NULL, 'METIER', 'M_ACV', 'Ingénieur ACV & performance environnementale', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(17, 9, NULL, NULL, 'DOMAINE_ACTIVITE', 'D_PETROLE', 'Pétrole & Gaz', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(18, 9, NULL, NULL, 'DOMAINE_ACTIVITE', 'D_ENERGIE', 'Énergie & Réseaux', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(19, 9, NULL, NULL, 'DOMAINE_ACTIVITE', 'D_ENR', 'Énergies renouvelables', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(20, 9, NULL, NULL, 'DOMAINE_ACTIVITE', 'D_BUREAUX', 'Bureaux d''études & Ingénierie', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL);
INSERT INTO public.formation_element (id, formation_id, specialisation_id, parent_id, type_element, code, nom, description, organisme, ordre_affichage, source_ref, actif, created_at, updated_at, parcours_id, valeur) VALUES
	(21, 9, NULL, NULL, 'DOMAINE_ACTIVITE', 'D_CONSEIL', 'Sociétés de conseil & expertises', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(22, 9, NULL, NULL, 'DOMAINE_ACTIVITE', 'D_BIOTECH', 'Biotechnologies & Agro/Biotech', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(23, 9, NULL, NULL, 'DOMAINE_ACTIVITE', 'D_RD', 'Recherche & Développement', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(24, 9, NULL, NULL, 'DOMAINE_ACTIVITE', 'D_CLIMAT', 'Bilan carbone & stratégie climat', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(25, 6, NULL, NULL, 'COMPETENCE', 'CIV_STRUCT', 'Conception et dimensionnement des structures', NULL, NULL, NULL, 'FLYER_GENIE_CIVIL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(26, 6, NULL, NULL, 'COMPETENCE', 'CIV_GEO', 'Études géotechniques et infrastructures', NULL, NULL, NULL, 'FLYER_GENIE_CIVIL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(27, 6, NULL, NULL, 'COMPETENCE', 'CIV_BETON', 'Béton et management des projets de construction', NULL, NULL, NULL, 'FLYER_GENIE_CIVIL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(28, 6, NULL, NULL, 'COMPETENCE', 'CIV_CAO', 'Modélisation et calcul assisté par ordinateur', NULL, NULL, NULL, 'FLYER_GENIE_CIVIL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(29, 6, NULL, NULL, 'COMPETENCE', 'CIV_QUAL', 'Contrôle qualité et expertise des matériaux', NULL, NULL, NULL, 'FLYER_GENIE_CIVIL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(30, 6, NULL, NULL, 'COMPETENCE', 'CIV_BIM', 'Maîtrise du BIM et des outils numériques de conception', NULL, NULL, NULL, 'FLYER_GENIE_CIVIL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(31, 6, NULL, NULL, 'METIER', 'CIV_M_ING', 'Ingénieur en Génie Civil', NULL, NULL, NULL, 'FLYER_GENIE_CIVIL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(32, 6, NULL, NULL, 'METIER', 'CIV_M_STRUCT', 'Ingénieur structures et géotechnique', NULL, NULL, NULL, 'FLYER_GENIE_CIVIL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(33, 6, NULL, NULL, 'METIER', 'CIV_M_TRAVAUX', 'Conducteur de travaux / Chef de chantier', NULL, NULL, NULL, 'FLYER_GENIE_CIVIL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(34, 6, NULL, NULL, 'METIER', 'CIV_M_AFFAIRES', 'Chargé d''affaires construction et BTP', NULL, NULL, NULL, 'FLYER_GENIE_CIVIL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(35, 6, NULL, NULL, 'METIER', 'CIV_M_HYDRAU', 'Ingénieur hydraulique', NULL, NULL, NULL, 'FLYER_GENIE_CIVIL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(36, 6, NULL, NULL, 'METIER', 'CIV_M_BIM', 'BIM Manager', NULL, NULL, NULL, 'FLYER_GENIE_CIVIL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(37, 6, NULL, NULL, 'DOMAINE_ACTIVITE', 'CIV_D_BAT', 'Bâtiments et ouvrages d''art', NULL, NULL, NULL, 'FLYER_GENIE_CIVIL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(38, 6, NULL, NULL, 'DOMAINE_ACTIVITE', 'CIV_D_VRD', 'Routes, infrastructures et VRD', NULL, NULL, NULL, 'FLYER_GENIE_CIVIL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(39, 6, NULL, NULL, 'DOMAINE_ACTIVITE', 'CIV_D_GEO', 'Géotechnique et fondations', NULL, NULL, NULL, 'FLYER_GENIE_CIVIL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(40, 6, NULL, NULL, 'DOMAINE_ACTIVITE', 'CIV_D_HYDRAU', 'Ouvrages hydrauliques et maritimes', NULL, NULL, NULL, 'FLYER_GENIE_CIVIL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL);
INSERT INTO public.formation_element (id, formation_id, specialisation_id, parent_id, type_element, code, nom, description, organisme, ordre_affichage, source_ref, actif, created_at, updated_at, parcours_id, valeur) VALUES
	(41, 6, NULL, NULL, 'DOMAINE_ACTIVITE', 'CIV_D_LABO', 'Laboratoires de contrôle qualité des matériaux', NULL, NULL, NULL, 'FLYER_GENIE_CIVIL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(42, 6, NULL, NULL, 'DOMAINE_ACTIVITE', 'CIV_D_ENTREPRISE', 'Bureaux d''études et entreprises de construction', NULL, NULL, NULL, 'FLYER_GENIE_CIVIL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(43, 6, NULL, NULL, 'DOMAINE_ACTIVITE', 'CIV_D_PUBLIC', 'Collectivités et institutions publiques', NULL, NULL, NULL, 'FLYER_GENIE_CIVIL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(44, 8, NULL, NULL, 'COMPETENCE', 'MEC_CAO', 'Conception mécanique assistée par ordinateur avec SolidWorks / CATIA', NULL, NULL, NULL, 'FLYER_GENIE_MECANIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(45, 8, NULL, NULL, 'COMPETENCE', 'MEC_STRUCT', 'Dimensionnement et calcul des structures mécaniques', NULL, NULL, NULL, 'FLYER_GENIE_MECANIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(46, 8, NULL, NULL, 'COMPETENCE', 'MEC_FAB', 'Fabrication et procédés industriels', NULL, NULL, NULL, 'FLYER_GENIE_MECANIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(47, 8, NULL, NULL, 'COMPETENCE', 'MEC_MAINT', 'Maintenance et fiabilité des systèmes industriels', NULL, NULL, NULL, 'FLYER_GENIE_MECANIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(48, 8, NULL, NULL, 'COMPETENCE', 'MEC_AUTO', 'Automatisation et mécatronique', NULL, NULL, NULL, 'FLYER_GENIE_MECANIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(49, 8, NULL, NULL, 'COMPETENCE', 'MEC_ENR', 'Énergies renouvelables et efficacité énergétique', NULL, NULL, NULL, 'FLYER_GENIE_MECANIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(50, 8, NULL, NULL, 'COMPETENCE', 'MEC_SIM', 'Simulation numérique', NULL, NULL, NULL, 'FLYER_GENIE_MECANIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(51, 8, NULL, NULL, 'COMPETENCE', 'MEC_PROJET', 'Gestion de projets industriels et innovation', NULL, NULL, NULL, 'FLYER_GENIE_MECANIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(52, 8, NULL, NULL, 'METIER', 'MEC_M_CONCEPTION', 'Ingénieur conception mécanique', NULL, NULL, NULL, 'FLYER_GENIE_MECANIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(53, 8, NULL, NULL, 'METIER', 'MEC_M_METHODES', 'Ingénieur méthodes', NULL, NULL, NULL, 'FLYER_GENIE_MECANIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(54, 8, NULL, NULL, 'METIER', 'MEC_M_PRODUCTION', 'Ingénieur production', NULL, NULL, NULL, 'FLYER_GENIE_MECANIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(55, 8, NULL, NULL, 'METIER', 'MEC_M_INDUSTRIALISATION', 'Ingénieur industrialisation', NULL, NULL, NULL, 'FLYER_GENIE_MECANIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(56, 8, NULL, NULL, 'METIER', 'MEC_M_MAINTENANCE', 'Ingénieur maintenance', NULL, NULL, NULL, 'FLYER_GENIE_MECANIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(57, 8, NULL, NULL, 'METIER', 'MEC_M_PROJET', 'Chef de projet industriel', NULL, NULL, NULL, 'FLYER_GENIE_MECANIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(58, 8, NULL, NULL, 'DOMAINE_ACTIVITE', 'MEC_D_AERO', 'Aéronautique et spatial', NULL, NULL, NULL, 'FLYER_GENIE_MECANIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(59, 8, NULL, NULL, 'DOMAINE_ACTIVITE', 'MEC_D_AUTO', 'Automobile et transport', NULL, NULL, NULL, 'FLYER_GENIE_MECANIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(60, 8, NULL, NULL, 'DOMAINE_ACTIVITE', 'MEC_D_ENERGIE', 'Énergies et génie énergétique', NULL, NULL, NULL, 'FLYER_GENIE_MECANIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL);
INSERT INTO public.formation_element (id, formation_id, specialisation_id, parent_id, type_element, code, nom, description, organisme, ordre_affichage, source_ref, actif, created_at, updated_at, parcours_id, valeur) VALUES
	(61, 8, NULL, NULL, 'DOMAINE_ACTIVITE', 'MEC_D_GENERAL', 'Mécanique générale', NULL, NULL, NULL, 'FLYER_GENIE_MECANIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(62, 8, NULL, NULL, 'DOMAINE_ACTIVITE', 'MEC_D_BTP', 'Bâtiment et travaux publics', NULL, NULL, NULL, 'FLYER_GENIE_MECANIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(63, 8, NULL, NULL, 'DOMAINE_ACTIVITE', 'MEC_D_CHIMIE', 'Industrie chimique et pharmaceutique', NULL, NULL, NULL, 'FLYER_GENIE_MECANIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(64, 8, NULL, NULL, 'DOMAINE_ACTIVITE', 'MEC_D_RD', 'Recherche et développement', NULL, NULL, NULL, 'FLYER_GENIE_MECANIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(65, 8, NULL, NULL, 'DOMAINE_ACTIVITE', 'MEC_D_IND40', 'Industrie 4.0 et digitalisation', NULL, NULL, NULL, 'FLYER_GENIE_MECANIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(66, 7, NULL, NULL, 'COMPETENCE', 'IND_AUTO', 'Automatisation & Informatique industrielle', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(67, 7, NULL, NULL, 'COMPETENCE', 'IND_MECA', 'Mécanique & Électronique', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(68, 7, NULL, NULL, 'COMPETENCE', 'IND_PY', 'Programmation Python', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(69, 7, NULL, NULL, 'COMPETENCE', 'IND_CLOUD', 'Maintenance prédictive & Cloud manufacturing', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(70, 7, NULL, NULL, 'COMPETENCE', 'IND_AI', 'Big Data, IoT & IA appliquée', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(71, 7, NULL, NULL, 'COMPETENCE', 'IND_CAO', 'Conception CAO SolidWorks', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(72, 7, NULL, NULL, 'COMPETENCE', 'IND_PLAN', 'Planification & Organisation', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(73, 7, NULL, NULL, 'COMPETENCE', 'IND_QUAL', 'Contrôle Qualité', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(74, 7, NULL, NULL, 'COMPETENCE', 'IND_GEST', 'Gestion & Économie', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(75, 7, NULL, NULL, 'COMPETENCE', 'IND_BI', 'Business Intelligence & Odoo ERP', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(76, 7, NULL, NULL, 'COMPETENCE', 'IND_SC', 'Supply Chain & Automated VSM', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(77, 7, NULL, NULL, 'COMPETENCE', 'IND_SOFT', 'Préparation à la carrière & Soft Skill', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(78, 7, NULL, NULL, 'COMPETENCE', 'IND_ERP', 'ERP Odoo-SAP', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(79, 7, NULL, NULL, 'METIER', 'IND_RESP_PROD', 'Responsable Production', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(80, 7, NULL, NULL, 'METIER', 'IND_SC_METIER', 'Ingénieur Supply Chain', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL);
INSERT INTO public.formation_element (id, formation_id, specialisation_id, parent_id, type_element, code, nom, description, organisme, ordre_affichage, source_ref, actif, created_at, updated_at, parcours_id, valeur) VALUES
	(81, 7, NULL, NULL, 'METIER', 'IND_SI_METIER', 'Ingénieur Systèmes d''Information', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(82, 7, NULL, NULL, 'METIER', 'IND_MAINT_METIER', 'Ingénieur Maintenance', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(83, 7, NULL, NULL, 'METIER', 'IND_DATA_METIER', 'Data Analyst industriel', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(84, 7, NULL, NULL, 'METIER', 'IND_40_METIER', 'Consultant Industrie 4.0', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(85, 7, NULL, NULL, 'METIER', 'M_QHSE', 'Responsable QHSE', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(86, 7, NULL, NULL, 'DOMAINE_ACTIVITE', 'IND_D_MECA', 'Mécanique & Automobile', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(87, 7, NULL, NULL, 'DOMAINE_ACTIVITE', 'IND_D_PHARMA', 'Pharmaceutique & Agroalimentaire', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(88, 7, NULL, NULL, 'DOMAINE_ACTIVITE', 'IND_D_INFO', 'Informatique & Numérique', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(89, 7, NULL, NULL, 'DOMAINE_ACTIVITE', 'IND_D_LOG', 'Logistique & Transport', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(90, 7, NULL, NULL, 'DOMAINE_ACTIVITE', 'IND_D_BANK', 'Banque & Services', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(91, 7, NULL, NULL, 'DOMAINE_ACTIVITE', 'IND_D_SANTE', 'Santé, Hôpitaux et cliniques', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(92, 7, NULL, NULL, 'DOMAINE_ACTIVITE', 'IND_D_BE', 'Bureaux d''étude', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(93, 10, NULL, NULL, 'COMPETENCE', 'ARCH_PROJET', 'Développement de projets architecturaux innovants, esthétiques et durables', NULL, NULL, NULL, 'FLYER_ARCHITECTURE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(94, 10, NULL, NULL, 'COMPETENCE', 'ARCH_OUTILS', 'Outils numériques', NULL, NULL, NULL, 'FLYER_ARCHITECTURE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(95, 10, NULL, NULL, 'COMPETENCE', 'ARCH_BIM', 'BIM / AutoCAD / Revit', NULL, NULL, NULL, 'FLYER_ARCHITECTURE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(96, 10, NULL, NULL, 'COMPETENCE', 'ARCH_BIO', 'Architecture bioclimatique / développement durable', NULL, NULL, NULL, 'FLYER_ARCHITECTURE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(97, 10, NULL, NULL, 'COMPETENCE', 'ARCH_IA', 'IA dans la conception et communication architecturale', NULL, NULL, NULL, 'FLYER_ARCHITECTURE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(98, 10, NULL, NULL, 'METIER', 'ARCH_CONCEPTEUR', 'Architecte concepteur', NULL, NULL, NULL, 'FLYER_ARCHITECTURE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(99, 10, NULL, NULL, 'METIER', 'ARCH_PAYSAGISTE', 'Architecte paysagiste', NULL, NULL, NULL, 'FLYER_ARCHITECTURE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(100, 10, NULL, NULL, 'METIER', 'ARCH_BIM_MGR', 'BIM Manager', NULL, NULL, NULL, 'FLYER_ARCHITECTURE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL);
INSERT INTO public.formation_element (id, formation_id, specialisation_id, parent_id, type_element, code, nom, description, organisme, ordre_affichage, source_ref, actif, created_at, updated_at, parcours_id, valeur) VALUES
	(101, 10, NULL, NULL, 'METIER', 'ARCH_URBANISTE', 'Architecte urbaniste', NULL, NULL, NULL, 'FLYER_ARCHITECTURE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(102, 10, NULL, NULL, 'METIER', 'ARCH_CHEF', 'Chef de projet', NULL, NULL, NULL, 'FLYER_ARCHITECTURE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(103, 10, NULL, NULL, 'DOMAINE_ACTIVITE', 'ARCH_D_HABITAT', 'Habitat et architecture', NULL, NULL, NULL, 'FLYER_ARCHITECTURE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(104, 10, NULL, NULL, 'DOMAINE_ACTIVITE', 'ARCH_D_ETUDES', 'Bureaux d''études et de conseils', NULL, NULL, NULL, 'FLYER_ARCHITECTURE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(105, 10, NULL, NULL, 'DOMAINE_ACTIVITE', 'ARCH_D_IMMO', 'Innovation immobilière et promotion architecturale', NULL, NULL, NULL, 'FLYER_ARCHITECTURE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(106, 10, NULL, NULL, 'DOMAINE_ACTIVITE', 'ARCH_D_URBA', 'Urbanisme et aménagement du territoire', NULL, NULL, NULL, 'FLYER_ARCHITECTURE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(107, 10, NULL, NULL, 'DOMAINE_ACTIVITE', 'ARCH_D_PATRIMOINE', 'Patrimoine, rénovation et conservation', NULL, NULL, NULL, 'FLYER_ARCHITECTURE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(108, 10, NULL, NULL, 'DOMAINE_ACTIVITE', 'ARCH_D_DESIGN', 'Design intérieur et scénographie', NULL, NULL, NULL, 'FLYER_ARCHITECTURE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(109, 3, NULL, NULL, 'COMPETENCE', 'LMS_CONCEPTION', 'Conception de systèmes mécatroniques', NULL, NULL, NULL, 'FLYER_LICENCE_MECATRONIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(110, 3, NULL, NULL, 'COMPETENCE', 'LMS_IOT', 'IoT et systèmes embarqués', NULL, NULL, NULL, 'FLYER_LICENCE_MECATRONIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(111, 3, NULL, NULL, 'COMPETENCE', 'LMS_INTELLIGENT', 'Systèmes intelligents', NULL, NULL, NULL, 'FLYER_LICENCE_MECATRONIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(112, 3, NULL, NULL, 'COMPETENCE', 'LMS_VISION', 'IA et vision', NULL, NULL, NULL, 'FLYER_LICENCE_MECATRONIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(113, 3, NULL, NULL, 'COMPETENCE', 'LMS_AUTO', 'Automatisation', NULL, NULL, NULL, 'FLYER_LICENCE_MECATRONIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(114, 3, NULL, NULL, 'DOMAINE_ACTIVITE', 'LMS_D_AERO', 'Aéronautique', NULL, NULL, NULL, 'FLYER_LICENCE_MECATRONIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(115, 3, NULL, NULL, 'DOMAINE_ACTIVITE', 'LMS_D_AUTO', 'Automobile', NULL, NULL, NULL, 'FLYER_LICENCE_MECATRONIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(116, 3, NULL, NULL, 'DOMAINE_ACTIVITE', 'LMS_D_MOBILITY', 'Smart Mobility', NULL, NULL, NULL, 'FLYER_LICENCE_MECATRONIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(117, 3, NULL, NULL, 'DOMAINE_ACTIVITE', 'LMS_D_ROBOT', 'Robotique', NULL, NULL, NULL, 'FLYER_LICENCE_MECATRONIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(118, 3, NULL, NULL, 'DOMAINE_ACTIVITE', 'LMS_D_ENERGY', 'Énergie et environnement', NULL, NULL, NULL, 'FLYER_LICENCE_MECATRONIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(119, 3, NULL, NULL, 'DOMAINE_ACTIVITE', 'LMS_D_IND40', 'Industrie 4.0', NULL, NULL, NULL, 'FLYER_LICENCE_MECATRONIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(120, 4, NULL, NULL, 'COMPETENCE', 'ELEC_CONCEPTION', 'Conception et gestion des systèmes électriques intelligents', NULL, NULL, NULL, 'FLYER_LICENCE_ELECTRIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL);
INSERT INTO public.formation_element (id, formation_id, specialisation_id, parent_id, type_element, code, nom, description, organisme, ordre_affichage, source_ref, actif, created_at, updated_at, parcours_id, valeur) VALUES
	(121, 4, NULL, NULL, 'COMPETENCE', 'ELEC_ENR', 'Intégration des énergies renouvelables et Smart Grids', NULL, NULL, NULL, 'FLYER_LICENCE_ELECTRIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(122, 4, NULL, NULL, 'COMPETENCE', 'ELEC_AUTO', 'Programmation, automatisme et contrôle des systèmes', NULL, NULL, NULL, 'FLYER_LICENCE_ELECTRIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(123, 4, NULL, NULL, 'COMPETENCE', 'ELEC_DATA', 'Analyse de données, IA et IoT appliqués à l''énergie', NULL, NULL, NULL, 'FLYER_LICENCE_ELECTRIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(124, 4, NULL, NULL, 'COMPETENCE', 'ELEC_PROJET', 'Gestion de projets, sécurité et développement durable', NULL, NULL, NULL, 'FLYER_LICENCE_ELECTRIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(125, 5, NULL, NULL, 'CERTIFICATION', 'CERT_HCIA', 'HCIA', NULL, NULL, NULL, 'FLYER_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(126, 5, NULL, NULL, 'CERTIFICATION', 'CERT_AWS', 'AWS', NULL, NULL, NULL, 'FLYER_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(127, 5, NULL, NULL, 'CERTIFICATION', 'CERT_NVIDIA', 'NVIDIA', NULL, NULL, NULL, 'FLYER_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(128, 5, NULL, NULL, 'CERTIFICATION', 'CERT_ISTQB', 'ISTQB', NULL, NULL, NULL, 'FLYER_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(129, 5, NULL, NULL, 'CERTIFICATION', 'CERT_CCNA', 'Cisco CCNA', NULL, 'Cisco', NULL, 'FLYER_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(130, 5, NULL, NULL, 'CERTIFICATION', 'CERT_IBM_SKILLSBUILD', 'IBM SkillsBuild', NULL, 'IBM', NULL, 'FLYER_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(131, 5, NULL, NULL, 'CERTIFICATION', 'CERT_MICROSOFT', 'Microsoft', NULL, 'Microsoft', NULL, 'FLYER_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(132, 5, NULL, NULL, 'LANGUE', 'LANG_FR', 'Francophone', NULL, NULL, NULL, 'FLYER_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(133, 5, NULL, NULL, 'LANGUE', 'LANG_EN', 'Anglophone', NULL, NULL, NULL, 'FLYER_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(134, 2, NULL, NULL, 'CERTIFICATION', 'CERT_AWS', 'AWS', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(135, 2, NULL, NULL, 'CERTIFICATION', 'CERT_ISTQB', 'ISTQB', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(136, 2, NULL, NULL, 'CERTIFICATION', 'CERT_PYTHON', 'Python', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(137, 2, NULL, NULL, 'CERTIFICATION', 'CERT_BIG_DATA', 'Big Data', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(138, 2, NULL, NULL, 'CERTIFICATION', 'CERT_IELTS', 'IELTS', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(139, 2, NULL, NULL, 'CERTIFICATION', 'CERT_DELF_DALF', 'DELF/DALF', NULL, 'France Éducation International', NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(140, 2, NULL, NULL, 'LANGUE', 'LANG_FR', 'Francophone', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL);
INSERT INTO public.formation_element (id, formation_id, specialisation_id, parent_id, type_element, code, nom, description, organisme, ordre_affichage, source_ref, actif, created_at, updated_at, parcours_id, valeur) VALUES
	(141, 2, NULL, NULL, 'LANGUE', 'LANG_EN', 'Anglophone', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(142, 2, NULL, NULL, 'OPPORTUNITE', 'OPP_TN_INTL', 'Tunisie et international', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(143, 7, NULL, NULL, 'CERTIFICATION', 'CERT_BLACK_BELT', 'Black Belt', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(144, 7, NULL, NULL, 'CERTIFICATION', 'CERT_GREEN_BELT', 'Green Belt', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(145, 7, NULL, NULL, 'CERTIFICATION', 'CERT_ISO_9001', 'ISO 9001', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(146, 7, NULL, NULL, 'CERTIFICATION', 'CERT_ISO_45001', 'ISO 45001', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(147, 7, NULL, NULL, 'CERTIFICATION', 'CERT_IELTS', 'IELTS', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(148, 7, NULL, NULL, 'CERTIFICATION', 'CERT_DELF_DALF', 'DELF/DALF', NULL, 'France Éducation International', NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(149, 9, NULL, NULL, 'CERTIFICATION', 'CERT_ISO_14001', 'ISO 14001', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(150, 9, NULL, NULL, 'CERTIFICATION', 'CERT_ISO_50001', 'ISO 50001', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(151, 9, NULL, NULL, 'CERTIFICATION', 'CERT_ISO_9001', 'ISO 9001', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(152, 9, NULL, NULL, 'CERTIFICATION', 'CERT_ISO_22000', 'ISO 22000', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(153, 9, NULL, NULL, 'CERTIFICATION', 'CERT_IELTS', 'IELTS', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(154, 9, NULL, NULL, 'CERTIFICATION', 'CERT_DELF_DALF', 'DELF/DALF', NULL, 'France Éducation International', NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(155, 10, NULL, NULL, 'MOBILITE', 'MOB_DOUBLE_DIPLOME', 'Double diplôme', NULL, NULL, NULL, 'FLYER_ARCHITECTURE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(156, 10, NULL, NULL, 'MOBILITE', 'MOB_SEMESTRE', 'Mobilité simple (un semestre d''études)', NULL, NULL, NULL, 'FLYER_ARCHITECTURE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(157, 10, NULL, NULL, 'MOBILITE', 'MOB_STAGE_INTL', 'Stage international en entreprise', NULL, NULL, NULL, 'FLYER_ARCHITECTURE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(158, 6, NULL, NULL, 'MOBILITE', 'MOB_DOUBLE_DIPLOME', 'Double diplôme', NULL, NULL, NULL, 'FLYER_GENIE_CIVIL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(159, 6, NULL, NULL, 'MOBILITE', 'MOB_SEMESTRE', 'Mobilité simple (un semestre d''études)', NULL, NULL, NULL, 'FLYER_GENIE_CIVIL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(160, 6, NULL, NULL, 'MOBILITE', 'MOB_STAGE_INTL', 'Stage international en entreprise', NULL, NULL, NULL, 'FLYER_GENIE_CIVIL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL);
INSERT INTO public.formation_element (id, formation_id, specialisation_id, parent_id, type_element, code, nom, description, organisme, ordre_affichage, source_ref, actif, created_at, updated_at, parcours_id, valeur) VALUES
	(161, 7, NULL, NULL, 'MOBILITE', 'MOB_DOUBLE_DIPLOME', 'Double diplôme', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(162, 7, NULL, NULL, 'MOBILITE', 'MOB_SEMESTRE', 'Mobilité simple (un semestre d''études)', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(163, 7, NULL, NULL, 'MOBILITE', 'MOB_STAGE_INTL', 'Stage international en entreprise', NULL, NULL, NULL, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(164, 8, NULL, NULL, 'MOBILITE', 'MOB_DOUBLE_DIPLOME', 'Double diplôme', NULL, NULL, NULL, 'FLYER_GENIE_MECANIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(165, 8, NULL, NULL, 'MOBILITE', 'MOB_SEMESTRE', 'Mobilité simple (un semestre d''études)', NULL, NULL, NULL, 'FLYER_GENIE_MECANIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(166, 8, NULL, NULL, 'MOBILITE', 'MOB_STAGE_INTL', 'Stage international en entreprise', NULL, NULL, NULL, 'FLYER_GENIE_MECANIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(167, 9, NULL, NULL, 'MOBILITE', 'MOB_DOUBLE_DIPLOME', 'Double diplôme', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(168, 9, NULL, NULL, 'MOBILITE', 'MOB_SEMESTRE', 'Mobilité simple (un semestre d''études)', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(169, 9, NULL, NULL, 'MOBILITE', 'MOB_STAGE_INTL', 'Stage international en entreprise', NULL, NULL, NULL, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(170, 2, NULL, NULL, 'MOBILITE', 'MOB_DOUBLE_DIPLOME', 'Double diplôme', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(171, 2, NULL, NULL, 'MOBILITE', 'MOB_SEMESTRE', 'Mobilité simple (un semestre d''études)', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(172, 2, NULL, NULL, 'MOBILITE', 'MOB_STAGE_INTL', 'Stage international en entreprise', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(173, 2, 5, NULL, 'CONTENU_PROGRAMME', 'AX_BD_VIS', 'Analyse & Visualisation', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(174, 2, 5, NULL, 'CONTENU_PROGRAMME', 'AX_BD_ML', 'Machine Learning', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(175, 2, 5, NULL, 'CONTENU_PROGRAMME', 'AX_BD_DS', 'Data Science', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(176, 2, 5, NULL, 'CONTENU_PROGRAMME', 'AX_BD_BIG', 'Big Data', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(177, 2, 6, NULL, 'CONTENU_PROGRAMME', 'AX_GL_WEB', 'Applications Web & Mobile', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(178, 2, 6, NULL, 'CONTENU_PROGRAMME', 'AX_GL_DEV', 'Développement logiciel', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(179, 2, 6, NULL, 'CONTENU_PROGRAMME', 'AX_GL_DB', 'Bases de données', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(180, 2, 6, NULL, 'CONTENU_PROGRAMME', 'AX_GL_AGILE', 'Méthodes Agile', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL);
INSERT INTO public.formation_element (id, formation_id, specialisation_id, parent_id, type_element, code, nom, description, organisme, ordre_affichage, source_ref, actif, created_at, updated_at, parcours_id, valeur) VALUES
	(181, 2, 7, NULL, 'CONTENU_PROGRAMME', 'AX_CY_AUDIT', 'Tests & Audit de sécurité', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(182, 2, 7, NULL, 'CONTENU_PROGRAMME', 'AX_CY_DATA', 'Protection des données', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(183, 2, 7, NULL, 'CONTENU_PROGRAMME', 'AX_CY_SYS', 'Sécurité des systèmes', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(184, 2, 7, NULL, 'CONTENU_PROGRAMME', 'AX_CY_NET', 'Réseaux', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(185, 2, 8, NULL, 'CONTENU_PROGRAMME', 'AX_IOT_EMB', 'Systèmes embarqués', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(186, 2, 8, NULL, 'CONTENU_PROGRAMME', 'AX_IOT_OBJ', 'Internet des Objets', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(187, 2, 8, NULL, 'CONTENU_PROGRAMME', 'AX_IOT_CAP', 'Capteurs & IoT', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(188, 2, 8, NULL, 'CONTENU_PROGRAMME', 'AX_IOT_40', 'Industrie 4.0', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(189, 2, 5, NULL, 'METIER', 'LIC_BD_M_DBA', 'Administrateur de bases de données', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(190, 2, 5, NULL, 'METIER', 'LIC_BD_M_ANALYSTE_PROG', 'Analyste programmeur informatique', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(191, 2, 5, NULL, 'METIER', 'LIC_BD_M_INTEGRATEUR', 'Intégrateur logiciels métiers', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(192, 2, 5, NULL, 'METIER', 'LIC_BD_M_TESTEUR', 'Testeur / Testeuse informatique', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(193, 2, 6, NULL, 'METIER', 'LIC_GL_M_ANALYSTE_ETUDE', 'Analyste d''étude informatique', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(194, 2, 6, NULL, 'METIER', 'LIC_GL_M_DECISIONNEL', 'Analyste décisionnel', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(195, 2, 6, NULL, 'METIER', 'LIC_GL_M_DEV_DATA', 'Développeur Data', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(196, 2, 6, NULL, 'METIER', 'LIC_GL_M_DATA_ANALYST', 'Data Analyst', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(197, 2, 7, NULL, 'METIER', 'LIC_CY_M_ADMIN_RESEAU', 'Administrateur réseau informatique', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(198, 2, 7, NULL, 'METIER', 'LIC_CY_M_ANALYSTE_RESEAU', 'Analyste réseau informatique', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(199, 2, 7, NULL, 'METIER', 'LIC_CY_M_ANALYSTE_CYBER', 'Analyste en cybersécurité', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(200, 2, 7, NULL, 'METIER', 'LIC_CY_M_CLOUD', 'Technicien Cloud', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL);
INSERT INTO public.formation_element (id, formation_id, specialisation_id, parent_id, type_element, code, nom, description, organisme, ordre_affichage, source_ref, actif, created_at, updated_at, parcours_id, valeur) VALUES
	(201, 2, 8, NULL, 'METIER', 'LIC_IOT_M_TECH', 'Technicienne en systèmes embarqués', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(202, 2, 8, NULL, 'METIER', 'LIC_IOT_M_TEST', 'Spécialiste test et validation logiciel', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(203, 2, 8, NULL, 'METIER', 'LIC_IOT_M_DEV', 'Développeuse systèmes embarqués', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(204, 2, 8, NULL, 'METIER', 'LIC_IOT_M_CLOUD', 'Technicien Cloud', NULL, NULL, NULL, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(205, NULL, NULL, NULL, 'INFORMATION', 'IIT_CONTACT_PUBLIC', 'Contacts publics IIT Sfax', 'L''Institut International de Technologie est situé à Sfax. Le téléphone public affiché est (+216) 74 46 50 20. L''adresse email générale publique est info@iit.tn. Le contact public du Génie Informatique est dep.tic@iit.ens.tn.', NULL, NULL, 'SRC_IIT_MAIN', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(206, 1, 1, NULL, 'MODULE', 'MOD_PREPA_PHYSIQUE', 'Physique', NULL, NULL, NULL, 'SRC_PREPA', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(207, 1, 1, NULL, 'MODULE', 'MOD_PREPA_ANALYSE', 'Analyse', NULL, NULL, NULL, 'SRC_PREPA', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(208, 1, 1, NULL, 'MODULE', 'MOD_PREPA_ALGEBRE', 'Algèbre', NULL, NULL, NULL, 'SRC_PREPA', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(209, 1, 1, NULL, 'MODULE', 'MOD_PREPA_CHIMIE', 'Chimie', NULL, NULL, NULL, 'SRC_PREPA', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(210, 1, 1, NULL, 'MODULE', 'MOD_PREPA_INFO', 'Informatique', NULL, NULL, NULL, 'SRC_PREPA', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(211, 1, 1, NULL, 'INFORMATION', 'INFO_PREPA_ADMISSION', 'Cycle Préparatoire - Prérequis institutionnels', 'Pour ce projet, le Cycle Préparatoire MP accepte les bacs Math et Sciences. L''admission finale n''est jamais automatique.', NULL, NULL, 'PROJECT_INSTITUTIONAL_RULES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(212, 1, 1, NULL, 'INFORMATION', 'INFO_PREPA_PROGRAMME', 'Cycle Préparatoire - Programme', 'Le programme public présente notamment physique, analyse, algèbre, chimie et informatique.', NULL, NULL, 'SRC_PREPA', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(213, 1, 1, NULL, 'INFORMATION', 'INFO_PREPA_DUREE', 'Cycle Préparatoire - Durée', 'Le guide étudiant public indique une durée de 2 ans pour le Cycle Préparatoire.', NULL, NULL, 'SRC_GUIDE_ETUDIANT', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(214, 1, 1, NULL, 'INFORMATION', 'INFO_PREPA_DIFFICULTE', 'Cycle Préparatoire - Exigence', 'Le site souligne que la Prépa demande beaucoup de travail et d''endurance.', NULL, NULL, 'SRC_PREPA', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(215, 2, 6, NULL, 'MODULE', 'MOD_GLSI_IA', 'Intelligence Artificielle', 'Mentionné dans le plan d''études public de la Licence Informatique.', NULL, NULL, 'SRC_PLAN_LICENCE_GLSI', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(216, 2, 6, NULL, 'MODULE', 'MOD_GLSI_WEB', 'Technologies Web', 'Mentionné dans le plan d''études public de la Licence Informatique.', NULL, NULL, 'SRC_PLAN_LICENCE_GLSI', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(217, 2, 6, NULL, 'MODULE', 'MOD_GLSI_BDD', 'Bases de Données', 'Mentionné dans le plan d''études public de la Licence Informatique.', NULL, NULL, 'SRC_PLAN_LICENCE_GLSI', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(218, 2, 6, NULL, 'MODULE', 'MOD_GLSI_GAME', 'Game Development', 'Mentionné dans le plan d''études public de la Licence Informatique.', NULL, NULL, 'SRC_PLAN_LICENCE_GLSI', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(219, 2, 6, NULL, 'MODULE', 'MOD_GLSI_DOTNET', 'Programmation .NET', 'Mentionné dans le plan d''études public de la Licence Informatique.', NULL, NULL, 'SRC_PLAN_LICENCE_GLSI', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(220, 2, 6, NULL, 'INFORMATION', 'INFO_LIC_GLSI_PROJECTS', 'Licence GLSI - Projets académiques', 'Le plan public contient un Projet Tutoré et un Projet Fédéré.', NULL, NULL, 'SRC_PLAN_LICENCE_GLSI', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL);
INSERT INTO public.formation_element (id, formation_id, specialisation_id, parent_id, type_element, code, nom, description, organisme, ordre_affichage, source_ref, actif, created_at, updated_at, parcours_id, valeur) VALUES
	(221, 2, 6, NULL, 'INFORMATION', 'INFO_LIC_GLSI_CAREERS', 'Licence GLSI - Débouchés publics', 'Les perspectives citées incluent développement logiciel et web, systèmes d''information, gestion de projets informatiques et analyse de données; elles ne garantissent pas un emploi.', NULL, NULL, 'SRC_LICENCE_GLSI', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(222, 5, 4, NULL, 'MODULE', 'MOD_GLID_SOFTWARE', 'Génie logiciel', NULL, NULL, NULL, 'SRC_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(223, 5, 4, NULL, 'MODULE', 'MOD_GLID_DISTRIBUTED', 'Systèmes distribués', NULL, NULL, NULL, 'SRC_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(224, 5, 4, NULL, 'MODULE', 'MOD_GLID_CLOUD', 'Cloud Computing', NULL, NULL, NULL, 'SRC_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(225, 5, 4, NULL, 'MODULE', 'MOD_GLID_AI', 'Intelligence Artificielle', NULL, NULL, NULL, 'SRC_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(226, 5, 4, NULL, 'MODULE', 'MOD_GLID_DATA', 'Science des données', NULL, NULL, NULL, 'SRC_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(227, 5, 4, NULL, 'MODULE', 'MOD_GLID_BI', 'Informatique décisionnelle', NULL, NULL, NULL, 'SRC_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(228, 5, 4, NULL, 'INFORMATION', 'INFO_GLID_PROGRAMME', 'GLID - Programme et orientation', 'GLID couvre notamment génie logiciel, systèmes distribués, cloud computing, intelligence artificielle, science des données et informatique décisionnelle.', NULL, NULL, 'SRC_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(229, 5, 4, NULL, 'INFORMATION', 'INFO_GLID_CAREERS', 'GLID - Débouchés publics', 'Les perspectives citées incluent ingénierie logiciel, BI, Data, IA/ML, architecture logicielle, Big Data, DevOps et gestion de projet; elles ne garantissent pas un emploi.', NULL, NULL, 'SRC_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(230, 5, 3, NULL, 'MODULE', 'MOD_ARSI_NETWORK', 'Réseaux', NULL, NULL, NULL, 'SRC_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(231, 5, 3, NULL, 'MODULE', 'MOD_ARSI_SYSTEMS', 'Administration systèmes', NULL, NULL, NULL, 'SRC_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(232, 5, 3, NULL, 'MODULE', 'MOD_ARSI_CYBER', 'Cybersécurité', NULL, NULL, NULL, 'SRC_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(233, 5, 3, NULL, 'MODULE', 'MOD_ARSI_CLOUD', 'Infrastructures Cloud', NULL, NULL, NULL, 'SRC_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(234, 5, 3, NULL, 'MODULE', 'MOD_ARSI_DEVSECOPS', 'DevSecOps', NULL, NULL, NULL, 'SRC_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(235, 5, 3, NULL, 'INFORMATION', 'INFO_ARSI_PROGRAMME', 'ARSI - Programme et orientation', 'ARSI couvre notamment réseaux, administration systèmes, cybersécurité, infrastructures cloud et DevSecOps.', NULL, NULL, 'SRC_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(236, 5, 3, NULL, 'INFORMATION', 'INFO_ARSI_CAREERS', 'ARSI - Débouchés publics', 'Les perspectives citées incluent administration réseaux et systèmes, ingénierie réseaux/cybersécurité, DevSecOps, audit et sécurité Cloud/IoT; elles ne garantissent pas un emploi.', NULL, NULL, 'SRC_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(237, 5, NULL, NULL, 'INFORMATION', 'INFO_ING_ADMISSION', 'Cycle Génie Informatique - Admission', 'La candidature se fait par pré-inscription, puis étude de dossier et entretien de validation. L''admission finale n''est pas automatique.', NULL, NULL, 'SRC_IIT_ADMISSION', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(238, 5, NULL, NULL, 'INFORMATION', 'INFO_ING_DUREE', 'Cycle Génie Informatique - Durée', 'Le guide étudiant public indique une durée de 3 ans après une Licence LMD ou un diplôme équivalent.', NULL, NULL, 'SRC_GUIDE_ETUDIANT', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(239, 5, NULL, NULL, 'INFORMATION', 'INFO_ING_PEDAGOGIE', 'Génie Informatique - Pédagogie et projets', 'Le programme combine bases théoriques, projets appliqués, travail en équipe, communication et gestion de projets d''ingénierie.', NULL, NULL, 'SRC_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL),
	(240, 5, NULL, NULL, 'INFORMATION', 'INFO_ING_ACCREDITATION', 'Génie Informatique - Accréditation', 'EURO-INF/ASIIN est une accréditation du programme et non une certification individuelle de l''étudiant.', NULL, NULL, 'SRC_ACCREDITATIONS', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01', NULL, NULL);
INSERT INTO public.formation_element (id, formation_id, specialisation_id, parent_id, type_element, code, nom, description, organisme, ordre_affichage, source_ref, actif, created_at, updated_at, parcours_id, valeur) VALUES
	(266, NULL, NULL, NULL, 'LIEN_PREINSCRIPTION', 'PREINSCRIPTION_URL', 'Préinscription IIT', NULL, NULL, 1, 'PROJECT_ENROLLMENT_SCOPE_V2', true, '2026-09-01 14:39:47.321786+01', '2026-09-01 14:39:47.321786+01', NULL, 'https://pre-inscription.iitadmin.com//?fbclid=IwAR1CfciROXUxaOBiXCcmv7DikLDQjD-8cKzEzuVLS9bEsnnZncSTAy96nzY'),
	(267, NULL, NULL, NULL, 'DOCUMENT_INSCRIPTION', 'DOC_BAC', 'Copie conforme du diplôme du Baccalauréat', NULL, NULL, 10, 'PROJECT_ENROLLMENT_SCOPE_V2', true, '2026-09-01 14:39:47.321786+01', '2026-09-01 14:39:47.321786+01', 1, NULL),
	(268, NULL, NULL, NULL, 'DOCUMENT_INSCRIPTION', 'DOC_BAC', 'Copie conforme du diplôme du Baccalauréat', NULL, NULL, 10, 'PROJECT_ENROLLMENT_SCOPE_V2', true, '2026-09-01 14:39:47.321786+01', '2026-09-01 14:39:47.321786+01', 2, NULL),
	(269, NULL, NULL, NULL, 'DOCUMENT_INSCRIPTION', 'DOC_BAC', 'Copie conforme du diplôme du Baccalauréat', NULL, NULL, 10, 'PROJECT_ENROLLMENT_SCOPE_V2', true, '2026-09-01 14:39:47.321786+01', '2026-09-01 14:39:47.321786+01', 3, NULL),
	(270, NULL, NULL, NULL, 'DOCUMENT_INSCRIPTION', 'DOC_BAC', 'Copie conforme du diplôme du Baccalauréat', NULL, NULL, 10, 'PROJECT_ENROLLMENT_SCOPE_V2', true, '2026-09-01 14:39:47.321786+01', '2026-09-01 14:39:47.321786+01', 4, NULL),
	(271, NULL, NULL, NULL, 'DOCUMENT_INSCRIPTION', 'DOC_RELEVE_BAC', 'Relevé de notes du Baccalauréat', NULL, NULL, 20, 'PROJECT_ENROLLMENT_SCOPE_V2', true, '2026-09-01 14:39:47.321786+01', '2026-09-01 14:39:47.321786+01', 1, NULL),
	(272, NULL, NULL, NULL, 'DOCUMENT_INSCRIPTION', 'DOC_RELEVE_BAC', 'Relevé de notes du Baccalauréat', NULL, NULL, 20, 'PROJECT_ENROLLMENT_SCOPE_V2', true, '2026-09-01 14:39:47.321786+01', '2026-09-01 14:39:47.321786+01', 2, NULL),
	(273, NULL, NULL, NULL, 'DOCUMENT_INSCRIPTION', 'DOC_RELEVE_BAC', 'Relevé de notes du Baccalauréat', NULL, NULL, 20, 'PROJECT_ENROLLMENT_SCOPE_V2', true, '2026-09-01 14:39:47.321786+01', '2026-09-01 14:39:47.321786+01', 3, NULL),
	(274, NULL, NULL, NULL, 'DOCUMENT_INSCRIPTION', 'DOC_RELEVE_BAC', 'Relevé de notes du Baccalauréat', NULL, NULL, 20, 'PROJECT_ENROLLMENT_SCOPE_V2', true, '2026-09-01 14:39:47.321786+01', '2026-09-01 14:39:47.321786+01', 4, NULL),
	(275, NULL, NULL, NULL, 'DOCUMENT_INSCRIPTION', 'DOC_PHOTOS', '3 photos', NULL, NULL, 50, 'PROJECT_ENROLLMENT_SCOPE_V2', true, '2026-09-01 14:39:47.321786+01', '2026-09-01 14:39:47.321786+01', 1, NULL),
	(276, NULL, NULL, NULL, 'DOCUMENT_INSCRIPTION', 'DOC_PHOTOS', '3 photos', NULL, NULL, 50, 'PROJECT_ENROLLMENT_SCOPE_V2', true, '2026-09-01 14:39:47.321786+01', '2026-09-01 14:39:47.321786+01', 2, NULL),
	(277, NULL, NULL, NULL, 'DOCUMENT_INSCRIPTION', 'DOC_PHOTOS', '3 photos', NULL, NULL, 50, 'PROJECT_ENROLLMENT_SCOPE_V2', true, '2026-09-01 14:39:47.321786+01', '2026-09-01 14:39:47.321786+01', 3, NULL),
	(278, NULL, NULL, NULL, 'DOCUMENT_INSCRIPTION', 'DOC_PHOTOS', '3 photos', NULL, NULL, 50, 'PROJECT_ENROLLMENT_SCOPE_V2', true, '2026-09-01 14:39:47.321786+01', '2026-09-01 14:39:47.321786+01', 4, NULL),
	(279, NULL, NULL, NULL, 'DOCUMENT_INSCRIPTION', 'DOC_REGLEMENT', 'Règlement intérieur avec signature légalisée à la Municipalité', NULL, NULL, 60, 'PROJECT_ENROLLMENT_SCOPE_V2', true, '2026-09-01 14:39:47.321786+01', '2026-09-01 14:39:47.321786+01', 1, NULL),
	(280, NULL, NULL, NULL, 'DOCUMENT_INSCRIPTION', 'DOC_REGLEMENT', 'Règlement intérieur avec signature légalisée à la Municipalité', NULL, NULL, 60, 'PROJECT_ENROLLMENT_SCOPE_V2', true, '2026-09-01 14:39:47.321786+01', '2026-09-01 14:39:47.321786+01', 2, NULL),
	(281, NULL, NULL, NULL, 'DOCUMENT_INSCRIPTION', 'DOC_REGLEMENT', 'Règlement intérieur avec signature légalisée à la Municipalité', NULL, NULL, 60, 'PROJECT_ENROLLMENT_SCOPE_V2', true, '2026-09-01 14:39:47.321786+01', '2026-09-01 14:39:47.321786+01', 3, NULL),
	(282, NULL, NULL, NULL, 'DOCUMENT_INSCRIPTION', 'DOC_REGLEMENT', 'Règlement intérieur avec signature légalisée à la Municipalité', NULL, NULL, 60, 'PROJECT_ENROLLMENT_SCOPE_V2', true, '2026-09-01 14:39:47.321786+01', '2026-09-01 14:39:47.321786+01', 4, NULL),
	(283, NULL, NULL, NULL, 'DOCUMENT_INSCRIPTION', 'DOC_CIN', 'Copie CIN', NULL, NULL, 70, 'PROJECT_ENROLLMENT_SCOPE_V2', true, '2026-09-01 14:39:47.321786+01', '2026-09-01 14:39:47.321786+01', 1, NULL),
	(284, NULL, NULL, NULL, 'DOCUMENT_INSCRIPTION', 'DOC_CIN', 'Copie CIN', NULL, NULL, 70, 'PROJECT_ENROLLMENT_SCOPE_V2', true, '2026-09-01 14:39:47.321786+01', '2026-09-01 14:39:47.321786+01', 2, NULL),
	(285, NULL, NULL, NULL, 'DOCUMENT_INSCRIPTION', 'DOC_CIN', 'Copie CIN', NULL, NULL, 70, 'PROJECT_ENROLLMENT_SCOPE_V2', true, '2026-09-01 14:39:47.321786+01', '2026-09-01 14:39:47.321786+01', 3, NULL);
INSERT INTO public.formation_element (id, formation_id, specialisation_id, parent_id, type_element, code, nom, description, organisme, ordre_affichage, source_ref, actif, created_at, updated_at, parcours_id, valeur) VALUES
	(286, NULL, NULL, NULL, 'DOCUMENT_INSCRIPTION', 'DOC_CIN', 'Copie CIN', NULL, NULL, 70, 'PROJECT_ENROLLMENT_SCOPE_V2', true, '2026-09-01 14:39:47.321786+01', '2026-09-01 14:39:47.321786+01', 4, NULL),
	(287, NULL, NULL, NULL, 'DOCUMENT_INSCRIPTION', 'DOC_PREINSCRIPTION', 'Pré-inscription', NULL, NULL, 80, 'PROJECT_ENROLLMENT_SCOPE_V2', true, '2026-09-01 14:39:47.321786+01', '2026-09-01 14:39:47.321786+01', 1, NULL),
	(288, NULL, NULL, NULL, 'DOCUMENT_INSCRIPTION', 'DOC_PREINSCRIPTION', 'Pré-inscription', NULL, NULL, 80, 'PROJECT_ENROLLMENT_SCOPE_V2', true, '2026-09-01 14:39:47.321786+01', '2026-09-01 14:39:47.321786+01', 2, NULL),
	(289, NULL, NULL, NULL, 'DOCUMENT_INSCRIPTION', 'DOC_PREINSCRIPTION', 'Pré-inscription', NULL, NULL, 80, 'PROJECT_ENROLLMENT_SCOPE_V2', true, '2026-09-01 14:39:47.321786+01', '2026-09-01 14:39:47.321786+01', 3, NULL),
	(290, NULL, NULL, NULL, 'DOCUMENT_INSCRIPTION', 'DOC_PREINSCRIPTION', 'Pré-inscription', NULL, NULL, 80, 'PROJECT_ENROLLMENT_SCOPE_V2', true, '2026-09-01 14:39:47.321786+01', '2026-09-01 14:39:47.321786+01', 4, NULL),
	(291, NULL, NULL, NULL, 'DOCUMENT_INSCRIPTION', 'DOC_LICENCE', 'Copie conforme du diplôme de Licence', NULL, NULL, 30, 'PROJECT_ENROLLMENT_SCOPE_V2', true, '2026-09-01 14:39:47.321786+01', '2026-09-01 14:39:47.321786+01', 3, NULL),
	(292, NULL, NULL, NULL, 'DOCUMENT_INSCRIPTION', 'DOC_RELEVES_LICENCE', '3 relevés de notes de Licence', NULL, NULL, 40, 'PROJECT_ENROLLMENT_SCOPE_V2', true, '2026-09-01 14:39:47.321786+01', '2026-09-01 14:39:47.321786+01', 3, NULL),
	(293, NULL, NULL, NULL, 'CERTIFICATION', 'CERT_ISO_21001', 'ISO 21001', 'Certification ISO 21001 déclarée par l opérateur; confirmation officielle IIT requise avant toute affirmation définitive.', NULL, 999, 'USER_PROVIDED_UNVERIFIED', true, '2026-09-03 11:40:53.411388+01', '2026-09-03 11:40:53.411388+01', NULL, NULL);


--
-- Data for Name: parcours; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.parcours (id, code, nom, duree_annees, description, actif, created_at, updated_at) VALUES
	(1, 'PREPA', 'Cycle Préparatoire', 2, 'Cycle Préparatoire aux études d''ingénieurs', true, '2026-08-30 13:15:21.369956+01', '2026-08-30 13:15:39.565163+01'),
	(2, 'LICENCE', 'Licence', 3, 'Cycle Licence', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01'),
	(3, 'INGENIEUR', 'Cycle Ingénieur', 3, 'Cycle Ingénieur', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01'),
	(4, 'ARCHITECTURE', 'Architecture', 6, 'Parcours du Diplôme National d''Architecte', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01');


--
-- Data for Name: regle_orientation; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.regle_orientation (id, formation_id, specialisation_id, code, nom, type_regle, criteres, description, priorite, source_ref, actif, created_at, updated_at) VALUES
	(2, 2, 6, 'ADMISSION_LICENCE_GLSI', 'Admission Licence Informatique — GLSI (historique)', 'ADMISSION', '{"diplome": "BAC", "type_bac": {"in": ["MATH", "SCIENCES", "INFORMATIQUE", "TECHNIQUE"]}}', 'Règle historique remplacée par ADMISSION_LICENCE_INFO; conservée inactive pour la traçabilité.', 1, 'SRC_LICENCE_GLSI', false, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01'),
	(3, 5, NULL, 'ADMISSION_INGENIEUR_INFO', 'Admission Cycle Génie Informatique', 'ADMISSION', '{"diplome": {"in": ["PREPA", "LICENCE", "MASTER"]}}', 'La page publique du Génie Informatique indique comme prérequis: Prépa, Licence ou Mastère.', 1, 'SRC_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01'),
	(4, 5, 4, 'RECOMMANDATION_GLID', 'Recommandation Orientation GLID', 'RECOMMANDATION', '{"interet": {"in": ["SOFTWARE", "DATA_AI"]}}', 'GLID est davantage aligné avec logiciel, Data, IA et Cloud qu''avec réseaux/cybersécurité.', 2, 'SRC_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01'),
	(5, 5, 3, 'RECOMMANDATION_ARSI', 'Recommandation Orientation ARSI', 'RECOMMANDATION', '{"interet": {"in": ["CYBER_NETWORKS"]}}', 'ARSI est davantage aligné avec réseaux, systèmes et cybersécurité qu''avec Data/IA.', 2, 'SRC_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01'),
	(6, 5, 2, 'RECOMMANDATION_SDIA', 'Recommandation Orientation SDIA', 'RECOMMANDATION', '{"interet": {"in": ["DATA_AI"]}}', 'L''intitulé officiel Science des Données et Intelligence Artificielle permet d''orienter un intérêt Data/IA vers SDIA; aucun contenu de programme supplémentaire n''est déduit.', 2, 'FLYER_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01'),
	(7, 2, NULL, 'ADMISSION_LICENCE_INFO', 'Admission Licence Informatique', 'ADMISSION', '{"diplome": "BAC", "type_bac": {"in": ["SCIENTIFIQUE", "ECONOMIQUE", "TECHNIQUE"]}}', 'Baccalauréat : toutes sections scientifiques, économiques et techniques.', 1, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01'),
	(8, 3, NULL, 'ADMISSION_LICENCE_MECATRONIQUE', 'Admission Licence Mécatronique', 'ADMISSION', '{"type_bac": {"in": ["MATH", "SCIENCES_EXPERIMENTALES", "INFORMATIQUE", "TECHNIQUE", "EQUIVALENT"]}}', 'Bac Math, Sciences expérimentales, Informatique, Technique ou équivalent.', 1, 'FLYER_LICENCE_MECATRONIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01'),
	(9, 6, NULL, 'ADMISSION_INGENIEUR_CIVIL', 'Admission Génie Civil', 'ADMISSION', '{"diplome": {"in": ["LICENCE", "MASTER", "PREPA"]}}', 'Licence, Mastère ou Préparatoire.', 1, 'FLYER_GENIE_CIVIL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01'),
	(10, 8, NULL, 'ADMISSION_INGENIEUR_MECANIQUE', 'Admission Génie Mécanique', 'ADMISSION', '{"diplome": {"in": ["LICENCE", "MASTER", "PREPA"]}}', 'Licence, Mastère ou Préparatoire.', 1, 'FLYER_GENIE_MECANIQUE', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01'),
	(11, 9, NULL, 'ADMISSION_INGENIEUR_PROCEDES', 'Admission Génie des Procédés', 'ADMISSION', '{"diplome": {"in": ["LICENCE", "MASTER", "PREPA"]}}', 'Licence, Mastère ou Préparatoire.', 1, 'FLYER_GENIE_PROCEDES', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01'),
	(12, 7, NULL, 'ADMISSION_INGENIEUR_INDUSTRIEL', 'Admission Génie Industriel', 'ADMISSION', '{"diplome_origine": {"in": ["LICENCE_MAINTENANCE_INDUSTRIELLE", "LICENCE_MATHEMATIQUE", "MATHEMATIQUE_APPLIQUEE", "LOGISTIQUE_INDUSTRIELLE", "PHYSIQUE_QUALITE", "PHYSIQUE_CHIMIE"]}}', 'Licence maintenance industrielle; Licence en Mathématique; Mathématique Appliquée; Logistique industrielle; Physique et Qualité; Physique-Chimie.', 1, 'FLYER_GENIE_INDUSTRIEL', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01'),
	(13, 10, NULL, 'ADMISSION_ARCH', 'ADMISSION Architecture', 'ADMISSION', '{"type_bac": {"in": ["MATH", "SCIENCES_EXPERIMENTALES", "INFORMATIQUE", "TECHNIQUE", "EQUIVALENT"]}}', NULL, 1, NULL, true, '2026-08-31 10:19:24.45689+01', '2026-08-31 10:19:24.45689+01'),
	(1, 1, NULL, 'ADMISSION_PREPA', 'Admission Cycle Préparatoire', 'ADMISSION', '{"diplome": "BAC", "type_bac": {"in": ["MATH", "SCIENCES"]}}', 'Règle institutionnelle courante: seuls les bacs Math et Sciences sont acceptés pour le Cycle Préparatoire.', 1, 'PROJECT_INSTITUTIONAL_RULES', true, '2026-08-30 13:15:21.369956+01', '2026-08-31 19:49:50.304515+01'),
	(14, 4, NULL, 'LIC_ELEC', 'Admission Licence Electriques', 'ADMISSION', '{"diplome": "BAC", "type_bac": {"in": ["MATH", "SCIENCES"]}}', NULL, 1, NULL, true, '2026-09-01 11:06:01.16214+01', '2026-09-01 11:06:01.16214+01');


--
-- Data for Name: specialisation; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.specialisation (id, formation_id, code, nom, description, ordre_affichage, source_ref, actif, created_at, updated_at) VALUES
	(1, 1, 'MP', 'Mathématiques-Physique (MP)', 'Spécialisation institutionnelle active du Cycle Préparatoire.', 1, 'PROJECT_INSTITUTIONAL_RULES', true, '2026-08-30 13:15:21.369956+01', '2026-08-30 13:15:39.565163+01'),
	(2, 5, 'SDIA', 'Science des Données et Intelligence Artificielle', NULL, 1, 'FLYER_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01'),
	(3, 5, 'ARSI', 'Administration Réseau et Sécurité Informatique', NULL, 2, 'FLYER_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01'),
	(4, 5, 'GLID', 'Génie Logiciel et Informatique Décisionnelle', NULL, 3, 'FLYER_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01'),
	(5, 2, 'LIC_INFO_BIG_DATA', 'Big Data & Analyse des Données', NULL, 1, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01'),
	(6, 2, 'LIC_INFO_GLSI', 'Génie Logiciel & Systèmes Intelligents', NULL, 2, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01'),
	(7, 2, 'LIC_INFO_CYBER', 'Cybersécurité et Réseaux', NULL, 3, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01'),
	(8, 2, 'LIC_INFO_IOT', 'Systèmes Embarqués & IoT', NULL, 4, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01');


--
-- Data for Name: tarif; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.tarif (id, formation_id, specialisation_id, frais_inscription, mensualite, nb_mensualites, devise, annee_universitaire, statut, remarque, source_ref, actif, created_at, updated_at, langue_enseignement, parcours_id) VALUES
	(5, 6, NULL, 800.00, 500.00, 10, 'TND', '2026-2027', 'CONFIRME', NULL, NULL, true, '2026-08-31 14:52:40.996603+01', '2026-09-02 09:24:58.357742+01', 'FRANCAIS', NULL),
	(3, 5, NULL, 800.00, 700.00, 10, 'TND', '2026-2027', 'CONFIRME', 'La page publique affiche 700 DT par mois sur 10 mois pour la première année, à titre indicatif. Un droit d''inscription de 800 DT est indiqué pour les étudiants tunisiens.', 'SRC_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-09-02 09:25:18.722053+01', 'FRANCAIS', NULL),
	(2, 2, NULL, 800.00, 600.00, 10, 'TND', '2026-2027', 'CONFIRME', 'La page publique affiche 667 DT par mois sur 9 mois pour la première année, à titre indicatif. Un droit d''inscription de 800 DT est indiqué pour les étudiants tunisiens.', 'SRC_LICENCE_GLSI', true, '2026-08-30 13:15:39.565163+01', '2026-09-02 09:25:23.688315+01', 'FRANCAIS', NULL),
	(1, 1, NULL, 800.00, 500.00, 10, 'TND', '2026-2027', 'CONFIRME', 'La page publique affiche 556 DT par mois sur 9 mois pour la première année, à titre indicatif. Un droit d''inscription de 800 DT est indiqué pour les étudiants tunisiens.', 'SRC_PREPA', true, '2026-08-30 13:15:39.565163+01', '2026-09-02 09:25:31.51601+01', 'FRANCAIS', NULL),
	(21, 2, NULL, 800.00, 800.00, 10, 'TND', '2026-2027', 'CONFIRME', NULL, NULL, true, '2026-09-02 11:52:49.437012+01', '2026-09-02 11:52:49.437012+01', 'ANGLAIS', NULL),
	(4, 10, NULL, 800.00, 700.00, 10, 'TND', '2026-2027', 'CONFIRME', NULL, NULL, true, '2026-08-31 14:52:12.788392+01', '2026-08-31 14:57:40.586958+01', 'FRANCAIS', NULL),
	(14, 5, NULL, 800.00, 850.00, 10, 'TND', '2026-2027', 'CONFIRME', NULL, NULL, true, '2026-08-31 18:49:46.245142+01', '2026-09-02 09:24:10.113989+01', 'ANGLAIS', NULL),
	(12, 3, NULL, 800.00, 710.00, 10, 'TND', '2026-2027', 'CONFIRME', NULL, NULL, true, '2026-08-31 14:56:09.680152+01', '2026-09-02 09:24:18.001071+01', 'ANGLAIS', NULL),
	(10, 4, NULL, 800.00, 710.00, 10, 'TND', '2026-2027', 'CONFIRME', NULL, NULL, true, '2026-08-31 14:54:57.723877+01', '2026-09-02 09:24:22.296035+01', 'ANGLAIS', NULL),
	(13, 2, NULL, 800.00, 600.00, 10, 'TND', '2026-2027', 'CONFIRME', NULL, NULL, true, '2026-08-31 14:56:48.84847+01', '2026-09-02 09:24:28.12157+01', 'FRANCAIS', NULL),
	(11, 3, NULL, 800.00, 510.00, 10, 'TND', '2026-2027', 'CONFIRME', NULL, NULL, true, '2026-08-31 14:55:41.88928+01', '2026-09-02 09:24:32.332393+01', 'FRANCAIS', NULL),
	(9, 4, NULL, 800.00, 510.00, 10, 'TND', '2026-2027', 'INDICATIF', NULL, NULL, true, '2026-08-31 14:54:34.85429+01', '2026-09-02 09:24:36.92446+01', 'FRANCAIS', NULL),
	(8, 9, NULL, 800.00, 550.00, 10, 'TND', '2026-2027', 'CONFIRME', NULL, NULL, true, '2026-08-31 14:53:56.487996+01', '2026-09-02 09:24:41.356303+01', 'FRANCAIS', NULL),
	(7, 8, NULL, 800.00, 550.00, 10, 'TND', '2026-2027', 'CONFIRME', NULL, NULL, true, '2026-08-31 14:53:35.006762+01', '2026-09-02 09:24:47.303874+01', 'FRANCAIS', NULL),
	(6, 7, NULL, 800.00, 550.00, 10, 'TND', '2026-2027', 'CONFIRME', NULL, NULL, true, '2026-08-31 14:53:16.931915+01', '2026-09-02 09:24:51.907154+01', 'FRANCAIS', NULL);


--
-- Name: accreditation_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.accreditation_id_seq', 10, true);


--
-- Name: formation_element_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.formation_element_id_seq', 293, true);


--
-- Name: formation_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.formation_id_seq', 11, true);


--
-- Name: parcours_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.parcours_id_seq', 4, true);


--
-- Name: regle_orientation_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.regle_orientation_id_seq', 14, true);


--
-- Name: specialisation_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.specialisation_id_seq', 8, true);


--
-- Name: tarif_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.tarif_id_seq', 21, true);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: accreditation pk_accreditation; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.accreditation
    ADD CONSTRAINT pk_accreditation PRIMARY KEY (id);


--
-- Name: conversation pk_conversation; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation
    ADD CONSTRAINT pk_conversation PRIMARY KEY (id);


--
-- Name: formation pk_formation; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.formation
    ADD CONSTRAINT pk_formation PRIMARY KEY (id);


--
-- Name: formation_element pk_formation_element; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.formation_element
    ADD CONSTRAINT pk_formation_element PRIMARY KEY (id);


--
-- Name: message pk_message; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.message
    ADD CONSTRAINT pk_message PRIMARY KEY (id);


--
-- Name: parcours pk_parcours; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parcours
    ADD CONSTRAINT pk_parcours PRIMARY KEY (id);


--
-- Name: regle_orientation pk_regle_orientation; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.regle_orientation
    ADD CONSTRAINT pk_regle_orientation PRIMARY KEY (id);


--
-- Name: specialisation pk_specialisation; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.specialisation
    ADD CONSTRAINT pk_specialisation PRIMARY KEY (id);


--
-- Name: tarif pk_tarif; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tarif
    ADD CONSTRAINT pk_tarif PRIMARY KEY (id);


--
-- Name: user_account pk_user_account; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_account
    ADD CONSTRAINT pk_user_account PRIMARY KEY (id);


--
-- Name: accreditation uq_accreditation_formation_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.accreditation
    ADD CONSTRAINT uq_accreditation_formation_code UNIQUE (formation_id, code);


--
-- Name: formation uq_formation_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.formation
    ADD CONSTRAINT uq_formation_code UNIQUE (code);


--
-- Name: message uq_message_conversation_role_request; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.message
    ADD CONSTRAINT uq_message_conversation_role_request UNIQUE (conversation_id, role, request_key);


--
-- Name: parcours uq_parcours_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parcours
    ADD CONSTRAINT uq_parcours_code UNIQUE (code);


--
-- Name: regle_orientation uq_regle_orientation_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.regle_orientation
    ADD CONSTRAINT uq_regle_orientation_code UNIQUE (code);


--
-- Name: specialisation uq_specialisation_formation_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.specialisation
    ADD CONSTRAINT uq_specialisation_formation_code UNIQUE (formation_id, code);


--
-- Name: specialisation uq_specialisation_formation_id_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.specialisation
    ADD CONSTRAINT uq_specialisation_formation_id_id UNIQUE (formation_id, id);


--
-- Name: user_account uq_user_account_email; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_account
    ADD CONSTRAINT uq_user_account_email UNIQUE (email);


--
-- Name: ix_accreditation_formation; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_accreditation_formation ON public.accreditation USING btree (formation_id);


--
-- Name: ix_conversation_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_conversation_user_id ON public.conversation USING btree (user_id);


--
-- Name: ix_conversation_user_updated; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_conversation_user_updated ON public.conversation USING btree (user_id, updated_at);


--
-- Name: ix_fe_formation; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_fe_formation ON public.formation_element USING btree (formation_id);


--
-- Name: ix_fe_parcours; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_fe_parcours ON public.formation_element USING btree (parcours_id);


--
-- Name: ix_fe_parent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_fe_parent ON public.formation_element USING btree (parent_id);


--
-- Name: ix_fe_specialisation; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_fe_specialisation ON public.formation_element USING btree (specialisation_id);


--
-- Name: ix_formation_parcours; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_formation_parcours ON public.formation USING btree (parcours_id);


--
-- Name: ix_message_conversation_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_message_conversation_created ON public.message USING btree (conversation_id, created_at);


--
-- Name: ix_message_conversation_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_message_conversation_id ON public.message USING btree (conversation_id);


--
-- Name: ix_regle_orientation_formation; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_regle_orientation_formation ON public.regle_orientation USING btree (formation_id);


--
-- Name: ix_regle_orientation_specialisation; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_regle_orientation_specialisation ON public.regle_orientation USING btree (specialisation_id);


--
-- Name: ix_specialisation_s_formation; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_specialisation_s_formation ON public.specialisation USING btree (formation_id);


--
-- Name: ix_tarif_formation; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tarif_formation ON public.tarif USING btree (formation_id);


--
-- Name: ix_tarif_formation_langue; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tarif_formation_langue ON public.tarif USING btree (formation_id, langue_enseignement);


--
-- Name: ix_tarif_parcours; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tarif_parcours ON public.tarif USING btree (parcours_id);


--
-- Name: ix_tarif_specialisation; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tarif_specialisation ON public.tarif USING btree (specialisation_id);


--
-- Name: uq_fe_formation_code; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_fe_formation_code ON public.formation_element USING btree (formation_id, type_element, code) WHERE ((parcours_id IS NULL) AND (formation_id IS NOT NULL) AND (specialisation_id IS NULL) AND (code IS NOT NULL));


--
-- Name: uq_fe_formation_nom; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_fe_formation_nom ON public.formation_element USING btree (formation_id, type_element, nom) WHERE ((parcours_id IS NULL) AND (formation_id IS NOT NULL) AND (specialisation_id IS NULL) AND (code IS NULL));


--
-- Name: uq_fe_global_code; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_fe_global_code ON public.formation_element USING btree (type_element, code) WHERE ((parcours_id IS NULL) AND (formation_id IS NULL) AND (specialisation_id IS NULL) AND (code IS NOT NULL));


--
-- Name: uq_fe_global_nom; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_fe_global_nom ON public.formation_element USING btree (type_element, nom) WHERE ((parcours_id IS NULL) AND (formation_id IS NULL) AND (specialisation_id IS NULL) AND (code IS NULL));


--
-- Name: uq_fe_parcours_code; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_fe_parcours_code ON public.formation_element USING btree (parcours_id, type_element, code) WHERE ((parcours_id IS NOT NULL) AND (code IS NOT NULL));


--
-- Name: uq_fe_parcours_nom; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_fe_parcours_nom ON public.formation_element USING btree (parcours_id, type_element, nom) WHERE ((parcours_id IS NOT NULL) AND (code IS NULL));


--
-- Name: uq_fe_specialisation_code; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_fe_specialisation_code ON public.formation_element USING btree (formation_id, specialisation_id, type_element, code) WHERE ((specialisation_id IS NOT NULL) AND (code IS NOT NULL));


--
-- Name: uq_fe_specialisation_nom; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_fe_specialisation_nom ON public.formation_element USING btree (formation_id, specialisation_id, type_element, nom) WHERE ((specialisation_id IS NOT NULL) AND (code IS NULL));


--
-- Name: accreditation fk_accreditation_formation_id_formation; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.accreditation
    ADD CONSTRAINT fk_accreditation_formation_id_formation FOREIGN KEY (formation_id) REFERENCES public.formation(id) ON DELETE CASCADE;


--
-- Name: conversation fk_conversation_user_id_user_account; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation
    ADD CONSTRAINT fk_conversation_user_id_user_account FOREIGN KEY (user_id) REFERENCES public.user_account(id) ON DELETE CASCADE;


--
-- Name: formation_element fk_fe_formation_specialisation; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.formation_element
    ADD CONSTRAINT fk_fe_formation_specialisation FOREIGN KEY (formation_id, specialisation_id) REFERENCES public.specialisation(formation_id, id) ON DELETE CASCADE;


--
-- Name: formation_element fk_formation_element_formation_id_formation; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.formation_element
    ADD CONSTRAINT fk_formation_element_formation_id_formation FOREIGN KEY (formation_id) REFERENCES public.formation(id) ON DELETE CASCADE;


--
-- Name: formation_element fk_formation_element_parcours_id_parcours; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.formation_element
    ADD CONSTRAINT fk_formation_element_parcours_id_parcours FOREIGN KEY (parcours_id) REFERENCES public.parcours(id) ON DELETE CASCADE;


--
-- Name: formation_element fk_formation_element_parent_id_formation_element; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.formation_element
    ADD CONSTRAINT fk_formation_element_parent_id_formation_element FOREIGN KEY (parent_id) REFERENCES public.formation_element(id) ON DELETE CASCADE;


--
-- Name: formation fk_formation_parcours_id_parcours; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.formation
    ADD CONSTRAINT fk_formation_parcours_id_parcours FOREIGN KEY (parcours_id) REFERENCES public.parcours(id);


--
-- Name: message fk_message_conversation_id_conversation; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.message
    ADD CONSTRAINT fk_message_conversation_id_conversation FOREIGN KEY (conversation_id) REFERENCES public.conversation(id) ON DELETE CASCADE;


--
-- Name: regle_orientation fk_regle_formation_specialisation; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.regle_orientation
    ADD CONSTRAINT fk_regle_formation_specialisation FOREIGN KEY (formation_id, specialisation_id) REFERENCES public.specialisation(formation_id, id) ON DELETE CASCADE;


--
-- Name: regle_orientation fk_regle_orientation_formation_id_formation; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.regle_orientation
    ADD CONSTRAINT fk_regle_orientation_formation_id_formation FOREIGN KEY (formation_id) REFERENCES public.formation(id) ON DELETE CASCADE;


--
-- Name: specialisation fk_specialisation_formation_id_formation; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.specialisation
    ADD CONSTRAINT fk_specialisation_formation_id_formation FOREIGN KEY (formation_id) REFERENCES public.formation(id) ON DELETE CASCADE;


--
-- Name: tarif fk_tarif_formation_id_formation; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tarif
    ADD CONSTRAINT fk_tarif_formation_id_formation FOREIGN KEY (formation_id) REFERENCES public.formation(id) ON DELETE CASCADE;


--
-- Name: tarif fk_tarif_formation_specialisation; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tarif
    ADD CONSTRAINT fk_tarif_formation_specialisation FOREIGN KEY (formation_id, specialisation_id) REFERENCES public.specialisation(formation_id, id) ON DELETE CASCADE;


--
-- Name: tarif fk_tarif_parcours_id_parcours; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tarif
    ADD CONSTRAINT fk_tarif_parcours_id_parcours FOREIGN KEY (parcours_id) REFERENCES public.parcours(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--


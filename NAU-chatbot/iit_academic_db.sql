-- ================================================================
-- 🎓 IIT SFAX — BASE DE DONNÉES ACADÉMIQUE & RAG SOURCE OF TRUTH
-- Source initiale : iit_v6_final(2).py (0 scraping, 0 hallucination)
-- Compatible : PostgreSQL 14, 15, 16, 17 | pgAdmin, DBeaver, psql
-- ================================================================

SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;

-- Ce fichier est le point d'entrée complet. Après la restauration du
-- schéma historique ci-dessous, il applique la migration académique v2
-- puis injecte de façon idempotente les données issues des flyers IIT.

-- ----------------------------------------------------------------
-- 1. NETTOYAGE PRÉALABLE DES TABLES
-- ----------------------------------------------------------------
DROP TABLE IF EXISTS parcours_specialite_element CASCADE;
DROP TABLE IF EXISTS element_formation CASCADE;
DROP TABLE IF EXISTS specialisation CASCADE;
DROP TABLE IF EXISTS information_academique CASCADE;
DROP TABLE IF EXISTS parcours_specialite_accreditation CASCADE;
DROP TABLE IF EXISTS label_accreditation CASCADE;
DROP TABLE IF EXISTS cours CASCADE;
DROP TABLE IF EXISTS module CASCADE;
DROP TABLE IF EXISTS critere_orientation CASCADE;
DROP TABLE IF EXISTS regle_orientation CASCADE;
DROP TABLE IF EXISTS tarif CASCADE;
DROP TABLE IF EXISTS parcours_specialite CASCADE;
DROP TABLE IF EXISTS source_information CASCADE;
DROP TABLE IF EXISTS specialite CASCADE;
DROP TABLE IF EXISTS parcours CASCADE;
DROP TABLE IF EXISTS departement CASCADE;


-- ----------------------------------------------------------------
-- 2. CRÉATION DES TABLES RELATIONNELLES (DDL)
-- ----------------------------------------------------------------

CREATE TABLE departement (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    nom VARCHAR(255) NOT NULL,
    description TEXT,
    actif BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE parcours (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    nom VARCHAR(255) NOT NULL,
    description TEXT,
    duree_annees INTEGER,
    actif BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE specialite (
    id SERIAL PRIMARY KEY,
    id_departement INTEGER NOT NULL REFERENCES departement(id) ON DELETE CASCADE,
    parent_specialite_id INTEGER REFERENCES specialite(id) ON DELETE SET NULL,
    code VARCHAR(50) NOT NULL UNIQUE,
    nom VARCHAR(255) NOT NULL,
    description TEXT,
    actif BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE source_information (
    id SERIAL PRIMARY KEY,
    code_source VARCHAR(100) NOT NULL,
    titre VARCHAR(255) NOT NULL,
    url VARCHAR(500) NOT NULL UNIQUE,
    type_source VARCHAR(50) NOT NULL DEFAULT 'WEB_PAGE',
    description TEXT,
    actif BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE parcours_specialite (
    id SERIAL PRIMARY KEY,
    id_parcours INTEGER NOT NULL REFERENCES parcours(id) ON DELETE CASCADE,
    id_specialite INTEGER NOT NULL REFERENCES specialite(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL UNIQUE,
    nom_affichage VARCHAR(255) NOT NULL,
    description TEXT,
    duree_annees INTEGER,
    actif BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_parcours_specialite_parcours_spec UNIQUE (id_parcours, id_specialite)
);

CREATE TABLE tarif (
    id SERIAL PRIMARY KEY,
    id_parcours_specialite INTEGER NOT NULL REFERENCES parcours_specialite(id) ON DELETE CASCADE,
    frais_inscription NUMERIC(10, 2),
    mensualite NUMERIC(10, 2),
    nb_mensualites INTEGER,
    devise VARCHAR(10) NOT NULL DEFAULT 'TND',
    annee_etude INTEGER,
    annee_universitaire VARCHAR(50),
    statut VARCHAR(50) NOT NULL DEFAULT 'INDICATIF',
    remarque TEXT,
    actif BOOLEAN NOT NULL DEFAULT TRUE,
    source_id INTEGER REFERENCES source_information(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE regle_orientation (
    id SERIAL PRIMARY KEY,
    id_parcours_specialite INTEGER NOT NULL REFERENCES parcours_specialite(id) ON DELETE CASCADE,
    code VARCHAR(100) NOT NULL UNIQUE,
    nom VARCHAR(255) NOT NULL,
    description TEXT,
    nature_regle VARCHAR(50) NOT NULL DEFAULT 'ADMISSION',
    priorite INTEGER NOT NULL DEFAULT 1,
    statut VARCHAR(50) NOT NULL DEFAULT 'CONFIRME',
    actif BOOLEAN NOT NULL DEFAULT TRUE,
    source_id INTEGER REFERENCES source_information(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE critere_orientation (
    id SERIAL PRIMARY KEY,
    id_regle INTEGER NOT NULL REFERENCES regle_orientation(id) ON DELETE CASCADE,
    type_critere VARCHAR(50) NOT NULL,
    operateur VARCHAR(20) NOT NULL,
    valeur_json JSONB NOT NULL,
    obligatoire BOOLEAN NOT NULL DEFAULT TRUE,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE module (
    id SERIAL PRIMARY KEY,
    id_parcours_specialite INTEGER NOT NULL REFERENCES parcours_specialite(id) ON DELETE CASCADE,
    code VARCHAR(50),
    nom VARCHAR(255) NOT NULL,
    description TEXT,
    annee_etude INTEGER,
    semestre INTEGER,
    credits NUMERIC(5, 2),
    ordre_affichage INTEGER DEFAULT 0,
    actif BOOLEAN NOT NULL DEFAULT TRUE,
    source_id INTEGER REFERENCES source_information(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE cours (
    id SERIAL PRIMARY KEY,
    id_module INTEGER NOT NULL REFERENCES module(id) ON DELETE CASCADE,
    code VARCHAR(50),
    nom VARCHAR(255) NOT NULL,
    description TEXT,
    type_cours VARCHAR(50),
    volume_horaire NUMERIC(6, 2),
    credits NUMERIC(5, 2),
    ordre_affichage INTEGER DEFAULT 0,
    actif BOOLEAN NOT NULL DEFAULT TRUE,
    source_id INTEGER REFERENCES source_information(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE label_accreditation (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    nom VARCHAR(255) NOT NULL,
    organisme VARCHAR(255) NOT NULL,
    description TEXT,
    date_debut DATE,
    date_fin DATE,
    actif BOOLEAN NOT NULL DEFAULT TRUE,
    source_id INTEGER REFERENCES source_information(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE parcours_specialite_accreditation (
    id SERIAL PRIMARY KEY,
    id_parcours_specialite INTEGER NOT NULL REFERENCES parcours_specialite(id) ON DELETE CASCADE,
    id_label INTEGER NOT NULL REFERENCES label_accreditation(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_parcours_spec_label UNIQUE (id_parcours_specialite, id_label)
);

CREATE TABLE information_academique (
    id SERIAL PRIMARY KEY,
    id_parcours_specialite INTEGER REFERENCES parcours_specialite(id) ON DELETE CASCADE,
    categorie VARCHAR(50) NOT NULL,
    titre VARCHAR(255) NOT NULL,
    contenu TEXT NOT NULL,
    source_id INTEGER REFERENCES source_information(id) ON DELETE SET NULL,
    actif BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ----------------------------------------------------------------
-- 3. INSERTIONS DES DONNÉES MÉTIER (DML)
-- ----------------------------------------------------------------

-- 3.1 Sources Information (Traçabilité)
INSERT INTO source_information (id, code_source, titre, url, type_source, description, actif) VALUES (1, 'SRC_IIT_MAIN', 'Contacts publics IIT Sfax', 'https://iit.tn/', 'WEB_PAGE', 'Portail institutionnel et contacts publics de l''IIT Sfax', TRUE);
INSERT INTO source_information (id, code_source, titre, url, type_source, description, actif) VALUES (2, 'SRC_IIT_ADMISSION', 'Procédure d''admission et préinscription', 'https://iit.tn/admission/procedure-et-frais-dinscription/', 'WEB_PAGE', 'Procédure publique d''admission et préinscription aux filières d''ingénierie', TRUE);
INSERT INTO source_information (id, code_source, titre, url, type_source, description, actif) VALUES (3, 'SRC_LICENCE_GLSI', 'Licence Génie Logiciel et Systèmes d''Information', 'https://iit.tn/licence-genie-logiciel-et-systheme-dinformation/', 'WEB_PAGE', 'Page publique de présentation de la Licence GLSI', TRUE);
INSERT INTO source_information (id, code_source, titre, url, type_source, description, actif) VALUES (4, 'SRC_PLAN_LICENCE_GLSI', 'Plan d''Études Licence Informatique', 'https://iit.tn/wp-content/uploads/2025/08/Plan_EtudeLicence-Info-1.pdf', 'PDF', 'Plan d''études public de la Licence Informatique (projets, modules, ISTQB)', TRUE);
INSERT INTO source_information (id, code_source, titre, url, type_source, description, actif) VALUES (5, 'SRC_PREPA', 'Cycle Préparatoire aux Études d''Ingénieurs', 'https://iit.tn/prepa/', 'WEB_PAGE', 'Page publique du Cycle Préparatoire IIT', TRUE);
INSERT INTO source_information (id, code_source, titre, url, type_source, description, actif) VALUES (6, 'SRC_GENIE_INFO', 'Cycle Génie Informatique (GLID & ARSI)', 'https://iit.tn/filieres-ingenieur/genie-informatique-2/', 'WEB_PAGE', 'Page publique du Cycle Ingénieur Génie Informatique avec options GLID et ARSI', TRUE);
INSERT INTO source_information (id, code_source, titre, url, type_source, description, actif) VALUES (7, 'SRC_GUIDE_ETUDIANT', 'Guide des Étudiants IIT', 'https://iit.tn/wp-content/uploads/2024/04/Guide-des-Etudiants-version-finale-FOR-WEB.pdf', 'PDF', 'Guide étudiant public IIT précisant les durées des cycles', TRUE);
INSERT INTO source_information (id, code_source, titre, url, type_source, description, actif) VALUES (8, 'SRC_ACCREDITATIONS', 'Accréditations et Labels IIT', 'https://iit.tn/a-propos/accreditations/', 'WEB_PAGE', 'Page publique des accréditations officielles IIT (EURO-INF / ASIIN)', TRUE);

-- 3.2 Départements
INSERT INTO departement (id, code, nom, description, actif) VALUES (1, 'INFO', 'Informatique', 'Département d''Informatique et Technologies de l''Information de l''IIT Sfax', TRUE);

-- 3.3 Parcours (Cycles)
INSERT INTO parcours (id, code, nom, description, duree_annees, actif) VALUES (1, 'PREPA', 'Cycle Préparatoire', 'Cycle Préparatoire aux études d''ingénieurs', 2, TRUE);
INSERT INTO parcours (id, code, nom, description, duree_annees, actif) VALUES (2, 'LICENCE', 'Licence', 'Cycle Licence', 3, TRUE);
INSERT INTO parcours (id, code, nom, description, duree_annees, actif) VALUES (3, 'INGENIEUR', 'Cycle Ingénieur', 'Cycle Ingénieur', 3, TRUE);

-- 3.4 Spécialités
INSERT INTO specialite (id, id_departement, parent_specialite_id, code, nom, description, actif) VALUES (1, 1, NULL, 'INFO', 'Informatique', 'Tronc commun et études générales en informatique', TRUE);
INSERT INTO specialite (id, id_departement, parent_specialite_id, code, nom, description, actif) VALUES (2, 1, 1, 'GLSI', 'Génie Logiciel et Systèmes d''Information', 'Licence Informatique — GLSI', TRUE);
INSERT INTO specialite (id, id_departement, parent_specialite_id, code, nom, description, actif) VALUES (3, 1, 1, 'GLID', 'Génie Logiciel et Informatique Décisionnelle', 'Spécialité ingénieur orientée Logiciel, Data, IA et Cloud', TRUE);
INSERT INTO specialite (id, id_departement, parent_specialite_id, code, nom, description, actif) VALUES (4, 1, 1, 'ARSI', 'Administration des Réseaux et Sécurité Informatique', 'Spécialité ingénieur orientée Réseaux, Systèmes et Cybersécurité', TRUE);

-- 3.5 Offres de Formation (Parcours x Spécialité)
INSERT INTO parcours_specialite (id, id_parcours, id_specialite, code, nom_affichage, description, duree_annees, actif) VALUES (1, 1, 1, 'PREPA_INFO', 'Cycle Préparatoire', 'Cycle Préparatoire aux études d''ingénieurs en informatique', 2, TRUE);
INSERT INTO parcours_specialite (id, id_parcours, id_specialite, code, nom_affichage, description, duree_annees, actif) VALUES (2, 2, 2, 'LICENCE_GLSI', 'Licence Informatique — GLSI', 'Licence en Génie Logiciel et Systèmes d''Information', NULL, TRUE);
INSERT INTO parcours_specialite (id, id_parcours, id_specialite, code, nom_affichage, description, duree_annees, actif) VALUES (3, 3, 1, 'INGENIEUR_INFO', 'Cycle Génie Informatique', 'Programme global et tronc commun du Cycle Génie Informatique', 3, TRUE);
INSERT INTO parcours_specialite (id, id_parcours, id_specialite, code, nom_affichage, description, duree_annees, actif) VALUES (4, 3, 3, 'INGENIEUR_GLID', 'Cycle Génie Informatique — GLID', 'Cycle Génie Informatique option Génie Logiciel et Informatique Décisionnelle', 3, TRUE);
INSERT INTO parcours_specialite (id, id_parcours, id_specialite, code, nom_affichage, description, duree_annees, actif) VALUES (5, 3, 4, 'INGENIEUR_ARSI', 'Cycle Génie Informatique — ARSI', 'Cycle Génie Informatique option Administration des Réseaux et Sécurité Informatique', 3, TRUE);

-- 3.6 Tarifs Indicatifs Officiels
INSERT INTO tarif (id, id_parcours_specialite, frais_inscription, mensualite, nb_mensualites, devise, annee_etude, annee_universitaire, statut, remarque, actif, source_id) VALUES (1, 2, 800.0, 667.0, 9, 'TND', 1, NULL, 'INDICATIF', 'La page publique affiche 667 DT par mois sur 9 mois pour la première année, à titre indicatif. Un droit d''inscription de 800 DT est indiqué pour les étudiants tunisiens.', TRUE, 3);
INSERT INTO tarif (id, id_parcours_specialite, frais_inscription, mensualite, nb_mensualites, devise, annee_etude, annee_universitaire, statut, remarque, actif, source_id) VALUES (2, 1, 800.0, 556.0, 9, 'TND', 1, NULL, 'INDICATIF', 'La page publique affiche 556 DT par mois sur 9 mois pour la première année, à titre indicatif. Un droit d''inscription de 800 DT est indiqué pour les étudiants tunisiens.', TRUE, 5);
INSERT INTO tarif (id, id_parcours_specialite, frais_inscription, mensualite, nb_mensualites, devise, annee_etude, annee_universitaire, statut, remarque, actif, source_id) VALUES (3, 3, 800.0, 778.0, 9, 'TND', 1, NULL, 'INDICATIF', 'La page publique affiche 778 DT par mois sur 9 mois pour la première année, à titre indicatif. Un droit d''inscription de 800 DT est indiqué pour les étudiants tunisiens.', TRUE, 6);

-- 3.7 Règles d'Orientation & d'Admission
INSERT INTO regle_orientation (id, id_parcours_specialite, code, nom, description, nature_regle, priorite, statut, actif, source_id) VALUES (1, 2, 'ADMISSION_LICENCE_GLSI', 'Admission Licence Informatique — GLSI', 'La page publique annonce la Licence GLSI accessible à partir d''un baccalauréat scientifique: mathématiques, sciences expérimentales, informatique ou technique.', 'ADMISSION', 1, 'CONFIRME', TRUE, 3);
INSERT INTO regle_orientation (id, id_parcours_specialite, code, nom, description, nature_regle, priorite, statut, actif, source_id) VALUES (2, 1, 'ADMISSION_PREPA', 'Admission Cycle Préparatoire', 'Le Cycle Préparatoire est annoncé comme accessible après un bac scientifique: mathématiques, sciences expérimentales, informatique ou technique.', 'ADMISSION', 1, 'CONFIRME', TRUE, 5);
INSERT INTO regle_orientation (id, id_parcours_specialite, code, nom, description, nature_regle, priorite, statut, actif, source_id) VALUES (3, 3, 'ADMISSION_INGENIEUR_INFO', 'Admission Cycle Génie Informatique', 'La page publique du Génie Informatique indique comme prérequis: Prépa, Licence ou Mastère.', 'ADMISSION', 1, 'CONFIRME', TRUE, 6);
INSERT INTO regle_orientation (id, id_parcours_specialite, code, nom, description, nature_regle, priorite, statut, actif, source_id) VALUES (4, 4, 'RECOMMANDATION_INGENIEUR_GLID', 'Recommandation Orientation GLID', 'GLID est davantage aligné avec logiciel, Data, IA et Cloud qu''avec réseaux/cybersécurité.', 'RECOMMANDATION', 2, 'INDICATIF', TRUE, 6);
INSERT INTO regle_orientation (id, id_parcours_specialite, code, nom, description, nature_regle, priorite, statut, actif, source_id) VALUES (5, 5, 'RECOMMANDATION_INGENIEUR_ARSI', 'Recommandation Orientation ARSI', 'ARSI est davantage aligné avec réseaux, systèmes et cybersécurité qu''avec Data/IA.', 'RECOMMANDATION', 2, 'INDICATIF', TRUE, 6);

-- 3.8 Critères d'Orientation (Format JSONB)
INSERT INTO critere_orientation (id, id_regle, type_critere, operateur, valeur_json, obligatoire, description) VALUES (85, 1, 'DIPLOME', 'EQ', '"BAC"'::jsonb, TRUE, 'Diplôme du Baccalauréat requis');
INSERT INTO critere_orientation (id, id_regle, type_critere, operateur, valeur_json, obligatoire, description) VALUES (86, 1, 'TYPE_BAC', 'IN', '["MATH", "SCIENCES", "INFORMATIQUE", "TECHNIQUE"]'::jsonb, TRUE, 'Sections de baccalauréat autorisées: Mathématiques, Sciences Expérimentales, Informatique, Technique');
INSERT INTO critere_orientation (id, id_regle, type_critere, operateur, valeur_json, obligatoire, description) VALUES (87, 2, 'DIPLOME', 'EQ', '"BAC"'::jsonb, TRUE, 'Diplôme du Baccalauréat requis');
INSERT INTO critere_orientation (id, id_regle, type_critere, operateur, valeur_json, obligatoire, description) VALUES (88, 2, 'TYPE_BAC', 'IN', '["MATH", "SCIENCES", "INFORMATIQUE", "TECHNIQUE"]'::jsonb, TRUE, 'Sections de baccalauréat autorisées: Mathématiques, Sciences Expérimentales, Informatique, Technique');
INSERT INTO critere_orientation (id, id_regle, type_critere, operateur, valeur_json, obligatoire, description) VALUES (89, 3, 'DIPLOME', 'IN', '["PREPA", "LICENCE", "MASTER"]'::jsonb, TRUE, 'Prérequis public: Prépa, Licence ou Mastère');
INSERT INTO critere_orientation (id, id_regle, type_critere, operateur, valeur_json, obligatoire, description) VALUES (90, 4, 'INTERET', 'IN', '["SOFTWARE", "DATA_AI"]'::jsonb, FALSE, 'Intérêt marqué pour le développement logiciel, la Data, l''IA et le Cloud');
INSERT INTO critere_orientation (id, id_regle, type_critere, operateur, valeur_json, obligatoire, description) VALUES (91, 5, 'INTERET', 'IN', '["CYBER_NETWORKS"]'::jsonb, FALSE, 'Intérêt marqué pour l''administration réseaux, systèmes et cybersécurité');

-- 3.9 Modules Pédagogiques du Programme
INSERT INTO module (id, id_parcours_specialite, code, nom, description, annee_etude, semestre, credits, ordre_affichage, actif, source_id) VALUES (1, 2, 'MOD_GLSI_IA', 'Intelligence Artificielle', 'Mentionné dans le plan d''études public de la Licence Informatique', NULL, NULL, NULL, 1, TRUE, 4);
INSERT INTO module (id, id_parcours_specialite, code, nom, description, annee_etude, semestre, credits, ordre_affichage, actif, source_id) VALUES (2, 2, 'MOD_GLSI_WEB', 'Technologies Web', 'Mentionné dans le plan d''études public de la Licence Informatique', NULL, NULL, NULL, 2, TRUE, 4);
INSERT INTO module (id, id_parcours_specialite, code, nom, description, annee_etude, semestre, credits, ordre_affichage, actif, source_id) VALUES (3, 2, 'MOD_GLSI_BDD', 'Bases de Données', 'Mentionné dans le plan d''études public de la Licence Informatique', NULL, NULL, NULL, 3, TRUE, 4);
INSERT INTO module (id, id_parcours_specialite, code, nom, description, annee_etude, semestre, credits, ordre_affichage, actif, source_id) VALUES (4, 2, 'MOD_GLSI_GAME_DEV', 'Game Development', 'Mentionné dans le plan d''études public de la Licence Informatique', NULL, NULL, NULL, 4, TRUE, 4);
INSERT INTO module (id, id_parcours_specialite, code, nom, description, annee_etude, semestre, credits, ordre_affichage, actif, source_id) VALUES (5, 2, 'MOD_GLSI_DOTNET', 'Programmation .NET', 'Mentionné dans le plan d''études public de la Licence Informatique', NULL, NULL, NULL, 5, TRUE, 4);
INSERT INTO module (id, id_parcours_specialite, code, nom, description, annee_etude, semestre, credits, ordre_affichage, actif, source_id) VALUES (6, 1, 'MOD_PREPA_PHYS', 'Physique', 'Présenté dans le programme public du Cycle Préparatoire', NULL, NULL, NULL, 1, TRUE, 5);
INSERT INTO module (id, id_parcours_specialite, code, nom, description, annee_etude, semestre, credits, ordre_affichage, actif, source_id) VALUES (7, 1, 'MOD_PREPA_ANA', 'Analyse', 'Présenté dans le programme public du Cycle Préparatoire', NULL, NULL, NULL, 2, TRUE, 5);
INSERT INTO module (id, id_parcours_specialite, code, nom, description, annee_etude, semestre, credits, ordre_affichage, actif, source_id) VALUES (8, 1, 'MOD_PREPA_ALG', 'Algèbre', 'Présenté dans le programme public du Cycle Préparatoire', NULL, NULL, NULL, 3, TRUE, 5);
INSERT INTO module (id, id_parcours_specialite, code, nom, description, annee_etude, semestre, credits, ordre_affichage, actif, source_id) VALUES (9, 1, 'MOD_PREPA_CHIM', 'Chimie', 'Présenté dans le programme public du Cycle Préparatoire', NULL, NULL, NULL, 4, TRUE, 5);
INSERT INTO module (id, id_parcours_specialite, code, nom, description, annee_etude, semestre, credits, ordre_affichage, actif, source_id) VALUES (10, 1, 'MOD_PREPA_INFO', 'Informatique', 'Présenté dans le programme public du Cycle Préparatoire', NULL, NULL, NULL, 5, TRUE, 5);
INSERT INTO module (id, id_parcours_specialite, code, nom, description, annee_etude, semestre, credits, ordre_affichage, actif, source_id) VALUES (11, 4, 'MOD_GLID_GL', 'Génie Logiciel', 'Couvert dans le programme du Cycle Génie Informatique — GLID', NULL, NULL, NULL, 1, TRUE, 6);
INSERT INTO module (id, id_parcours_specialite, code, nom, description, annee_etude, semestre, credits, ordre_affichage, actif, source_id) VALUES (12, 4, 'MOD_GLID_DISTRIB', 'Systèmes Distribués', 'Couvert dans le programme du Cycle Génie Informatique — GLID', NULL, NULL, NULL, 2, TRUE, 6);
INSERT INTO module (id, id_parcours_specialite, code, nom, description, annee_etude, semestre, credits, ordre_affichage, actif, source_id) VALUES (13, 4, 'MOD_GLID_CLOUD', 'Cloud Computing', 'Couvert dans le programme du Cycle Génie Informatique — GLID', NULL, NULL, NULL, 3, TRUE, 6);
INSERT INTO module (id, id_parcours_specialite, code, nom, description, annee_etude, semestre, credits, ordre_affichage, actif, source_id) VALUES (14, 4, 'MOD_GLID_IA', 'Intelligence Artificielle', 'Couvert dans le programme du Cycle Génie Informatique — GLID', NULL, NULL, NULL, 4, TRUE, 6);
INSERT INTO module (id, id_parcours_specialite, code, nom, description, annee_etude, semestre, credits, ordre_affichage, actif, source_id) VALUES (15, 4, 'MOD_GLID_DATA', 'Science des Données', 'Couvert dans le programme du Cycle Génie Informatique — GLID', NULL, NULL, NULL, 5, TRUE, 6);
INSERT INTO module (id, id_parcours_specialite, code, nom, description, annee_etude, semestre, credits, ordre_affichage, actif, source_id) VALUES (16, 4, 'MOD_GLID_BI', 'Informatique Décisionnelle', 'Couvert dans le programme du Cycle Génie Informatique — GLID', NULL, NULL, NULL, 6, TRUE, 6);
INSERT INTO module (id, id_parcours_specialite, code, nom, description, annee_etude, semestre, credits, ordre_affichage, actif, source_id) VALUES (17, 5, 'MOD_ARSI_RESEAUX', 'Réseaux', 'Couvert dans le programme du Cycle Génie Informatique — ARSI', NULL, NULL, NULL, 1, TRUE, 6);
INSERT INTO module (id, id_parcours_specialite, code, nom, description, annee_etude, semestre, credits, ordre_affichage, actif, source_id) VALUES (18, 5, 'MOD_ARSI_ADMIN_SYS', 'Administration Systèmes', 'Couvert dans le programme du Cycle Génie Informatique — ARSI', NULL, NULL, NULL, 2, TRUE, 6);
INSERT INTO module (id, id_parcours_specialite, code, nom, description, annee_etude, semestre, credits, ordre_affichage, actif, source_id) VALUES (19, 5, 'MOD_ARSI_CYBER', 'Cybersécurité', 'Couvert dans le programme du Cycle Génie Informatique — ARSI', NULL, NULL, NULL, 3, TRUE, 6);
INSERT INTO module (id, id_parcours_specialite, code, nom, description, annee_etude, semestre, credits, ordre_affichage, actif, source_id) VALUES (20, 5, 'MOD_ARSI_INFRA_CLOUD', 'Infrastructures Cloud', 'Couvert dans le programme du Cycle Génie Informatique — ARSI', NULL, NULL, NULL, 4, TRUE, 6);
INSERT INTO module (id, id_parcours_specialite, code, nom, description, annee_etude, semestre, credits, ordre_affichage, actif, source_id) VALUES (21, 5, 'MOD_ARSI_DEVSECOPS', 'DevSecOps', 'Couvert dans le programme du Cycle Génie Informatique — ARSI', NULL, NULL, NULL, 5, TRUE, 6);

-- 3.10 Accréditations Internationales
INSERT INTO label_accreditation (id, code, nom, organisme, description, date_debut, date_fin, actif, source_id) VALUES (1, 'EURO-INF', 'Label EURO-INF', 'ASIIN', 'Le Génie Informatique IIT porte le label EURO-INF attribué par ASIIN selon les pages publiques IIT. C''est une accréditation de programme international.', NULL, NULL, TRUE, 8);

-- 3.11 Association Offres x Accréditations
INSERT INTO parcours_specialite_accreditation (id, id_parcours_specialite, id_label) VALUES (1, 3, 1);

-- 3.12 Informations Académiques (Faits RAG 100% Préservés)
INSERT INTO information_academique (id, id_parcours_specialite, categorie, titre, contenu, source_id, actif) VALUES (1, NULL, 'CONTACT', 'Contacts publics IIT Sfax', 'L''Institut International de Technologie est situé à Sfax. Le téléphone public affiché est (+216) 74 46 50 20. L''adresse email générale publique est info@iit.tn. Le contact public du Génie Informatique est dep.tic@iit.ens.tn.', 1, TRUE);
INSERT INTO information_academique (id, id_parcours_specialite, categorie, titre, contenu, source_id, actif) VALUES (2, 3, 'ADMISSION', 'Admission aux filières d''ingénierie', 'La candidature aux filières d''ingénierie se fait par une pré-inscription en ligne. Une commission effectue un premier tri des candidatures. La procédure publique indique une admission sur dossier suivie d''un entretien de validation pour les filières d''ingénierie. L''admission finale n''est pas automatique.', 2, TRUE);
INSERT INTO information_academique (id, id_parcours_specialite, categorie, titre, contenu, source_id, actif) VALUES (3, 2, 'ADMISSION', 'Licence GLSI - Prérequis publics', 'La page publique utilisée dans cette base annonce la Licence GLSI accessible à partir d''un baccalauréat scientifique: mathématiques, sciences expérimentales, informatique ou technique. Si le bac de l''utilisateur n''apparaît pas dans cette liste, le chatbot doit demander une vérification d''éligibilité à l''IIT au lieu de promettre l''admission.', 3, TRUE);
INSERT INTO information_academique (id, id_parcours_specialite, categorie, titre, contenu, source_id, actif) VALUES (4, 2, 'PROGRAMME', 'Licence GLSI - Programme public', 'Le plan d''études public mentionne notamment intelligence artificielle, technologies Web, bases de données, Game Development et programmation .NET dans la partie publiée du plan.', 4, TRUE);
INSERT INTO information_academique (id, id_parcours_specialite, categorie, titre, contenu, source_id, actif) VALUES (5, 2, 'PROJECT', 'Licence GLSI - Projets académiques', 'Le plan d''études public de la Licence Informatique contient un Projet Tutoré. Le plan d''études public contient un Projet Fédéré.', 4, TRUE);
INSERT INTO information_academique (id, id_parcours_specialite, categorie, titre, contenu, source_id, actif) VALUES (6, 2, 'CERTIFICATION', 'Licence GLSI - Certification ISTQB', 'Le plan d''études public mentionne Tests des logiciels avec Certification ISTQB. Le chatbot ne doit pas inventer d''autres certifications individuelles si elles ne sont pas présentes dans les faits récupérés.', 4, TRUE);
INSERT INTO information_academique (id, id_parcours_specialite, categorie, titre, contenu, source_id, actif) VALUES (7, 2, 'CAREER', 'Licence GLSI - Débouchés publics', 'Les débouchés publics cités incluent développeur logiciel et web, ingénierie des systèmes d''information, gestion de projets informatiques et analyse de données. Ces débouchés sont des perspectives et ne constituent pas une garantie d''emploi.', 3, TRUE);
INSERT INTO information_academique (id, id_parcours_specialite, categorie, titre, contenu, source_id, actif) VALUES (8, 2, 'GENERAL', 'Licence GLSI - Frais publics indicatifs', 'La page publique affiche 667 DT par mois sur 9 mois pour la première année, à titre indicatif. Un droit d''inscription de 800 DT est indiqué pour les étudiants tunisiens. Les frais publics sont indicatifs et doivent être confirmés directement avec l''IIT.', 3, TRUE);
INSERT INTO information_academique (id, id_parcours_specialite, categorie, titre, contenu, source_id, actif) VALUES (9, 1, 'ADMISSION', 'Cycle Préparatoire - Prérequis publics', 'Le Cycle Préparatoire est annoncé comme accessible après un bac scientifique: mathématiques, sciences expérimentales, informatique ou technique. Le site souligne que la Prépa demande beaucoup de travail et d''endurance.', 5, TRUE);
INSERT INTO information_academique (id, id_parcours_specialite, categorie, titre, contenu, source_id, actif) VALUES (10, 1, 'PROGRAMME', 'Cycle Préparatoire - Programme', 'Le programme public présente notamment physique, analyse, algèbre, chimie et informatique.', 5, TRUE);
INSERT INTO information_academique (id, id_parcours_specialite, categorie, titre, contenu, source_id, actif) VALUES (11, 1, 'DURATION', 'Cycle Préparatoire - Durée', 'Le guide étudiant public indique une durée de 2 ans pour le Cycle Préparatoire.', 5, TRUE);
INSERT INTO information_academique (id, id_parcours_specialite, categorie, titre, contenu, source_id, actif) VALUES (12, 1, 'GENERAL', 'Cycle Préparatoire - Frais publics indicatifs', 'La page publique affiche 556 DT par mois sur 9 mois pour la première année, à titre indicatif. Un droit d''inscription de 800 DT est indiqué pour les étudiants tunisiens. Les frais publics sont indicatifs et doivent être confirmés directement avec l''IIT.', 5, TRUE);
INSERT INTO information_academique (id, id_parcours_specialite, categorie, titre, contenu, source_id, actif) VALUES (13, 3, 'ADMISSION', 'Cycle Génie Informatique - Prérequis', 'La page publique du Génie Informatique indique comme prérequis: Prépa, Licence ou Mastère. Le Génie Informatique propose trois parcours d''excellence : SDIA, ARSI et GLID. Une candidature reste soumise à la procédure d''admission de l''IIT; l''admission n''est pas automatique.', 6, TRUE);
INSERT INTO information_academique (id, id_parcours_specialite, categorie, titre, contenu, source_id, actif) VALUES (14, 3, 'GENERAL', 'Cycle Génie Informatique - Frais publics indicatifs', 'La page publique affiche 778 DT par mois sur 9 mois pour la première année, à titre indicatif. Un droit d''inscription de 800 DT est indiqué pour les étudiants tunisiens. Les frais publics sont indicatifs et doivent être confirmés directement avec l''IIT.', 6, TRUE);
INSERT INTO information_academique (id, id_parcours_specialite, categorie, titre, contenu, source_id, actif) VALUES (15, 3, 'DURATION', 'Cycle Génie Informatique - Durée', 'Le guide étudiant public IIT indique une durée de 3 ans pour le cycle ingénieur après une Licence LMD ou un diplôme équivalent. La durée applicable à une cohorte précise peut être reconfirmée auprès de l''IIT.', 7, TRUE);
INSERT INTO information_academique (id, id_parcours_specialite, categorie, titre, contenu, source_id, actif) VALUES (16, 3, 'PROJECT', 'Génie Informatique - Pédagogie et projets', 'La page publique indique que les élèves ingénieurs explorent les spécialités à travers des enseignements académiques et des projets appliqués. Le programme combine bases théoriques et activités pratiques. La page publique mentionne des opportunités d''interagir avec des partenaires industriels. Les résultats d''apprentissage publics incluent travail en équipe, communication et gestion de projets d''ingénierie.', 6, TRUE);
INSERT INTO information_academique (id, id_parcours_specialite, categorie, titre, contenu, source_id, actif) VALUES (17, 3, 'ACCREDITATION', 'Génie Informatique - Accréditation et certifications', 'Le Génie Informatique IIT porte le label EURO-INF attribué par ASIIN selon les pages publiques IIT. EURO-INF/ASIIN est une accréditation du programme, pas une certification individuelle de l''étudiant. La page publique Génie Informatique utilisée ici ne fournit pas une liste exhaustive de certifications individuelles propres à GLID ou ARSI.', 8, TRUE);
INSERT INTO information_academique (id, id_parcours_specialite, categorie, titre, contenu, source_id, actif) VALUES (18, 4, 'PROGRAMME', 'GLID - Programme et orientation', 'GLID signifie Génie Logiciel et Informatique Décisionnelle. GLID couvre notamment génie logiciel, systèmes distribués, cloud computing, intelligence artificielle, science des données et informatique décisionnelle. GLID est davantage aligné avec logiciel, Data, IA et Cloud qu''avec réseaux/cybersécurité.', 6, TRUE);
INSERT INTO information_academique (id, id_parcours_specialite, categorie, titre, contenu, source_id, actif) VALUES (19, 4, 'CAREER', 'GLID - Débouchés publics', 'Les débouchés publics cités pour GLID incluent ingénieur développement logiciel, BI, Data Scientist/Data Analyst, ingénieur IA/ML, architecte logiciel, ingénieur Big Data, ingénieur DevOps et chef de projet informatique. Ces débouchés sont des perspectives et ne constituent pas une garantie d''emploi.', 6, TRUE);
INSERT INTO information_academique (id, id_parcours_specialite, categorie, titre, contenu, source_id, actif) VALUES (20, 5, 'PROGRAMME', 'ARSI - Programme et orientation', 'ARSI signifie Administration des Réseaux et Sécurité Informatique. ARSI couvre notamment réseaux, administration systèmes, cybersécurité, infrastructures cloud et DevSecOps. ARSI est davantage aligné avec réseaux, systèmes et cybersécurité qu''avec Data/IA.', 6, TRUE);
INSERT INTO information_academique (id, id_parcours_specialite, categorie, titre, contenu, source_id, actif) VALUES (21, 5, 'CAREER', 'ARSI - Débouchés publics', 'Les débouchés publics cités pour ARSI incluent administrateur réseaux et systèmes, ingénieur réseaux, ingénieur cybersécurité, ingénieur DevSecOps, audit sécurité et sécurité Cloud/IoT. Ces débouchés sont des perspectives et ne constituent pas une garantie d''emploi.', 6, TRUE);
INSERT INTO information_academique (id, id_parcours_specialite, categorie, titre, contenu, source_id, actif) VALUES (22, 1, 'ADMISSION', 'Cycle Préparatoire - Préinscription', 'Pour le Cycle Préparatoire, la candidature commence par la pré-inscription via le lien officiel : https://iit.tn/admission/procedure-et-frais-dinscription/. Le droit d''inscription est de 800 DT. Le dossier est ensuite examiné selon les pièces demandées pour le parcours retenu. Pour tout paiement comptant, il existe une réduction de 5% sur le total des frais.', 2, TRUE);
INSERT INTO information_academique (id, id_parcours_specialite, categorie, titre, contenu, source_id, actif) VALUES (23, 2, 'ADMISSION', 'Licence Informatique - Préinscription', 'Pour la Licence en Informatique, la candidature commence par la pré-inscription via le lien officiel : https://iit.tn/admission/procedure-et-frais-dinscription/. Le droit d''inscription est de 800 DT. Le dossier est ensuite vérifié selon les pièces demandées pour le parcours retenu. Pour tout paiement comptant, il existe une réduction de 5% sur le total des frais.', 2, TRUE);
INSERT INTO information_academique (id, id_parcours_specialite, categorie, titre, contenu, source_id, actif) VALUES (24, 3, 'ADMISSION', 'Cycle Génie Informatique - Préinscription', 'Pour le Cycle Génie Informatique, la candidature commence par la pré-inscription via le lien officiel : https://iit.tn/admission/procedure-et-frais-dinscription/. Le droit d''inscription est de 800 DT. Le dossier est ensuite examiné selon les pièces demandées pour le parcours retenu. Pour tout paiement comptant, il existe une réduction de 5% sur le total des frais.', 2, TRUE);

-- ----------------------------------------------------------------
-- 4. SYNCHRONISATION DES SÉQUENCES AUTO-INCREMENT
-- ----------------------------------------------------------------
SELECT setval(pg_get_serial_sequence('information_academique', 'id'), COALESCE((SELECT MAX(id) FROM information_academique), 1), true);
SELECT setval(pg_get_serial_sequence('parcours_specialite_accreditation', 'id'), COALESCE((SELECT MAX(id) FROM parcours_specialite_accreditation), 1), true);
SELECT setval(pg_get_serial_sequence('label_accreditation', 'id'), COALESCE((SELECT MAX(id) FROM label_accreditation), 1), true);
SELECT setval(pg_get_serial_sequence('cours', 'id'), COALESCE((SELECT MAX(id) FROM cours), 1), true);
SELECT setval(pg_get_serial_sequence('module', 'id'), COALESCE((SELECT MAX(id) FROM module), 1), true);
SELECT setval(pg_get_serial_sequence('critere_orientation', 'id'), COALESCE((SELECT MAX(id) FROM critere_orientation), 1), true);
SELECT setval(pg_get_serial_sequence('regle_orientation', 'id'), COALESCE((SELECT MAX(id) FROM regle_orientation), 1), true);
SELECT setval(pg_get_serial_sequence('tarif', 'id'), COALESCE((SELECT MAX(id) FROM tarif), 1), true);
SELECT setval(pg_get_serial_sequence('parcours_specialite', 'id'), COALESCE((SELECT MAX(id) FROM parcours_specialite), 1), true);
SELECT setval(pg_get_serial_sequence('source_information', 'id'), COALESCE((SELECT MAX(id) FROM source_information), 1), true);
SELECT setval(pg_get_serial_sequence('specialite', 'id'), COALESCE((SELECT MAX(id) FROM specialite), 1), true);
SELECT setval(pg_get_serial_sequence('parcours', 'id'), COALESCE((SELECT MAX(id) FROM parcours), 1), true);
SELECT setval(pg_get_serial_sequence('departement', 'id'), COALESCE((SELECT MAX(id) FROM departement), 1), true);

-- ================================================================
-- MIGRATION ET DONNÉES ACADÉMIQUES DES FLYERS — VERSION 2
-- Les chemins sont résolus relativement à ce dump par psql.
-- ================================================================
BEGIN;

ALTER TABLE source_information ALTER COLUMN url DROP NOT NULL;
ALTER TABLE source_information ADD COLUMN IF NOT EXISTS fichier_source VARCHAR(500);
ALTER TABLE source_information ADD COLUMN IF NOT EXISTS date_document DATE;
ALTER TABLE source_information ADD COLUMN IF NOT EXISTS empreinte_sha256 CHAR(64);
CREATE UNIQUE INDEX IF NOT EXISTS uq_source_information_code_source ON source_information(code_source);
ALTER TABLE source_information DROP CONSTRAINT IF EXISTS source_information_type_source_check;
ALTER TABLE source_information ADD CONSTRAINT source_information_type_source_check
  CHECK (type_source IN ('WEB_PAGE','PDF','FLYER','OTHER')) NOT VALID;

ALTER TABLE specialite ALTER COLUMN id_departement DROP NOT NULL;
ALTER TABLE parcours_specialite ALTER COLUMN id_specialite DROP NOT NULL;
ALTER TABLE parcours_specialite ADD COLUMN IF NOT EXISTS nb_semestres INTEGER;
ALTER TABLE parcours_specialite ADD COLUMN IF NOT EXISTS credits_total INTEGER;
ALTER TABLE parcours_specialite ADD COLUMN IF NOT EXISTS intitule_diplome VARCHAR(255);
ALTER TABLE parcours_specialite ADD COLUMN IF NOT EXISTS legacy BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS specialisation (
 id SERIAL PRIMARY KEY,
 id_parcours_specialite INTEGER NOT NULL REFERENCES parcours_specialite(id) ON DELETE CASCADE,
 code VARCHAR(100) NOT NULL,
 nom VARCHAR(255) NOT NULL,
 description TEXT,
 ordre_affichage INTEGER NOT NULL DEFAULT 0,
 actif BOOLEAN NOT NULL DEFAULT TRUE,
 source_id INTEGER REFERENCES source_information(id) ON DELETE SET NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 CONSTRAINT uq_specialisation_formation_code UNIQUE(id_parcours_specialite,code)
);

ALTER TABLE module ADD COLUMN IF NOT EXISTS id_specialisation INTEGER REFERENCES specialisation(id) ON DELETE SET NULL;
ALTER TABLE regle_orientation ADD COLUMN IF NOT EXISTS id_specialisation INTEGER REFERENCES specialisation(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS element_formation (
 id SERIAL PRIMARY KEY,
 type_element VARCHAR(30) NOT NULL CHECK(type_element IN
   ('COMPETENCE','CONTENU_PROGRAMME','METIER','DOMAINE_ACTIVITE','CERTIFICATION','LANGUE','MOBILITE','OUTIL','OPPORTUNITE')),
 code VARCHAR(120),
 nom VARCHAR(255) NOT NULL,
 description TEXT,
 organisme VARCHAR(255),
 actif BOOLEAN NOT NULL DEFAULT TRUE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_element_formation_type_code
 ON element_formation(type_element,code) WHERE code IS NOT NULL;

CREATE TABLE IF NOT EXISTS parcours_specialite_element (
 id SERIAL PRIMARY KEY,
 id_parcours_specialite INTEGER NOT NULL REFERENCES parcours_specialite(id) ON DELETE CASCADE,
 id_specialisation INTEGER REFERENCES specialisation(id) ON DELETE CASCADE,
 id_element INTEGER NOT NULL REFERENCES element_formation(id) ON DELETE CASCADE,
 source_id INTEGER REFERENCES source_information(id) ON DELETE SET NULL,
 ordre_affichage INTEGER,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_pse_formation_element_global
 ON parcours_specialite_element(id_parcours_specialite,id_element) WHERE id_specialisation IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_pse_formation_specialisation_element
 ON parcours_specialite_element(id_parcours_specialite,id_specialisation,id_element) WHERE id_specialisation IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_specialisation_formation ON specialisation(id_parcours_specialite);
CREATE INDEX IF NOT EXISTS ix_specialisation_source ON specialisation(source_id);
CREATE INDEX IF NOT EXISTS ix_module_specialisation ON module(id_specialisation);
CREATE INDEX IF NOT EXISTS ix_regle_orientation_specialisation ON regle_orientation(id_specialisation);
CREATE INDEX IF NOT EXISTS ix_pse_formation ON parcours_specialite_element(id_parcours_specialite);
CREATE INDEX IF NOT EXISTS ix_pse_specialisation ON parcours_specialite_element(id_specialisation);
CREATE INDEX IF NOT EXISTS ix_pse_element ON parcours_specialite_element(id_element);
CREATE INDEX IF NOT EXISTS ix_pse_source ON parcours_specialite_element(source_id);

COMMIT;

BEGIN;

-- Parcours : exactement quatre actifs.
INSERT INTO parcours(code, nom, description, duree_annees, actif)
VALUES ('ARCHITECTURE','Architecture','Parcours du Diplôme National d''Architecte',6,TRUE)
ON CONFLICT(code) DO UPDATE SET nom=EXCLUDED.nom, duree_annees=EXCLUDED.duree_annees, actif=TRUE, updated_at=NOW();
UPDATE parcours SET duree_annees=CASE code WHEN 'PREPA' THEN 2 WHEN 'LICENCE' THEN 3 WHEN 'INGENIEUR' THEN 3 WHEN 'ARCHITECTURE' THEN 6 END,
 actif=(code IN ('PREPA','LICENCE','INGENIEUR','ARCHITECTURE')), updated_at=NOW();

-- Neuf flyers académiques distincts (les deux vues Procédés sont une seule source).
INSERT INTO source_information(code_source,titre,type_source,url,fichier_source,description,actif) VALUES
('FLYER_GENIE_INFO','Flyer Génie Informatique','FLYER',NULL,'c13241da-b36d-4fb1-bd1d-b3747ca3421b.jpg','Flyer officiel fourni par l''utilisateur.',TRUE),
('FLYER_ARCHITECTURE','Flyer Diplôme National d''Architecture','FLYER',NULL,'f65ce9a0-5b3d-4992-815d-2f9bff043b5b.jpg','Flyer officiel fourni par l''utilisateur.',TRUE),
('FLYER_LICENCE_MECATRONIQUE','Flyer Licence Mécatronique et Systèmes Intelligents','FLYER',NULL,'2d0af83a-bf70-4a29-8453-c0d5b2f54b8a.jpg','Flyer officiel fourni par l''utilisateur.',TRUE),
('FLYER_LICENCE_ELECTRIQUE','Flyer Licence Systèmes Électriques Intelligents et Énergies Renouvelables','FLYER',NULL,'1f9454f0-5c74-4c5d-b442-3b5f373a845b.jpg','Flyer officiel fourni par l''utilisateur.',TRUE),
('FLYER_GENIE_MECANIQUE','Flyer Génie Mécanique','FLYER',NULL,'7743f274-6c4b-475c-ac3e-31f3112bf9bd.jpg','Flyer officiel fourni par l''utilisateur.',TRUE),
('FLYER_GENIE_PROCEDES','Flyer Génie des Procédés','FLYER',NULL,'d8e262c1-24db-4494-a748-9dc036d0f198.jpg','Une formation; seconde photo 66b76f59-4bce-4c74-9d5d-e6c03fd2f877.jpg duplique le sujet.',TRUE),
('FLYER_GENIE_CIVIL','Flyer Génie Civil','FLYER',NULL,'e79c4c04-89ce-443e-a8f2-ffd52fc73aca.jpg','Flyer officiel fourni par l''utilisateur.',TRUE),
('FLYER_GENIE_INDUSTRIEL','Flyer Génie Industriel','FLYER',NULL,'5b3c7556-46af-45a9-9008-1be666cf395b.jpg','Flyer officiel fourni par l''utilisateur.',TRUE),
('FLYER_LICENCE_INFO','Flyer Licence en Informatique','FLYER',NULL,'ce3aed7e-4883-438b-a9a5-ed354d8192db.jpg','Flyer officiel fourni par l''utilisateur.',TRUE)
ON CONFLICT(code_source) DO UPDATE SET titre=EXCLUDED.titre,type_source='FLYER',url=NULL,fichier_source=EXCLUDED.fichier_source,description=EXCLUDED.description,actif=TRUE,updated_at=NOW();

-- Spécialités principales; aucune structure administrative n'est inventée.
INSERT INTO specialite(id_departement,code,nom,description,actif) VALUES
((SELECT id FROM departement WHERE code='INFO'),'INFORMATIQUE','Informatique','Formation principale informatique.',TRUE),
(NULL,'MECATRONIQUE_SI','Mécatronique et Systèmes Intelligents',NULL,TRUE),
(NULL,'ELEC_SEIER','Systèmes Électriques Intelligents et Énergies Renouvelables',NULL,TRUE),
(NULL,'CIVIL','Génie Civil',NULL,TRUE),(NULL,'INDUSTRIEL','Génie Industriel',NULL,TRUE),
(NULL,'MECANIQUE','Génie Mécanique',NULL,TRUE),(NULL,'PROCEDES','Génie des Procédés',NULL,TRUE),
(NULL,'ARCHITECTURE','Architecture',NULL,TRUE)
ON CONFLICT(code) DO UPDATE SET nom=EXCLUDED.nom,description=COALESCE(EXCLUDED.description,specialite.description),actif=TRUE,updated_at=NOW();

-- Les anciennes spécialités techniques sont remplacées par la table specialisation.
UPDATE specialite SET actif=FALSE,updated_at=NOW() WHERE code IN ('INFO','GLSI','GLID','ARSI');

-- PREPA général, conservation des dépendances de PREPA_INFO par renommage.
UPDATE parcours_specialite SET code='PREPA_GENERAL',id_specialite=NULL,nom_affichage='Cycle Préparatoire',
 description='Cycle Préparatoire général',legacy=FALSE,updated_at=NOW() WHERE code='PREPA_INFO';

-- Formations issues des flyers.
INSERT INTO parcours_specialite(id_parcours,id_specialite,code,nom_affichage,description,duree_annees,nb_semestres,credits_total,intitule_diplome,actif,legacy)
SELECT p.id,s.id,v.code,v.nom,v.description,v.duree,v.semestres,v.credits,v.diplome,TRUE,FALSE
FROM (VALUES
 ('LICENCE','INFORMATIQUE','LICENCE_INFO','Licence en Informatique',NULL,3,6,NULL,'Licence en Informatique'),
 ('LICENCE','MECATRONIQUE_SI','LICENCE_MECATRONIQUE_SI','Mécatronique & Systèmes Intelligents',NULL,3,6,NULL,'Licence Nationale en Mécatronique & Systèmes Intelligents'),
 ('LICENCE','ELEC_SEIER','LICENCE_ELEC_SEIER','Systèmes Électriques Intelligents & Énergies Renouvelables',NULL,3,6,NULL,'Licence en Génie Électrique'),
 ('INGENIEUR','INFORMATIQUE','INGENIEUR_INFO','Génie Informatique',NULL,3,NULL,NULL,NULL),
 ('INGENIEUR','CIVIL','INGENIEUR_CIVIL','Génie Civil',NULL,3,NULL,180,'Diplôme National d''Ingénieur en Génie Civil'),
 ('INGENIEUR','INDUSTRIEL','INGENIEUR_INDUSTRIEL','Génie Industriel',NULL,3,NULL,180,'Diplôme National d''Ingénieur en Génie Industriel'),
 ('INGENIEUR','MECANIQUE','INGENIEUR_MECANIQUE','Génie Mécanique',NULL,3,NULL,180,'Diplôme National d''Ingénieur en Génie Mécanique'),
 ('INGENIEUR','PROCEDES','INGENIEUR_PROCEDES','Génie des Procédés',NULL,3,NULL,180,'Diplôme National d''Ingénieur en Génie des Procédés'),
 ('ARCHITECTURE','ARCHITECTURE','ARCHITECTURE_DNA','Diplôme National d''Architecte',NULL,6,NULL,NULL,'Diplôme National d''Architecte')
) AS v(parcours,specialite,code,nom,description,duree,semestres,credits,diplome)
JOIN parcours p ON p.code=v.parcours JOIN specialite s ON s.code=v.specialite
ON CONFLICT(code) DO UPDATE SET id_parcours=EXCLUDED.id_parcours,id_specialite=EXCLUDED.id_specialite,nom_affichage=EXCLUDED.nom_affichage,
 duree_annees=EXCLUDED.duree_annees,nb_semestres=EXCLUDED.nb_semestres,credits_total=EXCLUDED.credits_total,intitule_diplome=EXCLUDED.intitule_diplome,actif=TRUE,legacy=FALSE,updated_at=NOW();

-- Ancienne licence et anciennes offres GLID/ARSI restent consultables mais legacy.
UPDATE parcours_specialite SET actif=FALSE,legacy=TRUE,updated_at=NOW()
 WHERE code IN ('LICENCE_GLSI','INGENIEUR_GLID','INGENIEUR_ARSI');

-- Spécialisations exactes.
INSERT INTO specialisation(id_parcours_specialite,code,nom,ordre_affichage,actif,source_id)
SELECT ps.id,v.code,v.nom,v.ordre,TRUE,src.id FROM (VALUES
 ('INGENIEUR_INFO','SDIA','Science des Données et Intelligence Artificielle',1,'FLYER_GENIE_INFO'),
 ('INGENIEUR_INFO','ARSI','Administration Réseau et Sécurité Informatique',2,'FLYER_GENIE_INFO'),
 ('INGENIEUR_INFO','GLID','Génie Logiciel et Informatique Décisionnelle',3,'FLYER_GENIE_INFO'),
 ('LICENCE_INFO','LIC_INFO_BIG_DATA','Big Data & Analyse des Données',1,'FLYER_LICENCE_INFO'),
 ('LICENCE_INFO','LIC_INFO_GLSI','Génie Logiciel & Systèmes Intelligents',2,'FLYER_LICENCE_INFO'),
 ('LICENCE_INFO','LIC_INFO_CYBER','Cybersécurité et Réseaux',3,'FLYER_LICENCE_INFO'),
 ('LICENCE_INFO','LIC_INFO_IOT','Systèmes Embarqués & IoT',4,'FLYER_LICENCE_INFO')
) v(formation,code,nom,ordre,source) JOIN parcours_specialite ps ON ps.code=v.formation JOIN source_information src ON src.code_source=v.source
ON CONFLICT(id_parcours_specialite,code) DO UPDATE SET nom=EXCLUDED.nom,ordre_affichage=EXCLUDED.ordre_affichage,actif=TRUE,source_id=EXCLUDED.source_id,updated_at=NOW();

-- Migration sans perte des modules/règles GLID et ARSI vers INGENIEUR_INFO + spécialisation.
UPDATE module m SET id_parcours_specialite=n.id,id_specialisation=sp.id
FROM parcours_specialite old,parcours_specialite n,specialisation sp
WHERE old.code='INGENIEUR_GLID' AND n.code='INGENIEUR_INFO' AND sp.id_parcours_specialite=n.id AND sp.code='GLID' AND m.id_parcours_specialite=old.id;
UPDATE module m SET id_parcours_specialite=n.id,id_specialisation=sp.id
FROM parcours_specialite old,parcours_specialite n,specialisation sp
WHERE old.code='INGENIEUR_ARSI' AND n.code='INGENIEUR_INFO' AND sp.id_parcours_specialite=n.id AND sp.code='ARSI' AND m.id_parcours_specialite=old.id;
UPDATE regle_orientation r SET id_parcours_specialite=n.id,id_specialisation=sp.id,code='RECOMMANDATION_GLID'
FROM parcours_specialite old,parcours_specialite n,specialisation sp
WHERE old.code='INGENIEUR_GLID' AND n.code='INGENIEUR_INFO' AND sp.id_parcours_specialite=n.id AND sp.code='GLID' AND r.id_parcours_specialite=old.id;
UPDATE regle_orientation r SET id_parcours_specialite=n.id,id_specialisation=sp.id,code='RECOMMANDATION_ARSI'
FROM parcours_specialite old,parcours_specialite n,specialisation sp
WHERE old.code='INGENIEUR_ARSI' AND n.code='INGENIEUR_INFO' AND sp.id_parcours_specialite=n.id AND sp.code='ARSI' AND r.id_parcours_specialite=old.id;

-- Éléments structurés globaux. Les axes de la Licence sont liés aux spécialisations plus bas.
WITH data(type_element,code,nom,organisme) AS (VALUES
 ('CERTIFICATION','CERT_HCIA','HCIA',NULL),('CERTIFICATION','CERT_AWS','AWS',NULL),('CERTIFICATION','CERT_NVIDIA','NVIDIA',NULL),
 ('CERTIFICATION','CERT_ISTQB','ISTQB',NULL),('CERTIFICATION','CERT_CCNA','Cisco CCNA','Cisco'),('CERTIFICATION','CERT_IBM_SKILLSBUILD','IBM SkillsBuild','IBM'),('CERTIFICATION','CERT_MICROSOFT','Microsoft','Microsoft'),
 ('CERTIFICATION','CERT_PYTHON','Python',NULL),('CERTIFICATION','CERT_BIG_DATA','Big Data',NULL),('CERTIFICATION','CERT_IELTS','IELTS',NULL),
 ('CERTIFICATION','CERT_DELF_DALF','DELF/DALF','France Éducation International'),
 ('CERTIFICATION','CERT_ISO_14001','ISO 14001',NULL),('CERTIFICATION','CERT_ISO_50001','ISO 50001',NULL),
 ('CERTIFICATION','CERT_ISO_9001','ISO 9001',NULL),('CERTIFICATION','CERT_ISO_22000','ISO 22000',NULL),('CERTIFICATION','CERT_ISO_45001','ISO 45001',NULL),
 ('CERTIFICATION','CERT_BLACK_BELT','Black Belt',NULL),('CERTIFICATION','CERT_GREEN_BELT','Green Belt',NULL),
 ('LANGUE','LANG_FR','Francophone',NULL),('LANGUE','LANG_EN','Anglophone',NULL),
 ('OPPORTUNITE','OPP_TN_INTL','Tunisie et international',NULL),
 ('MOBILITE','MOB_DOUBLE_DIPLOME','Double diplôme',NULL),('MOBILITE','MOB_SEMESTRE','Mobilité simple (un semestre d''études)',NULL),
 ('MOBILITE','MOB_STAGE_INTL','Stage international en entreprise',NULL)
) INSERT INTO element_formation(type_element,code,nom,organisme)
SELECT * FROM data ON CONFLICT(type_element,code) WHERE code IS NOT NULL DO UPDATE SET nom=EXCLUDED.nom,organisme=EXCLUDED.organisme,actif=TRUE,updated_at=NOW();

-- Compétences, métiers et domaines explicitement fournis/lisibles.
WITH data(type_element,code,nom) AS (VALUES
 ('COMPETENCE','PROC_SIM','Simulation de procédés (Aspen HYSYS, CFD, REVIT…)'),('COMPETENCE','PROC_TRANSFERT','Phénomènes de transfert et opérations unitaires'),('COMPETENCE','PROC_OPT','Contrôle et optimisation des procédés'),('COMPETENCE','PROC_QHSE','Sécurité, QHSE et environnement'),('COMPETENCE','PROC_FUTUR','Énergies du futur et développement durable'),('COMPETENCE','PROC_ACV','Bilan carbone, décarbonation industrielle et analyse du cycle de vie (ACV)'),
 ('METIER','PROC_M_PROD','Ingénieur de production'),('METIER','PROC_M_PROC','Ingénieur procédés'),('METIER','M_QHSE','Responsable QHSE'),('METIER','M_BUREAU','Responsable bureau d''études'),('METIER','M_CHEF_PROJET_IND','Chef de projet industriel'),('METIER','M_RD','Ingénieur R&D'),('METIER','M_TECH_COM','Ingénieur technico-commercial'),('METIER','M_BILAN_C','Ingénieur bilan carbone'),('METIER','M_TRANSITION','Consultant transition énergétique & climat'),('METIER','M_ACV','Ingénieur ACV & performance environnementale'),
 ('DOMAINE_ACTIVITE','D_PETROLE','Pétrole & Gaz'),('DOMAINE_ACTIVITE','D_ENERGIE','Énergie & Réseaux'),('DOMAINE_ACTIVITE','D_ENR','Énergies renouvelables'),('DOMAINE_ACTIVITE','D_BUREAUX','Bureaux d''études & Ingénierie'),('DOMAINE_ACTIVITE','D_CONSEIL','Sociétés de conseil & expertises'),('DOMAINE_ACTIVITE','D_BIOTECH','Biotechnologies & Agro/Biotech'),('DOMAINE_ACTIVITE','D_RD','Recherche & Développement'),('DOMAINE_ACTIVITE','D_CLIMAT','Bilan carbone & stratégie climat'),
 ('COMPETENCE','CIV_STRUCT','Conception et dimensionnement des structures'),('COMPETENCE','CIV_GEO','Études géotechniques et infrastructures'),('COMPETENCE','CIV_BETON','Béton et management des projets de construction'),('COMPETENCE','CIV_CAO','Modélisation et calcul assisté par ordinateur'),('COMPETENCE','CIV_QUAL','Contrôle qualité et expertise des matériaux'),('COMPETENCE','CIV_BIM','Maîtrise du BIM et des outils numériques de conception'),
 ('COMPETENCE','MEC_CAO','Conception mécanique assistée par ordinateur avec SolidWorks / CATIA'),('COMPETENCE','MEC_STRUCT','Dimensionnement et calcul des structures mécaniques'),('COMPETENCE','MEC_FAB','Fabrication et procédés industriels'),('COMPETENCE','MEC_MAINT','Maintenance et fiabilité des systèmes industriels'),('COMPETENCE','MEC_AUTO','Automatisation et mécatronique'),('COMPETENCE','MEC_ENR','Énergies renouvelables et efficacité énergétique'),('COMPETENCE','MEC_SIM','Simulation numérique'),('COMPETENCE','MEC_PROJET','Gestion de projets industriels et innovation'),
 ('COMPETENCE','IND_AUTO','Automatisation & Informatique industrielle'),('COMPETENCE','IND_MECA','Mécanique & Électronique'),('COMPETENCE','IND_PY','Programmation Python'),('COMPETENCE','IND_CLOUD','Maintenance prédictive & Cloud manufacturing'),('COMPETENCE','IND_AI','Big Data, IoT & IA appliquée'),('COMPETENCE','IND_CAO','Conception CAO SolidWorks'),('COMPETENCE','IND_PLAN','Planification & Organisation'),('COMPETENCE','IND_QUAL','Contrôle Qualité'),('COMPETENCE','IND_GEST','Gestion & Économie'),('COMPETENCE','IND_BI','Business Intelligence & Odoo ERP'),('COMPETENCE','IND_SC','Supply Chain & Automated VSM'),('COMPETENCE','IND_SOFT','Préparation à la carrière & Soft Skill'),('COMPETENCE','IND_ERP','ERP Odoo-SAP'),
 ('METIER','IND_RESP_PROD','Responsable Production'),('METIER','IND_SC_METIER','Ingénieur Supply Chain'),('METIER','IND_SI_METIER','Ingénieur Systèmes d''Information'),('METIER','IND_MAINT_METIER','Ingénieur Maintenance'),('METIER','IND_DATA_METIER','Data Analyst industriel'),('METIER','IND_40_METIER','Consultant Industrie 4.0'),
 ('DOMAINE_ACTIVITE','IND_D_MECA','Mécanique & Automobile'),('DOMAINE_ACTIVITE','IND_D_PHARMA','Pharmaceutique & Agroalimentaire'),('DOMAINE_ACTIVITE','IND_D_INFO','Informatique & Numérique'),('DOMAINE_ACTIVITE','IND_D_LOG','Logistique & Transport'),('DOMAINE_ACTIVITE','IND_D_BANK','Banque & Services'),('DOMAINE_ACTIVITE','IND_D_SANTE','Santé, Hôpitaux et cliniques'),('DOMAINE_ACTIVITE','IND_D_BE','Bureaux d''étude'),
 ('COMPETENCE','ARCH_PROJET','Développement de projets architecturaux innovants, esthétiques et durables'),('COMPETENCE','ARCH_OUTILS','Outils numériques'),('COMPETENCE','ARCH_BIM','BIM / AutoCAD / Revit'),('COMPETENCE','ARCH_BIO','Architecture bioclimatique / développement durable'),('COMPETENCE','ARCH_IA','IA dans la conception et communication architecturale'),
 ('METIER','ARCH_CONCEPTEUR','Architecte concepteur'),('METIER','ARCH_PAYSAGISTE','Architecte paysagiste'),('METIER','ARCH_BIM_MGR','BIM Manager'),('METIER','ARCH_URBANISTE','Architecte urbaniste'),('METIER','ARCH_CHEF','Chef de projet'),
 ('DOMAINE_ACTIVITE','ARCH_D_HABITAT','Habitat et architecture'),('DOMAINE_ACTIVITE','ARCH_D_ETUDES','Bureaux d''études et de conseils'),('DOMAINE_ACTIVITE','ARCH_D_IMMO','Innovation immobilière et promotion architecturale'),('DOMAINE_ACTIVITE','ARCH_D_URBA','Urbanisme et aménagement du territoire'),('DOMAINE_ACTIVITE','ARCH_D_PATRIMOINE','Patrimoine, rénovation et conservation'),('DOMAINE_ACTIVITE','ARCH_D_DESIGN','Design intérieur et scénographie'),
 ('COMPETENCE','ELEC_CONCEPTION','Conception et gestion des systèmes électriques intelligents'),('COMPETENCE','ELEC_ENR','Intégration des énergies renouvelables et Smart Grids'),('COMPETENCE','ELEC_AUTO','Programmation, automatisme et contrôle des systèmes'),('COMPETENCE','ELEC_DATA','Analyse de données, IA et IoT appliqués à l''énergie'),('COMPETENCE','ELEC_PROJET','Gestion de projets, sécurité et développement durable'),
 ('COMPETENCE','LMS_CONCEPTION','Conception de systèmes mécatroniques'),('COMPETENCE','LMS_IOT','IoT et systèmes embarqués'),('COMPETENCE','LMS_INTELLIGENT','Systèmes intelligents'),('COMPETENCE','LMS_VISION','IA et vision'),('COMPETENCE','LMS_AUTO','Automatisation'),
 ('DOMAINE_ACTIVITE','LMS_D_AERO','Aéronautique'),('DOMAINE_ACTIVITE','LMS_D_AUTO','Automobile'),('DOMAINE_ACTIVITE','LMS_D_MOBILITY','Smart Mobility'),('DOMAINE_ACTIVITE','LMS_D_ROBOT','Robotique'),('DOMAINE_ACTIVITE','LMS_D_ENERGY','Énergie et environnement'),('DOMAINE_ACTIVITE','LMS_D_IND40','Industrie 4.0'),
 ('METIER','MEC_M_CONCEPTION','Ingénieur conception mécanique'),('METIER','MEC_M_METHODES','Ingénieur méthodes'),('METIER','MEC_M_PRODUCTION','Ingénieur production'),('METIER','MEC_M_INDUSTRIALISATION','Ingénieur industrialisation'),('METIER','MEC_M_MAINTENANCE','Ingénieur maintenance'),('METIER','MEC_M_PROJET','Chef de projet industriel'),
 ('DOMAINE_ACTIVITE','MEC_D_AERO','Aéronautique et spatial'),('DOMAINE_ACTIVITE','MEC_D_AUTO','Automobile et transport'),('DOMAINE_ACTIVITE','MEC_D_ENERGIE','Énergies et génie énergétique'),('DOMAINE_ACTIVITE','MEC_D_GENERAL','Mécanique générale'),('DOMAINE_ACTIVITE','MEC_D_BTP','Bâtiment et travaux publics'),('DOMAINE_ACTIVITE','MEC_D_CHIMIE','Industrie chimique et pharmaceutique'),('DOMAINE_ACTIVITE','MEC_D_RD','Recherche et développement'),('DOMAINE_ACTIVITE','MEC_D_IND40','Industrie 4.0 et digitalisation'),
 ('METIER','CIV_M_ING','Ingénieur en Génie Civil'),('METIER','CIV_M_STRUCT','Ingénieur structures et géotechnique'),('METIER','CIV_M_TRAVAUX','Conducteur de travaux / Chef de chantier'),('METIER','CIV_M_AFFAIRES','Chargé d''affaires construction et BTP'),('METIER','CIV_M_HYDRAU','Ingénieur hydraulique'),('METIER','CIV_M_BIM','BIM Manager'),
 ('DOMAINE_ACTIVITE','CIV_D_BAT','Bâtiments et ouvrages d''art'),('DOMAINE_ACTIVITE','CIV_D_VRD','Routes, infrastructures et VRD'),('DOMAINE_ACTIVITE','CIV_D_GEO','Géotechnique et fondations'),('DOMAINE_ACTIVITE','CIV_D_HYDRAU','Ouvrages hydrauliques et maritimes'),('DOMAINE_ACTIVITE','CIV_D_LABO','Laboratoires de contrôle qualité des matériaux'),('DOMAINE_ACTIVITE','CIV_D_ENTREPRISE','Bureaux d''études et entreprises de construction'),('DOMAINE_ACTIVITE','CIV_D_PUBLIC','Collectivités et institutions publiques')
) INSERT INTO element_formation(type_element,code,nom) SELECT * FROM data
ON CONFLICT(type_element,code) WHERE code IS NOT NULL DO UPDATE SET nom=EXCLUDED.nom,actif=TRUE,updated_at=NOW();

-- Associations par préfixe de code, avec provenance flyer.
WITH map(formation,source,prefixes) AS (VALUES
 ('INGENIEUR_PROCEDES','FLYER_GENIE_PROCEDES',ARRAY['PROC_','M_QHSE','M_BUREAU','M_CHEF_PROJET_IND','M_RD','M_TECH_COM','M_BILAN_C','M_TRANSITION','M_ACV','D_']),
 ('INGENIEUR_CIVIL','FLYER_GENIE_CIVIL',ARRAY['CIV_']),('INGENIEUR_MECANIQUE','FLYER_GENIE_MECANIQUE',ARRAY['MEC_']),
 ('INGENIEUR_INDUSTRIEL','FLYER_GENIE_INDUSTRIEL',ARRAY['IND_','M_QHSE']),('ARCHITECTURE_DNA','FLYER_ARCHITECTURE',ARRAY['ARCH_']),
 ('LICENCE_MECATRONIQUE_SI','FLYER_LICENCE_MECATRONIQUE',ARRAY['LMS_']),('LICENCE_ELEC_SEIER','FLYER_LICENCE_ELECTRIQUE',ARRAY['ELEC_'])
) INSERT INTO parcours_specialite_element(id_parcours_specialite,id_element,source_id)
SELECT ps.id,e.id,src.id FROM map JOIN parcours_specialite ps ON ps.code=map.formation JOIN source_information src ON src.code_source=map.source
JOIN element_formation e ON EXISTS(SELECT 1 FROM unnest(map.prefixes) pfx WHERE e.code LIKE pfx || '%')
ON CONFLICT DO NOTHING;

-- Certifications/langues au niveau exact de la formation.
WITH map(formation,source,code) AS (VALUES
 ('INGENIEUR_INFO','FLYER_GENIE_INFO','CERT_HCIA'),('INGENIEUR_INFO','FLYER_GENIE_INFO','CERT_AWS'),('INGENIEUR_INFO','FLYER_GENIE_INFO','CERT_NVIDIA'),('INGENIEUR_INFO','FLYER_GENIE_INFO','CERT_ISTQB'),('INGENIEUR_INFO','FLYER_GENIE_INFO','CERT_CCNA'),('INGENIEUR_INFO','FLYER_GENIE_INFO','CERT_IBM_SKILLSBUILD'),('INGENIEUR_INFO','FLYER_GENIE_INFO','CERT_MICROSOFT'),('INGENIEUR_INFO','FLYER_GENIE_INFO','LANG_FR'),('INGENIEUR_INFO','FLYER_GENIE_INFO','LANG_EN'),
 ('LICENCE_INFO','FLYER_LICENCE_INFO','CERT_AWS'),('LICENCE_INFO','FLYER_LICENCE_INFO','CERT_ISTQB'),('LICENCE_INFO','FLYER_LICENCE_INFO','CERT_PYTHON'),('LICENCE_INFO','FLYER_LICENCE_INFO','CERT_BIG_DATA'),('LICENCE_INFO','FLYER_LICENCE_INFO','CERT_IELTS'),('LICENCE_INFO','FLYER_LICENCE_INFO','CERT_DELF_DALF'),('LICENCE_INFO','FLYER_LICENCE_INFO','LANG_FR'),('LICENCE_INFO','FLYER_LICENCE_INFO','LANG_EN'),('LICENCE_INFO','FLYER_LICENCE_INFO','OPP_TN_INTL')
) INSERT INTO parcours_specialite_element(id_parcours_specialite,id_element,source_id)
SELECT ps.id,e.id,src.id FROM map JOIN parcours_specialite ps ON ps.code=map.formation JOIN element_formation e ON e.code=map.code JOIN source_information src ON src.code_source=map.source
ON CONFLICT DO NOTHING;

-- Certifications placées dans la zone CERTIFICATIONS du flyer Génie Industriel.
WITH map(code) AS (VALUES ('CERT_BLACK_BELT'),('CERT_GREEN_BELT'),('CERT_ISO_9001'),('CERT_ISO_45001'),('CERT_IELTS'),('CERT_DELF_DALF'))
INSERT INTO parcours_specialite_element(id_parcours_specialite,id_element,source_id)
SELECT ps.id,e.id,src.id FROM map JOIN element_formation e USING(code)
JOIN parcours_specialite ps ON ps.code='INGENIEUR_INDUSTRIEL'
JOIN source_information src ON src.code_source='FLYER_GENIE_INDUSTRIEL' ON CONFLICT DO NOTHING;

-- Certifications explicitement présentées pour Génie des Procédés.
WITH map(code) AS (VALUES ('CERT_ISO_14001'),('CERT_ISO_50001'),('CERT_ISO_9001'),('CERT_ISO_22000'),('CERT_IELTS'),('CERT_DELF_DALF'))
INSERT INTO parcours_specialite_element(id_parcours_specialite,id_element,source_id)
SELECT ps.id,e.id,src.id FROM map JOIN element_formation e USING(code)
JOIN parcours_specialite ps ON ps.code='INGENIEUR_PROCEDES'
JOIN source_information src ON src.code_source='FLYER_GENIE_PROCEDES' ON CONFLICT DO NOTHING;

-- Mobilité annoncée dans les encadrés « Ouverture internationale ».
WITH formations(code,source) AS (VALUES
 ('ARCHITECTURE_DNA','FLYER_ARCHITECTURE'),('INGENIEUR_CIVIL','FLYER_GENIE_CIVIL'),
 ('INGENIEUR_INDUSTRIEL','FLYER_GENIE_INDUSTRIEL'),('INGENIEUR_MECANIQUE','FLYER_GENIE_MECANIQUE'),
 ('INGENIEUR_PROCEDES','FLYER_GENIE_PROCEDES'))
INSERT INTO parcours_specialite_element(id_parcours_specialite,id_element,source_id)
SELECT ps.id,e.id,src.id FROM formations f JOIN parcours_specialite ps ON ps.code=f.code
JOIN source_information src ON src.code_source=f.source
CROSS JOIN element_formation e WHERE e.code IN ('MOB_DOUBLE_DIPLOME','MOB_SEMESTRE','MOB_STAGE_INTL')
ON CONFLICT DO NOTHING;

-- Axes de chaque spécialisation Licence Informatique : contenus, pas modules officiels.
WITH data(spec,code,nom) AS (VALUES
 ('LIC_INFO_BIG_DATA','AX_BD_VIS','Analyse & Visualisation'),('LIC_INFO_BIG_DATA','AX_BD_ML','Machine Learning'),('LIC_INFO_BIG_DATA','AX_BD_DS','Data Science'),('LIC_INFO_BIG_DATA','AX_BD_BIG','Big Data'),
 ('LIC_INFO_GLSI','AX_GL_WEB','Applications Web & Mobile'),('LIC_INFO_GLSI','AX_GL_DEV','Développement logiciel'),('LIC_INFO_GLSI','AX_GL_DB','Bases de données'),('LIC_INFO_GLSI','AX_GL_AGILE','Méthodes Agile'),
 ('LIC_INFO_CYBER','AX_CY_AUDIT','Tests & Audit de sécurité'),('LIC_INFO_CYBER','AX_CY_DATA','Protection des données'),('LIC_INFO_CYBER','AX_CY_SYS','Sécurité des systèmes'),('LIC_INFO_CYBER','AX_CY_NET','Réseaux'),
 ('LIC_INFO_IOT','AX_IOT_EMB','Systèmes embarqués'),('LIC_INFO_IOT','AX_IOT_OBJ','Internet des Objets'),('LIC_INFO_IOT','AX_IOT_CAP','Capteurs & IoT'),('LIC_INFO_IOT','AX_IOT_40','Industrie 4.0')
), ins AS (
 INSERT INTO element_formation(type_element,code,nom) SELECT 'CONTENU_PROGRAMME',code,nom FROM data
 ON CONFLICT(type_element,code) WHERE code IS NOT NULL DO UPDATE SET nom=EXCLUDED.nom,updated_at=NOW() RETURNING id,code
) INSERT INTO parcours_specialite_element(id_parcours_specialite,id_specialisation,id_element,source_id)
SELECT ps.id,sp.id,e.id,src.id FROM data d JOIN element_formation e ON e.type_element='CONTENU_PROGRAMME' AND e.code=d.code
JOIN parcours_specialite ps ON ps.code='LICENCE_INFO' JOIN specialisation sp ON sp.id_parcours_specialite=ps.id AND sp.code=d.spec
JOIN source_information src ON src.code_source='FLYER_LICENCE_INFO' ON CONFLICT DO NOTHING;

-- Métiers explicitement lisibles pour les quatre parcours de Licence Informatique.
WITH data(spec,code,nom) AS (VALUES
 ('LIC_INFO_BIG_DATA','LIC_BD_M_DBA','Administrateur de bases de données'),('LIC_INFO_BIG_DATA','LIC_BD_M_ANALYSTE_PROG','Analyste programmeur informatique'),('LIC_INFO_BIG_DATA','LIC_BD_M_INTEGRATEUR','Intégrateur logiciels métiers'),('LIC_INFO_BIG_DATA','LIC_BD_M_TESTEUR','Testeur / Testeuse informatique'),
 ('LIC_INFO_GLSI','LIC_GL_M_ANALYSTE_ETUDE','Analyste d''étude informatique'),('LIC_INFO_GLSI','LIC_GL_M_DECISIONNEL','Analyste décisionnel'),('LIC_INFO_GLSI','LIC_GL_M_DEV_DATA','Développeur Data'),('LIC_INFO_GLSI','LIC_GL_M_DATA_ANALYST','Data Analyst'),
 ('LIC_INFO_CYBER','LIC_CY_M_ADMIN_RESEAU','Administrateur réseau informatique'),('LIC_INFO_CYBER','LIC_CY_M_ANALYSTE_RESEAU','Analyste réseau informatique'),('LIC_INFO_CYBER','LIC_CY_M_ANALYSTE_CYBER','Analyste en cybersécurité'),('LIC_INFO_CYBER','LIC_CY_M_CLOUD','Technicien Cloud'),
 ('LIC_INFO_IOT','LIC_IOT_M_TECH','Technicienne en systèmes embarqués'),('LIC_INFO_IOT','LIC_IOT_M_TEST','Spécialiste test et validation logiciel'),('LIC_INFO_IOT','LIC_IOT_M_DEV','Développeuse systèmes embarqués'),('LIC_INFO_IOT','LIC_IOT_M_CLOUD','Technicien Cloud')
), ins AS (
 INSERT INTO element_formation(type_element,code,nom) SELECT 'METIER',code,nom FROM data
 ON CONFLICT(type_element,code) WHERE code IS NOT NULL DO UPDATE SET nom=EXCLUDED.nom,updated_at=NOW() RETURNING id
)
INSERT INTO parcours_specialite_element(id_parcours_specialite,id_specialisation,id_element,source_id)
SELECT ps.id,sp.id,e.id,src.id FROM data d JOIN element_formation e ON e.type_element='METIER' AND e.code=d.code
JOIN parcours_specialite ps ON ps.code='LICENCE_INFO' JOIN specialisation sp ON sp.id_parcours_specialite=ps.id AND sp.code=d.spec
JOIN source_information src ON src.code_source='FLYER_LICENCE_INFO' ON CONFLICT DO NOTHING;

-- Mobilité explicitement annoncée sur le flyer Licence Informatique.
INSERT INTO parcours_specialite_element(id_parcours_specialite,id_element,source_id)
SELECT ps.id,e.id,src.id FROM parcours_specialite ps CROSS JOIN element_formation e
JOIN source_information src ON src.code_source='FLYER_LICENCE_INFO'
WHERE ps.code='LICENCE_INFO' AND e.code IN ('MOB_DOUBLE_DIPLOME','MOB_SEMESTRE','MOB_STAGE_INTL')
ON CONFLICT DO NOTHING;

-- Admissions structurées confirmées.
INSERT INTO regle_orientation(id_parcours_specialite,code,nom,description,nature_regle,priorite,statut,actif,source_id)
SELECT ps.id,v.code,v.nom,v.description,'ADMISSION',1,'CONFIRME',TRUE,s.id FROM (VALUES
 ('LICENCE_INFO','ADMISSION_LICENCE_INFO','Admission Licence Informatique','Baccalauréat : toutes sections scientifiques, économiques et techniques.','FLYER_LICENCE_INFO'),
 ('LICENCE_MECATRONIQUE_SI','ADMISSION_LICENCE_MECATRONIQUE','Admission Licence Mécatronique','Bac Math, Sciences expérimentales, Informatique, Technique ou équivalent.','FLYER_LICENCE_MECATRONIQUE'),
 ('INGENIEUR_CIVIL','ADMISSION_INGENIEUR_CIVIL','Admission Génie Civil','Licence, Mastère ou Préparatoire.','FLYER_GENIE_CIVIL'),
 ('INGENIEUR_MECANIQUE','ADMISSION_INGENIEUR_MECANIQUE','Admission Génie Mécanique','Licence, Mastère ou Préparatoire.','FLYER_GENIE_MECANIQUE'),
 ('INGENIEUR_PROCEDES','ADMISSION_INGENIEUR_PROCEDES','Admission Génie des Procédés','Licence, Mastère ou Préparatoire.','FLYER_GENIE_PROCEDES'),
 ('INGENIEUR_INDUSTRIEL','ADMISSION_INGENIEUR_INDUSTRIEL','Admission Génie Industriel','Licence maintenance industrielle; Licence en Mathématique; Mathématique Appliquée; Logistique industrielle; Physique et Qualité; Physique-Chimie.','FLYER_GENIE_INDUSTRIEL')
) v(formation,code,nom,description,source) JOIN parcours_specialite ps ON ps.code=v.formation JOIN source_information s ON s.code_source=v.source
ON CONFLICT(code) DO UPDATE SET id_parcours_specialite=EXCLUDED.id_parcours_specialite,description=EXCLUDED.description,source_id=EXCLUDED.source_id,actif=TRUE,updated_at=NOW();

INSERT INTO critere_orientation(id_regle,type_critere,operateur,valeur_json,obligatoire,description)
SELECT r.id,v.type_critere,v.operateur,v.valeur_json::jsonb,TRUE,v.description
FROM (VALUES
 ('ADMISSION_LICENCE_INFO','DIPLOME','EQ','"BAC"','Baccalauréat requis'),
 ('ADMISSION_LICENCE_INFO','TYPE_BAC','IN','["SCIENTIFIQUE","ECONOMIQUE","TECHNIQUE"]','Sections indiquées par le flyer'),
 ('ADMISSION_LICENCE_MECATRONIQUE','TYPE_BAC','IN','["MATH","SCIENCES_EXPERIMENTALES","INFORMATIQUE","TECHNIQUE","EQUIVALENT"]','Accès indiqué par le flyer'),
 ('ADMISSION_INGENIEUR_CIVIL','DIPLOME','IN','["LICENCE","MASTER","PREPA"]','Accès indiqué par le flyer'),
 ('ADMISSION_INGENIEUR_MECANIQUE','DIPLOME','IN','["LICENCE","MASTER","PREPA"]','Accès indiqué par le flyer'),
 ('ADMISSION_INGENIEUR_PROCEDES','DIPLOME','IN','["LICENCE","MASTER","PREPA"]','Accès indiqué par le flyer'),
 ('ADMISSION_INGENIEUR_INDUSTRIEL','DIPLOME_ORIGINE','IN','["LICENCE_MAINTENANCE_INDUSTRIELLE","LICENCE_MATHEMATIQUE","MATHEMATIQUE_APPLIQUEE","LOGISTIQUE_INDUSTRIELLE","PHYSIQUE_QUALITE","PHYSIQUE_CHIMIE"]','Diplômes/formations d''accès explicitement listés')
) v(regle,type_critere,operateur,valeur_json,description)
JOIN regle_orientation r ON r.code=v.regle
WHERE NOT EXISTS (SELECT 1 FROM critere_orientation c WHERE c.id_regle=r.id AND c.type_critere=v.type_critere);

COMMIT;

-- ================================================================
-- SIMPLIFICATION FINALE : 7 TABLES MÉTIER
-- ================================================================
BEGIN;

CREATE TABLE parcours_simplifie (
 id SERIAL PRIMARY KEY, code VARCHAR(50) NOT NULL UNIQUE, nom VARCHAR(255) NOT NULL,
 duree_annees INTEGER, description TEXT, actif BOOLEAN NOT NULL DEFAULT TRUE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE formation (
 id SERIAL PRIMARY KEY, parcours_id INTEGER NOT NULL REFERENCES parcours_simplifie(id),
 code VARCHAR(100) NOT NULL UNIQUE, nom VARCHAR(255) NOT NULL, intitule_diplome VARCHAR(255),
 duree_annees INTEGER, nb_semestres INTEGER, credits_total INTEGER, description TEXT,
 source_ref TEXT, actif BOOLEAN NOT NULL DEFAULT TRUE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE specialisation_simplifiee (
 id SERIAL PRIMARY KEY, formation_id INTEGER NOT NULL REFERENCES formation(id) ON DELETE CASCADE,
 code VARCHAR(100) NOT NULL, nom VARCHAR(255) NOT NULL, description TEXT, ordre_affichage INTEGER,
 source_ref TEXT, actif BOOLEAN NOT NULL DEFAULT TRUE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 UNIQUE(formation_id,code), UNIQUE(formation_id,id)
);

CREATE TABLE formation_element (
 id SERIAL PRIMARY KEY, formation_id INTEGER REFERENCES formation(id) ON DELETE CASCADE,
 specialisation_id INTEGER, parent_id INTEGER REFERENCES formation_element(id) ON DELETE CASCADE,
 type_element VARCHAR(30) NOT NULL CHECK(type_element IN ('MODULE','COURS','CONTENU_PROGRAMME','COMPETENCE','METIER','DOMAINE_ACTIVITE','CERTIFICATION','LANGUE','MOBILITE','OUTIL','OPPORTUNITE','INFORMATION')),
 code VARCHAR(120), nom VARCHAR(255) NOT NULL, description TEXT, organisme VARCHAR(255),
 ordre_affichage INTEGER, source_ref TEXT, actif BOOLEAN NOT NULL DEFAULT TRUE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 FOREIGN KEY(formation_id,specialisation_id) REFERENCES specialisation_simplifiee(formation_id,id) ON DELETE CASCADE,
 CHECK(specialisation_id IS NULL OR formation_id IS NOT NULL)
);

CREATE TABLE tarif_simplifie (
 id SERIAL PRIMARY KEY, formation_id INTEGER NOT NULL REFERENCES formation(id) ON DELETE CASCADE,
 specialisation_id INTEGER, frais_inscription NUMERIC(10,2), mensualite NUMERIC(10,2),
 nb_mensualites INTEGER, devise VARCHAR(10) NOT NULL DEFAULT 'TND', annee_universitaire VARCHAR(50),
 statut VARCHAR(50) NOT NULL DEFAULT 'INDICATIF', remarque TEXT, source_ref TEXT,
 actif BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 FOREIGN KEY(formation_id,specialisation_id) REFERENCES specialisation_simplifiee(formation_id,id) ON DELETE CASCADE
);

CREATE TABLE regle_orientation_simplifiee (
 id SERIAL PRIMARY KEY, formation_id INTEGER NOT NULL REFERENCES formation(id) ON DELETE CASCADE,
 specialisation_id INTEGER, code VARCHAR(100) NOT NULL UNIQUE, nom VARCHAR(255) NOT NULL,
 type_regle VARCHAR(50) NOT NULL, criteres JSONB NOT NULL DEFAULT '{}'::jsonb, description TEXT,
 priorite INTEGER NOT NULL DEFAULT 1, source_ref TEXT, actif BOOLEAN NOT NULL DEFAULT TRUE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 FOREIGN KEY(formation_id,specialisation_id) REFERENCES specialisation_simplifiee(formation_id,id) ON DELETE CASCADE
);

CREATE TABLE accreditation (
 id SERIAL PRIMARY KEY, formation_id INTEGER NOT NULL REFERENCES formation(id) ON DELETE CASCADE,
 code VARCHAR(100) NOT NULL, nom VARCHAR(255) NOT NULL, organisme VARCHAR(255), description TEXT,
 date_debut DATE, date_fin DATE, source_ref TEXT, actif BOOLEAN NOT NULL DEFAULT TRUE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 UNIQUE(formation_id,code)
);

INSERT INTO parcours_simplifie(id,code,nom,duree_annees,description,actif,created_at,updated_at)
SELECT id,code,nom,duree_annees,description,actif,created_at,updated_at FROM parcours WHERE actif;

INSERT INTO formation(id,parcours_id,code,nom,intitule_diplome,duree_annees,nb_semestres,credits_total,description,source_ref,actif,created_at,updated_at)
SELECT ps.id,ps.id_parcours,ps.code,ps.nom_affichage,ps.intitule_diplome,ps.duree_annees,ps.nb_semestres,
 ps.credits_total,ps.description,
 CASE ps.code WHEN 'LICENCE_INFO' THEN 'FLYER_LICENCE_INFO' WHEN 'LICENCE_MECATRONIQUE_SI' THEN 'FLYER_LICENCE_MECATRONIQUE'
 WHEN 'LICENCE_ELEC_SEIER' THEN 'FLYER_LICENCE_ELECTRIQUE' WHEN 'INGENIEUR_INFO' THEN 'FLYER_GENIE_INFO'
 WHEN 'INGENIEUR_CIVIL' THEN 'FLYER_GENIE_CIVIL' WHEN 'INGENIEUR_INDUSTRIEL' THEN 'FLYER_GENIE_INDUSTRIEL'
 WHEN 'INGENIEUR_MECANIQUE' THEN 'FLYER_GENIE_MECANIQUE' WHEN 'INGENIEUR_PROCEDES' THEN 'FLYER_GENIE_PROCEDES'
 WHEN 'ARCHITECTURE_DNA' THEN 'FLYER_ARCHITECTURE' ELSE NULL END,
 ps.actif,ps.created_at,ps.updated_at FROM parcours_specialite ps WHERE ps.actif;

INSERT INTO specialisation_simplifiee(id,formation_id,code,nom,description,ordre_affichage,source_ref,actif,created_at,updated_at)
SELECT s.id,s.id_parcours_specialite,s.code,s.nom,s.description,s.ordre_affichage,
 COALESCE(src.code_source,src.url),s.actif,s.created_at,s.updated_at
FROM specialisation s LEFT JOIN source_information src ON src.id=s.source_id
JOIN formation f ON f.id=s.id_parcours_specialite WHERE s.actif;

-- Éléments structurés provenant des flyers.
INSERT INTO formation_element(formation_id,specialisation_id,type_element,code,nom,description,organisme,ordre_affichage,source_ref,actif,created_at,updated_at)
SELECT l.id_parcours_specialite,l.id_specialisation,e.type_element,e.code,e.nom,e.description,e.organisme,
 l.ordre_affichage,COALESCE(src.code_source,src.url),e.actif,l.created_at,e.updated_at
FROM parcours_specialite_element l JOIN element_formation e ON e.id=l.id_element
JOIN formation f ON f.id=l.id_parcours_specialite
LEFT JOIN source_information src ON src.id=l.source_id;

-- Modules historiques valides; les modules GLID/ARSI sont déjà rattachés à leur spécialisation.
INSERT INTO formation_element(formation_id,specialisation_id,type_element,code,nom,description,ordre_affichage,source_ref,actif,created_at,updated_at)
SELECT COALESCE(f.id,fi.id),m.id_specialisation,'MODULE',m.code,m.nom,m.description,m.ordre_affichage,
 COALESCE(src.code_source,src.url),m.actif,m.created_at,m.updated_at
FROM module m LEFT JOIN formation f ON f.id=m.id_parcours_specialite
LEFT JOIN parcours_specialite ancien ON ancien.id=m.id_parcours_specialite
LEFT JOIN formation fi ON fi.code=CASE WHEN ancien.code='LICENCE_GLSI' THEN 'LICENCE_INFO' ELSE ancien.code END
LEFT JOIN source_information src ON src.id=m.source_id
WHERE COALESCE(f.id,fi.id) IS NOT NULL;

-- Aucun cours n'est inventé; ce SELECT migre uniquement d'éventuels cours réellement présents.
INSERT INTO formation_element(formation_id,specialisation_id,parent_id,type_element,code,nom,description,ordre_affichage,source_ref,actif,created_at,updated_at)
SELECT pm.formation_id,pm.specialisation_id,pm.id,'COURS',c.code,c.nom,c.description,c.ordre_affichage,
 COALESCE(src.code_source,src.url),c.actif,c.created_at,c.updated_at
FROM cours c JOIN module m ON m.id=c.id_module
JOIN formation_element pm ON pm.type_element='MODULE' AND pm.code=m.code
LEFT JOIN source_information src ON src.id=c.source_id;

-- Faits narratifs historiques encore utiles.
INSERT INTO formation_element(formation_id,specialisation_id,type_element,code,nom,description,source_ref,actif,created_at,updated_at)
SELECT COALESCE(f.id,fi.id),sp.id,'INFORMATION','INFO_'||ia.id,ia.titre,ia.contenu,
 COALESCE(src.code_source,src.url),ia.actif,ia.created_at,ia.updated_at
FROM information_academique ia
LEFT JOIN parcours_specialite ancien ON ancien.id=ia.id_parcours_specialite
LEFT JOIN formation f ON f.id=ia.id_parcours_specialite
LEFT JOIN formation fi ON fi.code=CASE WHEN ancien.code='LICENCE_GLSI' THEN 'LICENCE_INFO'
 WHEN ancien.code IN ('INGENIEUR_GLID','INGENIEUR_ARSI') THEN 'INGENIEUR_INFO' END
LEFT JOIN specialisation_simplifiee sp ON sp.formation_id=fi.id AND sp.code=CASE ancien.code WHEN 'INGENIEUR_GLID' THEN 'GLID' WHEN 'INGENIEUR_ARSI' THEN 'ARSI' END
LEFT JOIN source_information src ON src.id=ia.source_id
WHERE ia.actif;

INSERT INTO tarif_simplifie(id,formation_id,specialisation_id,frais_inscription,mensualite,nb_mensualites,devise,annee_universitaire,statut,remarque,source_ref,actif,created_at,updated_at)
SELECT t.id,COALESCE(f.id,fi.id),NULL,t.frais_inscription,t.mensualite,t.nb_mensualites,t.devise,
 t.annee_universitaire,t.statut,t.remarque,COALESCE(src.code_source,src.url),t.actif,t.created_at,t.updated_at
FROM tarif t LEFT JOIN formation f ON f.id=t.id_parcours_specialite
LEFT JOIN parcours_specialite ancien ON ancien.id=t.id_parcours_specialite
LEFT JOIN formation fi ON fi.code=CASE WHEN ancien.code='LICENCE_GLSI' THEN 'LICENCE_INFO' ELSE ancien.code END
LEFT JOIN source_information src ON src.id=t.source_id WHERE COALESCE(f.id,fi.id) IS NOT NULL;

INSERT INTO regle_orientation_simplifiee(id,formation_id,specialisation_id,code,nom,type_regle,criteres,description,priorite,source_ref,actif,created_at,updated_at)
SELECT r.id,COALESCE(f.id,fi.id),CASE WHEN s.formation_id=COALESCE(f.id,fi.id) THEN s.id END,r.code,r.nom,r.nature_regle,
 COALESCE((SELECT jsonb_object_agg(lower(c.type_critere),CASE WHEN c.operateur='IN' THEN jsonb_build_object('in',c.valeur_json) ELSE c.valeur_json END) FROM critere_orientation c WHERE c.id_regle=r.id),'{}'::jsonb),
 r.description,r.priorite,COALESCE(src.code_source,src.url),r.actif,r.created_at,r.updated_at
FROM regle_orientation r LEFT JOIN formation f ON f.id=r.id_parcours_specialite
LEFT JOIN parcours_specialite ancien ON ancien.id=r.id_parcours_specialite
LEFT JOIN formation fi ON fi.code=CASE WHEN ancien.code='LICENCE_GLSI' THEN 'LICENCE_INFO' ELSE ancien.code END
LEFT JOIN specialisation_simplifiee s ON s.id=r.id_specialisation
LEFT JOIN source_information src ON src.id=r.source_id WHERE COALESCE(f.id,fi.id) IS NOT NULL;

INSERT INTO accreditation(formation_id,code,nom,organisme,description,date_debut,date_fin,source_ref,actif,created_at,updated_at)
SELECT f.id,a.code,CASE WHEN a.code='EURO-INF' THEN 'EURO-INF' ELSE a.nom END,a.organisme,a.description,
 a.date_debut,a.date_fin,COALESCE(src.code_source,src.url),a.actif,a.created_at,a.updated_at
FROM parcours_specialite_accreditation l JOIN formation f ON f.id=l.id_parcours_specialite
JOIN label_accreditation a ON a.id=l.id_label LEFT JOIN source_information src ON src.id=a.source_id;

CREATE UNIQUE INDEX uq_fe_global_code ON formation_element(formation_id,type_element,code)
 WHERE specialisation_id IS NULL AND code IS NOT NULL;
CREATE UNIQUE INDEX uq_fe_specialisation_code ON formation_element(formation_id,specialisation_id,type_element,code)
 WHERE specialisation_id IS NOT NULL AND code IS NOT NULL;
CREATE UNIQUE INDEX uq_fe_global_nom ON formation_element(formation_id,type_element,nom)
 WHERE specialisation_id IS NULL AND code IS NULL;
CREATE UNIQUE INDEX uq_fe_specialisation_nom ON formation_element(formation_id,specialisation_id,type_element,nom)
 WHERE specialisation_id IS NOT NULL AND code IS NULL;
CREATE INDEX ix_formation_parcours ON formation(parcours_id);
CREATE INDEX ix_specialisation_s_formation ON specialisation_simplifiee(formation_id);
CREATE INDEX ix_fe_formation ON formation_element(formation_id);
CREATE INDEX ix_fe_specialisation ON formation_element(specialisation_id);
CREATE INDEX ix_fe_parent ON formation_element(parent_id);

-- Suppression de l'ancien modèle après migration des données.
DROP TABLE parcours_specialite_element CASCADE;
DROP TABLE element_formation CASCADE;
DROP TABLE information_academique CASCADE;
DROP TABLE parcours_specialite_accreditation CASCADE;
DROP TABLE label_accreditation CASCADE;
DROP TABLE cours CASCADE;
DROP TABLE module CASCADE;
DROP TABLE critere_orientation CASCADE;
DROP TABLE regle_orientation CASCADE;
DROP TABLE tarif CASCADE;
DROP TABLE specialisation CASCADE;
DROP TABLE parcours_specialite CASCADE;
DROP TABLE source_information CASCADE;
DROP TABLE specialite CASCADE;
DROP TABLE departement CASCADE;
DROP TABLE parcours CASCADE;

ALTER TABLE parcours_simplifie RENAME TO parcours;
ALTER TABLE specialisation_simplifiee RENAME TO specialisation;
ALTER TABLE tarif_simplifie RENAME TO tarif;
ALTER TABLE regle_orientation_simplifiee RENAME TO regle_orientation;

SELECT setval(pg_get_serial_sequence('parcours','id'),COALESCE((SELECT max(id) FROM parcours),1),true);
SELECT setval(pg_get_serial_sequence('formation','id'),COALESCE((SELECT max(id) FROM formation),1),true);
SELECT setval(pg_get_serial_sequence('specialisation','id'),COALESCE((SELECT max(id) FROM specialisation),1),true);
SELECT setval(pg_get_serial_sequence('formation_element','id'),COALESCE((SELECT max(id) FROM formation_element),1),true);
SELECT setval(pg_get_serial_sequence('tarif','id'),COALESCE((SELECT max(id) FROM tarif),1),true);
SELECT setval(pg_get_serial_sequence('regle_orientation','id'),COALESCE((SELECT max(id) FROM regle_orientation),1),true);
SELECT setval(pg_get_serial_sequence('accreditation','id'),COALESCE((SELECT max(id) FROM accreditation),1),true);

COMMIT;

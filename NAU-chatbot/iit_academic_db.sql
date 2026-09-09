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
DROP TABLE IF EXISTS accreditation CASCADE;
DROP TABLE IF EXISTS formation_element CASCADE;
DROP TABLE IF EXISTS specialisation CASCADE;
DROP TABLE IF EXISTS formation CASCADE;
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
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 CHECK(duree_annees IS NULL OR duree_annees > 0)
);

CREATE TABLE formation (
 id SERIAL PRIMARY KEY, parcours_id INTEGER NOT NULL REFERENCES parcours_simplifie(id),
 code VARCHAR(100) NOT NULL UNIQUE, nom VARCHAR(255) NOT NULL, intitule_diplome VARCHAR(255),
 duree_annees INTEGER, nb_semestres INTEGER, credits_total INTEGER, description TEXT,
 source_ref TEXT, actif BOOLEAN NOT NULL DEFAULT TRUE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 langues_enseignement VARCHAR(50)[] NOT NULL DEFAULT ARRAY['FRANCAIS']::VARCHAR[],
 CHECK(duree_annees IS NULL OR duree_annees > 0),
 CHECK(nb_semestres IS NULL OR nb_semestres > 0),
 CHECK(credits_total IS NULL OR credits_total > 0),
 CHECK(cardinality(langues_enseignement) > 0)
);

CREATE TABLE specialisation_simplifiee (
 id SERIAL PRIMARY KEY, formation_id INTEGER NOT NULL REFERENCES formation(id) ON DELETE CASCADE,
 code VARCHAR(100) NOT NULL, nom VARCHAR(255) NOT NULL, description TEXT, ordre_affichage INTEGER,
 source_ref TEXT, actif BOOLEAN NOT NULL DEFAULT TRUE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 UNIQUE(formation_id,code), UNIQUE(formation_id,id),
 CHECK(ordre_affichage IS NULL OR ordre_affichage >= 0)
);

CREATE TABLE formation_element (
 id SERIAL PRIMARY KEY, formation_id INTEGER REFERENCES formation(id) ON DELETE CASCADE,
 specialisation_id INTEGER, parent_id INTEGER REFERENCES formation_element(id) ON DELETE CASCADE,
 type_element VARCHAR(30) NOT NULL CHECK(type_element IN ('MODULE','COURS','CONTENU_PROGRAMME','COMPETENCE','METIER','DOMAINE_ACTIVITE','CERTIFICATION','LANGUE','MOBILITE','OUTIL','OPPORTUNITE','INFORMATION','DOCUMENT_INSCRIPTION','LIEN_PREINSCRIPTION')),
 code VARCHAR(120), nom VARCHAR(255) NOT NULL, description TEXT, organisme VARCHAR(255),
 ordre_affichage INTEGER, source_ref TEXT, actif BOOLEAN NOT NULL DEFAULT TRUE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 parcours_id INTEGER REFERENCES parcours_simplifie(id) ON DELETE CASCADE, valeur TEXT,
 FOREIGN KEY(formation_id,specialisation_id) REFERENCES specialisation_simplifiee(formation_id,id) ON DELETE CASCADE,
 CHECK(specialisation_id IS NULL OR formation_id IS NOT NULL),
 CHECK(parcours_id IS NULL OR (formation_id IS NULL AND specialisation_id IS NULL)),
 CHECK(ordre_affichage IS NULL OR ordre_affichage >= 0)
);

CREATE TABLE tarif_simplifie (
 id SERIAL PRIMARY KEY, formation_id INTEGER REFERENCES formation(id) ON DELETE CASCADE,
 specialisation_id INTEGER, frais_inscription NUMERIC(10,2), mensualite NUMERIC(10,2),
 nb_mensualites INTEGER, devise VARCHAR(10) NOT NULL DEFAULT 'TND', annee_universitaire VARCHAR(50),
 statut VARCHAR(50) NOT NULL DEFAULT 'INDICATIF', remarque TEXT, source_ref TEXT,
 actif BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 langue_enseignement VARCHAR(50), parcours_id INTEGER REFERENCES parcours_simplifie(id) ON DELETE CASCADE,
 FOREIGN KEY(formation_id,specialisation_id) REFERENCES specialisation_simplifiee(formation_id,id) ON DELETE CASCADE,
 CHECK(frais_inscription IS NULL OR frais_inscription >= 0),
 CHECK(mensualite IS NULL OR mensualite >= 0),
 CHECK(nb_mensualites IS NULL OR nb_mensualites > 0),
 CHECK(langue_enseignement IS NULL OR langue_enseignement ~ '^[A-Z0-9][A-Z0-9_-]*$'),
 CHECK(parcours_id IS NULL OR (formation_id IS NULL AND specialisation_id IS NULL)),
 CHECK(parcours_id IS NOT NULL OR formation_id IS NOT NULL),
 CHECK(specialisation_id IS NULL OR formation_id IS NOT NULL)
);

CREATE TABLE regle_orientation_simplifiee (
 id SERIAL PRIMARY KEY, formation_id INTEGER NOT NULL REFERENCES formation(id) ON DELETE CASCADE,
 specialisation_id INTEGER, code VARCHAR(100) NOT NULL UNIQUE, nom VARCHAR(255) NOT NULL,
 type_regle VARCHAR(50) NOT NULL, criteres JSONB NOT NULL DEFAULT '{}'::jsonb, description TEXT,
 priorite INTEGER NOT NULL DEFAULT 1, source_ref TEXT, actif BOOLEAN NOT NULL DEFAULT TRUE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 FOREIGN KEY(formation_id,specialisation_id) REFERENCES specialisation_simplifiee(formation_id,id) ON DELETE CASCADE,
 CHECK(priorite > 0)
);

CREATE TABLE accreditation (
 id SERIAL PRIMARY KEY, formation_id INTEGER NOT NULL REFERENCES formation(id) ON DELETE CASCADE,
 code VARCHAR(100) NOT NULL, nom VARCHAR(255) NOT NULL, organisme VARCHAR(255), description TEXT,
 date_debut DATE, date_fin DATE, source_ref TEXT, actif BOOLEAN NOT NULL DEFAULT TRUE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 UNIQUE(formation_id,code),
 CHECK(date_debut IS NULL OR date_fin IS NULL OR date_fin >= date_debut)
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
ALTER SEQUENCE parcours_simplifie_id_seq RENAME TO parcours_id_seq;
ALTER SEQUENCE specialisation_simplifiee_id_seq RENAME TO specialisation_id_seq;
ALTER SEQUENCE tarif_simplifie_id_seq RENAME TO tarif_id_seq;
ALTER SEQUENCE regle_orientation_simplifiee_id_seq RENAME TO regle_orientation_id_seq;

-- ================================================================
-- SNAPSHOT RAG CANONIQUE — SYNCHRONISÉ DEPUIS LA BASE ACTIVE
-- Généré le 2026-09-09. Les comptes, sessions et conversations sont exclus.
-- Ce remplacement final garantit que le backup reproduit exactement les
-- données académiques validées, indépendamment des migrations historiques.
-- ================================================================
TRUNCATE TABLE
 accreditation, regle_orientation, tarif, formation_element,
 specialisation, formation, parcours
 RESTART IDENTITY;

-- Les index historiques sont remplacés par les index du schéma RAG courant,
-- qui distingue les éléments globaux, de parcours, de formation et de spécialité.
DROP INDEX uq_fe_global_code;
DROP INDEX uq_fe_global_nom;
DROP INDEX uq_fe_specialisation_code;
DROP INDEX uq_fe_specialisation_nom;

CREATE UNIQUE INDEX uq_fe_global_code ON formation_element(type_element,code)
 WHERE parcours_id IS NULL AND formation_id IS NULL AND specialisation_id IS NULL AND code IS NOT NULL;
CREATE UNIQUE INDEX uq_fe_global_nom ON formation_element(type_element,nom)
 WHERE parcours_id IS NULL AND formation_id IS NULL AND specialisation_id IS NULL AND code IS NULL;
CREATE UNIQUE INDEX uq_fe_parcours_code ON formation_element(parcours_id,type_element,code)
 WHERE parcours_id IS NOT NULL AND code IS NOT NULL;
CREATE UNIQUE INDEX uq_fe_parcours_nom ON formation_element(parcours_id,type_element,nom)
 WHERE parcours_id IS NOT NULL AND code IS NULL;
CREATE UNIQUE INDEX uq_fe_formation_code ON formation_element(formation_id,type_element,code)
 WHERE parcours_id IS NULL AND formation_id IS NOT NULL AND specialisation_id IS NULL AND code IS NOT NULL;
CREATE UNIQUE INDEX uq_fe_formation_nom ON formation_element(formation_id,type_element,nom)
 WHERE parcours_id IS NULL AND formation_id IS NOT NULL AND specialisation_id IS NULL AND code IS NULL;
CREATE UNIQUE INDEX uq_fe_specialisation_code ON formation_element(formation_id,specialisation_id,type_element,code)
 WHERE specialisation_id IS NOT NULL AND code IS NOT NULL;
CREATE UNIQUE INDEX uq_fe_specialisation_nom ON formation_element(formation_id,specialisation_id,type_element,nom)
 WHERE specialisation_id IS NOT NULL AND code IS NULL;

CREATE INDEX ix_fe_parcours ON formation_element(parcours_id);
CREATE INDEX ix_tarif_parcours ON tarif(parcours_id);
CREATE INDEX ix_tarif_formation ON tarif(formation_id);
CREATE INDEX ix_tarif_specialisation ON tarif(specialisation_id);
CREATE INDEX ix_tarif_formation_langue ON tarif(formation_id,langue_enseignement);
CREATE INDEX ix_regle_orientation_formation ON regle_orientation(formation_id);
CREATE INDEX ix_regle_orientation_specialisation ON regle_orientation(specialisation_id);
CREATE INDEX ix_accreditation_formation ON accreditation(formation_id);

INSERT INTO public.parcours (id, code, nom, duree_annees, description, actif, created_at, updated_at) VALUES
	(1, 'PREPA', 'Cycle Préparatoire', 2, 'Cycle Préparatoire aux études d''ingénieurs', true, '2026-08-30 13:15:21.369956+01', '2026-08-30 13:15:39.565163+01'),
	(2, 'LICENCE', 'Licence', 3, 'Cycle Licence', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01'),
	(3, 'INGENIEUR', 'Cycle Ingénieur', 3, 'Cycle Ingénieur', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01'),
	(4, 'ARCHITECTURE', 'Architecture', 6, 'Parcours du Diplôme National d''Architecte', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01');

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

INSERT INTO public.specialisation (id, formation_id, code, nom, description, ordre_affichage, source_ref, actif, created_at, updated_at) VALUES
	(1, 1, 'MP', 'Mathématiques-Physique (MP)', 'Spécialisation institutionnelle active du Cycle Préparatoire.', 1, 'PROJECT_INSTITUTIONAL_RULES', true, '2026-08-30 13:15:21.369956+01', '2026-08-30 13:15:39.565163+01'),
	(2, 5, 'SDIA', 'Science des Données et Intelligence Artificielle', NULL, 1, 'FLYER_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01'),
	(3, 5, 'ARSI', 'Administration Réseau et Sécurité Informatique', NULL, 2, 'FLYER_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01'),
	(4, 5, 'GLID', 'Génie Logiciel et Informatique Décisionnelle', NULL, 3, 'FLYER_GENIE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01'),
	(5, 2, 'LIC_INFO_BIG_DATA', 'Big Data & Analyse des Données', NULL, 1, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01'),
	(6, 2, 'LIC_INFO_GLSI', 'Génie Logiciel & Systèmes Intelligents', NULL, 2, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01'),
	(7, 2, 'LIC_INFO_CYBER', 'Cybersécurité et Réseaux', NULL, 3, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01'),
	(8, 2, 'LIC_INFO_IOT', 'Systèmes Embarqués & IoT', NULL, 4, 'FLYER_LICENCE_INFO', true, '2026-08-30 13:15:39.565163+01', '2026-08-30 13:15:39.565163+01');

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

SELECT pg_catalog.setval('public.accreditation_id_seq', 10, true);

SELECT pg_catalog.setval('public.formation_element_id_seq', 293, true);

SELECT pg_catalog.setval('public.formation_id_seq', 11, true);

SELECT pg_catalog.setval('public.parcours_id_seq', 4, true);

SELECT pg_catalog.setval('public.regle_orientation_id_seq', 14, true);

SELECT pg_catalog.setval('public.specialisation_id_seq', 8, true);

SELECT pg_catalog.setval('public.tarif_id_seq', 21, true);


COMMIT;

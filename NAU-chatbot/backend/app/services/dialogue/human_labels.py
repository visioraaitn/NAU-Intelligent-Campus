from __future__ import annotations

import re

from app.domain.conversation.models import AcademicProfile


PROFILE_LABELS = {
    AcademicProfile.UNKNOWN: "situation académique à préciser",
    AcademicProfile.NEW_BAC: "nouveau bachelier",
    AcademicProfile.PREPA_STUDENT: "étudiant en cycle préparatoire",
    AcademicProfile.PREPA_HOLDER: "cycle préparatoire validé",
    AcademicProfile.LICENCE_STUDENT: "étudiant en licence",
    AcademicProfile.LICENCE_HOLDER: "titulaire d'une licence",
    AcademicProfile.MASTER_HOLDER: "titulaire d'un mastère",
}

VALUE_LABELS = {
    "MATH": "Mathématiques",
    "SCIENCES": "Sciences expérimentales",
    "INFORMATIQUE": "Informatique",
    "TECHNIQUE": "Sciences techniques",
    "ECONOMIE_GESTION": "Économie et Gestion",
    "LETTERS": "Lettres",
    "SPORT": "Sport",
    "HIGH": "à l'aise",
    "MEDIUM": "niveau intermédiaire",
    "LOW": "à renforcer",
    "ENGINEERING": "cycle ingénieur",
    "PREPA": "cycle préparatoire",
    "LICENCE": "licence",
    "DATA_AI": "Data et intelligence artificielle",
    "SOFTWARE": "développement logiciel",
    "CYBER_NETWORKS": "cybersécurité et réseaux",
    "EMBEDDED_IOT": "systèmes embarqués et IoT",
    "INDUSTRY": "industrie et production",
    "CIVIL_ARCH": "génie civil et architecture",
    "ENERGY": "énergie",
    "GENERAL_INFO": "informatique au sens large",
    "PREPA_GENERAL": "Cycle Préparatoire",
    "LICENCE_INFO": "Licence en Informatique",
    "LICENCE_MECATRONIQUE_SI": "Licence en Mécatronique et Systèmes Intelligents",
    "LICENCE_ELEC_SEIER": "Licence en Génie Électrique",
    "INGENIEUR_INFO": "Génie Informatique",
    "INGENIEUR_CIVIL": "Génie Civil",
    "INGENIEUR_INDUSTRIEL": "Génie Industriel",
    "INGENIEUR_MECANIQUE": "Génie Mécanique",
    "INGENIEUR_PROCEDES": "Génie des Procédés",
    "ARCHITECTURE_DNA": "Diplôme National d'Architecte",
    "LIC_INFO_BIG_DATA": "Big Data et Analyse des Données",
    "LIC_INFO_GLSI": "Génie Logiciel et Systèmes Intelligents",
    "LIC_INFO_CYBER": "Cybersécurité et Réseaux",
    "LIC_INFO_IOT": "Systèmes Embarqués et IoT",
}

INTENT_LABELS = {
    "CATALOG": "catalogue des formations",
    "FEES": "tarifs",
    "DURATION": "durée",
    "PROGRAMME": "programme d'études",
    "CAREERS": "débouchés",
    "MARKET": "perspectives professionnelles",
    "CERTIFICATIONS": "certifications",
    "INTERNATIONAL": "international",
    "ACCREDITATION": "reconnaissance du diplôme",
    "ADMISSION": "admission",
    "PAYMENT": "paiement",
    "PREINSCRIPTION": "pré-inscription",
    "REGISTRATION_DOCUMENTS": "documents d'inscription",
    "CONTACT": "contact",
    "ORIENTATION": "orientation",
    "DETAILS": "détails",
    "DIFFICULTY": "niveau de difficulté",
    "PERSUASION": "atouts de l'IIT",
    "PROFILE_RECALL": "rappel du profil académique",
    "GENERAL": "échange général",
}


def profile_label(profile: AcademicProfile) -> str:
    return PROFILE_LABELS[profile]


def value_label(value: object) -> str:
    text = str(value)
    return VALUE_LABELS.get(text, text.replace("_", " ").lower())


def intent_label(intent: str) -> str:
    return INTENT_LABELS.get(intent, intent.replace("_", " ").lower())


def humanize_text(text: str) -> str:
    readable = text
    for internal, label in VALUE_LABELS.items():
        readable = re.sub(rf"\b{re.escape(internal)}\b", label, readable, flags=re.I)
    return readable

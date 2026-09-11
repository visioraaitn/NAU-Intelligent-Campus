from __future__ import annotations

import re
from collections.abc import Sequence
from decimal import Decimal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.domain.academic.enums import FormationElementType
from app.domain.conversation.models import AcademicProfile, SubjectState
from app.domain.recommendation.schemas import (
    EligibilityStatus,
    RecommendationDecision,
    RecommendationOption,
)
from app.repositories.academic import PageRequest
from app.services.academic.catalog_service import AcademicCatalogService
from app.services.academic.element_resolution import AcademicElementResolutionService
from app.services.academic.target_resolver import AcademicTarget
from app.services.dialogue.human_labels import value_label
from app.services.dialogue.normalizer import contains_phrase, fold_text


FORMATION_LINKS = {
    "PREPA_GENERAL": "https://iit.tn/prepa/",
    "LICENCE_INFO": "https://iit.tn/licences/",
    "LICENCE_MECATRONIQUE_SI": "https://iit.tn/licences/",
    "LICENCE_ELEC_SEIER": "https://iit.tn/licences/",
    "INGENIEUR_INFO": "https://iit.tn/filieres-ingenieur/genie-informatique-2/",
    "INGENIEUR_CIVIL": "https://iit.tn/filieres-ingenieur/genie-civil/",
    "INGENIEUR_INDUSTRIEL": "https://iit.tn/filieres-ingenieur/genie-industriel-2/",
    "INGENIEUR_MECANIQUE": "https://iit.tn/filieres-ingenieur/genie-mecanique-2/",
    "INGENIEUR_PROCEDES": "https://iit.tn/genie-des-procedes/",
    "ARCHITECTURE_DNA": "https://iit.tn/architecture-2/",
}


class StructuredResponseBuilder:
    def __init__(self, catalogue: AcademicCatalogService) -> None:
        self.catalogue = catalogue

    async def catalogue_overview(self, message: str) -> str:
        formations = (
            await self.catalogue.formations.list(PageRequest(page_size=100))
        ).items
        formations = sorted(
            formations,
            key=lambda item: (item.parcours_id, item.id),
        )
        parcours = (
            await self.catalogue.parcours.list(PageRequest(page_size=100))
        ).items
        parcours_names = {item.id: item.nom for item in parcours}
        text = fold_text(message)
        asks_informatics = any(
            contains_phrase(text, term)
            for term in ("informatique", "info", "numerique", "numérique")
        )
        if asks_informatics:
            formations = [
                item
                for item in formations
                if "INFO" in item.code or "informatique" in fold_text(item.nom)
            ]
        if re.search(r"\blicences?\b", text):
            formations = [item for item in formations if item.code.startswith("LICENCE_")]

        lines = [
            "Voici les formations IIT actuellement enregistrées"
            + (" en informatique :" if asks_informatics else " :")
        ]
        for formation in formations:
            specs = (
                await self.catalogue.specialisations.list(
                    PageRequest(
                        page_size=100,
                        filters={"formation_id": formation.id},
                    )
                )
            ).items
            duration = (
                f" — {formation.duree_annees} ans"
                if formation.duree_annees
                else ""
            )
            lines.append(
                f"• {parcours_names.get(formation.parcours_id, 'Parcours')} — "
                f"{formation.nom}{duration}"
            )
            if specs:
                lines.append(
                    "  Spécialisations : " + ", ".join(item.nom for item in specs)
                )
        lines.append("\nCatalogue officiel : https://iit.tn/formation/")
        lines.append(
            "Dis-moi ton niveau actuel et ta section ou spécialité, et je te montrerai uniquement les formations compatibles avec ton profil."
        )
        return "\n".join(lines)

    async def accreditation(
        self,
        target: AcademicTarget | None,
        message: str,
    ) -> str:
        formations = [target.formation] if target else (
            await self.catalogue.formations.list(PageRequest(page_size=100))
        ).items
        requested_iso = "iso" in fold_text(message)
        lines: list[str] = []
        for formation in (formations if not requested_iso or target else ()):
            records = (
                await self.catalogue.accreditations.list(
                    PageRequest(page_size=100, filters={"formation_id": formation.id})
                )
            ).items
            if records:
                for record in records:
                    organism = f" par {record.organisme}" if record.organisme else ""
                    source_ref = getattr(record, "source_ref", None)
                    verification = (
                        ""
                        if source_ref
                        else " Source officielle non renseignée dans la base."
                    )
                    lines.append(
                        f"• {formation.nom} : enregistrement {record.nom}{organism}.{verification}"
                    )
            elif target:
                lines.append(
                    f"• Aucune accréditation n'est renseignée pour {formation.nom} dans la base académique active."
                )
        global_certifications = (
            await self.catalogue.elements.list(
                PageRequest(page_size=100, filters={"formation_id": None})
            )
        ).items
        for item in global_certifications:
            if item.type_element.value == "CERTIFICATION" and "21001" in item.nom:
                lines.append(
                    f"• Certification institutionnelle déclarée : {item.nom}. La preuve officielle doit être confirmée par l'IIT."
                )
        iso_recorded = any("21001" in item.nom for item in global_certifications)
        if requested_iso and not iso_recorded:
            lines.append(
                "ISO 21001 n'est pas documentée dans la base académique active; je ne peux donc pas affirmer que l'IIT possède cette certification. Consulte la page officielle des accréditations : https://iit.tn/a-propos/accreditations/"
            )
        elif requested_iso:
            lines.append(
                "ISO 21001 est enregistrée comme déclaration à confirmer; je ne peux pas la présenter comme certification officielle sans preuve IIT vérifiable. Consulte la page officielle des accréditations : https://iit.tn/a-propos/accreditations/"
            )
        if not lines:
            lines.append(
                "Aucune accréditation précise n'est renseignée pour cette portée dans la base académique active. Consulte la page officielle : https://iit.tn/a-propos/accreditations/"
            )
        lines.append(
            "Une accréditation concerne un programme, pas automatiquement chaque étudiant. La reconnaissance ou l'équivalence dans un pays donné doit être vérifiée auprès de l'établissement ou de l'autorité compétente."
        )
        return "\n".join(lines)

    async def institutional_advantages(self) -> str:
        formations = (await self.catalogue.formations.list(PageRequest(page_size=100))).items
        formation_names = ", ".join(item.nom for item in formations[:12])
        accreditations = (await self.catalogue.accreditations.list(PageRequest(page_size=100))).items
        accreditation_names = ", ".join(
            dict.fromkeys(
                f"{item.nom} ({item.organisme})" if getattr(item, "organisme", None) else item.nom
                for item in accreditations
            )
        )
        global_elements = (
            await self.catalogue.elements.list(
                PageRequest(page_size=100, filters={"formation_id": None})
            )
        ).items
        iso = next(
            (item.nom for item in global_elements if "21001" in item.nom),
            None,
        )
        iso_line = (
            f"• certification institutionnelle déclarée : {iso}, à confirmer par une preuve officielle;\n"
            if iso
            else "• aucune certification ISO 21001 vérifiée n'est actuellement enregistrée dans la base active;\n"
        )
        return (
            "Pour découvrir l'IIT, voici les éléments actuellement enregistrés dans la base académique :\n"
            f"• formations proposées : {formation_names or 'catalogue à consulter sur le site officiel'};\n"
            "• pédagogie orientée vers les projets appliqués, la communication et le travail en équipe;\n"
            "• ouverture internationale, notamment mobilité, échanges et partenariats lorsqu'ils sont documentés;\n"
            + iso_line
            + f"• accréditations de programmes enregistrées : {accreditation_names or 'aucune dans la base active'};\n"
            + "Les accréditations concernent des programmes précis : consulte la fiche de la formation pour voir son label et son organisme.\n"
            "Ces éléments ne garantissent ni l'admission, ni un emploi, ni une équivalence automatique. Pour vérifier les formations et les informations à jour : https://iit.tn/formation/"
        )

    async def location(self) -> str:
        return (
            "L'IIT indique deux implantations à Sfax :\n"
            "• Route de Tunis km 10, Technopole El Ons, Sfax;\n"
            "• Route Mharza km 1,5, Sfax.\n"
            "La possibilité d'étudier dans l'un ou l'autre site dépend de la formation et de l'organisation de l'année. "
            "Pour confirmer le campus, les horaires et les cours du soir, contacte l'administration : (+216) 70 28 26 00 ou info@iit.tn.\n"
            "Source officielle : https://iit.tn/contact-3/"
        )

    async def schedule(self) -> str:
        return (
            "Les horaires des cours du soir ne sont pas suffisamment documentés dans la base académique active. "
            "Ils peuvent dépendre de la formation et de l'année universitaire. "
            "Pour confirmer la disponibilité des cours du soir, le campus et les horaires, contacte directement l'administration IIT : "
            "(+216) 70 28 26 00 ou info@iit.tn."
        )

    async def fees(
        self,
        target: AcademicTarget | None,
        *,
        include_all: bool = False,
        licence_only: bool = False,
    ) -> str:
        if target is not None:
            formations = [target.formation]
        elif not include_all:
            return (
                "Pour te donner le bon tarif sans mélanger les formations, indique-moi "
                "la formation qui t'intéresse."
            )
        else:
            formations = (
                await self.catalogue.formations.list(PageRequest(page_size=100))
            ).items
            formations = sorted(
                formations,
                key=lambda item: (item.parcours_id, item.id),
            )
            if licence_only:
                formations = [
                    item for item in formations if item.code.startswith("LICENCE_")
                ]

        entries: list[tuple[object, object]] = []
        seen_entries: set[tuple[object, ...]] = set()
        for formation in formations:
            tariffs = (
                await self.catalogue.tarifs.list(
                    PageRequest(
                        page_size=100,
                        filters={"formation_id": formation.id},
                    )
                )
            ).items
            for tariff in tariffs:
                language = getattr(tariff, "langue_enseignement", None)
                academic_year = getattr(tariff, "annee_universitaire", None)
                status = getattr(tariff, "statut", None)
                semantic_key = (
                    formation.id,
                    language,
                    academic_year,
                    tariff.frais_inscription,
                    tariff.mensualite,
                    tariff.nb_mensualites,
                    tariff.devise,
                    status,
                )
                if semantic_key in seen_entries:
                    continue
                seen_entries.add(semantic_key)
                entries.append((formation, tariff))

        if not entries:
            formation_name = target.formation.nom if target else "cette formation"
            return (
                f"Le tarif de {formation_name} n'est pas renseigné dans la base académique active. "
                "Je préfère ne pas inventer un montant : l'équipe IIT doit le confirmer. "
                "Veux-tu les coordonnées de contact ou les étapes de pré-inscription ?"
            )

        lines = ["Tarifs publics indicatifs de première année :"]
        for formation, tariff in entries:
            parts: list[str] = []
            if tariff.frais_inscription is not None:
                parts.append(
                    f"inscription {_money(tariff.frais_inscription)} {tariff.devise}"
                )
            if tariff.mensualite is not None and tariff.nb_mensualites:
                parts.append(
                    f"{tariff.nb_mensualites} mensualités de "
                    f"{_money(tariff.mensualite)} {tariff.devise}"
                )
            total = _annual_total(
                tariff.frais_inscription,
                tariff.mensualite,
                tariff.nb_mensualites,
            )
            if total is not None:
                parts.append(f"total indicatif {_money(total)} {tariff.devise}")
            qualifiers = []
            language = getattr(tariff, "langue_enseignement", None)
            if language:
                qualifiers.append(_language_label(language))
            academic_year = getattr(tariff, "annee_universitaire", None)
            if academic_year:
                qualifiers.append(academic_year)
            context = f" ({' · '.join(qualifiers)})" if qualifiers else ""
            amount = " + ".join(parts) if parts else "montant à confirmer"
            lines.append(f"• {formation.nom}{context} : {amount}.")
        lines.append(
            "Paiement comptant : pour tous les parcours, un paiement au comptant donne une réduction de 5% sur le total des frais. "
            "Les montants doivent être reconfirmés pour l'année universitaire visée."
        )
        lines.append(
            "Veux-tu que je t'aide à préparer une pré-inscription ?"
        )
        return "\n".join(lines)

    async def orientation(
        self,
        subject: SubjectState,
        decision: RecommendationDecision,
    ) -> str | None:
        primary = decision.primary
        if primary is None:
            if subject.profile is AcademicProfile.NEW_BAC and subject.bac_specialty:
                return (
                    f"Avec un bac {value_label(subject.bac_specialty)}, aucune formation IIT n'est confirmée comme admissible dans les règles actives. "
                    "Je préfère te le dire clairement plutôt que d'inventer une filière. L'administration peut compléter ou corriger cette règle depuis l'espace admin."
                )
            return None

        formation = await self.catalogue.formations.require(primary.formation_id)
        alternatives = self._distinct_alternatives(decision)
        if (
            subject.profile is AcademicProfile.NEW_BAC
            and subject.bac_specialty in {"MATH", "SCIENCES"}
            and subject.offer_intro_done
            and alternatives
        ):
            return await self._scientific_bac_comparison(primary, alternatives)

        specs = (
            await self.catalogue.specialisations.list(
                PageRequest(page_size=100, filters={"formation_id": formation.id})
            )
        ).items
        elements = (
            await self.catalogue.elements.list(
                PageRequest(page_size=100, filters={"formation_id": formation.id})
            )
        ).items
        lines: list[str] = []

        if subject.profile is AcademicProfile.NEW_BAC:
            bac = value_label(subject.bac_specialty or "")
            if formation.code == "PREPA_GENERAL":
                lines.append(
                    f"Puisque tu souhaites suivre une Prépa, ton bac {bac} te permet d'envisager le {formation.nom}."
                )
            else:
                lines.append(
                    f"Avec ton bac {bac}, je te recommande d'abord les licences IIT admissibles. Une première piste à explorer est {formation.nom}."
                )
            lines.append(
                "Si les conditions de la Prépa correspondent à ton bac, c'est aussi une voie possible vers le cycle ingénieur; "
                "je peux comparer les deux parcours selon ton objectif."
            )
        elif (
            subject.profile is AcademicProfile.LICENCE_STUDENT
            and (
                subject.target == "LICENCE"
                or formation.code.startswith("LICENCE_")
            )
        ):
            level = subject.licence_year
            has_interest = any(
                interest != "GENERAL_INFO" for interest in subject.interests
            )
            if level == 1:
                level_guidance = (
                    "Comme tu es en première année, la poursuite normale est de candidater en première année "
                    "de la licence correspondante."
                )
            elif level in {2, 3}:
                level_guidance = (
                    f"Comme tu es en {level}e année, contacte l'admission IIT avec tes relevés et le programme "
                    f"suivi : elle étudiera la possibilité de te faire poursuivre au niveau correspondant, "
                    "notamment une éventuelle entrée en deuxième année, sans garantie automatique."
                )
            else:
                level_guidance = (
                    "Pour déterminer l'année de reprise ou de poursuite, l'admission doit vérifier ton niveau, "
                    "tes relevés et le contenu des matières déjà validées. Si tu es en L2, "
                    "elle pourra notamment étudier une entrée en deuxième année."
                )
            lines.append(
                f"Tu veux continuer tes études à l'IIT : la piste proposée est {formation.nom}. "
                "Comme ta licence est encore en cours, l'admission vérifiera ton niveau et les équivalences. "
                + level_guidance
            )
            missing_profile = []
            if not subject.licence_specialty:
                missing_profile.append("ta spécialité de licence")
            if not subject.bac_specialty:
                missing_profile.append("ta section de bac")
            if missing_profile:
                lines.append(
                    "Pour personnaliser cette orientation, il me manque "
                    + " et ".join(missing_profile)
                    + "."
                )
            lines.append(
                "Si ton objectif est plutôt le cycle ingénieur, ta licence devra d'abord être validée. "
                "Après validation, l'admission pourra étudier ton dossier et comparer ta spécialité avec les cycles "
                "Génie Informatique, Génie Industriel, Génie Mécanique ou Génie des Procédés; ce n'est pas une admission automatique."
            )
        elif subject.profile is AcademicProfile.LICENCE_STUDENT:
            lines.append(
                f"Tu peux viser le cycle ingénieur {formation.nom} si ta licence est dans un domaine compatible "
                "et si elle est validée. Si tu n'as pas encore validé ta licence, tu peux aussi poursuivre ou reprendre "
                "le parcours correspondant à l'IIT."
            )
            if subject.licence_year:
                lines.append(
                    f"Tu es actuellement en {subject.licence_year}e année de licence : termine et valide ce niveau "
                    "avant l'intégration ingénieur, puis fais étudier ton dossier par l'admission."
                )
            else:
                lines.append(
                    "Comme tu dis seulement être en licence, précise si elle est en cours ou déjà validée "
                    "ainsi que ton niveau (L1, L2 ou L3)."
                )
            lines.append(
                "Ta licence ne doit pas forcément être proposée par l'IIT : nous regardons la correspondance "
                "entre ta spécialité et le cycle ingénieur visé."
            )
            if primary.eligibility.status is EligibilityStatus.UNKNOWN:
                lines.append(
                    f"{formation.nom} est une piste à examiner; l'admission reste à confirmer : "
                    "le diplôme en cours doit être validé avant de conclure."
                )
            lines.append(
                "Si tu es déjà en deuxième année, contacte l'admission IIT avec tes relevés : l'équipe pourra étudier "
                "une éventuelle entrée en deuxième année, sans te faire recommencer automatiquement en première année."
            )
        elif subject.profile is AcademicProfile.LICENCE_HOLDER:
            lines.append(
                f"Avec une licence en {subject.licence_specialty.replace('_', ' ').title() if subject.licence_specialty else 'domaine compatible'}, "
                f"tu peux candidater au cycle ingénieur {formation.nom}, sous réserve de l'étude du dossier."
            )
            lines.append(
                "La licence n'a pas besoin d'être un parcours proposé par l'IIT : l'admission étudie la "
                "correspondance de ton domaine avec le cycle ingénieur demandé."
            )
            lines.append(
                "Prépare le diplôme ou l'attestation de licence, les relevés de notes et, si le diplôme vient d'un établissement privé, "
                "le document d'équivalence ou de reconnaissance demandé. L'admission IIT pourra confirmer les pièces exactes."
            )
        elif subject.profile is AcademicProfile.PREPA_HOLDER:
            lines.append(
                f"Comme tu as validé la Prépa, la suite logique est le cycle ingénieur {formation.nom}."
            )
        elif subject.profile is AcademicProfile.PREPA_STUDENT:
            lines.append(
                f"Si ta Prépa n'est pas encore validée, l'accès au cycle ingénieur {formation.nom} doit attendre la validation. "
                "Tu peux discuter avec l'admission IIT d'une poursuite ou d'un complément du cycle préparatoire à l'IIT."
            )
        elif primary.eligibility.status is EligibilityStatus.UNKNOWN:
            lines.append(f"Avec ton parcours actuel, {formation.nom} est une piste à examiner.")
            if subject.profile in {AcademicProfile.LICENCE_STUDENT, AcademicProfile.PREPA_STUDENT}:
                lines.append("L'admission reste à confirmer : ton diplôme en cours doit être validé avant de conclure.")
            else:
                lines.append("L'admission reste à confirmer à partir des informations manquantes sur ton parcours.")
        else:
            lines.append(
                f"Avec ton parcours actuel, la voie IIT la plus cohérente est {formation.nom}."
            )

        if formation.duree_annees:
            lines.append(f"Durée : {formation.duree_annees} ans.")
        if formation.intitule_diplome and formation.code != "PREPA_GENERAL":
            lines.append(f"Diplôme préparé : {formation.intitule_diplome}.")

        show_specialisation = bool(
            primary.specialisation_name
            and any(interest != "GENERAL_INFO" for interest in subject.interests)
        )
        if show_specialisation:
            label = (
                "Option active"
                if formation.code == "PREPA_GENERAL"
                else "Spécialisation la plus proche de tes intérêts"
            )
            lines.append(f"{label} : {primary.specialisation_name}.")
            relevant = [
                item
                for item in elements
                if item.specialisation_id in {None, primary.specialisation_id}
            ]
            contents = [
                item.nom
                for item in relevant
                if item.type_element.value
                in {"CONTENU_PROGRAMME", "MODULE", "COMPETENCE"}
            ][:6]
            if contents:
                lines.append("Tu y étudieras notamment : " + ", ".join(contents) + ".")
        elif formation.code == "PREPA_GENERAL" and specs:
            lines.append("Option active : " + ", ".join(item.nom for item in specs) + ".")
            contents = [
                item.nom
                for item in elements
                if item.type_element.value in {"CONTENU_PROGRAMME", "MODULE"}
            ][:6]
            if contents:
                lines.append("Tu y étudieras notamment : " + ", ".join(contents) + ".")
        elif specs:
            lines.append(
                f"Cette formation propose {len(specs)} "
                + ("spécialisation." if len(specs) == 1 else "spécialisations.")
            )
            lines.append(
                "Je peux te présenter leurs noms et leurs programmes si tu veux les comparer."
            )

        difficulty = self._difficulty(elements)
        if difficulty:
            lines.append("Niveau d'exigence : " + difficulty)
        if formation.code.startswith("LICENCE_"):
            lines.append(
                "Après la licence, tu pourras aussi candidater à un cycle ingénieur compatible, selon les conditions d'admission."
            )
        if formation.code == "PREPA_GENERAL":
            lines.append(
                "Ce cycle prépare la poursuite vers les études d'ingénieur; il ne s'agit pas d'une admission directe en cycle ingénieur."
            )

        if alternatives:
            lines.append("Autres formations admissibles à comparer :" if all(
                option.eligibility.status is EligibilityStatus.ELIGIBLE for option in alternatives
            ) else "Autres pistes à examiner, sous réserve de confirmation de l'admission :")
            for option in alternatives:
                lines.extend(await self._alternative_summary(option))

        if formation.code == "PREPA_GENERAL" and alternatives:
            lines.append(
                "Veux-tu que je compare cette Prépa aux licences admissibles selon ton projet et ta manière d'étudier ?"
            )
        elif show_specialisation:
            lines.append(
                "Veux-tu d'abord approfondir le programme et les exigences de cette spécialisation ?"
            )
        elif specs:
            lines.append(
                "Veux-tu que je t'aide à choisir la spécialisation la plus adaptée à tes intérêts ?"
            )
        else:
            lines.append(
                "Veux-tu voir le programme détaillé de cette formation ?"
            )
        return "\n".join(lines)

    @staticmethod
    def unavailable_formation(
        requested_label: str,
        subject: SubjectState,
        decision: RecommendationDecision | None,
    ) -> str:
        lines = [
            f"La formation « {requested_label} » ne figure pas dans le catalogue académique actif de l'IIT."
        ]
        options: list[str] = []
        if decision and decision.primary:
            options.append(decision.primary.formation_name)
            options.extend(
                option.formation_name
                for option in decision.alternatives
                if option.formation_name not in options
            )
        if options and subject.profile is not AcademicProfile.UNKNOWN:
            profile = (
                f"ton bac {value_label(subject.bac_specialty)}"
                if subject.profile is AcademicProfile.NEW_BAC
                and subject.bac_specialty
                else "ton profil académique"
            )
            if len(options) == 1:
                lines.append(
                    f"Selon les règles d'admission actives pour {profile}, la formation confirmée est {options[0]}."
                )
            else:
                lines.append(
                    f"Selon les règles d'admission actives pour {profile}, les formations confirmées sont :"
                )
                lines.extend(f"• {name}" for name in options)
            lines.append("Veux-tu que je te présente cette possibilité en détail ?")
        elif subject.profile is AcademicProfile.NEW_BAC and subject.bac_specialty:
            lines.append(
                f"Avec un bac {value_label(subject.bac_specialty)}, aucune formation IIT n'est actuellement confirmée comme admissible par les règles actives."
            )
        else:
            lines.append(
                "Indique-moi ton niveau actuel et, si tu as le bac, ta section : je vérifierai uniquement les formations réellement enregistrées et admissibles."
            )
        return "\n".join(lines)

    @staticmethod
    def profile_summary(subject: SubjectState) -> str:
        if subject.profile is AcademicProfile.NEW_BAC:
            if subject.bac_specialty:
                return f"Tu m'as indiqué avoir un bac {value_label(subject.bac_specialty)}."
            return "Tu m'as indiqué avoir le bac, mais ta section n'est pas encore précisée."
        labels = {
            AcademicProfile.PREPA_STUDENT: "être actuellement en cycle préparatoire",
            AcademicProfile.PREPA_HOLDER: "avoir validé un cycle préparatoire",
            AcademicProfile.LICENCE_STUDENT: "être actuellement en licence",
            AcademicProfile.LICENCE_HOLDER: "être titulaire d'une licence",
            AcademicProfile.MASTER_HOLDER: "être titulaire d'un mastère",
        }
        known = labels.get(subject.profile)
        if known:
            return f"Tu m'as indiqué {known}."
        return "Tu ne m'as pas encore indiqué clairement ton niveau d'études actuel."

    async def credential_options(self, subject: SubjectState) -> list[str]:
        """Find fuller published titles for an underspecified original diploma."""
        words = fold_text((subject.licence_specialty or '').replace('_', ' ')).split()
        if subject.profile not in {AcademicProfile.LICENCE_STUDENT, AcademicProfile.LICENCE_HOLDER} or len(words) != 1 or len(words[0]) < 4:
            return []
        rules = (await self.catalogue.orientation_rules.list(PageRequest(page_size=100, filters={'type_regle': 'ADMISSION'}))).items
        labels = []
        for rule in rules:
            expected = (rule.criteres or {}).get('diplome_origine', [])
            if isinstance(expected, dict):
                expected = expected.get('in', [])
            if isinstance(expected, str):
                expected = [expected]
            for label in expected:
                text = fold_text(str(label).replace('_', ' '))
                if any(token.startswith(words[0]) or words[0].startswith(token) for token in text.split() if len(token) >= 4):
                    labels.append(text)
        return list(dict.fromkeys(labels))

    @staticmethod
    def no_confirmed_orientation(subject: SubjectState, credential_options: Sequence[str] = ()) -> str:
        if credential_options:
            specialty = (subject.licence_specialty or '').replace('_', ' ').lower()
            return (
                f"Pour examiner une poursuite en cycle ingénieur avec ta licence{(' en ' + specialty) if specialty else ''}, "
                "il me faut l'intitulé exact de ton diplôme. Un domaine général ne suffit pas à vérifier les conditions d'admission. "
                "Les règles distinguent notamment : " + ", ".join(credential_options) + ". "
                "Quel intitulé figure sur ton diplôme ou ton attestation ?"
            )
        if subject.profile is AcademicProfile.NEW_BAC and subject.bac_specialty:
            profile = f"un bac {value_label(subject.bac_specialty)}"
        elif subject.licence_specialty:
            profile = f"une licence en {subject.licence_specialty.replace('_', ' ').title()}"
        else:
            profile = "ce profil"
        return (
            f"Je ne trouve aucune orientation IIT confirmée dans les règles actives pour {profile}. "
            "Je préfère ne pas inventer une équivalence ou une formation. "
            "Pour vérifier ton admissibilité et les possibilités particulières, contacte l'administration IIT : "
            "(+216) 70 28 26 00 ou info@iit.tn."
        )

    @staticmethod
    def missing_formation_for_details() -> str:
        return (
            "Je peux vérifier les matières, le programme, la durée, les débouchés, les certifications ou les conditions d'admission, "
            "mais il me faut d'abord le nom de la formation ou de la spécialisation. "
            "Donne-moi par exemple « licence informatique », « génie info » ou « génie industriel »."
        )

    @staticmethod
    def _distinct_alternatives(
        decision: RecommendationDecision,
    ) -> tuple[RecommendationOption, ...]:
        options = decision.alternatives or (
            (decision.secondary,) if getattr(decision, "secondary", None) is not None else ()
        )
        unique: list[RecommendationOption] = []
        seen: set[int] = (
            {decision.primary.formation_id} if decision.primary is not None else set()
        )
        for option in options:
            if option.formation_id in seen:
                continue
            seen.add(option.formation_id)
            unique.append(option)
        return tuple(unique)

    async def _alternative_summary(
        self,
        option: RecommendationOption,
    ) -> list[str]:
        formation = await self.catalogue.formations.require(option.formation_id)
        parts = [formation.nom]
        if formation.duree_annees:
            parts.append(f"{formation.duree_annees} ans")
        if formation.intitule_diplome:
            parts.append(f"diplôme : {formation.intitule_diplome}")
        lines = ["• " + " — ".join(parts) + "."]
        if formation.code == "PREPA_GENERAL":
            lines.append(
                "  Autre voie possible pour préparer une poursuite vers un cycle ingénieur."
            )
        return lines

    async def _scientific_bac_comparison(
        self,
        primary: RecommendationOption,
        alternatives: tuple[RecommendationOption, ...],
    ) -> str:
        lines = ["Pour te conseiller clairement, compare ces chemins :"]
        for option in (primary, *alternatives):
            formation = await self.catalogue.formations.require(option.formation_id)
            specs = (
                await self.catalogue.specialisations.list(
                    PageRequest(page_size=100, filters={"formation_id": formation.id})
                )
            ).items
            elements = (
                await self.catalogue.elements.list(
                    PageRequest(page_size=100, filters={"formation_id": formation.id})
                )
            ).items
            duration = f"{formation.duree_annees} ans" if formation.duree_annees else "durée à confirmer"
            if formation.code == "PREPA_GENERAL":
                option_name = specs[0].nom if specs else "Mathématiques-Physique"
                lines.append(
                    f"• {formation.nom}, option {option_name} — {duration} : autre voie possible pour préparer une poursuite vers un cycle ingénieur."
                )
                difficulty = self._difficulty(elements)
                if difficulty:
                    lines.append("  Défi : " + difficulty)
                continue
            diploma = formation.intitule_diplome or "diplôme à confirmer"
            lines.append(
                f"• {formation.nom} — {duration}; diplôme préparé : {diploma}."
            )
            if specs:
                lines.append(
                    "  Choix disponibles : " + ", ".join(item.nom for item in specs) + "."
                )
            else:
                competencies = [
                    item.nom
                    for item in elements
                    if item.type_element.value in {"COMPETENCE", "CONTENU_PROGRAMME"}
                ][:4]
                if competencies:
                    lines.append("  Axes principaux : " + ", ".join(competencies) + ".")
        lines.append(
            "Parmi ces parcours, quel domaine correspond le mieux à ton projet et à ta manière d'étudier ?"
        )
        return "\n".join(lines)

    @staticmethod
    def _difficulty(elements: list[object]) -> str | None:
        for item in elements:
            if item.type_element.value != "INFORMATION":
                continue
            identity = fold_text(f"{item.nom} {item.description or ''}")
            if not any(term in identity for term in ("exigence", "difficulte", "endurance")):
                continue
            if "beaucoup de travail" in identity and "endurance" in identity:
                return "cette voie demande beaucoup de travail et d'endurance."
            if item.description:
                return item.description.rstrip(".") + "."
        return None

    async def formation_details(
        self,
        target: AcademicTarget,
        intents: list[str],
        *,
        include_all: bool = False,
        continuing: bool = False,
        show_source: bool = True,
        show_specialisations: bool = True,
    ) -> str:
        formation = target.formation
        specs = (
            await self.catalogue.specialisations.list(
                PageRequest(page_size=100, filters={"formation_id": formation.id})
            )
        ).items
        elements = (
            await self.catalogue.elements.list(
                PageRequest(page_size=100, filters={"formation_id": formation.id})
            )
        ).items
        relevant = [
            item
            for item in elements
            if target.specialisation is None
            or item.specialisation_id in {None, target.specialisation.id}
        ]
        title = target.specialisation.nom if target.specialisation else formation.nom
        lines = []
        overview = "DETAILS" in intents and not set(intents).difference({"DETAILS", "GENERAL"})
        if overview and not continuing:
            introduction = f"{title}"
            if formation.duree_annees:
                introduction += f" se déroule sur {formation.duree_annees} ans"
            if formation.intitule_diplome and formation.code != "PREPA_GENERAL" and fold_text(formation.intitule_diplome) != fold_text(title):
                introduction += (" et prépare" if formation.duree_annees else " prépare") + f" au diplôme {formation.intitule_diplome}"
            lines.append(introduction + ".\n")
        if overview and formation.code == "PREPA_GENERAL":
            lines.append("Ce parcours prépare la poursuite vers un cycle ingénieur ; il ne délivre pas lui-même un diplôme d'ingénieur.\n")

        if "DURATION" in intents:
            if formation.duree_annees:
                lines.append(f"La formation dure {formation.duree_annees} ans.\n")
            else:
                lines.append("Je n'ai pas de durée confirmée pour cette formation. L'IIT pourra te la préciser.\n")

        if "CAREERS" in intents:
            public_careers = [item.description for item in relevant if item.type_element.value == "INFORMATION" and "debouches publics" in fold_text(item.nom) and item.description]
            careers = [item.nom for item in relevant if item.type_element.value == "METIER"]
            if public_careers:
                lines.append("Débouchés possibles : " + " ".join(public_careers))
            elif careers:
                lines.append("Débouchés possibles : " + ", ".join(careers) + ".")
            else:
                lines.append("Aucun débouché précis n'est renseigné pour cette portée.")
            lines.append("Le diplôme ne garantit pas un emploi : le recrutement dépend notamment des compétences, de l'expérience et des employeurs.")

        if "INTERNATIONAL" in intents:
            mobility = [item.nom for item in relevant if item.type_element.value == "MOBILITE"]
            if mobility:
                lines.append("Possibilités internationales : " + ", ".join(mobility) + ".")
            else:
                lines.append("Aucune mobilité internationale n'est renseignée pour cette formation.")

        if "CERTIFICATIONS" in intents:
            certifications = [
                item.nom for item in relevant if item.type_element.value == "CERTIFICATION"
            ]
            if certifications:
                lines.append("Les certifications mentionnées pour cette formation sont " + ", ".join(dict.fromkeys(certifications)) + ".")
            else:
                lines.append("Aucune certification n'est renseignée pour cette formation.")
            lines.append("Leur obtention n'est pas automatique : il faut confirmer les examens et les conditions auprès de l'IIT.\n")

        practical_intents = {"PRACTICE", "PROJECTS", "INTERNSHIPS"}.intersection(intents)
        if practical_intents:
            lines.append(await self.practical_learning(target, practical_intents, elements=relevant))

        if "DIFFICULTY" in intents:
            difficulty = self._difficulty(relevant)
            if difficulty:
                lines.append("Niveau d'exigence : " + difficulty)
            else:
                lines.append(
                    "Je ne peux pas qualifier cette formation de facile ou difficile pour tout le monde : le niveau d'exigence n'est pas décrit précisément dans la base active."
                )
                study_topics = [
                    item.nom
                    for item in relevant
                    if item.type_element.value
                    in {"CONTENU_PROGRAMME", "MODULE", "COMPETENCE"}
                ][:4]
                if study_topics:
                    lines.append(
                        "Pour réussir, il faut notamment travailler régulièrement : "
                        + ", ".join(study_topics)
                        + "."
                    )

        if "MARKET" in intents:
            opportunities = [
                item.nom for item in relevant if item.type_element.value == "OPPORTUNITE"
            ]
            careers = [item.nom for item in relevant if item.type_element.value == "METIER"][:4]
            if opportunities:
                lines.append("Perspectives enregistrées : " + ", ".join(opportunities) + ".")
            if careers:
                lines.append("Exemples de débouchés : " + ", ".join(careers) + ".")
            lines.append(
                "La base ne contient pas d'indicateur chiffré du marché de l'emploi; je ne peux donc pas garantir qu'un métier est demandé."
            )

        detail_intents = {"DETAILS", "PROGRAMME"}
        if set(intents).intersection(detail_intents):
            contents = [
                item.nom
                for item in relevant
                if item.type_element.value in {
                    "CONTENU_PROGRAMME",
                    "MODULE",
                    "COMPETENCE",
                }
            ]
            if contents:
                contents = list(dict.fromkeys(contents))
                displayed_contents = contents if include_all else contents[:8]
                if len(displayed_contents) <= 3:
                    lines.append("Tu étudieras notamment " + ", ".join(displayed_contents) + ".")
                else:
                    lines.append("Voici les matières et compétences au programme :")
                    lines.extend("• " + item for item in displayed_contents)
                if len(contents) > len(displayed_contents):
                    lines.append(f"\nCe sont {len(displayed_contents)} des {len(contents)} éléments disponibles ; tu peux demander la liste complète.")
            else:
                lines.append("Je n'ai pas de liste détaillée des matières pour cette formation. L'IIT pourra te communiquer le programme.")
            if target.specialisation is None and specs and show_specialisations:
                lines.append("\nTu peux ensuite approfondir l'une de ces spécialisations :")
                lines.extend(f"• {item.nom}" for item in specs)

        if "DIFFICULTY" in intents:
            lines.append("Veux-tu voir le programme détaillé de cette formation ?")
        elif target.specialisation is None and specs and show_specialisations and set(intents).intersection(detail_intents):
            lines.append("Laquelle de ces spécialisations veux-tu approfondir ?")
        if show_source:
            lines.append(f"\nPour approfondir {title} : {FORMATION_LINKS.get(formation.code, 'https://iit.tn/formation/')}")
        return "\n".join(lines)

    async def practical_learning(self, target, intents, *, elements=None) -> str:
        if elements is None:
            filters = {"formation_id": target.formation.id if target else None}
            elements = (await self.catalogue.elements.list(PageRequest(page_size=100, filters=filters))).items
        criteria = {
            "PRACTICE": ("Pratique et pédagogie", r"\b(?:prati\w*|projets?\s+(?:appliques?|tutores?|federes?|architecturaux)|travaux pratiques|laboratoire\w*)\b"),
            "PROJECTS": ("Projets académiques", r"\b(?:projet\s+(?:tutore|federe)|projets?\s+(?:appliques?|academiques?|architecturaux)|pfe|projet\s+de\s+fin)\b"),
            "INTERNSHIPS": ("Stages", r"\bstages?\b"),
        }
        lines = []
        seen_evidence = set()
        any_evidence = False
        for intent, (label, pattern) in criteria.items():
            if intent not in intents:
                continue
            matches = [item for item in elements if item.type_element.value in {"INFORMATION", "CONTENU_PROGRAMME", "MODULE", "MOBILITE", "COMPETENCE"} and re.search(pattern, fold_text(f"{item.nom} {item.description or ''}"))]
            if len(intents) > 1:
                lines.append(label + " :")
            if matches:
                any_evidence = True
                evidence = list(dict.fromkeys(
                    ("Compétence au programme : " if item.type_element.value == "COMPETENCE" else "") + (item.description or item.nom)
                    for item in matches
                ))
                fresh = [text for text in evidence if text not in seen_evidence]
                seen_evidence.update(fresh)
                if not fresh:
                    lines.append("Il s'agit des mêmes activités que celles citées juste au-dessus.")
                elif len(intents) == 1 and len(fresh) == 1:
                    if fresh[0].startswith("Compétence au programme : "):
                        lines.append("Le programme prévoit notamment cette compétence : " + fresh[0].removeprefix("Compétence au programme : "))
                    else:
                        introduction = {"INTERNSHIPS": "Pour les stages, le catalogue indique", "PROJECTS": "Côté projets, le programme indique", "PRACTICE": "Pour la pratique, le programme indique"}[intent]
                        lines.append(f"{introduction} : {fresh[0]}")
                else:
                    if len(intents) == 1:
                        lines.append({"INTERNSHIPS": "Voici les stages mentionnés :", "PROJECTS": "Tu retrouveras ces projets dans le programme :", "PRACTICE": "Voici les éléments de pratique documentés :"}[intent])
                    lines.extend("• " + text for text in fresh)
            else:
                lines.append(f"Je n'ai pas de modalités précises concernant {label.lower()} pour cette formation. Cela ne signifie pas qu'il n'y en a pas ; l'IIT peut confirmer les activités proposées.")
            lines.append("")
        if any_evidence:
            followups = {
                "INTERNSHIPS": "L'IIT pourra te préciser la durée du stage et les conditions pour y accéder.",
                "PRACTICE": "Pour le volume de pratique et l'organisation des séances, les modalités restent à confirmer auprès de l'IIT.",
                "PROJECTS": "L'encadrement, le calendrier et les livrables des projets sont à confirmer auprès de l'IIT.",
            }
            lines.append(followups[next(iter(intents))] if len(intents) == 1 else "La durée, l'encadrement et les modalités exactes restent à confirmer auprès de l'IIT.")
        return "\n".join(lines)

    async def alternance(self, target) -> str:
        filters = {"formation_id": target.formation.id if target else None}
        elements = (await self.catalogue.elements.list(PageRequest(page_size=100, filters=filters))).items
        records = [item for item in elements if item.type_element.value == "INFORMATION" and "alternance" in fold_text(f"{item.nom} {item.description or ''}")]
        if records:
            return "Alternance :\n" + "\n".join("• " + (item.description or item.nom) for item in records)
        return "Alternance : aucun dispositif précis n'est documenté pour cette formation dans la base. Des cours du soir ou un stage ne suffisent pas à confirmer une formation en alternance. Demande à l'IIT le rythme école/entreprise, le contrat et les formations concernées."

    async def admission(self, target, subject, decision) -> str:
        from app.domain.recommendation.schemas import EligibilityStatus
        records = (await self.catalogue.orientation_rules.list(PageRequest(page_size=100, filters={"formation_id": target.formation.id}))).items
        rules = [item for item in records if item.type_regle == "ADMISSION" and item.specialisation_id in {None, target.specialisation.id if target.specialisation else None}]
        lines = [f"Admission — {target.formation.nom} :"]
        for rule in rules:
            if rule.description:
                lines.append("• " + rule.description)
            else:
                for key, criterion in rule.criteres.items():
                    values = criterion.get("in", []) if isinstance(criterion, dict) else [criterion]
                    if values:
                        label = {"diplome": "Diplôme", "type_bac": "Sections de bac", "diplome_origine": "Diplômes d'origine"}.get(key, "Critère")
                        lines.append(label + " : " + ", ".join(value_label(str(value)) for value in values) + ".")
        if not rules:
            lines.append("Les conditions précises ne sont pas renseignées ; l'administration doit confirmer ton admissibilité.")
        elif decision and decision.status is EligibilityStatus.ELIGIBLE:
            lines.append("Ton profil est compatible avec les critères enregistrés ; l'admission finale reste soumise à l'étude du dossier par l'IIT.")
        elif decision and decision.status is EligibilityStatus.NOT_ELIGIBLE:
            lines.append("Ton profil ne remplit pas les critères enregistrés pour cette formation ; je ne peux pas confirmer une admission ni te proposer cette pré-inscription.")
        else:
            lines.append("Pour vérifier ton cas, quel diplôme as-tu obtenu et dans quelle spécialité ?")
        return "\n".join(lines)

    async def next_detail_step(self, target: AcademicTarget) -> str:
        formation = target.formation
        specs = (
            await self.catalogue.specialisations.list(
                PageRequest(page_size=100, filters={"formation_id": formation.id})
            )
        ).items
        if target.specialisation is None and specs:
            lines = [
                f"Pour approfondir {formation.nom} sans répéter les mêmes informations, choisis une spécialisation :"
            ]
            lines.extend(f"• {item.nom}" for item in specs)
            lines.append(
                "Réponds simplement avec le nom qui t'attire le plus; je te donnerai ensuite son programme et ses exigences connues."
            )
            return "\n".join(lines)
        title = target.specialisation.nom if target.specialisation else formation.nom
        return (
            f"Je t'ai déjà présenté les principaux détails académiques disponibles pour {title}. "
            "Quelle information veux-tu approfondir maintenant : programme, certifications, international, débouchés ou frais ?"
        )

    async def registration_documents(
        self,
        target: AcademicTarget | None,
        *,
        pre_registration_completed: bool,
    ) -> str:
        if target is None:
            return (
                "Pour te donner la bonne liste de documents sans mélanger les parcours, "
                "indique-moi la formation concernée."
            )

        effective_elements = await AcademicElementResolutionService(
            self.catalogue.elements
        ).resolve_effective_elements(
            target.formation.parcours_id,
            target.formation.id,
            target.specialisation.id if target.specialisation else None,
            types=(FormationElementType.DOCUMENT_INSCRIPTION,),
        )
        documents = [item.element for item in effective_elements]
        if not documents:
            return (
                f"Les documents d'inscription de {target.formation.nom} ne sont pas "
                "renseignés dans la base académique active. Je préfère ne pas inventer "
                "de pièces à fournir."
            )

        if pre_registration_completed:
            remaining_documents = [
                document
                for document in documents
                if document.code != "DOC_PREINSCRIPTION"
            ]
            lines = [
                "Puisque tu as déjà effectué la pré-inscription, voici les documents "
                f"restants enregistrés pour {target.formation.nom} :"
            ]
        else:
            remaining_documents = documents
            lines = [
                f"Voici les éléments du dossier d'inscription enregistrés pour {target.formation.nom} :"
            ]

        if not remaining_documents:
            lines.append("• Aucun autre document n'est renseigné.")
        else:
            lines.extend(f"• {document.nom}" for document in remaining_documents)
        return "\n".join(lines)

    async def pre_registration(self, target: AcademicTarget) -> str:
        formation = target.formation
        elements = (
            await self.catalogue.elements.list(
                PageRequest(page_size=100, filters={"formation_id": formation.id})
            )
        ).items

        procedure = next(
            (
                item.description
                for item in elements
                if item.type_element.value == "INFORMATION"
                and item.description
                and (
                    "pré-inscription" in item.description.casefold()
                    or "pre-inscription" in item.description.casefold()
                    or "préinscription" in item.description.casefold()
                )
            ),
            None,
        )

        admission_link = next(
            (
                match.group(0)
                for item in elements
                if item.description
                for match in [re.search(r"https?://\S+", item.description)]
                if match
            ),
            "https://iit.tn/admission/procedure-et-frais-dinscription/",
        )

        global_elements = (
            await self.catalogue.elements.list(
                PageRequest(page_size=100, filters={"formation_id": None})
            )
        ).items
        contact = next(
            (
                item.description
                for item in global_elements
                if item.formation_id is None
                and item.description
                and "téléphone" in item.description.casefold()
            ),
            None,
        )
        registration_links = [
            item for item in [*elements, *global_elements]
            if item.type_element.value == "LIEN_PREINSCRIPTION"
            and getattr(item, "parcours_id", None) in {None, formation.parcours_id}
            and item.specialisation_id in {None, target.specialisation.id if target.specialisation else None}
            and getattr(item, "valeur", None)
        ]
        if registration_links:
            parts = urlsplit(registration_links[0].valeur)
            if parts.scheme in {"http", "https"} and parts.netloc:
                query = urlencode([(key, value) for key, value in parse_qsl(parts.query) if key != "fbclid" and not key.startswith("utm_")])
                admission_link = urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))

        lines = [
            f"Très bien, pour {formation.nom}, la démarche recommandée est la pré-inscription suivie du dossier d'admission."
        ]
        lines.append(
            "Tu peux commencer dès maintenant via ce lien : "
            f"{admission_link}"
        )
        lines.append(
            "Important : pour tous les parcours, un paiement comptant donne une réduction de 5% sur le total des frais."
        )
        if procedure:
            lines.append(procedure)
        else:
            lines.append(
                "La procédure détaillée de cette formation est disponible dans la base académique active et doit être confirmée avec l'IIT pour les pièces exactes et les dates de dépôt."
            )
        if contact:
            lines.append(_public_contact(contact, include_department=formation.code == "INGENIEUR_INFO"))
        lines.append(
            "Si tu veux, je peux aussi te guider pour préparer le dossier ou vérifier les frais selon ton profil."
        )
        return "\n".join(lines)


def _money(value: object) -> str:
    amount = Decimal(str(value))
    if amount == amount.to_integral():
        return f"{int(amount):,}".replace(",", " ")
    return f"{amount:,.2f}".replace(",", " ").replace(".", ",")


def _language_label(value: str) -> str:
    return {
        "FRANCAIS": "français",
        "ANGLAIS": "anglais",
    }.get(value.upper(), value.replace("_", " ").lower())


def _public_contact(value: str, *, include_department: bool) -> str:
    if include_department:
        return value
    sentences = re.split(r"(?<=[.!?])\s+", value.strip())
    return " ".join(
        sentence
        for sentence in sentences
        if "génie informatique" not in sentence.casefold()
    )


def _annual_total(
    registration: object | None,
    monthly: object | None,
    months: int | None,
) -> Decimal | None:
    if registration is None or monthly is None or not months:
        return None
    return Decimal(str(registration)) + Decimal(str(monthly)) * months

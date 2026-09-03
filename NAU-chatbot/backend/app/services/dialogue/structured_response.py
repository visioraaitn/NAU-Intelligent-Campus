from __future__ import annotations

import re
from decimal import Decimal

from app.domain.academic.enums import FormationElementType
from app.domain.conversation.models import AcademicProfile, SubjectState
from app.domain.recommendation.schemas import (
    RecommendationDecision,
    RecommendationOption,
)
from app.repositories.academic import PageRequest
from app.services.academic.catalog_service import AcademicCatalogService
from app.services.academic.element_resolution import AcademicElementResolutionService
from app.services.academic.target_resolver import AcademicTarget
from app.services.dialogue.human_labels import value_label
from app.services.dialogue.normalizer import contains_phrase, fold_text


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
        lines.append(
            "Dis-moi ton niveau actuel et ta section ou spécialité, et je te montrerai uniquement les formations compatibles avec ton profil."
        )
        return "\n".join(lines)

    async def fees(
        self,
        target: AcademicTarget | None,
        *,
        include_all: bool = False,
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
        else:
            lines.append(
                f"Avec ton parcours actuel, la voie IIT la plus cohérente est {formation.nom}."
            )

        if formation.duree_annees:
            lines.append(f"Durée : {formation.duree_annees} ans.")
        if formation.intitule_diplome and formation.code != "PREPA_GENERAL":
            lines.append(f"Diplôme préparé : {formation.intitule_diplome}.")

        if primary.specialisation_name:
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
                f"Cette formation comprend {len(specs)} "
                + ("spécialisation :" if len(specs) == 1 else "spécialisations :")
            )
            lines.extend(f"• {item.nom}" for item in specs)

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
            lines.append("Autres formations admissibles à comparer :")
            for option in alternatives:
                lines.extend(await self._alternative_summary(option))

        if formation.code == "PREPA_GENERAL" and alternatives:
            lines.append(
                "Veux-tu que je compare cette Prépa aux licences admissibles selon ton projet et ta manière d'étudier ?"
            )
        elif primary.specialisation_name:
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
        if options:
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

    @staticmethod
    def _distinct_alternatives(
        decision: RecommendationDecision,
    ) -> tuple[RecommendationOption, ...]:
        options = decision.alternatives or (
            (decision.secondary,) if decision.secondary is not None else ()
        )
        unique: list[RecommendationOption] = []
        seen: set[int] = set()
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
        specs = (
            await self.catalogue.specialisations.list(
                PageRequest(page_size=100, filters={"formation_id": formation.id})
            )
        ).items
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
        if specs:
            lines.append(
                "  Spécialisations : " + ", ".join(item.nom for item in specs) + "."
            )
            return lines
        elements = (
            await self.catalogue.elements.list(
                PageRequest(page_size=100, filters={"formation_id": formation.id})
            )
        ).items
        competencies = [
            item.nom
            for item in elements
            if item.type_element.value in {"COMPETENCE", "CONTENU_PROGRAMME"}
        ][:4]
        if competencies:
            lines.append("  Axes étudiés : " + ", ".join(competencies) + ".")
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
        lines = [title]

        if formation.intitule_diplome and formation.code != "PREPA_GENERAL":
            lines.append(f"Diplôme préparé : {formation.intitule_diplome}.")
        elif formation.code == "PREPA_GENERAL":
            lines.append(
                "Finalité : préparer la poursuite vers un cycle ingénieur; ce cycle n'est pas lui-même un diplôme d'ingénieur."
            )

        if "DURATION" in intents or {"DETAILS", "PROGRAMME"}.intersection(intents):
            if formation.duree_annees:
                lines.append(f"Durée enregistrée : {formation.duree_annees} ans.")
            else:
                lines.append("La durée n'est pas renseignée dans la base active.")

        if "CAREERS" in intents:
            careers = [item.nom for item in relevant if item.type_element.value == "METIER"]
            if careers:
                lines.append("Débouchés possibles : " + ", ".join(careers) + ".")
            else:
                lines.append("Aucun débouché précis n'est renseigné pour cette portée.")

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
                lines.append("Certifications préparées ou mentionnées : " + ", ".join(certifications) + ".")
            else:
                lines.append("Aucune certification n'est renseignée pour cette formation.")

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
            if target.specialisation is None and specs:
                lines.append("Spécialisations disponibles :")
                lines.extend(f"• {item.nom}" for item in specs)
            contents = [
                item.nom
                for item in relevant
                if item.type_element.value in {
                    "CONTENU_PROGRAMME",
                    "MODULE",
                    "COMPETENCE",
                }
            ]
            if contents and (target.specialisation is not None or not specs):
                displayed_contents = contents if include_all else contents[:8]
                lines.append("Contenus et compétences : " + ", ".join(displayed_contents) + ".")

        if "DIFFICULTY" in intents:
            lines.append("Veux-tu voir le programme détaillé de cette formation ?")
        elif target.specialisation is None and specs:
            lines.append("Laquelle de ces spécialisations veux-tu approfondir ?")
        else:
            lines.append("Souhaites-tu ensuite préparer une pré-inscription ?")
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

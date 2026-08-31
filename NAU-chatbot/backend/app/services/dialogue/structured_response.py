from __future__ import annotations

from decimal import Decimal

from app.domain.conversation.models import AcademicProfile, SubjectState
from app.domain.recommendation.schemas import (
    RecommendationDecision,
    RecommendationOption,
)
from app.repositories.academic import PageRequest
from app.services.academic.catalog_service import AcademicCatalogService
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

    async def fees(self, target: AcademicTarget | None) -> str:
        if target is not None:
            formations = [target.formation]
        else:
            formations = (
                await self.catalogue.formations.list(PageRequest(page_size=100))
            ).items
            formations = sorted(
                formations,
                key=lambda item: (item.parcours_id, item.id),
            )

        entries: list[tuple[object, object]] = []
        for formation in formations:
            tariffs = (
                await self.catalogue.tarifs.list(
                    PageRequest(
                        page_size=100,
                        filters={"formation_id": formation.id},
                    )
                )
            ).items
            entries.extend((formation, tariff) for tariff in tariffs)

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
            lines.append(f"• {formation.nom} : " + " + ".join(parts) + ".")
        lines.append(
            "Ces montants doivent être reconfirmés pour l'année universitaire visée. Veux-tu que je t'aide à préparer une pré-inscription ?"
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
                    f"Avec ton bac {bac}, mon conseil prioritaire est le {formation.nom}."
                )
            else:
                lines.append(
                    f"Avec ton bac {bac}, la voie IIT compatible que je te recommande est {formation.nom}."
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
                "Tu préfères que je compare la Prépa MP, la Licence en Informatique et la Licence en Mécatronique selon ton projet et ta manière d'étudier ?"
            )
        elif primary.specialisation_name:
            lines.append(
                "Veux-tu d'abord approfondir le programme et les exigences de cette spécialisation ?"
            )
        elif specs:
            lines.append(
                "Laquelle de ces spécialisations veux-tu découvrir en détail ?"
            )
        else:
            lines.append(
                "Veux-tu voir le programme, les débouchés ou les frais de cette formation ?"
            )
        return "\n".join(lines)

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
                    f"• {formation.nom}, option {option_name} — {duration} : voie prioritaire si ton objectif est le cycle ingénieur."
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
            "Tu te vois plutôt dans un rythme intensif en maths-physique, dans l'informatique, ou dans la mécatronique et les systèmes intelligents ?"
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
                    "Le niveau d'exigence n'est pas décrit précisément dans la base active."
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
                lines.append("Contenus et compétences : " + ", ".join(contents[:8]) + ".")

        lines.append(
            "Veux-tu maintenant comparer les spécialisations, voir les frais ou commencer les étapes de pré-inscription ?"
        )
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
                and "pré-inscription" in item.description.casefold()
            ),
            None,
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
            f"Très bien, tu peux passer à l'étape de pré-inscription pour {formation.nom}."
        ]
        if procedure:
            lines.append(procedure)
        else:
            lines.append(
                "La procédure détaillée de cette formation n'est pas renseignée dans la base active; l'équipe IIT doit confirmer les pièces et étapes exactes."
            )
        if contact:
            lines.append(contact)
        lines.append(
            "Souhaites-tu d'abord vérifier les frais ou les conditions d'admission avant de contacter l'IIT ?"
        )
        return "\n".join(lines)


def _money(value: object) -> str:
    amount = Decimal(str(value))
    if amount == amount.to_integral():
        return f"{int(amount):,}".replace(",", " ")
    return f"{amount:,.2f}".replace(",", " ").replace(".", ",")


def _annual_total(
    registration: object | None,
    monthly: object | None,
    months: int | None,
) -> Decimal | None:
    if registration is None or monthly is None or not months:
        return None
    return Decimal(str(registration)) + Decimal(str(monthly)) * months

import type { FormationElementType } from "../../types/academic";

export interface ElementBusinessGroup {
  type: FormationElementType;
  title: string;
  singular: string;
  emptyMessage: string;
}

export const PROGRAM_GROUPS: ElementBusinessGroup[] = [
  { type: "MODULE", title: "Modules", singular: "module", emptyMessage: "Aucun module renseigné." },
  { type: "COURS", title: "Cours", singular: "cours", emptyMessage: "Aucun cours renseigné." },
  { type: "CONTENU_PROGRAMME", title: "Contenus", singular: "contenu", emptyMessage: "Aucun contenu de programme renseigné." },
];

export const OUTCOME_GROUPS: ElementBusinessGroup[] = [
  { type: "COMPETENCE", title: "Compétences", singular: "compétence", emptyMessage: "Aucune compétence renseignée." },
  { type: "METIER", title: "Métiers", singular: "métier", emptyMessage: "Aucun métier renseigné." },
  { type: "DOMAINE_ACTIVITE", title: "Domaines d’activité", singular: "domaine", emptyMessage: "Aucun domaine d’activité renseigné." },
];

export const CERTIFICATION_GROUPS: ElementBusinessGroup[] = [
  { type: "CERTIFICATION", title: "Certifications proposées", singular: "certification", emptyMessage: "Aucune certification proposée." },
  { type: "OUTIL", title: "Outils", singular: "outil", emptyMessage: "Aucun outil renseigné." },
];

export const INTERNATIONAL_GROUPS: ElementBusinessGroup[] = [
  { type: "LANGUE", title: "Langues", singular: "langue", emptyMessage: "Aucune langue complémentaire renseignée." },
  { type: "MOBILITE", title: "Mobilité", singular: "mobilité", emptyMessage: "Aucune mobilité renseignée." },
  { type: "OPPORTUNITE", title: "Opportunités", singular: "opportunité", emptyMessage: "Aucune opportunité renseignée." },
];

export const PRACTICAL_GROUP: ElementBusinessGroup = {
  type: "INFORMATION",
  title: "Informations pratiques",
  singular: "information",
  emptyMessage: "Aucune information pratique renseignée.",
};

export const CONTEXTUAL_ELEMENT_FIELDS = [
  "nom",
  "description",
  "organisme",
  "ordre_affichage",
  "actif",
];

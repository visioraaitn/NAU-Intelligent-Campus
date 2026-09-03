import type { AcademicResource } from "../../types/academic";

export type FieldKind = "text" | "textarea" | "number" | "date" | "select" | "checkbox" | "json" | "reference" | "string-list" | "language";
export type ColumnFormat = "text" | "enum" | "currency" | "date" | "json" | "criteria" | "reference" | "list" | "language" | "years";

export interface SelectOption {
  value: string;
  label: string;
}

export interface EntityField {
  name: string;
  label: string;
  kind: FieldKind;
  required?: boolean;
  fullWidth?: boolean;
  placeholder?: string;
  help?: string;
  min?: number;
  minLength?: number;
  max?: number;
  step?: number;
  maxLength?: number;
  pattern?: string;
  defaultValue?: string | number | boolean | Record<string, unknown>;
  options?: SelectOption[];
  reference?: AcademicResource;
}

export interface EntityColumn {
  key: string;
  label: string;
  format?: ColumnFormat;
  reference?: AcademicResource;
}

export interface EntityRowNavigation {
  resource: AcademicResource | "academic-overview" | "cycle-workspace";
  filterParam: string;
  valueKey?: string;
  contextParams?: Array<{
    param: string;
    valueKey: string;
  }>;
}

export interface EntityHierarchyContext {
  filterParam: string;
  reference: AcademicResource;
  parentReference: AcademicResource;
  parentIdKey: string;
  parentResource: AcademicResource;
  parentFilterParam: string;
  rootResource: AcademicResource;
  rootLabel: string;
}

export interface EntityConfig {
  resource: AcademicResource;
  singular: string;
  plural: string;
  title: string;
  description: string;
  createTitle?: string;
  editTitle?: string;
  createActionLabel?: string;
  fields: EntityField[];
  columns: EntityColumn[];
  compactTable?: boolean;
  contextualCreate?: {
    field: string;
    queryParam: string;
  };
  filteredEmptyState?: {
    message: string;
    actionLabel: string;
  };
  hierarchyContext?: EntityHierarchyContext;
  parcoursFilter?: boolean;
  formationFilter?: boolean;
  formationFilterInUrl?: boolean;
  specialisationFilter?: boolean;
  rowNavigation?: EntityRowNavigation;
}

const codePattern = "[A-Z0-9][A-Z0-9_\\-]*";
const extendedCodePattern = "[A-Z0-9][A-Z0-9_.\\-]*";
const ragTextMaxLength = 600;

const activeField: EntityField = {
  name: "actif",
  label: "Actif et visible",
  kind: "checkbox",
  defaultValue: true,
  fullWidth: true,
  help: "Les entrées inactives restent archivées mais ne sont pas proposées par l’assistant.",
};

const formationField = (required = true): EntityField => ({
  name: "formation_id",
  label: "Formation",
  kind: "reference",
  reference: "formations",
  required,
});

const parcoursField = (): EntityField => ({
  name: "parcours_id",
  label: "Cycle académique",
  kind: "reference",
  reference: "parcours",
  help: "Laisser vide pour une information globale ou choisir une formation ci-dessous.",
});

const specialisationField = (): EntityField => ({
  name: "specialisation_id",
  label: "Spécialisation",
  kind: "reference",
  reference: "specialisations",
  help: "Laisser vide pour appliquer l’entrée à toute la formation.",
});

const sourceField: EntityField = {
  name: "source_ref",
  label: "Référence de la source",
  kind: "text",
  maxLength: 2_048,
  fullWidth: true,
  placeholder: "Ex. brochure officielle 2026, page 12",
};

export const entityConfigs: Record<AcademicResource, EntityConfig> = {
  parcours: {
    resource: "parcours",
    singular: "cycle académique",
    plural: "cycles académiques",
    title: "Cycles académiques",
    description: "Un cycle académique représente le type ou niveau du cursus. Les disciplines sont créées comme formations.",
    compactTable: true,
    rowNavigation: {
      resource: "cycle-workspace",
      filterParam: "parcours_id",
    },
    columns: [
      { key: "nom", label: "Cycle académique" },
      { key: "duree_annees", label: "Durée", format: "years" },
    ],
    fields: [
      { name: "code", label: "Code", kind: "text", required: true, maxLength: 50, pattern: codePattern, placeholder: "LICENCE" },
      { name: "nom", label: "Nom", kind: "text", required: true, maxLength: 255 },
      { name: "duree_annees", label: "Durée en années", kind: "number", min: 1, max: 20, step: 1 },
      { name: "description", label: "Description", kind: "textarea", maxLength: ragTextMaxLength, fullWidth: true },
      activeField,
    ],
  },
  formations: {
    resource: "formations",
    singular: "formation",
    plural: "formations",
    title: "Formations",
    createActionLabel: "Créer la formation",
    description: "Diplômes et programmes proposés au sein de chaque cycle académique.",
    compactTable: true,
    parcoursFilter: true,
    rowNavigation: {
      resource: "academic-overview",
      filterParam: "formation_id",
    },
    columns: [
      { key: "nom", label: "Formation" },
      { key: "intitule_diplome", label: "Diplôme" },
      { key: "duree_annees", label: "Durée", format: "years" },
      { key: "langues_enseignement", label: "Langues", format: "list" },
    ],
    fields: [
      { name: "parcours_id", label: "Cycle académique", kind: "reference", reference: "parcours", required: true },
      { name: "code", label: "Code", kind: "text", required: true, maxLength: 100, pattern: codePattern },
      { name: "nom", label: "Nom", kind: "text", required: true, maxLength: 255 },
      { name: "intitule_diplome", label: "Intitulé du diplôme", kind: "text", maxLength: 255 },
      { name: "duree_annees", label: "Durée en années", kind: "number", min: 1, max: 20, step: 1 },
      { name: "nb_semestres", label: "Nombre de semestres", kind: "number", min: 1, max: 40, step: 1 },
      { name: "credits_total", label: "Crédits totaux", kind: "number", min: 1, max: 1_000, step: 1 },
      {
        name: "langues_enseignement",
        label: "Langues d’enseignement",
        kind: "string-list",
        required: true,
        defaultValue: "FRANCAIS",
        maxLength: 500,
        fullWidth: true,
        placeholder: "FRANCAIS, ANGLAIS",
        help: "Séparez les langues par des virgules. Vous pourrez ajouter librement une nouvelle langue à l’avenir.",
      },
      { name: "description", label: "Description", kind: "textarea", maxLength: ragTextMaxLength, fullWidth: true },
      sourceField,
      activeField,
    ],
  },
  specialisations: {
    resource: "specialisations",
    singular: "spécialisation",
    plural: "spécialisations",
    title: "Spécialisations",
    description: "Options, filières et spécialisations rattachées à une formation.",
    createTitle: "Nouvelle spécialisation",
    editTitle: "Modifier la spécialisation",
    createActionLabel: "Créer la spécialisation",
    compactTable: true,
    contextualCreate: {
      field: "formation_id",
      queryParam: "formation_id",
    },
    filteredEmptyState: {
      message: "Aucune spécialisation n’est encore définie pour cette formation.",
      actionLabel: "Ajouter une spécialisation",
    },
    formationFilter: true,
    formationFilterInUrl: true,
    hierarchyContext: {
      filterParam: "formation_id",
      reference: "formations",
      parentReference: "parcours",
      parentIdKey: "parcours_id",
      parentResource: "formations",
      parentFilterParam: "parcours_id",
      rootResource: "parcours",
      rootLabel: "Cycle académique",
    },
    columns: [
      { key: "code", label: "Spécialisation" },
    ],
    fields: [
      formationField(),
      { name: "code", label: "Code", kind: "text", required: true, maxLength: 100, pattern: codePattern },
      { name: "nom", label: "Nom", kind: "text", required: true, maxLength: 255 },
      { name: "ordre_affichage", label: "Ordre d’affichage", kind: "number", min: 0, step: 1 },
      { name: "description", label: "Description", kind: "textarea", maxLength: ragTextMaxLength, fullWidth: true },
      sourceField,
      activeField,
    ],
  },
  elements: {
    resource: "elements",
    singular: "élément de formation",
    plural: "éléments de formation",
    title: "Éléments de formation",
    description: "Modules, compétences, métiers, outils et autres faits pédagogiques utilisés par l’assistant.",
    formationFilter: true,
    specialisationFilter: true,
    columns: [
      { key: "parcours_id", label: "Cycle académique", format: "reference", reference: "parcours" },
      { key: "formation_id", label: "Formation", format: "reference", reference: "formations" },
      { key: "specialisation_id", label: "Spécialisation", format: "reference", reference: "specialisations" },
      { key: "type_element", label: "Type", format: "enum" },
      { key: "nom", label: "Élément" },
      { key: "organisme", label: "Organisme" },
    ],
    fields: [
      parcoursField(),
      formationField(false),
      specialisationField(),
      { name: "parent_id", label: "Élément parent", kind: "reference", reference: "elements" },
      {
        name: "type_element",
        label: "Type d’élément",
        kind: "select",
        required: true,
        options: ([
          ["MODULE", "Module"], ["COURS", "Cours"], ["CONTENU_PROGRAMME", "Contenu de programme"],
          ["COMPETENCE", "Compétence"], ["METIER", "Métier"], ["DOMAINE_ACTIVITE", "Domaine d’activité"],
          ["CERTIFICATION", "Certification"], ["LANGUE", "Langue"], ["MOBILITE", "Mobilité"],
          ["OUTIL", "Outil"], ["OPPORTUNITE", "Opportunité"], ["INFORMATION", "Information"],
          ["DOCUMENT_INSCRIPTION", "Document d’inscription"], ["LIEN_PREINSCRIPTION", "Lien de préinscription"],
        ] as const).map(([value, label]) => ({ value, label })),
      },
      { name: "code", label: "Code", kind: "text", maxLength: 120, pattern: extendedCodePattern },
      { name: "nom", label: "Nom", kind: "text", required: true, maxLength: 255 },
      { name: "organisme", label: "Organisme", kind: "text", maxLength: 255 },
      { name: "ordre_affichage", label: "Ordre d’affichage", kind: "number", min: 0, step: 1 },
      { name: "description", label: "Description", kind: "textarea", maxLength: ragTextMaxLength, fullWidth: true, help: "Gardez un fait atomique et concis; créez plusieurs éléments pour des informations distinctes." },
      { name: "valeur", label: "Valeur ou lien", kind: "textarea", maxLength: 2_048, fullWidth: true },
      sourceField,
      activeField,
    ],
  },
  tarifs: {
    resource: "tarifs",
    singular: "tarif",
    plural: "tarifs",
    title: "Tarifs",
    description: "Frais communs du cycle académique et échéanciers propres aux formations.",
    formationFilter: true,
    specialisationFilter: true,
    columns: [
      { key: "parcours_id", label: "Cycle académique", format: "reference", reference: "parcours" },
      { key: "formation_id", label: "Formation", format: "reference", reference: "formations" },
      { key: "specialisation_id", label: "Spécialisation", format: "reference", reference: "specialisations" },
      { key: "langue_enseignement", label: "Langue", format: "language" },
      { key: "annee_universitaire", label: "Année" },
      { key: "frais_inscription", label: "Inscription", format: "currency" },
      { key: "mensualite", label: "Mensualité", format: "currency" },
      { key: "nb_mensualites", label: "Échéances" },
      { key: "statut", label: "Statut", format: "enum" },
    ],
    fields: [
      parcoursField(),
      formationField(false),
      specialisationField(),
      {
        name: "langue_enseignement",
        label: "Langue d’enseignement",
        kind: "language",
        defaultValue: "FRANCAIS",
        help: "Les choix proviennent des langues configurées sur la formation sélectionnée.",
      },
      { name: "frais_inscription", label: "Frais d’inscription", kind: "number", min: 0, step: 0.01 },
      { name: "mensualite", label: "Mensualité", kind: "number", min: 0, step: 0.01 },
      { name: "nb_mensualites", label: "Nombre de mensualités", kind: "number", min: 1, max: 120, step: 1 },
      { name: "devise", label: "Devise", kind: "text", required: true, minLength: 3, maxLength: 10, pattern: "[A-Z]+", defaultValue: "TND" },
      { name: "annee_universitaire", label: "Année universitaire", kind: "text", maxLength: 50, placeholder: "2026-2027" },
      { name: "statut", label: "Statut", kind: "select", required: true, defaultValue: "INDICATIF", options: [
        { value: "INDICATIF", label: "Indicatif" }, { value: "CONFIRME", label: "Confirmé" },
      ] },
      { name: "remarque", label: "Remarque", kind: "textarea", maxLength: ragTextMaxLength, fullWidth: true },
      sourceField,
      activeField,
    ],
  },
  "orientation-rules": {
    resource: "orientation-rules",
    singular: "règle d’orientation",
    plural: "règles d’orientation",
    title: "Règles d’orientation",
    description: "Critères officiels d’admission et règles de recommandation.",
    formationFilter: true,
    specialisationFilter: true,
    columns: [
      { key: "formation_id", label: "Formation", format: "reference", reference: "formations" },
      { key: "specialisation_id", label: "Spécialisation", format: "reference", reference: "specialisations" },
      { key: "code", label: "Code" },
      { key: "nom", label: "Règle" },
      { key: "type_regle", label: "Type", format: "enum" },
      { key: "criteres", label: "Critères lisibles", format: "criteria" },
      { key: "priorite", label: "Priorité" },
    ],
    fields: [
      formationField(),
      specialisationField(),
      { name: "code", label: "Code", kind: "text", required: true, maxLength: 100, pattern: codePattern },
      { name: "nom", label: "Nom", kind: "text", required: true, maxLength: 255 },
      { name: "type_regle", label: "Type", kind: "select", required: true, options: [
        { value: "ADMISSION", label: "Admission" }, { value: "RECOMMANDATION", label: "Recommandation" },
      ] },
      { name: "priorite", label: "Priorité", kind: "number", required: true, min: 1, step: 1, defaultValue: 1 },
      {
        name: "criteres",
        label: "Critères structurés",
        kind: "json",
        required: true,
        defaultValue: {},
        maxLength: 300,
        fullWidth: true,
        help: "La prévisualisation lisible apparaît sous le champ. Exemples : diplome, type_bac, diplome_origine ou interet.",
      },
      { name: "description", label: "Description", kind: "textarea", maxLength: ragTextMaxLength, fullWidth: true },
      sourceField,
      activeField,
    ],
  },
  accreditations: {
    resource: "accreditations",
    singular: "accréditation",
    plural: "accréditations",
    title: "Accréditations",
    description: "Reconnaissances et accréditations officielles associées aux formations.",
    formationFilter: true,
    columns: [
      { key: "formation_id", label: "Formation", format: "reference", reference: "formations" },
      { key: "code", label: "Code" },
      { key: "nom", label: "Accréditation" },
      { key: "organisme", label: "Organisme" },
      { key: "date_debut", label: "Début", format: "date" },
      { key: "date_fin", label: "Fin", format: "date" },
    ],
    fields: [
      formationField(),
      { name: "code", label: "Code", kind: "text", required: true, maxLength: 100, pattern: codePattern },
      { name: "nom", label: "Nom", kind: "text", required: true, maxLength: 255 },
      { name: "organisme", label: "Organisme", kind: "text", maxLength: 255 },
      { name: "date_debut", label: "Date de début", kind: "date" },
      { name: "date_fin", label: "Date de fin", kind: "date" },
      { name: "description", label: "Description", kind: "textarea", maxLength: ragTextMaxLength, fullWidth: true },
      sourceField,
      activeField,
    ],
  },
};

export const entityConfigList = Object.values(entityConfigs);

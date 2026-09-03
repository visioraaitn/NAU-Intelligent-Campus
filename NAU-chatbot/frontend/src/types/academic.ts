import type { Page } from "./api";

export const academicResources = [
  "parcours",
  "formations",
  "specialisations",
  "elements",
  "tarifs",
  "orientation-rules",
  "accreditations",
] as const;

export type AcademicResource = (typeof academicResources)[number];

export interface AcademicEntity extends Record<string, unknown> {
  id: number;
  actif: boolean;
  created_at: string;
  updated_at: string;
  code?: string | null;
  nom?: string | null;
  source_ref?: string | null;
}

export interface Parcours extends AcademicEntity {
  code: string;
  nom: string;
  duree_annees: number | null;
  description: string | null;
}

export interface Formation extends AcademicEntity {
  parcours_id: number;
  code: string;
  nom: string;
  intitule_diplome: string | null;
  duree_annees: number | null;
  nb_semestres: number | null;
  credits_total: number | null;
  langues_enseignement: string[];
  description: string | null;
  source_ref: string | null;
}

export interface Specialisation extends AcademicEntity {
  formation_id: number;
  code: string;
  nom: string;
  description: string | null;
  ordre_affichage: number | null;
  source_ref: string | null;
}

export type FormationElementType =
  | "MODULE"
  | "COURS"
  | "CONTENU_PROGRAMME"
  | "COMPETENCE"
  | "METIER"
  | "DOMAINE_ACTIVITE"
  | "CERTIFICATION"
  | "LANGUE"
  | "MOBILITE"
  | "OUTIL"
  | "OPPORTUNITE"
  | "INFORMATION"
  | "DOCUMENT_INSCRIPTION"
  | "LIEN_PREINSCRIPTION";

export interface FormationElement extends AcademicEntity {
  parcours_id: number | null;
  formation_id: number | null;
  specialisation_id: number | null;
  parent_id: number | null;
  type_element: FormationElementType;
  code: string | null;
  nom: string;
  description: string | null;
  valeur: string | null;
  organisme: string | null;
  ordre_affichage: number | null;
  source_ref: string | null;
}

export type FormationElementScope = "GLOBAL" | "PARCOURS" | "FORMATION" | "SPECIALISATION";

export interface EffectiveFormationElement {
  element: FormationElement;
  scope: FormationElementScope;
}

export interface Tarif extends AcademicEntity {
  parcours_id: number | null;
  formation_id: number | null;
  specialisation_id: number | null;
  frais_inscription: string | number | null;
  mensualite: string | number | null;
  nb_mensualites: number | null;
  langue_enseignement: string | null;
  devise: string;
  annee_universitaire: string | null;
  statut: string;
  remarque: string | null;
  source_ref: string | null;
}

export interface EffectiveTarif {
  parcours_id: number;
  formation_id: number;
  specialisation_id: number | null;
  langue_enseignement: string | null;
  frais_inscription: string | number | null;
  mensualite: string | number | null;
  nb_mensualites: number | null;
  devise: string;
  annee_universitaire: string | null;
  statut: string;
  remarque: string | null;
  source_ref: string | null;
  field_origins: Record<string, FormationElementScope>;
  source_tarif_ids: number[];
}

export interface OrientationRule extends AcademicEntity {
  formation_id: number;
  specialisation_id: number | null;
  code: string;
  nom: string;
  type_regle: string;
  criteres: Record<string, unknown>;
  description: string | null;
  priorite: number;
  source_ref: string | null;
}

export interface Accreditation extends AcademicEntity {
  formation_id: number;
  code: string;
  nom: string;
  organisme: string | null;
  description: string | null;
  date_debut: string | null;
  date_fin: string | null;
  source_ref: string | null;
}

export type AcademicPage = Page<AcademicEntity>;

export interface MutationResponse {
  entity: AcademicEntity | null;
  action: "CREATED" | "UPDATED" | "ACTIVATED" | "DEACTIVATED" | "DELETED" | string;
  indexing_status: "QUEUED" | "NOT_APPLICABLE" | "PUBLISH_FAILED" | string;
  event_ids: string[];
}

export type RagJobState = "QUEUED" | "RUNNING" | "SUCCEEDED" | "RETRYING" | "FAILED";

export interface RagJob {
  event_id: string;
  entity_type: string;
  entity_id: number;
  formation_id: number | null;
  action: string;
  occurred_at: string;
  updated_at: string;
  attempt: number;
  state: RagJobState;
  detail?: string;
}

export interface RagStatusResponse {
  jobs: RagJob[];
}

export interface RagQueueResponse {
  queued: number;
  event_ids: string[];
}

export interface OrientationMatrixFormation {
  formation_id: number;
  formation_code: string;
  formation_name: string;
  parcours_name: string;
  eligibility: "ELIGIBLE" | "NOT_ELIGIBLE" | "UNKNOWN";
  explanation: string;
  rule_codes: string[];
  source_refs: string[];
  recommended: boolean;
}

export interface OrientationMatrixProfile {
  code: string;
  label: string;
  policy: string;
  recommendation: string | null;
  formations: OrientationMatrixFormation[];
}

export interface FormationDataDiagnostic {
  formation_id: number;
  formation_name: string;
  has_admission_rule: boolean;
  has_tariff: boolean;
  specialisation_count: number;
  element_count: number;
  issues: string[];
}

export interface OrientationMatrixResponse {
    profiles: OrientationMatrixProfile[];
    diagnostics: FormationDataDiagnostic[];
}

export interface RagDocumentPreview {
  document_id: string;
  content: string;
  metadata: Record<string, string | number | boolean>;
}

export interface AcademicFormationOverview {
  parcours: Parcours;
  formation: Formation;
  specialisations: Specialisation[];
  elements: FormationElement[];
  effective_elements: EffectiveFormationElement[];
  tarifs: Tarif[];
  effective_tarifs: EffectiveTarif[];
  orientation_rules: OrientationRule[];
  accreditations: Accreditation[];
  rag_documents: RagDocumentPreview[];
}

export interface AcademicOverviewResponse {
  formations: AcademicFormationOverview[];
  global_elements: FormationElement[];
  global_rag_documents: RagDocumentPreview[];
}

export interface AcademicCycleOverviewResponse {
  parcours: Parcours;
  formations: Formation[];
  effective_elements: EffectiveFormationElement[];
  tarifs: Tarif[];
}

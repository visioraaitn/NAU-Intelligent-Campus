import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { adminApi } from "../api/admin";
import { Icon } from "../components/Icon";
import { Modal } from "../components/Modal";
import { AdminBreadcrumb } from "../features/admin/AdminBreadcrumb";
import { AdmissionRuleEditor } from "../features/admin/AdmissionRuleEditor";
import { CrudForm } from "../features/admin/CrudForm";
import {
  CERTIFICATION_GROUPS,
  CONTEXTUAL_ELEMENT_FIELDS,
  INTERNATIONAL_GROUPS,
  OUTCOME_GROUPS,
  PRACTICAL_GROUP,
  PROGRAM_GROUPS,
  type ElementBusinessGroup,
} from "../features/admin/elementViews";
import { entityConfigs } from "../features/admin/entityConfig";
import { useReferenceData } from "../features/admin/useReferenceData";
import type {
  AcademicEntity,
  AcademicFormationOverview,
  AcademicResource,
  EffectiveFormationElement,
  EffectiveTarif,
  FormationElement,
  FormationElementType,
  OrientationRule,
  Tarif,
} from "../types/academic";
import { errorMessage } from "../utils/errors";
import { formatCriteria, formatCurrency, formatLanguage, humanizeEnum } from "../utils/format";

const workspaceSections = [
  ["general", "Général"],
  ["specialisations", "Spécialisations"],
  ["programme", "Programme"],
  ["outcomes", "Compétences & débouchés"],
  ["tarifs", "Tarifs & langues"],
  ["admission", "Admission"],
  ["certifications", "Certifications & reconnaissance"],
  ["international", "International"],
  ["practical", "Informations pratiques"],
] as const;

type WorkspaceSection = (typeof workspaceSections)[number][0];

interface WorkspaceEditor {
  resource: AcademicResource;
  title: string;
  entity: AcademicEntity | null;
  fixedValues?: Record<string, unknown>;
  initialValues?: Record<string, unknown>;
  visibleFields?: string[];
}

function readFormationId(params: URLSearchParams): number | undefined {
  const value = Number(params.get("formation_id"));
  return Number.isInteger(value) && value > 0 ? value : undefined;
}

function readSection(params: URLSearchParams): WorkspaceSection {
  const value = params.get("section");
  return workspaceSections.some(([section]) => section === value)
    ? value as WorkspaceSection
    : "general";
}

function tariffTotal(tarif: Pick<Tarif, "frais_inscription" | "mensualite" | "nb_mensualites"> | EffectiveTarif): number | null {
  const total = Number(tarif.frais_inscription ?? 0)
    + Number(tarif.mensualite ?? 0) * Number(tarif.nb_mensualites ?? 0);
  return Number.isFinite(total) && total > 0 ? total : null;
}

function ScopeSelector({ overview, value, onChange }: { overview: AcademicFormationOverview; value: string; onChange: (value: string) => void }) {
  if (overview.specialisations.length === 0) return null;
  return <label className="toolbar-select workspace-scope-filter"><span>Appliquer à</span><select aria-label="Choisir la spécialisation" value={value} onChange={(event) => onChange(event.target.value)}><option value="">Toute la formation</option>{overview.specialisations.map((item) => <option value={item.id} key={item.id}>{item.nom}</option>)}</select></label>;
}

function ElementCard({
  element,
  specialisation,
  scopeLabel,
  onEdit,
  onAdapt,
}: {
  element: FormationElement;
  specialisation?: string;
  scopeLabel?: string;
  onEdit?: () => void;
  onAdapt?: () => void;
}) {
  return (
    <article className="workspace-fact">
      <div className="workspace-fact__heading">
        <strong>{element.nom}</strong>
        {(onEdit || onAdapt) && (
          <button className="icon-button" type="button" onClick={onEdit ?? onAdapt} aria-label={`${onEdit ? "Modifier" : "Adapter"} ${element.nom}`}>
            <Icon name="edit" />
          </button>
        )}
      </div>
      {(specialisation || scopeLabel) && <span className="scope-badge">{scopeLabel ?? specialisation}</span>}
      {element.description && <p>{element.description}</p>}
      {element.organisme && <small>Organisme : {element.organisme}</small>}
      {!element.actif && <span className="status-badge status-badge--inactive">Inactif</span>}
    </article>
  );
}

function ElementBusinessSections({
  overview,
  groups,
  elements,
  onAdd,
  onEdit,
}: {
  overview: AcademicFormationOverview;
  groups: ElementBusinessGroup[];
  elements: FormationElement[];
  onAdd: (group: ElementBusinessGroup) => void;
  onEdit: (element: FormationElement, group: ElementBusinessGroup) => void;
}) {
  return (
    <div className="workspace-groups">
      {groups.map((group) => {
        const matching = elements.filter((element) => element.type_element === group.type);
        return (
          <section className="workspace-group admin-card" key={group.type} aria-labelledby={`group-${group.type}`}>
            <header>
              <div><h2 id={`group-${group.type}`}>{group.title}</h2><span>{matching.length} élément{matching.length > 1 ? "s" : ""}</span></div>
              <button className="button button--secondary button--compact" type="button" onClick={() => onAdd(group)}>
                <Icon name="plus" /> Ajouter {group.singular === "cours" ? "un" : "une"} {group.singular}
              </button>
            </header>
            {matching.length ? (
              <div className="workspace-fact-grid">
                {matching.map((element) => (
                  <ElementCard
                    key={element.id}
                    element={element}
                    specialisation={overview.specialisations.find((item) => item.id === element.specialisation_id)?.nom}
                    onEdit={() => onEdit(element, group)}
                  />
                ))}
              </div>
            ) : <p className="workspace-empty">{group.emptyMessage}</p>}
          </section>
        );
      })}
    </div>
  );
}

function GeneralSection({ overview, onEdit }: { overview: AcademicFormationOverview; onEdit: () => void }) {
  const { formation } = overview;
  return (
    <section className="workspace-panel admin-card">
      <header><div><h2>Informations générales</h2><p>Identité et organisation académique de la formation.</p></div><button className="button button--secondary button--compact" type="button" onClick={onEdit}><Icon name="edit" /> Modifier</button></header>
      <dl className="workspace-details">
        <div><dt>Nom</dt><dd>{formation.nom}</dd></div>
        <div><dt>Code</dt><dd>{formation.code}</dd></div>
        <div><dt>Diplôme</dt><dd>{formation.intitule_diplome || "Non renseigné"}</dd></div>
        <div><dt>Durée</dt><dd>{formation.duree_annees ? `${formation.duree_annees} ans` : "Non renseignée"}</dd></div>
        <div><dt>Semestres</dt><dd>{formation.nb_semestres ?? "Non renseigné"}</dd></div>
        <div><dt>Crédits</dt><dd>{formation.credits_total ?? "Non renseigné"}</dd></div>
        <div><dt>Langues d’enseignement</dt><dd>{formation.langues_enseignement.map(formatLanguage).join(", ")}</dd></div>
        <div><dt>Statut</dt><dd>{formation.actif ? "Actif" : "Inactif"}</dd></div>
        <div className="workspace-details__wide"><dt>Description</dt><dd>{formation.description || "Aucune description renseignée."}</dd></div>
      </dl>
    </section>
  );
}

function SpecialisationsSection({ overview, onAdd, onEdit }: { overview: AcademicFormationOverview; onAdd: () => void; onEdit: (entity: AcademicEntity) => void }) {
  return (
    <section className="workspace-panel admin-card">
      <header><div><h2>Spécialisations</h2><p>Options rattachées directement à cette formation.</p></div><button className="button button--primary button--compact" type="button" onClick={onAdd}><Icon name="plus" /> Ajouter une spécialisation</button></header>
      {overview.specialisations.length ? (
        <div className="workspace-list">
          {overview.specialisations.map((specialisation) => (
            <article key={specialisation.id}>
              <div><strong>{specialisation.nom}</strong><code>{specialisation.code}</code></div>
              {specialisation.description && <p>{specialisation.description}</p>}
              <button className="icon-button" type="button" onClick={() => onEdit(specialisation)} aria-label={`Modifier ${specialisation.nom}`}><Icon name="edit" /></button>
            </article>
          ))}
        </div>
      ) : <p className="workspace-empty">Aucune spécialisation n’est définie pour cette formation.</p>}
    </section>
  );
}

function TariffsSection({ overview, specialisationId, onAdd, onEdit }: { overview: AcademicFormationOverview; specialisationId: string; onAdd: () => void; onEdit: (entity: AcademicEntity) => void }) {
  const effective = overview.effective_tarifs.filter((tarif) => String(tarif.specialisation_id ?? "") === specialisationId);
  const components = overview.tarifs.filter((tarif) => String(tarif.specialisation_id ?? "") === specialisationId);
  return (
    <section className="workspace-panel admin-card">
      <header><div><h2>Tarifs & langues</h2><p>Tarifs existants, distingués par langue d’enseignement.</p></div><button className="button button--primary button--compact" type="button" onClick={onAdd}><Icon name="plus" /> Ajouter un tarif</button></header>
      {effective.length ? (
        <div className="workspace-tariffs">
          {effective.map((tarif) => {
            const total = tariffTotal(tarif);
            return (
              <article key={`${tarif.specialisation_id ?? "formation"}-${tarif.langue_enseignement ?? "commun"}`}>
                <header><strong>{formatLanguage(tarif.langue_enseignement)}</strong><span>{humanizeEnum(tarif.statut)}</span></header>
                <dl>
                  <div><dt>Inscription</dt><dd>{formatCurrency(tarif.frais_inscription, tarif.devise)}{tarif.field_origins.frais_inscription === "PARCOURS" && <small>Hérité du {overview.parcours.nom}</small>}</dd></div>
                  <div><dt>Mensualité</dt><dd>{formatCurrency(tarif.mensualite, tarif.devise)}{tarif.nb_mensualites ? ` × ${tarif.nb_mensualites}` : ""}</dd></div>
                  <div><dt>Total indicatif</dt><dd>{total === null ? "—" : formatCurrency(total, tarif.devise)}</dd></div>
                </dl>
              </article>
            );
          })}
        </div>
      ) : <p className="workspace-empty">Aucun tarif n’est renseigné.</p>}
      {components.length > 0 && <div className="workspace-components"><strong>Composants propres à cette portée</strong>{components.map((tarif) => <button type="button" key={tarif.id} onClick={() => onEdit(tarif)}><span>{formatLanguage(tarif.langue_enseignement)} · {formatCurrency(tarif.mensualite ?? tarif.frais_inscription, tarif.devise)}</span><Icon name="edit" /></button>)}</div>}
    </section>
  );
}

function AdmissionSection({ overview, specialisationId, onAdd, onEdit }: { overview: AcademicFormationOverview; specialisationId: string; onAdd: () => void; onEdit: (rule: OrientationRule) => void }) {
  const rules = overview.orientation_rules.filter((rule) => String(rule.specialisation_id ?? "") === specialisationId);
  return (
    <section className="workspace-panel admin-card">
      <header><div><h2>Admission</h2><p>Éligibilité et recommandations présentées sous une forme lisible.</p></div><button className="button button--primary button--compact" type="button" onClick={onAdd}><Icon name="plus" /> Ajouter une règle</button></header>
      {rules.length ? (
        <div className="workspace-rules">
          {rules.map((rule) => (
            <article key={rule.id}><div><strong>{rule.nom}</strong><span className={`rule-kind rule-kind--${rule.type_regle.toLowerCase()}`}>{rule.type_regle === "ADMISSION" ? "Admission — éligibilité" : "Recommandation — conseil"}</span></div><p>{formatCriteria(rule.criteres)}</p>{rule.description && <small>{rule.description}</small>}<button className="icon-button" type="button" onClick={() => onEdit(rule)} aria-label={`Modifier ${rule.nom}`}><Icon name="edit" /></button></article>
          ))}
        </div>
      ) : <p className="workspace-empty">Aucune règle d’admission active n’est renseignée.</p>}
    </section>
  );
}

function RecognitionSection({ overview, elements, onAddElement, onEditElement, onAddAccreditation, onEditAccreditation }: {
  overview: AcademicFormationOverview;
  elements: FormationElement[];
  onAddElement: (group: ElementBusinessGroup) => void;
  onEditElement: (element: FormationElement, group: ElementBusinessGroup) => void;
  onAddAccreditation: () => void;
  onEditAccreditation: (entity: AcademicEntity) => void;
}) {
  return (
    <>
      <ElementBusinessSections overview={overview} groups={CERTIFICATION_GROUPS} elements={elements} onAdd={onAddElement} onEdit={onEditElement} />
      <section className="workspace-panel admin-card">
        <header><div><h2>Accréditation du programme</h2><p>Reconnaissances officielles de la formation.</p></div><button className="button button--secondary button--compact" type="button" onClick={onAddAccreditation}><Icon name="plus" /> Ajouter</button></header>
        {overview.accreditations.length ? <div className="workspace-list">{overview.accreditations.map((item) => <article key={item.id}><div><strong>{item.nom}</strong><span>{item.organisme || "Organisme non renseigné"}</span></div>{item.description && <p>{item.description}</p>}<button className="icon-button" type="button" onClick={() => onEditAccreditation(item)} aria-label={`Modifier ${item.nom}`}><Icon name="edit" /></button></article>)}</div> : <p className="workspace-empty">Aucune accréditation n’est rattachée à cette formation.</p>}
      </section>
    </>
  );
}

function PracticalSection({ overview, onAdd, onEdit, onAdapt }: {
  overview: AcademicFormationOverview;
  onAdd: () => void;
  onEdit: (element: FormationElement) => void;
  onAdapt: (item: EffectiveFormationElement) => void;
}) {
  const items = overview.effective_elements.filter((item) => item.element.type_element === "INFORMATION");
  return (
    <section className="workspace-panel admin-card">
      <header><div><h2>Informations pratiques</h2><p>Informations propres à la formation ou héritées automatiquement.</p></div><button className="button button--primary button--compact" type="button" onClick={onAdd}><Icon name="plus" /> Ajouter une information</button></header>
      {items.length ? <div className="workspace-fact-grid workspace-fact-grid--padded">{items.map((item) => {
        const scopeLabel = item.scope === "PARCOURS" ? `Hérité du ${overview.parcours.nom}` : item.scope === "GLOBAL" ? "Information globale IIT" : item.scope === "SPECIALISATION" ? "Information de spécialisation" : "Information de la formation";
        return <ElementCard key={`${item.scope}-${item.element.id}`} element={item.element} scopeLabel={scopeLabel} onEdit={item.scope === "FORMATION" ? () => onEdit(item.element) : undefined} onAdapt={item.scope !== "FORMATION" ? () => onAdapt(item) : undefined} />;
      })}</div> : <p className="workspace-empty">{PRACTICAL_GROUP.emptyMessage}</p>}
    </section>
  );
}

export function AcademicOverviewPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const formationId = readFormationId(searchParams);
  const activeSection = readSection(searchParams);
  const [data, setData] = useState<Awaited<ReturnType<typeof adminApi.academicOverview>> | null>(null);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [editor, setEditor] = useState<WorkspaceEditor | null>(null);
  const [scopeSpecialisation, setScopeSpecialisation] = useState("");
  const [ruleEditor, setRuleEditor] = useState<OrientationRule | null | undefined>(undefined);
  const references = useReferenceData(entityConfigs.elements, ["parcours", "formations", "specialisations"]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await adminApi.academicOverview(includeInactive, formationId));
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setLoading(false);
    }
  }, [formationId, includeInactive]);

  useEffect(() => { void load(); }, [load]);

  const overview = formationId ? data?.formations[0] ?? null : null;
  const programmeElements = useMemo(() => {
    if (!overview) return [];
    const allowed = new Set<FormationElementType>(PROGRAM_GROUPS.map((group) => group.type));
    return overview.elements.filter((element) => allowed.has(element.type_element) && String(element.specialisation_id ?? "") === scopeSpecialisation);
  }, [overview, scopeSpecialisation]);

  const openElementEditor = (group: ElementBusinessGroup, element: FormationElement | null = null, initialValues?: Record<string, unknown>, fixedValues?: Record<string, unknown>) => {
    if (!overview) return;
    setEditor({
      resource: "elements",
      title: element ? `Modifier ${group.singular}` : `Ajouter ${group.singular}`,
      entity: element,
      initialValues,
      fixedValues: fixedValues ?? {
        formation_id: overview.formation.id,
        type_element: group.type,
      },
      visibleFields: CONTEXTUAL_ELEMENT_FIELDS,
    });
  };

  const saveEditor = async (payload: Record<string, unknown>) => {
    if (!editor) return;
    if (editor.entity) await adminApi.update(editor.resource, editor.entity.id, payload);
    else await adminApi.create(editor.resource, payload);
    setEditor(null);
    setNotice("Modification enregistrée.");
    await load();
  };

  const setSection = (section: WorkspaceSection) => {
    const next = new URLSearchParams(searchParams);
    if (section === "general") next.delete("section");
    else next.set("section", section);
    setSearchParams(next, { replace: true });
  };

  if (!formationId) {
    return (
      <section className="admin-page" aria-labelledby="overview-title">
        <header className="page-heading"><div><span className="eyebrow">Catalogue académique</span><h1 id="overview-title">Fiches formations</h1><p>Sélectionnez une formation pour ouvrir son espace de gestion.</p></div></header>
        {error && <div className="alert alert--error" role="alert">{error}</div>}
        {loading && !data ? <div className="table-loading"><span className="spinner" /> Chargement…</div> : <div className="workspace-formation-picker">{data?.formations.map((item) => <Link className="admin-card" to={`/admin/academic-overview?formation_id=${item.formation.id}`} key={item.formation.id}><span>{item.parcours.nom}</span><strong>{item.formation.nom}</strong><small>{item.formation.code}</small><Icon name="chevron-right" /></Link>)}</div>}
      </section>
    );
  }

  return (
    <section className="admin-page workspace" aria-labelledby="workspace-title">
      {overview && <AdminBreadcrumb items={[{ label: "Catalogue académique", to: "/admin/catalogue" }, { label: overview.parcours.nom, to: `/admin/cycle-workspace?parcours_id=${overview.parcours.id}&section=formations` }, { label: overview.formation.nom }]} />}
      {error && <div className="alert alert--error" role="alert">{error}</div>}
      {notice && <div className="alert alert--success" role="status">{notice}</div>}
      {loading && !overview && <div className="table-loading"><span className="spinner" /> Chargement de la formation…</div>}
      {overview && <>
        <header className="workspace-hero admin-card">
          <div><span>{overview.parcours.nom}</span><h1 id="workspace-title">{overview.formation.nom}</h1><p>{[overview.formation.duree_annees ? `${overview.formation.duree_annees} ans` : null, overview.formation.credits_total ? `${overview.formation.credits_total} crédits` : null, overview.formation.langues_enseignement.map(formatLanguage).join(", ")].filter(Boolean).join(" • ")}</p></div>
          <div className="workspace-hero__actions"><span className={`status-badge ${overview.formation.actif ? "status-badge--active" : "status-badge--inactive"}`}>{overview.formation.actif ? "Actif" : "Inactif"}</span><label className="checkbox-field checkbox-field--inline"><input type="checkbox" checked={includeInactive} onChange={(event) => setIncludeInactive(event.target.checked)} /><span>Voir les inactifs</span></label></div>
        </header>
        <nav className="workspace-tabs" aria-label="Sections de la formation">{workspaceSections.map(([section, label]) => <button className={activeSection === section ? "active" : ""} type="button" key={section} onClick={() => setSection(section)}>{label}</button>)}</nav>
        <div className="workspace-content">
          {activeSection === "general" && <GeneralSection overview={overview} onEdit={() => setEditor({ resource: "formations", title: "Modifier la formation", entity: overview.formation })} />}
          {activeSection === "specialisations" && <SpecialisationsSection overview={overview} onAdd={() => setEditor({ resource: "specialisations", title: "Ajouter une spécialisation", entity: null, fixedValues: { formation_id: overview.formation.id }, visibleFields: ["code", "nom", "ordre_affichage", "description", "source_ref", "actif"] })} onEdit={(entity) => setEditor({ resource: "specialisations", title: "Modifier la spécialisation", entity, fixedValues: { formation_id: overview.formation.id }, visibleFields: ["code", "nom", "ordre_affichage", "description", "source_ref", "actif"] })} />}
          {activeSection === "programme" && <section className="workspace-programme"><ScopeSelector overview={overview} value={scopeSpecialisation} onChange={setScopeSpecialisation} /><ElementBusinessSections overview={overview} groups={PROGRAM_GROUPS} elements={programmeElements} onAdd={(group) => openElementEditor(group, null, undefined, { formation_id: overview.formation.id, specialisation_id: scopeSpecialisation ? Number(scopeSpecialisation) : null, type_element: group.type })} onEdit={(element, group) => openElementEditor(group, element)} /></section>}
          {activeSection === "outcomes" && <section className="workspace-programme"><ScopeSelector overview={overview} value={scopeSpecialisation} onChange={setScopeSpecialisation} /><ElementBusinessSections overview={overview} groups={OUTCOME_GROUPS} elements={overview.elements.filter((element) => String(element.specialisation_id ?? "") === scopeSpecialisation)} onAdd={(group) => openElementEditor(group, null, undefined, { formation_id: overview.formation.id, specialisation_id: scopeSpecialisation ? Number(scopeSpecialisation) : null, type_element: group.type })} onEdit={(element, group) => openElementEditor(group, element)} /></section>}
          {activeSection === "tarifs" && <section className="workspace-programme"><ScopeSelector overview={overview} value={scopeSpecialisation} onChange={setScopeSpecialisation} /><TariffsSection overview={overview} specialisationId={scopeSpecialisation} onAdd={() => setEditor({ resource: "tarifs", title: "Ajouter un tarif", entity: null, fixedValues: { parcours_id: null, formation_id: overview.formation.id, specialisation_id: scopeSpecialisation ? Number(scopeSpecialisation) : null }, visibleFields: entityConfigs.tarifs.fields.map((field) => field.name).filter((name) => !["parcours_id", "formation_id", "specialisation_id"].includes(name)) })} onEdit={(entity) => setEditor({ resource: "tarifs", title: "Modifier le tarif", entity, fixedValues: { parcours_id: null, formation_id: overview.formation.id, specialisation_id: scopeSpecialisation ? Number(scopeSpecialisation) : null }, visibleFields: entityConfigs.tarifs.fields.map((field) => field.name).filter((name) => !["parcours_id", "formation_id", "specialisation_id"].includes(name)) })} /></section>}
          {activeSection === "admission" && <section className="workspace-programme"><ScopeSelector overview={overview} value={scopeSpecialisation} onChange={setScopeSpecialisation} /><AdmissionSection overview={overview} specialisationId={scopeSpecialisation} onAdd={() => setRuleEditor(null)} onEdit={setRuleEditor} /></section>}
          {activeSection === "certifications" && <RecognitionSection overview={overview} elements={overview.elements} onAddElement={(group) => openElementEditor(group)} onEditElement={(element, group) => openElementEditor(group, element)} onAddAccreditation={() => setEditor({ resource: "accreditations", title: "Ajouter une accréditation", entity: null, fixedValues: { formation_id: overview.formation.id }, visibleFields: entityConfigs.accreditations.fields.map((field) => field.name).filter((name) => name !== "formation_id") })} onEditAccreditation={(entity) => setEditor({ resource: "accreditations", title: "Modifier l’accréditation", entity, fixedValues: { formation_id: overview.formation.id }, visibleFields: entityConfigs.accreditations.fields.map((field) => field.name).filter((name) => name !== "formation_id") })} />}
          {activeSection === "international" && <ElementBusinessSections overview={overview} groups={INTERNATIONAL_GROUPS} elements={overview.elements} onAdd={(group) => openElementEditor(group)} onEdit={(element, group) => openElementEditor(group, element)} />}
          {activeSection === "practical" && <PracticalSection overview={overview} onAdd={() => openElementEditor(PRACTICAL_GROUP)} onEdit={(element) => openElementEditor(PRACTICAL_GROUP, element)} onAdapt={(item) => openElementEditor(PRACTICAL_GROUP, null, item.element, { parcours_id: null, formation_id: overview.formation.id, specialisation_id: null, type_element: "INFORMATION", code: item.element.code })} />}
        </div>
      </>}
      <Modal open={editor !== null} title={editor?.title ?? "Modifier"} description="Le contexte de la formation et le type de donnée sont appliqués automatiquement." onClose={() => setEditor(null)} size="large">
        {editor && <CrudForm key={`${editor.resource}-${editor.entity?.id ?? "new"}-${editor.title}`} config={entityConfigs[editor.resource]} entity={editor.entity} references={references.data} referencesLoading={references.loading} referencesError={references.error} initialValues={editor.initialValues} fixedValues={editor.fixedValues} visibleFields={editor.visibleFields} onCancel={() => setEditor(null)} onSubmit={saveEditor} />}
      </Modal>
      <Modal open={ruleEditor !== undefined} title={ruleEditor ? "Modifier la règle" : "Ajouter une règle"} description="Admission et recommandation restent distinctes. Les critères avancés sont conservés." onClose={() => setRuleEditor(undefined)} size="large">
        {ruleEditor !== undefined && <AdmissionRuleEditor formationId={overview?.formation.id ?? 0} rule={ruleEditor} specialisations={overview?.specialisations ?? []} fixedSpecialisationId={scopeSpecialisation ? Number(scopeSpecialisation) : undefined} onCancel={() => setRuleEditor(undefined)} onSaved={async () => { setRuleEditor(undefined); setNotice("Règle enregistrée."); await load(); }} />}
      </Modal>
    </section>
  );
}

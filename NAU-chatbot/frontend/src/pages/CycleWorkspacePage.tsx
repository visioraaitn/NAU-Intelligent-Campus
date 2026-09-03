import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { adminApi } from "../api/admin";
import { Icon } from "../components/Icon";
import { Modal } from "../components/Modal";
import { AdminBreadcrumb } from "../features/admin/AdminBreadcrumb";
import { CrudForm } from "../features/admin/CrudForm";
import { CycleFormationList } from "../features/admin/CycleFormationList";
import { CycleRegistrationPanel } from "../features/admin/CycleRegistrationPanel";
import { entityConfigs } from "../features/admin/entityConfig";
import { readPositiveId, updateQueryParams } from "../features/admin/hierarchyQuery";
import { useReferenceData } from "../features/admin/useReferenceData";
import type { AcademicEntity, AcademicResource, Formation } from "../types/academic";
import { errorMessage } from "../utils/errors";

type CycleSection = "general" | "formations" | "inscription";

interface Editor {
  resource: Extract<AcademicResource, "parcours" | "formations">;
  entity: AcademicEntity | null;
  title: string;
}

const sections: Array<[CycleSection, string]> = [["general", "Général"], ["formations", "Formations"], ["inscription", "Inscription"]];

export function CycleWorkspacePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const cycleId = readPositiveId(searchParams, "parcours_id");
  const requestedSection = searchParams.get("section");
  const activeSection: CycleSection = sections.some(([section]) => section === requestedSection) ? requestedSection as CycleSection : "general";
  const [overview, setOverview] = useState<Awaited<ReturnType<typeof adminApi.cycleOverview>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [editor, setEditor] = useState<Editor | null>(null);
  const references = useReferenceData(entityConfigs.formations, ["parcours"]);

  const load = useCallback(async () => {
    if (!cycleId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setOverview(await adminApi.cycleOverview(Number(cycleId), true));
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setLoading(false);
    }
  }, [cycleId]);

  useEffect(() => { void load(); }, [load]);

  const setSection = (section: CycleSection) => {
    setSearchParams(updateQueryParams(searchParams, { section: section === "general" ? null : section }), { replace: true });
  };

  const saveEditor = async (payload: Record<string, unknown>) => {
    if (!editor) return;
    if (editor.entity) await adminApi.update(editor.resource, editor.entity.id, payload);
    else await adminApi.create(editor.resource, payload);
    setEditor(null);
    setNotice("Modification enregistrée.");
    await load();
  };

  if (!cycleId) return <section className="admin-page"><div className="alert alert--error">Cycle académique non indiqué.</div><Link className="button button--secondary" to="/admin/catalogue">Retour au catalogue</Link></section>;

  return (
    <section className="admin-page workspace cycle-workspace" aria-labelledby="cycle-workspace-title">
      <AdminBreadcrumb items={[{ label: "Catalogue académique", to: "/admin/catalogue" }, { label: overview?.parcours.nom ?? "Cycle académique" }]} />
      {error && <div className="alert alert--error" role="alert">{error}</div>}
      {notice && <div className="alert alert--success" role="status">{notice}</div>}
      {loading && !overview && <div className="table-loading"><span className="spinner" /> Chargement du cycle…</div>}
      {overview && <>
        <header className="workspace-hero admin-card">
          <div><span>Cycle académique</span><h1 id="cycle-workspace-title">{overview.parcours.nom}</h1><p>{overview.parcours.duree_annees ? `${overview.parcours.duree_annees} ans` : "Durée non renseignée"} • {overview.parcours.actif ? "Actif" : "Inactif"}</p></div>
          <Link className="button button--secondary button--compact" to={`/admin/catalogue?configure=${overview.parcours.id}`}><Icon name="edit" /> Continuer la configuration</Link>
        </header>
        <nav className="workspace-tabs" aria-label="Sections du cycle académique">{sections.map(([section, label]) => <button className={activeSection === section ? "active" : ""} type="button" key={section} onClick={() => setSection(section)}>{label}</button>)}</nav>
        <div className="workspace-content">
          {activeSection === "general" && <section className="workspace-panel admin-card"><header><div><h2>Informations générales</h2><p>Identité et statut du cycle académique.</p></div><button className="button button--secondary button--compact" type="button" onClick={() => setEditor({ resource: "parcours", entity: overview.parcours, title: "Modifier le cycle académique" })}><Icon name="edit" /> Modifier</button></header><dl className="workspace-details"><div><dt>Nom</dt><dd>{overview.parcours.nom}</dd></div><div><dt>Code</dt><dd>{overview.parcours.code}</dd></div><div><dt>Durée</dt><dd>{overview.parcours.duree_annees ? `${overview.parcours.duree_annees} ans` : "—"}</dd></div><div><dt>Statut</dt><dd>{overview.parcours.actif ? "Actif" : "Inactif"}</dd></div><div className="workspace-details__wide"><dt>Description</dt><dd>{overview.parcours.description || "Aucune description renseignée."}</dd></div></dl></section>}
          {activeSection === "formations" && <CycleFormationList overview={overview} onAdd={() => setEditor({ resource: "formations", entity: null, title: "Ajouter une formation" })} onEdit={(formation: Formation) => setEditor({ resource: "formations", entity: formation, title: "Modifier la formation" })} />}
          {activeSection === "inscription" && <CycleRegistrationPanel overview={overview} onChanged={load} />}
        </div>
      </>}
      <Modal open={editor !== null} title={editor?.title ?? "Modifier"} description={editor?.resource === "formations" ? "Le cycle académique est appliqué automatiquement." : undefined} onClose={() => setEditor(null)} size="large">
        {editor && overview && <CrudForm config={entityConfigs[editor.resource]} entity={editor.entity} references={references.data} referencesLoading={references.loading} referencesError={references.error} fixedValues={editor.resource === "formations" ? { parcours_id: overview.parcours.id } : undefined} visibleFields={editor.resource === "formations" ? entityConfigs.formations.fields.map((field) => field.name).filter((name) => name !== "parcours_id") : undefined} onCancel={() => setEditor(null)} onSubmit={saveEditor} />}
      </Modal>
    </section>
  );
}

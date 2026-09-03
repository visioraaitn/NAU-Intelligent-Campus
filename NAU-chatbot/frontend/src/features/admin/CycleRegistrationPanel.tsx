import { useState } from "react";
import { adminApi } from "../../api/admin";
import { Icon } from "../../components/Icon";
import { Modal } from "../../components/Modal";
import type { AcademicCycleOverviewResponse, AcademicEntity, EffectiveFormationElement, FormationElement } from "../../types/academic";
import { CrudForm } from "./CrudForm";
import { entityConfigs } from "./entityConfig";
import { useReferenceData } from "./useReferenceData";

interface ElementEditor {
  title: string;
  entity: FormationElement | null;
  initialValues?: Record<string, unknown>;
  fixedValues: Record<string, unknown>;
  visibleFields: string[];
}

const elementFields = ["code", "nom", "valeur", "ordre_affichage", "source_ref", "actif"];
const documentFields = ["code", "nom", "ordre_affichage", "source_ref", "actif"];

function byOrder(left: EffectiveFormationElement, right: EffectiveFormationElement) {
  return (left.element.ordre_affichage ?? 10_000) - (right.element.ordre_affichage ?? 10_000);
}

export function CycleRegistrationPanel({ overview, onChanged }: { overview: AcademicCycleOverviewResponse; onChanged: () => Promise<void> }) {
  const references = useReferenceData(entityConfigs.elements, ["parcours", "formations", "specialisations"]);
  const [elementEditor, setElementEditor] = useState<ElementEditor | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const links = overview.effective_elements.filter((item) => item.element.type_element === "LIEN_PREINSCRIPTION").sort(byOrder);
  const documents = overview.effective_elements.filter((item) => item.element.type_element === "DOCUMENT_INSCRIPTION").sort(byOrder);

  const openElement = (item: EffectiveFormationElement | null, type: "LIEN_PREINSCRIPTION" | "DOCUMENT_INSCRIPTION") => {
    const inherited = item && item.scope !== "PARCOURS";
    setElementEditor({
      title: item ? (inherited ? "Adapter pour ce cycle" : "Modifier") : type === "LIEN_PREINSCRIPTION" ? "Ajouter le lien de préinscription" : "Ajouter un document",
      entity: item && !inherited ? item.element : null,
      initialValues: inherited ? item.element : undefined,
      fixedValues: {
        parcours_id: overview.parcours.id,
        formation_id: null,
        specialisation_id: null,
        type_element: type,
        ...(inherited ? { code: item.element.code } : {}),
      },
      visibleFields: (type === "LIEN_PREINSCRIPTION" ? elementFields : documentFields).filter(
        (field) => !inherited || field !== "code",
      ),
    });
  };

  const saveElement = async (payload: Record<string, unknown>) => {
    if (!elementEditor) return;
    if (elementEditor.entity) await adminApi.update("elements", elementEditor.entity.id, payload);
    else await adminApi.create("elements", payload);
    setElementEditor(null);
    setNotice("Informations d’inscription enregistrées.");
    await onChanged();
  };

  const moveDocument = async (item: EffectiveFormationElement, direction: -1 | 1) => {
    const index = documents.findIndex((document) => document.element.id === item.element.id);
    const adjacent = documents[index + direction];
    if (!adjacent || item.scope !== "PARCOURS" || adjacent.scope !== "PARCOURS") return;
    setBusyId(item.element.id);
    const currentOrder = item.element.ordre_affichage ?? (index + 1) * 10;
    const adjacentOrder = adjacent.element.ordre_affichage ?? (index + direction + 1) * 10;
    await Promise.all([
      adminApi.update("elements", item.element.id, { ordre_affichage: adjacentOrder }),
      adminApi.update("elements", adjacent.element.id, { ordre_affichage: currentOrder }),
    ]);
    setBusyId(null);
    await onChanged();
  };

  const removeDocument = async (item: EffectiveFormationElement) => {
    if (item.scope !== "PARCOURS" || !window.confirm(`Supprimer « ${item.element.nom} » des pièces demandées ?`)) return;
    setBusyId(item.element.id);
    await adminApi.remove("elements", item.element.id);
    setBusyId(null);
    setNotice("Document supprimé.");
    await onChanged();
  };

  return (
    <div className="cycle-registration">
      {notice && <div className="alert alert--success" role="status">{notice}</div>}
      <section className="workspace-panel admin-card">
        <header><div><h2>Préinscription</h2><p>Lien utilisé après la décision d’inscription.</p></div><button className="button button--secondary button--compact" type="button" onClick={() => openElement(links[0] ?? null, "LIEN_PREINSCRIPTION")}><Icon name={links.length ? "edit" : "plus"} /> {links.length ? "Modifier" : "Ajouter"}</button></header>
        {links.length ? links.map((item) => <div className="registration-link" key={`${item.scope}-${item.element.id}`}><a href={item.element.valeur ?? "#"} target="_blank" rel="noreferrer">{item.element.valeur || item.element.nom}</a><small>{item.scope === "PARCOURS" ? "Spécifique à ce cycle" : "Information globale — adaptable pour ce cycle"}</small></div>) : <p className="workspace-empty">Aucun lien de préinscription n’est renseigné.</p>}
      </section>

      <section className="workspace-panel admin-card">
        <header><div><h2>Pièces à fournir</h2><p>Documents communs demandés pour ce cycle académique.</p></div><button className="button button--primary button--compact" type="button" onClick={() => openElement(null, "DOCUMENT_INSCRIPTION")}><Icon name="plus" /> Ajouter un document</button></header>
        {documents.length ? <ol className="registration-documents">{documents.map((item, index) => <li key={`${item.scope}-${item.element.id}`}><span><strong>{item.element.nom}</strong><small>{item.scope === "PARCOURS" ? "Cycle académique" : "Information héritée"}</small></span><div><button className="icon-button" type="button" disabled={index === 0 || busyId === item.element.id || item.scope !== "PARCOURS"} onClick={() => void moveDocument(item, -1)} aria-label={`Monter ${item.element.nom}`}><Icon name="chevron-left" /></button><button className="icon-button" type="button" disabled={index === documents.length - 1 || busyId === item.element.id || item.scope !== "PARCOURS"} onClick={() => void moveDocument(item, 1)} aria-label={`Descendre ${item.element.nom}`}><Icon name="chevron-right" /></button><button className="icon-button" type="button" onClick={() => openElement(item, "DOCUMENT_INSCRIPTION")} aria-label={`Modifier ${item.element.nom}`}><Icon name="edit" /></button>{item.scope === "PARCOURS" && <button className="icon-button icon-button--danger" type="button" onClick={() => void removeDocument(item)} aria-label={`Supprimer ${item.element.nom}`}><Icon name="trash" /></button>}</div></li>)}</ol> : <p className="workspace-empty">Aucune pièce d’inscription n’est renseignée.</p>}
      </section>

      <Modal open={elementEditor !== null} title={elementEditor?.title ?? "Modifier"} description="Cette information est enregistrée au niveau du cycle académique." onClose={() => setElementEditor(null)} size="large">
        {elementEditor && <CrudForm config={entityConfigs.elements} entity={elementEditor.entity as AcademicEntity | null} references={references.data} referencesLoading={references.loading} referencesError={references.error} initialValues={elementEditor.initialValues} fixedValues={elementEditor.fixedValues} visibleFields={elementEditor.visibleFields} onCancel={() => setElementEditor(null)} onSubmit={saveElement} />}
      </Modal>
    </div>
  );
}

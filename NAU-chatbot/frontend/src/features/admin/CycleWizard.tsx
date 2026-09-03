import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { adminApi } from "../../api/admin";
import { Icon } from "../../components/Icon";
import { Modal } from "../../components/Modal";
import type { AcademicEntity, Formation } from "../../types/academic";
import { errorMessage } from "../../utils/errors";
import { CrudForm } from "./CrudForm";
import { CycleFormationList } from "./CycleFormationList";
import { CycleRegistrationPanel } from "./CycleRegistrationPanel";
import { entityConfigs } from "./entityConfig";
import { useReferenceData } from "./useReferenceData";

interface CycleWizardProps {
  initialCycleId?: number;
  onClose: () => void;
  onFinished: (cycleId: number) => void;
}

const steps = ["Cycle", "Formations", "Inscription", "Vérification"];

export function CycleWizard({ initialCycleId, onClose, onFinished }: CycleWizardProps) {
  const [cycleId, setCycleId] = useState(initialCycleId ?? 0);
  const [step, setStep] = useState(initialCycleId ? 2 : 1);
  const [overview, setOverview] = useState<Awaited<ReturnType<typeof adminApi.cycleOverview>> | null>(null);
  const [formationEditor, setFormationEditor] = useState<Formation | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const references = useReferenceData(entityConfigs.formations, ["parcours"]);

  const load = useCallback(async () => {
    if (!cycleId) return;
    try {
      const result = await adminApi.cycleOverview(cycleId, true);
      setOverview(result);
      if (initialCycleId && step === 2) {
        const hasRegistration = result.effective_elements.some((item) => ["LIEN_PREINSCRIPTION", "DOCUMENT_INSCRIPTION"].includes(item.element.type_element)) || result.tarifs.length > 0;
        setStep(result.formations.length === 0 ? 2 : hasRegistration ? 4 : 3);
      }
    } catch (reason) {
      setError(errorMessage(reason));
    }
  }, [cycleId, initialCycleId, step]);

  useEffect(() => { void load(); }, [load]);

  const saveCycle = async (payload: Record<string, unknown>) => {
    const result = cycleId ? await adminApi.update("parcours", cycleId, payload) : await adminApi.create("parcours", payload);
    const persistedId = cycleId || Number(result.entity?.id);
    if (!persistedId) throw new Error("Le cycle a été enregistré sans identifiant exploitable.");
    setCycleId(persistedId);
    setStep(2);
  };

  const saveFormation = async (payload: Record<string, unknown>) => {
    if (formationEditor) await adminApi.update("formations", formationEditor.id, payload);
    else await adminApi.create("formations", payload);
    setFormationEditor(undefined);
    await load();
  };

  const missing = overview ? [
    overview.formations.length === 0 ? "Aucune formation" : null,
    overview.effective_elements.some((item) => item.element.type_element === "LIEN_PREINSCRIPTION") ? null : "Lien de préinscription non renseigné",
    overview.effective_elements.some((item) => item.element.type_element === "DOCUMENT_INSCRIPTION") ? null : "Pièces d’inscription non renseignées",
    overview.tarifs.length ? null : "Frais commun non renseigné",
  ].filter(Boolean) as string[] : [];

  return (
    <Modal open title={cycleId ? "Configurer le cycle académique" : "Nouveau cycle académique"} description="Chaque étape est enregistrée immédiatement. Vous pouvez reprendre la configuration plus tard." onClose={onClose} size="large">
      <div className="cycle-wizard">
        <ol className="wizard-steps">{steps.map((label, index) => <li className={step === index + 1 ? "active" : step > index + 1 ? "done" : ""} key={label}><span>{index + 1}</span>{label}</li>)}</ol>
        {error && <div className="alert alert--error" role="alert">{error}</div>}
        {step === 1 && <section><h3>Informations du cycle</h3><CrudForm config={entityConfigs.parcours} entity={overview?.parcours ?? null} references={{}} referencesLoading={false} referencesError={null} onCancel={onClose} onSubmit={saveCycle} submitLabel="Enregistrer et continuer" /></section>}
        {step === 2 && overview && <section><div className="wizard-section-heading"><div><h3>Formations du cycle</h3><p>Le cycle est déjà enregistré. Ajoutez maintenant ses formations.</p></div></div>{formationEditor === undefined ? <><CycleFormationList overview={overview} onAdd={() => setFormationEditor(null)} onEdit={setFormationEditor} /><div className="wizard-actions"><button className="button button--ghost" type="button" onClick={() => setStep(1)}>Retour</button><button className="button button--primary" type="button" onClick={() => setStep(3)}>Continuer</button></div></> : <div className="wizard-inline-form"><h4>{formationEditor ? `Modifier ${formationEditor.nom}` : "Ajouter une formation"}</h4><CrudForm config={entityConfigs.formations} entity={formationEditor as AcademicEntity | null} references={references.data} referencesLoading={references.loading} referencesError={references.error} fixedValues={{ parcours_id: overview.parcours.id }} visibleFields={entityConfigs.formations.fields.map((field) => field.name).filter((name) => name !== "parcours_id")} onCancel={() => setFormationEditor(undefined)} onSubmit={saveFormation} />{formationEditor && <Link className="button button--ghost" to={`/admin/academic-overview?formation_id=${formationEditor.id}`}>Configurer dans son workspace <Icon name="external" /></Link>}</div>}</section>}
        {step === 3 && overview && <section><div className="wizard-section-heading"><div><h3>Inscription commune</h3><p>Cette étape est facultative et s’applique à toutes les formations du cycle.</p></div></div><CycleRegistrationPanel overview={overview} onChanged={load} /><div className="wizard-actions"><button className="button button--ghost" type="button" onClick={() => setStep(2)}>Retour</button><button className="button button--primary" type="button" onClick={() => setStep(4)}>Continuer</button></div></section>}
        {step === 4 && overview && <section className="wizard-review"><h3>Vérification</h3><dl><div><dt>Cycle académique</dt><dd>{overview.parcours.nom}</dd></div><div><dt>Formations</dt><dd>{overview.formations.length}</dd></div><div><dt>Inscription commune</dt><dd>{missing.length ? "À compléter" : "Configurée"}</dd></div></dl>{missing.length ? <div className="wizard-missing"><strong>Éléments manquants</strong><ul>{missing.map((item) => <li key={item}>{item}</li>)}</ul><p>Ces éléments sont facultatifs et pourront être complétés plus tard.</p></div> : <div className="alert alert--success">La configuration principale est complète.</div>}<div className="wizard-actions"><button className="button button--ghost" type="button" onClick={() => setStep(3)}>Retour</button><button className="button button--primary" type="button" onClick={() => onFinished(cycleId)}>Terminer</button></div></section>}
      </div>
    </Modal>
  );
}

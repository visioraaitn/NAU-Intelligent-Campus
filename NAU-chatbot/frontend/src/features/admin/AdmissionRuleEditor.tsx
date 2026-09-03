import { type FormEvent, useState } from "react";
import { adminApi } from "../../api/admin";
import { Icon } from "../../components/Icon";
import type { OrientationRule, Specialisation } from "../../types/academic";
import { errorMessage } from "../../utils/errors";
import {
  parseCriteriaForForm,
  parseCriteriaValues,
  serializeCriteriaFromForm,
  type CriterionFormRow,
} from "./orientationCriteria";

interface AdmissionRuleEditorProps {
  formationId: number;
  rule: OrientationRule | null;
  specialisations: Specialisation[];
  fixedSpecialisationId?: number;
  onCancel: () => void;
  onSaved: () => Promise<void>;
}

export function AdmissionRuleEditor({
  formationId,
  rule,
  specialisations,
  fixedSpecialisationId,
  onCancel,
  onSaved,
}: AdmissionRuleEditorProps) {
  const parsed = parseCriteriaForForm(rule?.criteres ?? {});
  const [code, setCode] = useState(rule?.code ?? "");
  const [nom, setNom] = useState(rule?.nom ?? "");
  const [typeRegle, setTypeRegle] = useState(rule?.type_regle ?? "ADMISSION");
  const [specialisationId, setSpecialisationId] = useState(
    String(fixedSpecialisationId ?? rule?.specialisation_id ?? ""),
  );
  const [priorite, setPriorite] = useState(String(rule?.priorite ?? 1));
  const [description, setDescription] = useState(rule?.description ?? "");
  const [actif, setActif] = useState(rule?.actif ?? true);
  const [rows, setRows] = useState<CriterionFormRow[]>(parsed.rows);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateRow = (index: number, update: Partial<CriterionFormRow>) => {
    setRows((current) => current.map((row, rowIndex) => rowIndex === index ? { ...row, ...update } : row));
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    const payload = {
      formation_id: formationId,
      specialisation_id: specialisationId ? Number(specialisationId) : null,
      code: code.trim(),
      nom: nom.trim(),
      type_regle: typeRegle,
      criteres: serializeCriteriaFromForm(rows, parsed.advanced),
      description: description.trim() || null,
      priorite: Number(priorite),
      source_ref: rule?.source_ref ?? null,
      actif,
    };
    try {
      if (rule) await adminApi.update("orientation-rules", rule.id, payload);
      else await adminApi.create("orientation-rules", payload);
      await onSaved();
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="admission-editor" onSubmit={submit}>
      {error && <div className="alert alert--error" role="alert">{error}</div>}
      <div className="form-grid">
        <label className="field"><span>Nom *</span><input required maxLength={255} value={nom} onChange={(event) => setNom(event.target.value)} /></label>
        <label className="field"><span>Identifiant *</span><input required maxLength={100} pattern="[A-Z0-9][A-Z0-9_-]*" value={code} onChange={(event) => setCode(event.target.value.toUpperCase())} /></label>
        <label className="field"><span>Finalité *</span><select required value={typeRegle} onChange={(event) => setTypeRegle(event.target.value)}><option value="ADMISSION">Admission — éligibilité</option><option value="RECOMMANDATION">Recommandation — conseil</option></select></label>
        <label className="field"><span>Spécialisation</span><select disabled={fixedSpecialisationId !== undefined} value={specialisationId} onChange={(event) => setSpecialisationId(event.target.value)}><option value="">Toute la formation</option>{specialisations.map((item) => <option value={item.id} key={item.id}>{item.nom}</option>)}</select></label>
        <label className="field"><span>Priorité *</span><input required type="number" min="1" value={priorite} onChange={(event) => setPriorite(event.target.value)} /></label>
        <label className="checkbox-field"><input type="checkbox" checked={actif} onChange={(event) => setActif(event.target.checked)} /><span><strong>Règle active</strong></span></label>
        <label className="field field--full"><span>Conditions supplémentaires</span><textarea rows={3} maxLength={600} value={description} onChange={(event) => setDescription(event.target.value)} /></label>
      </div>

      <section className="criteria-editor">
        <header><div><h3>Critères</h3><p>Définissez des conditions simples sans manipuler le format technique.</p></div><button className="button button--secondary button--compact" type="button" onClick={() => setRows((current) => [...current, { key: "", operator: "IN", values: [] }])}><Icon name="plus" /> Ajouter une condition</button></header>
        {rows.map((row, index) => (
          <div className="criteria-editor__row" key={`${row.key}-${index}`}>
            <label><span>Type de critère</span><input value={row.key} onChange={(event) => updateRow(index, { key: event.target.value })} placeholder="Ex. diplome" /></label>
            <label><span>Opérateur</span><select value={row.operator} onChange={(event) => updateRow(index, { operator: event.target.value as CriterionFormRow["operator"] })}><option value="EQUALS">Est égal à</option><option value="IN">Fait partie de</option></select></label>
            <label><span>Valeur(s)</span><input value={row.values.join(", ")} onChange={(event) => updateRow(index, { values: parseCriteriaValues(event.target.value) })} placeholder="Valeurs séparées par des virgules" /></label>
            <button className="icon-button icon-button--danger" type="button" onClick={() => setRows((current) => current.filter((_, rowIndex) => rowIndex !== index))} aria-label={`Supprimer le critère ${row.key || index + 1}`}><Icon name="trash" /></button>
          </div>
        ))}
        {rows.length === 0 && <p className="workspace-empty">Aucun critère simple.</p>}
      </section>

      {Object.keys(parsed.advanced).length > 0 && (
        <details className="advanced-criteria"><summary>Cette règle contient des critères avancés — Vue avancée</summary><pre>{JSON.stringify(parsed.advanced, null, 2)}</pre><p>Ces propriétés sont conservées automatiquement et ne seront pas écrasées.</p></details>
      )}

      <div className="modal__actions"><button className="button button--ghost" type="button" onClick={onCancel} disabled={busy}>Annuler</button><button className="button button--primary" type="submit" disabled={busy}>{busy ? "Enregistrement…" : "Enregistrer"}</button></div>
    </form>
  );
}

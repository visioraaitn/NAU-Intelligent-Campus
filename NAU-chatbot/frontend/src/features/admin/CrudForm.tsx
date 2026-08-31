import { type FormEvent, useId, useMemo, useState } from "react";
import type { AcademicEntity } from "../../types/academic";
import { errorMessage } from "../../utils/errors";
import { formatCriteria, formatDateTime, formatLanguage, humanizeEnum } from "../../utils/format";
import type { EntityConfig, EntityField } from "./entityConfig";
import type { ReferenceData } from "./useReferenceData";

type FormValue = string | boolean;

interface CrudFormProps {
  config: EntityConfig;
  entity: AcademicEntity | null;
  references: ReferenceData;
  referencesLoading: boolean;
  referencesError: string | null;
  onCancel: () => void;
  onSubmit: (payload: Record<string, unknown>) => Promise<void>;
}

function initialFieldValue(field: EntityField, entity: AcademicEntity | null): FormValue {
  const raw = entity?.[field.name] ?? field.defaultValue;
  if (field.kind === "checkbox") return raw === undefined ? false : Boolean(raw);
  if (field.kind === "string-list") {
    return Array.isArray(raw) ? raw.join(", ") : String(raw ?? "");
  }
  if (field.kind === "json") {
    return raw && typeof raw === "object" ? JSON.stringify(raw, null, 2) : "{}";
  }
  return raw === null || raw === undefined ? "" : String(raw);
}

function referenceLabel(entity: AcademicEntity): string {
  const code = typeof entity.code === "string" ? entity.code : null;
  const name = typeof entity.nom === "string" ? entity.nom : null;
  const type = typeof entity.type_element === "string" ? humanizeEnum(entity.type_element) : null;
  return [code, name ?? type].filter(Boolean).join(" — ") || "Entrée sans libellé";
}

function serialize(
  config: EntityConfig,
  values: Record<string, FormValue>,
  editing: boolean,
): Record<string, unknown> {
  const payload: Record<string, unknown> = {};
  for (const field of config.fields) {
    const value = values[field.name];
    if (field.kind === "checkbox") {
      payload[field.name] = Boolean(value);
      continue;
    }
    const text = typeof value === "string" ? value.trim() : "";
    if (!text && !field.required) {
      if (editing) payload[field.name] = null;
      continue;
    }
    if (field.kind === "number" || field.kind === "reference") {
      payload[field.name] = Number(text);
    } else if (field.kind === "string-list") {
      payload[field.name] = [...new Set(
        text.split(",").map((item) => item.trim().toLocaleUpperCase("fr")).filter(Boolean),
      )];
    } else if (field.kind === "json") {
      payload[field.name] = JSON.parse(text || "{}") as unknown;
    } else {
      payload[field.name] = text;
    }
  }
  return payload;
}

export function CrudForm({
  config,
  entity,
  references,
  referencesLoading,
  referencesError,
  onCancel,
  onSubmit,
}: CrudFormProps) {
  const formId = useId();
  const [values, setValues] = useState<Record<string, FormValue>>(() =>
    Object.fromEntries(config.fields.map((field) => [field.name, initialFieldValue(field, entity)])),
  );
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const sortedReferences = useMemo(() => {
    const result: ReferenceData = {};
    for (const [resource, entries] of Object.entries(references)) {
      result[resource as keyof ReferenceData] = [...(entries ?? [])].sort((left, right) =>
        referenceLabel(left).localeCompare(referenceLabel(right), "fr"),
      );
    }
    return result;
  }, [references]);

  const update = (field: EntityField, value: FormValue) => {
    setValues((current) => {
      const next = { ...current, [field.name]: value };
      if (field.name === "formation_id" && current.formation_id !== value) {
        next.specialisation_id = "";
        if (config.resource === "elements") next.parent_id = "";
        if (config.resource === "tarifs") {
          const formation = (references.formations ?? []).find(
            (entry) => Number(entry.id) === Number(value),
          );
          const languages = Array.isArray(formation?.langues_enseignement)
            ? formation.langues_enseignement.map(String)
            : [];
          const currentLanguage = String(current.langue_enseignement ?? "");
          next.langue_enseignement = languages.includes(currentLanguage)
            ? currentLanguage
            : languages[0] ?? "";
        }
      }
      return next;
    });
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (busy) return;
    setFormError(null);

    if (values.specialisation_id && !values.formation_id) {
      setFormError("Choisissez une formation avant de sélectionner une spécialisation.");
      return;
    }
    if (
      typeof values.date_debut === "string" &&
      typeof values.date_fin === "string" &&
      values.date_debut &&
      values.date_fin &&
      values.date_fin < values.date_debut
    ) {
      setFormError("La date de fin doit être postérieure ou égale à la date de début.");
      return;
    }

    let payload: Record<string, unknown>;
    try {
      payload = serialize(config, values, entity !== null);
      const criteria = payload.criteres;
      if (criteria !== undefined && (criteria === null || Array.isArray(criteria) || typeof criteria !== "object")) {
        throw new Error("invalid JSON object");
      }
    } catch {
      setFormError("Le champ Critères doit contenir un objet JSON valide.");
      return;
    }

    setBusy(true);
    try {
      await onSubmit(payload);
    } catch (reason) {
      setFormError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form id={formId} className="crud-form" onSubmit={handleSubmit}>
      {referencesError && (
        <div className="alert alert--warning" role="status">
          Certaines listes de référence n’ont pas pu être chargées. {referencesError}
        </div>
      )}
      {formError && <div className="alert alert--error" role="alert">{formError}</div>}

      <div className="form-grid">
        {config.fields.map((field) => {
          const fieldId = `${formId}-${field.name}`;
          const helpId = `${fieldId}-help`;
          const common = {
            id: fieldId,
            name: field.name,
            required: field.required,
            "aria-describedby": field.help ? helpId : undefined,
          };

          if (field.kind === "checkbox") {
            return (
              <label className={`checkbox-field ${field.fullWidth ? "field--full" : ""}`} key={field.name}>
                <input
                  {...common}
                  type="checkbox"
                  checked={Boolean(values[field.name])}
                  onChange={(event) => update(field, event.target.checked)}
                />
                <span>
                  <strong>{field.label}</strong>
                  {field.help && <small id={helpId}>{field.help}</small>}
                </span>
              </label>
            );
          }

          let control;
          if (field.kind === "textarea" || field.kind === "json") {
            control = (
              <textarea
                {...common}
                className={field.kind === "json" ? "code-input" : undefined}
                maxLength={field.maxLength}
                placeholder={field.placeholder}
                rows={field.kind === "json" ? 8 : 4}
                value={String(values[field.name] ?? "")}
                onChange={(event) => update(field, event.target.value)}
              />
            );
          } else if (field.kind === "select") {
            control = (
              <select
                {...common}
                value={String(values[field.name] ?? "")}
                onChange={(event) => update(field, event.target.value)}
              >
                <option value="">Sélectionner…</option>
                {field.options?.map((option) => (
                  <option value={option.value} key={option.value}>{option.label}</option>
                ))}
              </select>
            );
          } else if (field.kind === "language") {
            const formation = (sortedReferences.formations ?? []).find(
              (entry) => Number(entry.id) === Number(values.formation_id),
            );
            const languages = Array.isArray(formation?.langues_enseignement)
              ? formation.langues_enseignement.map(String)
              : [];
            const currentLanguage = String(values[field.name] ?? "");
            const options = languages.includes(currentLanguage) || !currentLanguage
              ? languages
              : [currentLanguage, ...languages];
            control = (
              <select
                {...common}
                disabled={!formation}
                value={currentLanguage}
                onChange={(event) => update(field, event.target.value)}
              >
                <option value="">Sélectionner une formation d’abord…</option>
                {options.map((language) => (
                  <option value={language} key={language}>{formatLanguage(language)}</option>
                ))}
              </select>
            );
          } else if (field.kind === "reference") {
            const formationId = Number(values.formation_id);
            let entries = field.reference ? sortedReferences[field.reference] ?? [] : [];
            if (field.name === "specialisation_id" && formationId) {
              entries = entries.filter((entry) => Number(entry.formation_id) === formationId);
            }
            if (field.name === "parent_id") {
              entries = entries.filter(
                (entry) => entry.id !== entity?.id && (!formationId || Number(entry.formation_id) === formationId),
              );
            }
            control = (
              <select
                {...common}
                disabled={referencesLoading || (field.name === "specialisation_id" && !formationId)}
                value={String(values[field.name] ?? "")}
                onChange={(event) => update(field, event.target.value)}
              >
                <option value="">{field.required ? "Sélectionner…" : "Non renseigné"}</option>
                {entries.map((entry) => (
                  <option value={entry.id} key={entry.id} disabled={!entry.actif}>
                    {referenceLabel(entry)}{entry.actif ? "" : " (inactif)"}
                  </option>
                ))}
              </select>
            );
          } else {
            control = (
              <input
                {...common}
                type={field.kind === "string-list" ? "text" : field.kind}
                min={field.min}
                max={field.max}
                step={field.step}
                minLength={field.minLength}
                maxLength={field.maxLength}
                pattern={field.pattern}
                placeholder={field.placeholder}
                value={String(values[field.name] ?? "")}
                onChange={(event) => update(field, event.target.value)}
              />
            );
          }

          return (
            <label className={`field ${field.fullWidth ? "field--full" : ""}`} key={field.name}>
              <span>{field.label}{field.required && <span aria-hidden="true"> *</span>}</span>
              {control}
              {field.name === "criteres" && (
                <span className="criteria-preview">
                  <strong>Lecture par le chatbot :</strong> {(() => {
                    try {
                      return formatCriteria(JSON.parse(String(values[field.name] || "{}")));
                    } catch {
                      return "JSON invalide";
                    }
                  })()}
                </span>
              )}
              {field.help && <small id={helpId}>{field.help}</small>}
            </label>
          );
        })}
      </div>

      {entity && (
        <dl className="entity-metadata">
          {typeof entity.source_ref === "string" && entity.source_ref && (
            <div><dt>Source</dt><dd>{entity.source_ref}</dd></div>
          )}
          <div><dt>Dernière modification</dt><dd>{formatDateTime(entity.updated_at)}</dd></div>
        </dl>
      )}

      <div className="modal__actions crud-form__actions">
        <button className="button button--ghost" type="button" onClick={onCancel} disabled={busy}>Annuler</button>
        <button className="button button--primary" type="submit" disabled={busy || referencesLoading}>
          {busy && <span className="spinner spinner--small" aria-hidden="true" />}
          {busy ? "Enregistrement…" : entity ? "Enregistrer" : `Créer le ${config.singular}`}
        </button>
      </div>
    </form>
  );
}

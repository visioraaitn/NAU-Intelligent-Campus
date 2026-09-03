import type { CSSProperties } from "react";
import { Icon } from "../../components/Icon";
import type { AcademicEntity } from "../../types/academic";
import { formatCriteria, formatCurrency, formatDate, formatDateTime, formatLanguage, formatValue, humanizeEnum } from "../../utils/format";
import type { EntityColumn, EntityConfig } from "./entityConfig";
import type { ReferenceData } from "./useReferenceData";

interface CrudTableProps {
  config: EntityConfig;
  entities: AcademicEntity[];
  loading: boolean;
  references: ReferenceData;
  onEdit: (entity: AcademicEntity) => void;
  onToggle: (entity: AcademicEntity) => void;
  onDelete: (entity: AcademicEntity) => void;
  onOpen?: (entity: AcademicEntity) => void;
  emptyMessage?: string;
  emptyActionLabel?: string;
  onCreate?: () => void;
}

function referenceValue(entity: AcademicEntity, value: unknown, column: EntityColumn, references: ReferenceData): string {
  if (!column.reference || value === null || value === undefined) {
    if (column.key === "parcours_id" && entity.formation_id) {
      const formation = (references.formations ?? []).find(
        (item) => Number(item.id) === Number(entity.formation_id),
      );
      const parcours = (references.parcours ?? []).find(
        (item) => Number(item.id) === Number(formation?.parcours_id),
      );
      return parcours ? String(parcours.nom ?? parcours.code ?? "—") : "—";
    }
    if (column.key === "formation_id" && entity.parcours_id) return "Commun au cycle";
    if (column.key === "specialisation_id" && entity.parcours_id) return "Toutes les formations du cycle";
    return column.key === "formation_id" ? "Information globale IIT" : "Toute la formation";
  }
  const match = (references[column.reference] ?? []).find((item) => Number(item.id) === Number(value));
  if (!match) return `Entrée #${String(value)}`;
  if (column.reference === "formations") {
    if (Object.prototype.hasOwnProperty.call(entity, "parcours_id")) {
      return String(match.nom ?? match.code ?? `Entrée #${String(value)}`);
    }
    const parcours = (references.parcours ?? []).find(
      (item) => Number(item.id) === Number(match.parcours_id),
    );
    return [parcours?.nom, match.nom].filter(Boolean).join(" / ");
  }
  return [match.code, match.nom].filter(Boolean).join(" — ");
}

function cellValue(entity: AcademicEntity, column: EntityColumn, references: ReferenceData): string {
  const value = entity[column.key];
  if (column.format === "reference") return referenceValue(entity, value, column, references);
  if (column.format === "enum") return humanizeEnum(value);
  if (column.format === "currency") return formatCurrency(value, String(entity.devise ?? "TND"));
  if (column.format === "language") return formatLanguage(value);
  if (column.format === "years") {
    const years = Number(value);
    return Number.isFinite(years) && years > 0 ? `${years} an${years > 1 ? "s" : ""}` : "—";
  }
  if (column.format === "date") return formatDate(value);
  if (column.format === "json") return typeof value === "object" ? JSON.stringify(value) : formatValue(value);
  if (column.format === "criteria") return formatCriteria(value);
  if (column.format === "list") {
    return Array.isArray(value) ? value.map(formatLanguage).join(", ") : formatValue(value);
  }
  return formatValue(value);
}

function entityLabel(entity: AcademicEntity, fallback: string): string {
  return (typeof entity.nom === "string" && entity.nom) ||
    (typeof entity.code === "string" && entity.code) || fallback;
}

export function CrudTable({
  config,
  entities,
  loading,
  references,
  onEdit,
  onToggle,
  onDelete,
  onOpen,
  emptyMessage,
  emptyActionLabel,
  onCreate,
}: CrudTableProps) {
  const wideTable = config.columns.length >= 7;

  if (loading && entities.length === 0) {
    return (
      <div className="table-loading" role="status">
        <span className="spinner" aria-hidden="true" /> Chargement des {config.plural}…
      </div>
    );
  }
  if (!loading && entities.length === 0) {
    return (
      <div className="empty-state empty-state--compact">
        <h2>Aucun résultat</h2>
        <p>{emptyMessage ?? `Modifiez les filtres ou créez un nouveau ${config.singular}.`}</p>
        {emptyActionLabel && onCreate && (
          <button className="button button--primary button--compact" type="button" onClick={onCreate}>
            <Icon name="plus" /> {emptyActionLabel}
          </button>
        )}
      </div>
    );
  }

  return (
    <div className={`table-wrap ${wideTable ? "table-wrap--wide" : ""} ${loading ? "table-wrap--loading" : ""}`} aria-busy={loading}>
      {wideTable && (
        <div className="table-scroll-hint">Faites défiler horizontalement pour voir toutes les informations.</div>
      )}
      <table
        className={`data-table ${config.compactTable ? "data-table--compact" : ""} ${wideTable ? "data-table--wide" : ""}`}
        style={wideTable
          ? { "--data-table-min-width": `${Math.max(1080, (config.columns.length + 2) * 104)}px` } as CSSProperties
          : undefined}
      >
        <caption className="sr-only">Liste des {config.plural}</caption>
        <thead>
          <tr>
            {config.columns.map((column) => (
              <th className={`data-table__cell--${column.key}`} scope="col" key={column.key}>{column.label}</th>
            ))}
            <th scope="col">{config.compactTable ? "Statut" : "État et source"}</th>
            <th scope="col"><span className="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          {entities.map((entity) => {
            const label = entityLabel(entity, config.singular);
            return (
              <tr
                key={entity.id}
                className={onOpen ? "data-table__row--link" : undefined}
                onClick={onOpen ? () => onOpen(entity) : undefined}
                onKeyDown={onOpen ? (event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onOpen(entity);
                  }
                } : undefined}
                role={onOpen ? "link" : undefined}
                tabIndex={onOpen ? 0 : undefined}
                aria-label={onOpen ? `Ouvrir ${label}` : undefined}
              >
                {config.columns.map((column, index) => (
                  <td
                    data-label={column.label}
                    key={column.key}
                    className={`${index === 0 ? "data-table__primary " : ""}data-table__cell--${column.key}`}
                  >
                    {cellValue(entity, column, references)}
                    {index === 0 && typeof entity.nom === "string" && column.key !== "nom" && (
                      <span className="data-table__secondary">{entity.nom}</span>
                    )}
                  </td>
                ))}
                <td data-label={config.compactTable ? "Statut" : "État et source"}>
                  <span className={`status-badge ${entity.actif ? "status-badge--active" : "status-badge--inactive"}`}>
                    {entity.actif ? "Actif" : "Inactif"}
                  </span>
                  {!config.compactTable && (
                    <>
                      <span className="data-table__secondary" title={formatDateTime(entity.updated_at)}>
                        Mis à jour {formatDateTime(entity.updated_at)}
                      </span>
                      {typeof entity.source_ref === "string" && entity.source_ref && (
                        <span className="source-ref" title={entity.source_ref}>Source : {entity.source_ref}</span>
                      )}
                    </>
                  )}
                </td>
                <td
                  data-label="Actions"
                  className={`data-table__actions ${onOpen ? "data-table__actions--navigable" : ""}`}
                  onClick={onOpen ? (event) => event.stopPropagation() : undefined}
                  onKeyDown={onOpen ? (event) => event.stopPropagation() : undefined}
                >
                  <button className="icon-button" type="button" onClick={() => onEdit(entity)} aria-label={`Modifier ${label}`} title="Modifier">
                    <Icon name="edit" />
                  </button>
                  <button
                    className="icon-button"
                    type="button"
                    onClick={() => onToggle(entity)}
                    aria-label={`${entity.actif ? "Désactiver" : "Activer"} ${label}`}
                    title={entity.actif ? "Désactiver" : "Activer"}
                  >
                    <Icon name={entity.actif ? "archive" : "refresh"} />
                  </button>
                  <button className="icon-button icon-button--danger" type="button" onClick={() => onDelete(entity)} aria-label={`Supprimer ${label}`} title="Supprimer">
                    <Icon name="trash" />
                  </button>
                  {onOpen && (
                    <button
                      className="data-table__open-button"
                      type="button"
                      onClick={() => onOpen(entity)}
                      aria-label={`Ouvrir ${label}`}
                      title="Ouvrir les formations"
                    >
                      <Icon name="chevron-right" />
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

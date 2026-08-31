import { type FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { adminApi } from "../../api/admin";
import { ApiError } from "../../api/http";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { Icon } from "../../components/Icon";
import { Modal } from "../../components/Modal";
import { Pagination } from "../../components/Pagination";
import { ADMIN_PAGE_SIZE } from "../../config/env";
import type { Page } from "../../types/api";
import type { AcademicEntity } from "../../types/academic";
import { errorMessage } from "../../utils/errors";
import { CrudForm } from "./CrudForm";
import { CrudTable } from "./CrudTable";
import type { EntityConfig } from "./entityConfig";
import { useReferenceData } from "./useReferenceData";

interface PendingAction {
  kind: "toggle" | "delete";
  entity: AcademicEntity;
}

const emptyPage: Page<AcademicEntity> = { items: [], total: 0, limit: ADMIN_PAGE_SIZE, offset: 0 };

function labelFor(entity: AcademicEntity, singular: string): string {
  const label = entity.nom ?? entity.code;
  return typeof label === "string" ? `« ${label} »` : `ce ${singular}`;
}

export function CrudPage({ config }: { config: EntityConfig }) {
  const [data, setData] = useState<Page<AcademicEntity>>(emptyPage);
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [includeInactive, setIncludeInactive] = useState(false);
  const [formationId, setFormationId] = useState("");
  const [specialisationId, setSpecialisationId] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ tone: "success" | "warning"; text: string } | null>(null);
  const [editing, setEditing] = useState<AcademicEntity | null | undefined>(undefined);
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);
  const [actionBusy, setActionBusy] = useState(false);
  const loadSequence = useRef(0);
  const { data: references, loading: referencesLoading, error: referencesError } = useReferenceData(config);

  const load = useCallback(async () => {
    const sequence = ++loadSequence.current;
    setLoading(true);
    setLoadError(null);
    try {
      const result = await adminApi.list(config.resource, {
        page,
        pageSize: ADMIN_PAGE_SIZE,
        search,
        includeInactive,
        formationId: formationId ? Number(formationId) : undefined,
        specialisationId: specialisationId ? Number(specialisationId) : undefined,
      });
      if (sequence !== loadSequence.current) return;
      setData(result);
      if (page > 1 && result.items.length === 0 && result.total > 0) setPage(page - 1);
    } catch (reason) {
      if (sequence !== loadSequence.current) return;
      setLoadError(errorMessage(reason));
    } finally {
      if (sequence === loadSequence.current) setLoading(false);
    }
  }, [config.resource, formationId, includeInactive, page, search, specialisationId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    setPage(1);
    setSearchInput("");
    setSearch("");
    setFormationId("");
    setSpecialisationId("");
    setIncludeInactive(false);
    setEditing(undefined);
    setNotice(null);
  }, [config.resource]);

  const formations = references.formations ?? [];
  const specialisations = useMemo(
    () => (references.specialisations ?? []).filter(
      (entry) => !formationId || Number(entry.formation_id) === Number(formationId),
    ),
    [formationId, references.specialisations],
  );

  const submitSearch = (event: FormEvent) => {
    event.preventDefault();
    setPage(1);
    setSearch(searchInput.trim());
  };

  const handleSave = async (payload: Record<string, unknown>) => {
    const result = editing
      ? await adminApi.update(config.resource, editing.id, payload)
      : await adminApi.create(config.resource, payload);
    setEditing(undefined);
    const queued = result.indexing_status === "QUEUED";
    const failed = result.indexing_status === "PUBLISH_FAILED";
    setNotice({
      tone: failed ? "warning" : "success",
      text: failed
        ? "Les données sont enregistrées, mais leur indexation a été retardée. Consultez le suivi RAG."
        : queued
          ? "Modification enregistrée. L’indexation de l’assistant est en file d’attente."
          : "Modification enregistrée.",
    });
    await load();
  };

  const confirmAction = async () => {
    if (!pendingAction) return;
    setActionBusy(true);
    setLoadError(null);
    try {
      if (pendingAction.kind === "delete") {
        await adminApi.remove(config.resource, pendingAction.entity.id);
        setNotice({ tone: "success", text: `${config.singular} supprimé. L’index sera actualisé.` });
      } else if (pendingAction.entity.actif) {
        await adminApi.deactivate(config.resource, pendingAction.entity.id);
        setNotice({ tone: "success", text: `${config.singular} désactivé et retiré des réponses publiques.` });
      } else {
        await adminApi.activate(config.resource, pendingAction.entity.id);
        setNotice({ tone: "success", text: `${config.singular} activé. L’index sera actualisé.` });
      }
      setPendingAction(null);
      await load();
    } catch (reason) {
      const suffix = reason instanceof ApiError && reason.status === 409
        ? " Désactivez plutôt cette entrée, ou retirez d’abord ses dépendances."
        : "";
      setLoadError(`${errorMessage(reason)}${suffix}`);
      setPendingAction(null);
    } finally {
      setActionBusy(false);
    }
  };

  const actionLabel = pendingAction ? labelFor(pendingAction.entity, config.singular) : "cette entrée";
  const deleting = pendingAction?.kind === "delete";
  const deactivating = pendingAction?.kind === "toggle" && pendingAction.entity.actif;

  return (
    <section className="admin-page" aria-labelledby="entity-title">
      <header className="page-heading">
        <div>
          <span className="eyebrow">Catalogue académique</span>
          <h1 id="entity-title">{config.title}</h1>
          <p>{config.description}</p>
        </div>
        <button className="button button--primary" type="button" onClick={() => setEditing(null)}>
          <Icon name="plus" /> Ajouter
        </button>
      </header>

      <div className="notice-region" aria-live="polite">
        {notice && <div className={`alert alert--${notice.tone}`}>{notice.text}</div>}
        {loadError && (
          <div className="alert alert--error" role="alert">
            <span>{loadError}</span>
            <button className="button button--ghost button--compact" type="button" onClick={() => void load()}>
              Réessayer
            </button>
          </div>
        )}
      </div>

      <div className="admin-card">
        <form className="crud-toolbar" onSubmit={submitSearch}>
          <label className="search-field">
            <span className="sr-only">Rechercher</span>
            <Icon name="search" />
            <input
              type="search"
              maxLength={200}
              placeholder={`Rechercher dans les ${config.plural}…`}
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
            />
          </label>
          <button className="button button--secondary button--compact" type="submit">Rechercher</button>

          {config.formationFilter && (
            <label className="toolbar-select">
              <span className="sr-only">Filtrer par formation</span>
              <select
                value={formationId}
                onChange={(event) => {
                  setFormationId(event.target.value);
                  setSpecialisationId("");
                  setPage(1);
                }}
              >
                <option value="">Toutes les formations</option>
                {formations.map((entry) => (
                  <option value={entry.id} key={entry.id}>{entry.code} — {entry.nom}</option>
                ))}
              </select>
            </label>
          )}

          {config.specialisationFilter && (
            <label className="toolbar-select">
              <span className="sr-only">Filtrer par spécialisation</span>
              <select
                value={specialisationId}
                onChange={(event) => {
                  setSpecialisationId(event.target.value);
                  setPage(1);
                }}
              >
                <option value="">Toutes les spécialisations</option>
                {specialisations.map((entry) => (
                  <option value={entry.id} key={entry.id}>{entry.code} — {entry.nom}</option>
                ))}
              </select>
            </label>
          )}

          <label className="checkbox-field checkbox-field--inline">
            <input
              type="checkbox"
              checked={includeInactive}
              onChange={(event) => {
                setIncludeInactive(event.target.checked);
                setPage(1);
              }}
            />
            <span>Inclure les inactifs</span>
          </label>
        </form>

        <CrudTable
          config={config}
          entities={data.items}
          loading={loading}
          references={references}
          onEdit={(entity) => setEditing(entity)}
          onToggle={(entity) => setPendingAction({ kind: "toggle", entity })}
          onDelete={(entity) => setPendingAction({ kind: "delete", entity })}
        />
        <Pagination page={page} pageSize={data.limit || ADMIN_PAGE_SIZE} total={data.total} onPageChange={setPage} />
      </div>

      <Modal
        open={editing !== undefined}
        title={editing ? `Modifier le ${config.singular}` : `Nouveau ${config.singular}`}
        description="Les champs marqués d’un astérisque sont obligatoires."
        onClose={() => setEditing(undefined)}
        size="large"
      >
        {editing !== undefined && (
          <CrudForm
            key={editing?.id ?? "new"}
            config={config}
            entity={editing}
            references={references}
            referencesLoading={referencesLoading}
            referencesError={referencesError}
            onCancel={() => setEditing(undefined)}
            onSubmit={handleSave}
          />
        )}
      </Modal>

      <ConfirmDialog
        open={pendingAction !== null}
        title={deleting ? "Supprimer définitivement" : deactivating ? "Désactiver l’entrée" : "Réactiver l’entrée"}
        message={
          deleting
            ? `Supprimer ${actionLabel} ? La suppression sera refusée si des données en dépendent.`
            : deactivating
              ? `Désactiver ${actionLabel} ? Cette information ne sera plus utilisée dans les réponses publiques.`
              : `Réactiver ${actionLabel} et le rendre à nouveau disponible ?`
        }
        confirmLabel={deleting ? "Supprimer" : deactivating ? "Désactiver" : "Activer"}
        destructive={deleting || deactivating}
        busy={actionBusy}
        onCancel={() => setPendingAction(null)}
        onConfirm={() => void confirmAction()}
      />
    </section>
  );
}

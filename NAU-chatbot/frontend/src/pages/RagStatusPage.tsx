import { useCallback, useEffect, useMemo, useState } from "react";
import { adminApi } from "../api/admin";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { Icon } from "../components/Icon";
import type { AcademicEntity, RagJob, RagJobState } from "../types/academic";
import { errorMessage } from "../utils/errors";
import { formatDateTime, humanizeEnum } from "../utils/format";

const stateLabels: Record<RagJobState, string> = {
  QUEUED: "En attente",
  RUNNING: "En cours",
  SUCCEEDED: "Terminé",
  RETRYING: "Nouvel essai",
  FAILED: "Échec",
};

function stateLabel(state: string): string {
  return stateLabels[state as RagJobState] ?? humanizeEnum(state);
}

export function RagStatusPage() {
  const [jobs, setJobs] = useState<RagJob[]>([]);
  const [formations, setFormations] = useState<AcademicEntity[]>([]);
  const [formationId, setFormationId] = useState("");
  const [loading, setLoading] = useState(true);
  const [queueing, setQueueing] = useState(false);
  const [confirmAll, setConfirmAll] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const loadStatus = useCallback(async (quiet = false) => {
    if (!quiet) setLoading(true);
    try {
      const response = await adminApi.ragStatus();
      setJobs(response.jobs);
      setLastUpdated(new Date().toISOString());
      setError(null);
    } catch (reason) {
      if (!quiet) setError(errorMessage(reason));
    } finally {
      if (!quiet) setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    void adminApi.list("formations", { pageSize: 100 })
      .then((response) => {
        if (active) setFormations(response.items);
      })
      .catch(() => undefined);
    void loadStatus();
    const timer = window.setInterval(() => void loadStatus(true), 10_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [loadStatus]);

  const summary = useMemo(() => ({
    queued: jobs.filter((job) => job.state === "QUEUED" || job.state === "RETRYING").length,
    running: jobs.filter((job) => job.state === "RUNNING").length,
    succeeded: jobs.filter((job) => job.state === "SUCCEEDED").length,
    failed: jobs.filter((job) => job.state === "FAILED").length,
  }), [jobs]);

  const reindex = async (all: boolean) => {
    setQueueing(true);
    setError(null);
    setNotice(null);
    try {
      const response = all
        ? await adminApi.reindexAll()
        : await adminApi.reindexFormation(Number(formationId));
      setNotice(`${response.queued} tâche${response.queued === 1 ? "" : "s"} ajoutée${response.queued === 1 ? "" : "s"} à la file d’indexation.`);
      setConfirmAll(false);
      await loadStatus(true);
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setQueueing(false);
    }
  };

  return (
    <section className="admin-page" aria-labelledby="rag-title">
      <header className="page-heading">
        <div>
          <span className="eyebrow">Assistant</span>
          <h1 id="rag-title">Indexation RAG</h1>
          <p>Suivez la propagation du catalogue vers l’index de connaissances de l’assistant.</p>
        </div>
        <button className="button button--secondary" type="button" onClick={() => void loadStatus()} disabled={loading}>
          <Icon name="refresh" /> Actualiser
        </button>
      </header>

      <div className="notice-region" aria-live="polite">
        {notice && <div className="alert alert--success">{notice}</div>}
        {error && <div className="alert alert--error" role="alert">{error}</div>}
      </div>

      <div className="rag-summary" aria-label="Résumé des tâches récentes">
        <div><span className="status-dot status-dot--queued" /><strong>{summary.queued}</strong><span>En attente</span></div>
        <div><span className="status-dot status-dot--running" /><strong>{summary.running}</strong><span>En cours</span></div>
        <div><span className="status-dot status-dot--success" /><strong>{summary.succeeded}</strong><span>Terminées</span></div>
        <div><span className="status-dot status-dot--failed" /><strong>{summary.failed}</strong><span>Échecs</span></div>
      </div>

      <div className="admin-card rag-actions-card">
        <div>
          <h2>Relancer une indexation</h2>
          <p>Choisissez une formation pour limiter l’opération, ou reconstruisez tout le catalogue.</p>
        </div>
        <div className="rag-actions">
          <label className="field">
            <span>Formation</span>
            <select value={formationId} onChange={(event) => setFormationId(event.target.value)}>
              <option value="">Sélectionner une formation…</option>
              {formations.map((formation) => (
                <option value={formation.id} key={formation.id}>{formation.code} — {formation.nom}</option>
              ))}
            </select>
          </label>
          <button className="button button--primary" type="button" disabled={!formationId || queueing} onClick={() => void reindex(false)}>
            <Icon name="refresh" /> Indexer cette formation
          </button>
          <button className="button button--ghost" type="button" disabled={queueing} onClick={() => setConfirmAll(true)}>
            Tout réindexer
          </button>
        </div>
      </div>

      <div className="admin-card">
        <div className="card-heading">
          <div><h2>Activité récente</h2><p>Les 50 dernières tâches, actualisées automatiquement.</p></div>
          {lastUpdated && <small>Actualisé {formatDateTime(lastUpdated)}</small>}
        </div>
        {loading ? (
          <div className="table-loading" role="status"><span className="spinner" aria-hidden="true" /> Chargement du suivi…</div>
        ) : jobs.length === 0 ? (
          <div className="empty-state empty-state--compact">
            <h3>Aucune tâche récente</h3>
            <p>Les prochaines modifications du catalogue apparaîtront ici.</p>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="data-table rag-table">
              <caption className="sr-only">Tâches d’indexation récentes</caption>
              <thead><tr><th>État</th><th>Contenu</th><th>Action</th><th>Tentative</th><th>Mise à jour</th></tr></thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.event_id}>
                    <td data-label="État"><span className={`job-state job-state--${job.state.toLowerCase()}`}>{stateLabel(job.state)}</span></td>
                    <td data-label="Contenu">{humanizeEnum(job.entity_type)}</td>
                    <td data-label="Action">{humanizeEnum(job.action)}</td>
                    <td data-label="Tentative">{job.attempt + 1}</td>
                    <td data-label="Mise à jour">{formatDateTime(job.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <ConfirmDialog
        open={confirmAll}
        title="Réindexer tout le catalogue"
        message="Cette opération peut prendre plusieurs minutes. Les données PostgreSQL restent disponibles pendant la reconstruction."
        confirmLabel="Lancer la réindexation"
        busy={queueing}
        onCancel={() => setConfirmAll(false)}
        onConfirm={() => void reindex(true)}
      />
    </section>
  );
}

import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { adminApi } from "../api/admin";
import { Icon } from "../components/Icon";
import { CycleWizard } from "../features/admin/CycleWizard";
import type { Parcours } from "../types/academic";
import { errorMessage } from "../utils/errors";

export function CycleCataloguePage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const configuredId = Number(searchParams.get("configure")) || 0;
  const [cycles, setCycles] = useState<Parcours[]>([]);
  const [newWizardOpen, setNewWizardOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await adminApi.list("parcours", { pageSize: 100, includeInactive: true });
      setCycles(result.items as Parcours[]);
      setError(null);
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const closeWizard = async () => {
    setNewWizardOpen(false);
    if (configuredId) {
      const next = new URLSearchParams(searchParams);
      next.delete("configure");
      setSearchParams(next, { replace: true });
    }
    await load();
  };

  return (
    <section className="admin-page cycle-catalogue" aria-labelledby="catalogue-title">
      <header className="page-heading"><div><span className="eyebrow">Catalogue académique</span><h1 id="catalogue-title">Cycles académiques</h1><p>Un cycle académique représente le type ou niveau du cursus. Les disciplines sont créées comme formations.</p></div><button className="button button--primary" type="button" onClick={() => setNewWizardOpen(true)}><Icon name="plus" /> Nouveau cycle académique</button></header>
      {error && <div className="alert alert--error" role="alert">{error}</div>}
      {loading ? <div className="table-loading"><span className="spinner" /> Chargement du catalogue…</div> : cycles.length ? <div className="cycle-catalogue-list">{cycles.map((cycle) => <Link to={`/admin/cycle-workspace?parcours_id=${cycle.id}`} key={cycle.id}><span><strong>{cycle.nom}</strong><small>{cycle.description || cycle.code}</small></span><span>{cycle.duree_annees ? `${cycle.duree_annees} ans` : "Durée non renseignée"}</span><span className={`status-badge ${cycle.actif ? "status-badge--active" : "status-badge--inactive"}`}>{cycle.actif ? "Actif" : "Inactif"}</span><Icon name="chevron-right" /></Link>)}</div> : <div className="workspace-empty-state"><p>Aucun cycle académique n’est configuré.</p><button className="button button--primary" type="button" onClick={() => setNewWizardOpen(true)}>Créer le premier cycle</button></div>}
      {(newWizardOpen || configuredId > 0) && <CycleWizard key={configuredId || "new"} initialCycleId={configuredId || undefined} onClose={() => void closeWizard()} onFinished={(cycleId) => navigate(`/admin/cycle-workspace?parcours_id=${cycleId}`)} />}
    </section>
  );
}

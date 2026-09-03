import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { adminApi } from "../api/admin";
import { Icon } from "../components/Icon";
import type { Formation, Parcours } from "../types/academic";
import { errorMessage } from "../utils/errors";

export function AdmissionHubPage() {
  const [cycles, setCycles] = useState<Parcours[]>([]);
  const [formations, setFormations] = useState<Formation[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    void Promise.all([
      adminApi.list("parcours", { pageSize: 100, includeInactive: true }),
      adminApi.list("formations", { pageSize: 100, includeInactive: true }),
    ]).then(([cyclePage, formationPage]) => {
      if (!active) return;
      setCycles(cyclePage.items as Parcours[]);
      setFormations(formationPage.items as Formation[]);
    }).catch((reason) => {
      if (active) setError(errorMessage(reason));
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, []);

  return (
    <section className="admin-page admission-hub" aria-labelledby="admission-hub-title">
      <header className="page-heading"><div><span className="eyebrow">Gestion métier</span><h1 id="admission-hub-title">Admission & inscription</h1><p>L’admission vérifie l’éligibilité. L’inscription regroupe les démarches et pièces à fournir après la décision.</p></div></header>
      {error && <div className="alert alert--error" role="alert">{error}</div>}
      {loading ? <div className="table-loading"><span className="spinner" /> Chargement…</div> : <div className="admission-hub__grid">
        <section className="workspace-panel admin-card"><header><div><h2>Admission</h2><p>Règles d’éligibilité et recommandations par formation.</p></div></header><div className="hub-link-list">{formations.map((formation) => <Link to={`/admin/academic-overview?formation_id=${formation.id}&section=admission`} key={formation.id}><span><strong>{formation.nom}</strong><small>{formation.code}</small></span><Icon name="chevron-right" /></Link>)}</div></section>
        <section className="workspace-panel admin-card"><header><div><h2>Inscription</h2><p>Préinscription, pièces et frais communs par cycle académique.</p></div></header><div className="hub-link-list">{cycles.map((cycle) => <Link to={`/admin/cycle-workspace?parcours_id=${cycle.id}&section=inscription`} key={cycle.id}><span><strong>{cycle.nom}</strong><small>{cycle.code}</small></span><Icon name="chevron-right" /></Link>)}</div></section>
      </div>}
    </section>
  );
}

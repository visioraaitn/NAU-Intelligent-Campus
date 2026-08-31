import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { adminApi } from "../api/admin";
import { Icon } from "../components/Icon";
import { entityConfigList } from "../features/admin/entityConfig";
import type { AcademicResource } from "../types/academic";

type Counts = Partial<Record<AcademicResource, number | null>>;

export function AdminDashboardPage() {
  const [counts, setCounts] = useState<Counts>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    void Promise.allSettled(
      entityConfigList.map((config) => adminApi.list(config.resource, { pageSize: 1, includeInactive: true })),
    ).then((results) => {
      if (!active) return;
      const next: Counts = {};
      results.forEach((result, index) => {
        const config = entityConfigList[index];
        if (!config) return;
        next[config.resource] = result.status === "fulfilled" ? result.value.total : null;
      });
      setCounts(next);
      setLoading(false);
    });
    return () => {
      active = false;
    };
  }, []);

  return (
    <section className="admin-page" aria-labelledby="dashboard-title">
      <header className="page-heading page-heading--dashboard">
        <div>
          <span className="eyebrow">Vue d’ensemble</span>
          <h1 id="dashboard-title">Tableau de bord</h1>
          <p>Gérez les informations académiques utilisées par l’assistant IIT.</p>
        </div>
        <Link className="button button--secondary" to="/" target="_blank" rel="noreferrer">
          <Icon name="external" /> Ouvrir l’assistant
        </Link>
      </header>

      <div className="dashboard-intro">
        <div>
          <span className="dashboard-intro__icon" aria-hidden="true"><Icon name="sparkles" /></span>
          <div>
            <h2>Le catalogue est la source de vérité</h2>
            <p>Chaque modification validée est enregistrée puis envoyée à l’index de connaissances.</p>
          </div>
        </div>
        <Link to="/admin/rag">Suivre l’indexation <Icon name="chevron-right" /></Link>
      </div>

      <Link className="orientation-diagnostic-link" to="/admin/orientation-matrix">
        <span className="entity-card__icon" aria-hidden="true"><Icon name="sparkles" /></span>
        <span>
          <strong>Vérifier les règles par profil</strong>
          <small>Comparez les données d’admission et les recommandations réellement appliquées par le chatbot.</small>
        </span>
        <Icon name="chevron-right" />
      </Link>

      <Link className="orientation-diagnostic-link academic-overview-link" to="/admin/academic-overview">
        <span className="entity-card__icon" aria-hidden="true"><Icon name="database" /></span>
        <span>
          <strong>Consulter les fiches académiques complètes</strong>
          <small>Visualisez chaque formation avec ses matières, spécialisations, règles, tarifs, sources et contenus RAG.</small>
        </span>
        <Icon name="chevron-right" />
      </Link>

      <div className="entity-card-grid">
        {entityConfigList.map((config) => {
          const count = counts[config.resource];
          return (
            <Link className="entity-card" to={`/admin/${config.resource}`} key={config.resource}>
              <span className="entity-card__icon" aria-hidden="true"><Icon name="database" /></span>
              <span className="entity-card__content">
                <strong>{config.title}</strong>
                <small>{config.description}</small>
              </span>
              <span className="entity-card__count" aria-label={count === null ? "Indisponible" : `${count ?? 0} entrées`}>
                {loading ? <span className="skeleton skeleton--number" /> : count === null ? "—" : count ?? 0}
              </span>
              <Icon name="chevron-right" className="entity-card__arrow" />
            </Link>
          );
        })}
      </div>
    </section>
  );
}

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { adminApi } from "../api/admin";
import { Icon } from "../components/Icon";
import {
  DashboardAction,
  DashboardResourceLink,
  DashboardStat,
} from "../features/admin/DashboardUI";
import { entityConfigList } from "../features/admin/entityConfig";
import type { AcademicResource, FormationDataDiagnostic } from "../types/academic";

type Counts = Partial<Record<AcademicResource, number | null>>;

const dashboardResources = entityConfigList.filter((config) => config.resource !== "elements");

export function AdminDashboardPage() {
  const [counts, setCounts] = useState<Counts>({});
  const [countsLoading, setCountsLoading] = useState(true);
  const [diagnostics, setDiagnostics] = useState<FormationDataDiagnostic[] | null | undefined>();

  useEffect(() => {
    let active = true;

    void Promise.allSettled(
      dashboardResources.map((config) =>
        adminApi.list(config.resource, { pageSize: 1, includeInactive: true }),
      ),
    ).then((results) => {
      if (!active) return;
      const next: Counts = {};
      results.forEach((result, index) => {
        const resource = dashboardResources[index]?.resource;
        if (resource) next[resource] = result.status === "fulfilled" ? result.value.total : null;
      });
      setCounts(next);
      setCountsLoading(false);
    });

    void adminApi.orientationMatrix()
      .then((response) => {
        if (active) setDiagnostics(response.diagnostics);
      })
      .catch(() => {
        if (active) setDiagnostics(null);
      });

    return () => {
      active = false;
    };
  }, []);

  const attentionCount = diagnostics?.filter((item) => item.issues.length > 0).length;
  const missingAdmissionCount = diagnostics?.filter((item) => !item.has_admission_rule).length;
  const missingTariffCount = diagnostics?.filter((item) => !item.has_tariff).length;
  const diagnosticsLoading = diagnostics === undefined;

  return (
    <section className="admin-page dashboard" aria-labelledby="dashboard-title">
      <header className="page-heading page-heading--dashboard">
        <div>
          <span className="eyebrow">Vue d’ensemble</span>
          <h1 id="dashboard-title">Administration académique</h1>
          <p>Pilotez le catalogue, l’admission et les informations académiques.</p>
        </div>
        <Link className="button button--secondary" to="/" target="_blank" rel="noreferrer">
          <Icon name="external" /> Voir l’assistant public
        </Link>
      </header>

      <section className="dashboard-summary" aria-labelledby="dashboard-summary-title">
        <h2 className="sr-only" id="dashboard-summary-title">Résumé du catalogue</h2>
        <DashboardStat label="Cycles académiques" value={counts.parcours} loading={countsLoading} to="/admin/catalogue" />
        <DashboardStat label="Formations" value={counts.formations} loading={countsLoading} to="/admin/formations" />
        <DashboardStat label="Spécialisations" value={counts.specialisations} loading={countsLoading} to="/admin/specialisations" />
        <DashboardStat label="À vérifier" value={diagnostics === null ? null : attentionCount} loading={diagnosticsLoading} to="/admin/orientation-matrix" />
      </section>

      <section className="dashboard-section" aria-labelledby="workflows-title">
        <header className="dashboard-section__heading">
          <div>
            <span className="eyebrow">Accès rapides</span>
            <h2 id="workflows-title">Gestion académique</h2>
          </div>
          <p>Accédez directement aux principaux espaces de travail.</p>
        </header>
        <div className="dashboard-actions">
          <DashboardAction
            title="Catalogue académique"
            description="Gérer les cycles, formations et spécialisations"
            to="/admin/catalogue"
            icon="database"
          />
          <DashboardAction
            title="Admission et inscription"
            description="Configurer les règles, tarifs et informations d’inscription"
            to="/admin/admission"
            icon="edit"
          />
          <DashboardAction
            title="Diagnostic d’orientation"
            description="Vérifier la couverture des règles et des tarifs"
            to="/admin/orientation-matrix"
            icon="sparkles"
          />
        </div>
      </section>

      <section className="dashboard-section dashboard-quality" aria-labelledby="quality-title">
        <header className="dashboard-section__heading">
          <div>
            <span className="eyebrow">Qualité du catalogue</span>
            <h2 id="quality-title">À vérifier</h2>
          </div>
          <Link className="text-link" to="/admin/orientation-matrix">Voir le diagnostic <Icon name="chevron-right" /></Link>
        </header>

        {diagnosticsLoading ? (
          <div className="dashboard-quality__loading" role="status">Analyse des données du catalogue…</div>
        ) : diagnostics === null ? (
          <div className="dashboard-quality__empty">Le diagnostic est momentanément indisponible.</div>
        ) : attentionCount === 0 ? (
          <div className="dashboard-quality__healthy" role="status">
            <span aria-hidden="true">✓</span>
            <div><strong>Aucun point bloquant détecté</strong><small>Les formations disposent des informations contrôlées.</small></div>
          </div>
        ) : (
          <div className="dashboard-quality__items">
            <Link to="/admin/orientation-rules">
              <strong>{missingAdmissionCount}</strong>
              <span>formation{missingAdmissionCount === 1 ? "" : "s"} sans règle d’admission</span>
              <Icon name="chevron-right" />
            </Link>
            <Link to="/admin/tarifs">
              <strong>{missingTariffCount}</strong>
              <span>formation{missingTariffCount === 1 ? "" : "s"} sans tarif</span>
              <Icon name="chevron-right" />
            </Link>
            <Link to="/admin/orientation-matrix">
              <strong>{attentionCount}</strong>
              <span>formation{attentionCount === 1 ? "" : "s"} à contrôler</span>
              <Icon name="chevron-right" />
            </Link>
          </div>
        )}
      </section>

      <section className="dashboard-section dashboard-resources" aria-labelledby="resources-title">
        <header className="dashboard-section__heading">
          <div>
            <span className="eyebrow">Données disponibles</span>
            <h2 id="resources-title">Ressources du catalogue</h2>
          </div>
        </header>
        <div className="dashboard-resource-grid">
          {dashboardResources.map((config) => (
            <DashboardResourceLink
              key={config.resource}
              title={config.title}
              count={counts[config.resource]}
              loading={countsLoading}
              to={`/admin/${config.resource}`}
            />
          ))}
        </div>
      </section>
    </section>
  );
}

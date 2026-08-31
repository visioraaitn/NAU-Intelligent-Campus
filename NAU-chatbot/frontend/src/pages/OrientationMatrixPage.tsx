import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { adminApi } from "../api/admin";
import { Icon } from "../components/Icon";
import type { OrientationMatrixResponse } from "../types/academic";
import { errorMessage } from "../utils/errors";

const eligibilityLabels = {
  ELIGIBLE: "Admissible selon les données",
  NOT_ELIGIBLE: "Non admissible",
  UNKNOWN: "Donnée insuffisante",
} as const;

export function OrientationMatrixPage() {
  const [data, setData] = useState<OrientationMatrixResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void adminApi.orientationMatrix()
      .then((response) => active && setData(response))
      .catch((reason) => active && setError(errorMessage(reason)));
    return () => { active = false; };
  }, []);

  return (
    <section className="admin-page" aria-labelledby="matrix-title">
      <header className="page-heading">
        <div>
          <span className="eyebrow">Données vs logique chatbot</span>
          <h1 id="matrix-title">Diagnostic d’orientation</h1>
          <p>
            Vérifiez ce que les règles académiques autorisent et ce que le chatbot recommande réellement pour chaque section de bac.
          </p>
        </div>
        <Link className="button button--primary" to="/admin/orientation-rules">
          <Icon name="edit" /> Modifier les règles
        </Link>
      </header>

      <div className="dashboard-intro matrix-explainer">
        <div>
          <span className="dashboard-intro__icon" aria-hidden="true"><Icon name="sparkles" /></span>
          <div>
            <h2>Comment lire cette page ?</h2>
            <p>“Admissible” vient de PostgreSQL. “Recommandation chatbot” applique ensuite la politique commerciale sans contourner l’admission.</p>
          </div>
        </div>
      </div>

      {error && <div className="alert alert--error" role="alert">{error}</div>}
      {!data && !error && <div className="table-loading"><span className="spinner" /> Chargement du diagnostic…</div>}

      {data && (
        <>
          <div className="orientation-profile-grid">
            {data.profiles.map((profile) => {
              const visible = profile.formations.filter(
                (formation) => formation.eligibility === "ELIGIBLE" || formation.recommended,
              );
              const unresolved = profile.formations.filter(
                (formation) => formation.eligibility === "UNKNOWN",
              );
              return (
                <article className="orientation-profile-card" key={profile.code}>
                  <header>
                    <span className="eyebrow">Profil étudiant</span>
                    <h2>{profile.label}</h2>
                    <p>{profile.policy}</p>
                  </header>
                  <div className="matrix-recommendation">
                    <strong>Recommandation chatbot</strong>
                    <span>{profile.recommendation ?? "Aucune recommandation confirmée"}</span>
                  </div>
                  <div className="matrix-formation-list">
                    {visible.length ? visible.map((formation) => (
                      <div className={formation.recommended ? "recommended" : ""} key={formation.formation_id}>
                        <span>
                          <strong>{formation.formation_name}</strong>
                          <small>{formation.parcours_name} · {formation.explanation}</small>
                        </span>
                        <span className={`matrix-status matrix-status--${formation.eligibility.toLowerCase()}`}>
                          {eligibilityLabels[formation.eligibility]}
                        </span>
                      </div>
                    )) : <p className="matrix-empty">Aucune formation admissible n’est confirmée dans les règles actives.</p>}
                  </div>
                  <details>
                    <summary>Voir les données incomplètes ({unresolved.length})</summary>
                    {unresolved.map((formation) => (
                      <p key={formation.formation_id}><strong>{formation.formation_name}</strong> — {formation.explanation}</p>
                    ))}
                  </details>
                </article>
              );
            })}
          </div>

          <section className="admin-card data-diagnostics" aria-labelledby="quality-title">
            <header>
              <div>
                <span className="eyebrow">Qualité des données</span>
                <h2 id="quality-title">Informations manquantes par formation</h2>
              </div>
              <span>{data.diagnostics.filter((item) => item.issues.length > 0).length} formations à vérifier</span>
            </header>
            <div className="diagnostic-list">
              {data.diagnostics.map((item) => (
                <article key={item.formation_id}>
                  <div>
                    <strong>{item.formation_name}</strong>
                    <span>{item.specialisation_count} spécialisation(s) · {item.element_count} information(s)</span>
                  </div>
                  <div className="diagnostic-badges">
                    <span className={item.has_admission_rule ? "ok" : "missing"}>Admission {item.has_admission_rule ? "renseignée" : "manquante"}</span>
                    <span className={item.has_tariff ? "ok" : "missing"}>Tarif {item.has_tariff ? "renseigné" : "manquant"}</span>
                  </div>
                  {item.issues.map((issue) => <p key={issue}>{issue}</p>)}
                </article>
              ))}
            </div>
          </section>
        </>
      )}
    </section>
  );
}

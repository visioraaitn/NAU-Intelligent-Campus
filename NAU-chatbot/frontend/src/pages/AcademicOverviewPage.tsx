import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { adminApi } from "../api/admin";
import { Icon } from "../components/Icon";
import type {
  AcademicFormationOverview,
  AcademicOverviewResponse,
  FormationElement,
  FormationElementType,
  RagDocumentPreview,
  Tarif,
} from "../types/academic";
import { errorMessage } from "../utils/errors";
import { formatCriteria, formatCurrency, formatLanguage, humanizeEnum } from "../utils/format";

const elementLabels: Record<FormationElementType, string> = {
  MODULE: "Matières et modules",
  COURS: "Cours",
  CONTENU_PROGRAMME: "Contenus du programme",
  COMPETENCE: "Compétences développées",
  METIER: "Débouchés possibles",
  DOMAINE_ACTIVITE: "Domaines d’activité",
  CERTIFICATION: "Certifications préparées",
  LANGUE: "Langues",
  MOBILITE: "Mobilité internationale",
  OUTIL: "Outils étudiés",
  OPPORTUNITE: "Perspectives",
  INFORMATION: "Informations académiques",
};

const elementOrder = Object.keys(elementLabels) as FormationElementType[];

function elementScope(element: FormationElement, overview: AcademicFormationOverview): string {
  if (!element.specialisation_id) return "Toute la formation";
  return overview.specialisations.find((item) => item.id === element.specialisation_id)?.nom
    ?? "Spécialisation non retrouvée";
}

function specialisationName(id: number, overview: AcademicFormationOverview): string {
  return overview.specialisations.find((item) => item.id === id)?.nom
    ?? "Spécialisation non retrouvée";
}

function tariffTotal(tarif: Tarif): number | null {
  const registration = Number(tarif.frais_inscription ?? 0);
  const monthly = Number(tarif.mensualite ?? 0);
  const count = Number(tarif.nb_mensualites ?? 0);
  const total = registration + monthly * count;
  return Number.isFinite(total) && total > 0 ? total : null;
}

function RagDocuments({ documents }: { documents: RagDocumentPreview[] }) {
  if (!documents.length) {
    return <p className="overview-empty">Aucun document actif n’est actuellement envoyé à l’index RAG.</p>;
  }
  return (
    <div className="rag-document-list">
      {documents.map((document) => (
        <details key={document.document_id}>
          <summary>
            <span>{humanizeEnum(document.metadata.entity_type)}</span>
            <code>{document.document_id}</code>
          </summary>
          <p>{document.content}</p>
          <dl>
            <div><dt>Portée</dt><dd>{String(document.metadata.specialisation_code || document.metadata.formation_code || "IIT global")}</dd></div>
            <div><dt>Source</dt><dd>{String(document.metadata.source_ref || "Non renseignée")}</dd></div>
            <div><dt>Type</dt><dd>{humanizeEnum(document.metadata.element_type)}</dd></div>
          </dl>
        </details>
      ))}
    </div>
  );
}

function ElementGroups({ overview }: { overview: AcademicFormationOverview }) {
  const grouped = useMemo(() => {
    const result = new Map<FormationElementType, FormationElement[]>();
    for (const element of overview.elements) {
      const current = result.get(element.type_element) ?? [];
      current.push(element);
      result.set(element.type_element, current);
    }
    return result;
  }, [overview]);

  if (!overview.elements.length) {
    return <p className="overview-empty">Aucune information pédagogique n’est renseignée.</p>;
  }

  return (
    <div className="academic-info-groups">
      {elementOrder.map((type) => {
        const elements = grouped.get(type) ?? [];
        if (!elements.length) return null;
        return (
          <section className="academic-info-group" key={type}>
            <header>
              <div><h3>{elementLabels[type]}</h3><p>{elements.length} information{elements.length > 1 ? "s" : ""}</p></div>
              <Link to="/admin/elements">Gérer</Link>
            </header>
            <div className="academic-fact-grid">
              {elements.map((element) => (
                <article key={element.id}>
                  <div className="academic-fact__heading">
                    <strong>{element.nom}</strong>
                    {!element.actif && <span className="status-badge status-badge--inactive">Inactif</span>}
                  </div>
                  <span className="scope-badge">{elementScope(element, overview)}</span>
                  {element.description && <p>{element.description}</p>}
                  {element.organisme && <small>Organisme : {element.organisme}</small>}
                  <small>Source : {element.source_ref || "non renseignée"}</small>
                </article>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}

function FormationSheet({ overview }: { overview: AcademicFormationOverview }) {
  const { formation, parcours } = overview;
  return (
    <div className="formation-sheet">
      <section className="overview-hero admin-card">
        <div>
          <span className="overview-breadcrumb">{parcours.nom} / {formation.nom}</span>
          <h2>{formation.nom}</h2>
          <p>{formation.description || "Aucune description générale n’est renseignée."}</p>
        </div>
        <span className={`status-badge ${formation.actif ? "status-badge--active" : "status-badge--inactive"}`}>
          {formation.actif ? "Formation active" : "Formation inactive"}
        </span>
        <dl className="overview-metrics">
          <div><dt>Diplôme</dt><dd>{formation.intitule_diplome || "Poursuite d’études / non renseigné"}</dd></div>
          <div><dt>Durée</dt><dd>{formation.duree_annees ? `${formation.duree_annees} ans` : "Non renseignée"}</dd></div>
          <div><dt>Semestres</dt><dd>{formation.nb_semestres ?? "Non renseigné"}</dd></div>
          <div><dt>Crédits</dt><dd>{formation.credits_total ?? "Non renseigné"}</dd></div>
          <div><dt>Langues</dt><dd>{formation.langues_enseignement.map(formatLanguage).join(", ")}</dd></div>
          <div><dt>Source principale</dt><dd>{formation.source_ref || "Non renseignée"}</dd></div>
        </dl>
      </section>

      <section className="overview-section admin-card">
        <header><div><span className="eyebrow">Organisation</span><h2>Spécialisations et sections</h2></div><Link to="/admin/specialisations">Gérer</Link></header>
        {overview.specialisations.length ? (
          <div className="specialisation-overview-grid">
            {overview.specialisations.map((specialisation) => {
              const count = overview.elements.filter((item) => item.specialisation_id === specialisation.id).length;
              return (
                <article key={specialisation.id}>
                  <div><strong>{specialisation.nom}</strong><code>{specialisation.code}</code></div>
                  <p>{specialisation.description || "Aucune description spécifique."}</p>
                  <span>{count} information{count > 1 ? "s" : ""} liée{count > 1 ? "s" : ""}</span>
                </article>
              );
            })}
          </div>
        ) : <p className="overview-empty">Cette formation ne contient aucune spécialisation.</p>}
      </section>

      <section className="overview-section admin-card">
        <header><div><span className="eyebrow">Connaissances académiques</span><h2>Matières, compétences et toutes les informations</h2></div><Link to="/admin/elements">Gérer les informations</Link></header>
        <ElementGroups overview={overview} />
      </section>

      <section className="overview-section admin-card">
        <header><div><span className="eyebrow">Admission</span><h2>Règles appliquées par le chatbot</h2></div><Link to="/admin/orientation-rules">Modifier les règles</Link></header>
        {overview.orientation_rules.length ? (
          <div className="rule-overview-list">
            {overview.orientation_rules.map((rule) => (
              <article key={rule.id}>
                <div><strong>{rule.nom}</strong><span>{humanizeEnum(rule.type_regle)} · priorité {rule.priorite}</span></div>
                <p>{formatCriteria(rule.criteres)}</p>
                {rule.description && <small>{rule.description}</small>}
                <small>Portée : {rule.specialisation_id ? specialisationName(rule.specialisation_id, overview) : "Toute la formation"} · Source : {rule.source_ref || "non renseignée"}</small>
              </article>
            ))}
          </div>
        ) : <p className="overview-empty">Aucune règle d’admission active n’est renseignée.</p>}
      </section>

      <section className="overview-section admin-card">
        <header><div><span className="eyebrow">Finances</span><h2>Tarifs avec parcours et formation</h2></div><Link to="/admin/tarifs">Gérer les tarifs</Link></header>
        {overview.tarifs.length ? (
          <div className="tariff-overview-grid">
            {overview.tarifs.map((tarif) => {
              const specialisation = overview.specialisations.find((item) => item.id === tarif.specialisation_id);
              const total = tariffTotal(tarif);
              return (
                <article key={tarif.id}>
                  <span className="overview-breadcrumb">{parcours.nom} / {formation.nom}{specialisation ? ` / ${specialisation.nom}` : ""}</span>
                  <div className="tariff-overview__title"><strong>{tarif.annee_universitaire || "Année non précisée"}</strong><span>{formatLanguage(tarif.langue_enseignement)} · {humanizeEnum(tarif.statut)}</span></div>
                  <dl>
                    <div><dt>Inscription</dt><dd>{formatCurrency(tarif.frais_inscription, tarif.devise)}</dd></div>
                    <div><dt>Mensualité</dt><dd>{formatCurrency(tarif.mensualite, tarif.devise)}</dd></div>
                    <div><dt>Échéances</dt><dd>{tarif.nb_mensualites ?? "—"}</dd></div>
                    <div><dt>Total indicatif</dt><dd>{total === null ? "—" : formatCurrency(total, tarif.devise)}</dd></div>
                  </dl>
                  {tarif.remarque && <p>{tarif.remarque}</p>}
                  <small>Source : {tarif.source_ref || "non renseignée"}</small>
                </article>
              );
            })}
          </div>
        ) : <p className="overview-empty">Aucun tarif n’est renseigné pour cette formation.</p>}
      </section>

      <section className="overview-section admin-card">
        <header><div><span className="eyebrow">Reconnaissance</span><h2>Accréditations</h2></div><Link to="/admin/accreditations">Gérer</Link></header>
        {overview.accreditations.length ? overview.accreditations.map((item) => (
          <article className="accreditation-overview" key={item.id}><strong>{item.nom}</strong><span>{item.organisme || "Organisme non renseigné"}</span>{item.description && <p>{item.description}</p>}</article>
        )) : <p className="overview-empty">Aucune accréditation n’est rattachée à cette formation.</p>}
      </section>

      <section className="overview-section admin-card">
        <header><div><span className="eyebrow">Assistant</span><h2>Aperçu exact des documents RAG</h2><p>Ces textes sont générés depuis la base académique puis envoyés à l’index de connaissances.</p></div><Link to="/admin/rag">Suivre l’indexation</Link></header>
        <RagDocuments documents={overview.rag_documents} />
      </section>
    </div>
  );
}

function GlobalSheet({ data }: { data: AcademicOverviewResponse }) {
  return (
    <div className="formation-sheet">
      <section className="overview-hero admin-card">
        <div><span className="overview-breadcrumb">Portée globale</span><h2>Informations générales IIT</h2><p>Contacts et informations utilisées pour toutes les formations.</p></div>
      </section>
      <section className="overview-section admin-card">
        <header><div><h2>Informations globales</h2></div><Link to="/admin/elements">Gérer</Link></header>
        <div className="academic-fact-grid">
          {data.global_elements.map((element) => (
            <article key={element.id}><strong>{element.nom}</strong>{element.description && <p>{element.description}</p>}<small>Source : {element.source_ref || "non renseignée"}</small></article>
          ))}
        </div>
      </section>
      <section className="overview-section admin-card">
        <header><div><h2>Documents RAG globaux</h2></div><Link to="/admin/rag">Indexation</Link></header>
        <RagDocuments documents={data.global_rag_documents} />
      </section>
    </div>
  );
}

export function AcademicOverviewPage() {
  const [data, setData] = useState<AcademicOverviewResponse | null>(null);
  const [selected, setSelected] = useState<string>("global");
  const [search, setSearch] = useState("");
  const [includeInactive, setIncludeInactive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    void adminApi.academicOverview(includeInactive)
      .then((response) => {
        if (!active) return;
        setData(response);
        setSelected((currentSelected) =>
          currentSelected !== "global"
          && !response.formations.some((item) => String(item.formation.id) === currentSelected)
            ? "global"
            : currentSelected,
        );
      })
      .catch((reason) => active && setError(errorMessage(reason)))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [includeInactive]);

  const filtered = useMemo(() => {
    const normalized = search.trim().toLocaleLowerCase("fr");
    if (!data || !normalized) return data?.formations ?? [];
    return data.formations.filter((item) =>
      `${item.parcours.nom} ${item.formation.nom} ${item.formation.code}`.toLocaleLowerCase("fr").includes(normalized),
    );
  }, [data, search]);

  const current = data?.formations.find((item) => String(item.formation.id) === selected) ?? null;

  return (
    <section className="admin-page" aria-labelledby="overview-title">
      <header className="page-heading">
        <div><span className="eyebrow">Lecture simplifiée de la base</span><h1 id="overview-title">Fiches académiques complètes</h1><p>Consultez, par parcours et formation, tout ce que le chatbot peut utiliser : sections, matières, règles, tarifs, débouchés, sources et documents RAG.</p></div>
        <Link className="button button--secondary" to="/admin/orientation-matrix"><Icon name="sparkles" /> Diagnostic des règles</Link>
      </header>

      <div className="overview-toolbar admin-card">
        <label className="search-field"><Icon name="search" /><input type="search" placeholder="Rechercher une formation…" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
        <label className="checkbox-field checkbox-field--inline"><input type="checkbox" checked={includeInactive} onChange={(event) => setIncludeInactive(event.target.checked)} /><span>Inclure les données inactives</span></label>
      </div>

      {error && <div className="alert alert--error" role="alert">{error}</div>}
      {loading && !data && <div className="table-loading"><span className="spinner" /> Chargement des fiches complètes…</div>}

      {data && (
        <div className="academic-overview-layout">
          <aside className="academic-overview-nav admin-card" aria-label="Formations">
            <button className={selected === "global" ? "active" : ""} type="button" onClick={() => setSelected("global")}><span><strong>Informations générales IIT</strong><small>{data.global_elements.length} information(s)</small></span><Icon name="chevron-right" /></button>
            {filtered.map((item) => (
              <button className={selected === String(item.formation.id) ? "active" : ""} type="button" key={item.formation.id} onClick={() => setSelected(String(item.formation.id))}>
                <span><small>{item.parcours.nom}</small><strong>{item.formation.nom}</strong><small>{item.elements.length} infos · {item.orientation_rules.length} règles · {item.tarifs.length} tarifs</small></span><Icon name="chevron-right" />
              </button>
            ))}
          </aside>
          <main className="academic-overview-content">
            {selected === "global" ? <GlobalSheet data={data} /> : current ? <FormationSheet overview={current} /> : <p className="overview-empty">Sélectionnez une formation.</p>}
          </main>
        </div>
      )}
    </section>
  );
}

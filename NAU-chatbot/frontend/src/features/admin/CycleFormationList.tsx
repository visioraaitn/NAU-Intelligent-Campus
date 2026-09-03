import { Link } from "react-router-dom";
import { Icon } from "../../components/Icon";
import type { AcademicCycleOverviewResponse, Formation } from "../../types/academic";

export function CycleFormationList({ overview, onAdd, onEdit }: { overview: AcademicCycleOverviewResponse; onAdd: () => void; onEdit?: (formation: Formation) => void }) {
  return (
    <section className="workspace-panel admin-card">
      <header><div><h2>Formations du cycle</h2><p>Disciplines et diplômes rattachés à {overview.parcours.nom}.</p></div><button className="button button--primary button--compact" type="button" onClick={onAdd}><Icon name="plus" /> Ajouter une formation</button></header>
      {overview.formations.length ? <div className="cycle-formation-list">{overview.formations.map((formation) => <article key={formation.id}><Link to={`/admin/academic-overview?formation_id=${formation.id}`}><span><strong>{formation.nom}</strong><small>{formation.intitule_diplome || formation.code}</small></span><span className={`status-badge ${formation.actif ? "status-badge--active" : "status-badge--inactive"}`}>{formation.actif ? "Actif" : "Inactif"}</span><Icon name="chevron-right" /></Link>{onEdit && <button className="icon-button" type="button" onClick={() => onEdit(formation)} aria-label={`Modifier ${formation.nom}`}><Icon name="edit" /></button>}</article>)}</div> : <div className="workspace-empty-state"><p>Aucune formation n’est encore rattachée à ce cycle.</p><button className="button button--secondary" type="button" onClick={onAdd}><Icon name="plus" /> Créer la première formation</button></div>}
    </section>
  );
}

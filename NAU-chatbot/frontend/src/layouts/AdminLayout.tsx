import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Brand } from "../components/Brand";
import { Icon } from "../components/Icon";
import { entityConfigList } from "../features/admin/entityConfig";
import { useAuth } from "../features/auth/AuthContext";

export function AdminLayout() {
  const { logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);

  useEffect(() => setMenuOpen(false), [location.pathname]);

  useEffect(() => {
    if (!menuOpen) return;
    const close = (event: KeyboardEvent) => event.key === "Escape" && setMenuOpen(false);
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [menuOpen]);

  const handleLogout = async () => {
    setLoggingOut(true);
    await logout();
    navigate("/admin/connexion", { replace: true });
  };

  return (
    <div className="admin-shell">
      <a className="skip-link" href="#admin-content">Aller au contenu</a>
      <aside className={`admin-sidebar ${menuOpen ? "admin-sidebar--open" : ""}`} aria-label="Navigation d’administration">
        <div className="admin-sidebar__brand">
          <Brand link="/admin" />
          <button className="icon-button admin-sidebar__close" type="button" onClick={() => setMenuOpen(false)} aria-label="Fermer le menu">
            <Icon name="close" />
          </button>
        </div>
        <nav className="admin-nav">
          <span className="admin-nav__label">Vue d’ensemble</span>
          <NavLink end to="/admin" className={({ isActive }) => isActive ? "active" : undefined}>
            <Icon name="dashboard" /> Tableau de bord
          </NavLink>
          <NavLink to="/admin/academic-overview" className={({ isActive }) => isActive ? "active" : undefined}>
            <Icon name="database" /> Fiches académiques
          </NavLink>
          <NavLink to="/admin/orientation-matrix" className={({ isActive }) => isActive ? "active" : undefined}>
            <Icon name="sparkles" /> Diagnostic orientation
          </NavLink>
          <span className="admin-nav__label">Données académiques</span>
          {entityConfigList.filter((config) => config.resource !== "orientation-rules").map((config) => (
            <NavLink
              key={config.resource}
              to={`/admin/${config.resource}`}
              className={({ isActive }) => isActive ? "active" : undefined}
            >
              <Icon name="database" /> {config.title}
            </NavLink>
          ))}
          <span className="admin-nav__label">Règles</span>
          <NavLink to="/admin/orientation-rules" className={({ isActive }) => isActive ? "active" : undefined}>
            <Icon name="edit" /> Règles d’orientation
          </NavLink>
          <span className="admin-nav__label">Assistant</span>
          <NavLink to="/admin/rag" className={({ isActive }) => isActive ? "active" : undefined}>
            <Icon name="sparkles" /> Indexation RAG
          </NavLink>
        </nav>
        <div className="admin-sidebar__footer">
          <Link className="sidebar-public-link" to="/" target="_blank" rel="noreferrer">
            <Icon name="external" /> Voir l’assistant public
          </Link>
          <button type="button" onClick={() => void handleLogout()} disabled={loggingOut}>
            <Icon name="logout" /> {loggingOut ? "Déconnexion…" : "Se déconnecter"}
          </button>
        </div>
      </aside>

      {menuOpen && <button className="sidebar-scrim" type="button" aria-label="Fermer le menu" onClick={() => setMenuOpen(false)} />}

      <div className="admin-main">
        <header className="admin-topbar">
          <button className="icon-button admin-menu-button" type="button" onClick={() => setMenuOpen(true)} aria-label="Ouvrir le menu">
            <Icon name="menu" />
          </button>
          <div className="admin-topbar__title">
            <span>Administration</span>
            <strong>IIT Knowledge</strong>
          </div>
          <div className="admin-user" aria-label="Session administrateur">
            <span className="admin-user__avatar" aria-hidden="true">A</span>
            <span><strong>Administrateur</strong><small>Session sécurisée</small></span>
          </div>
        </header>
        <main className="admin-content" id="admin-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

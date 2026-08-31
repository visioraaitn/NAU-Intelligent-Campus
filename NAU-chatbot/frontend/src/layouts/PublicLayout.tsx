import { Outlet } from "react-router-dom";
import { Brand } from "../components/Brand";

export function PublicLayout() {
  return (
    <div className="public-shell">
      <a className="skip-link" href="#main-content">Aller au contenu</a>
      <header className="public-header">
        <Brand />
        <span className="public-header__label">Assistant académique</span>
      </header>
      <Outlet />
      <footer className="public-footer">
        <p>Les réponses sont indicatives. Vérifiez les informations importantes auprès de l’IIT.</p>
      </footer>
    </div>
  );
}

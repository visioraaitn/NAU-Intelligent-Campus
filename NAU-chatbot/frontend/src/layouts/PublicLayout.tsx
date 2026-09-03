import { Outlet, useLocation } from "react-router-dom";
import { Brand } from "../components/Brand";

export function PublicLayout() {
  const pathname = useLocation().pathname;
  const isChat = pathname.startsWith("/chat");
  const isAuth = pathname === "/login" || pathname === "/signup";
  const immersive = isChat || isAuth;
  return (
    <div className={`public-shell ${isChat ? "public-shell--chat" : ""} ${isAuth ? "public-shell--auth" : ""}`}>
      <a className="skip-link" href="#main-content">Aller au contenu</a>
      {!immersive && <header className="public-header">
        <Brand />
        <span className="public-header__label">Orientation &amp; admissions</span>
      </header>}
      <Outlet />
      {!immersive && <footer className="public-footer">
        <p>Les réponses sont indicatives. Vérifiez les informations importantes auprès de l’IIT.</p>
      </footer>}
    </div>
  );
}

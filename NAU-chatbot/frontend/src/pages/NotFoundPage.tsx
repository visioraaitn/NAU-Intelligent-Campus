import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <main className="not-found">
      <span className="not-found__code">404</span>
      <h1>Page introuvable</h1>
      <p>La page demandée n’existe pas ou a été déplacée.</p>
      <Link className="button button--primary" to="/">Retour à l’accueil</Link>
    </main>
  );
}

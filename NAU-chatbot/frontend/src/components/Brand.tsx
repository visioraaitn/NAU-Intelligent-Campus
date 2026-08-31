import { Link } from "react-router-dom";

export function Brand({ compact = false, link = "/" }: { compact?: boolean; link?: string }) {
  return (
    <Link className="brand" to={link} aria-label="IIT — Accueil">
      <span className="brand__mark" aria-hidden="true">IIT</span>
      {!compact && (
        <span className="brand__copy">
          <strong>Institut International</strong>
          <span>de Technologie</span>
        </span>
      )}
    </Link>
  );
}

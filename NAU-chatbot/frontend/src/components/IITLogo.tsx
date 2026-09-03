import { Link } from "react-router-dom";

interface IITLogoProps {
  className?: string;
  link?: string;
  decorative?: boolean;
}

export function IITLogo({ className = "", link, decorative = false }: IITLogoProps) {
  const wordmark = (
    <>
      <span className="iit-logo__mark" aria-hidden="true">IIT</span>
      <span className="iit-logo__copy">
        <strong>Institut International</strong>
        <span>de Technologie</span>
      </span>
    </>
  );

  if (!link) {
    return <span className={`iit-logo ${className}`.trim()} aria-hidden={decorative || undefined}>{wordmark}</span>;
  }

  return (
    <Link className={`iit-logo ${className}`.trim()} to={link} aria-label="IIT — Accueil">
      {wordmark}
    </Link>
  );
}

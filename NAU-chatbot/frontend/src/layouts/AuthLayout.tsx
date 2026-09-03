import type { ReactNode } from "react";
import { IITLogo } from "../components/IITLogo";

interface AuthLayoutProps {
  titleId: string;
  eyebrow: string;
  title: string;
  subtitle: string;
  children: ReactNode;
  footer: ReactNode;
}

export function AuthLayout({ titleId, eyebrow, title, subtitle, children, footer }: AuthLayoutProps) {
  return (
    <main className="auth-page" id="main-content">
      <section className="auth-panel" aria-labelledby={titleId}>
        <div className="auth-panel__content">
          <IITLogo className="auth-panel__logo" link="/login" />
          <div className="auth-panel__heading">
            <span className="eyebrow">{eyebrow}</span>
            <h1 id={titleId}>{title}</h1>
            <p>{subtitle}</p>
          </div>
          {children}
          {footer}
        </div>
      </section>

      <aside className="auth-brand-panel" aria-label="Présentation de l’assistant IIT">
        <div className="auth-brand-panel__content">
          <span className="auth-brand-panel__accent" aria-hidden="true" />
          <IITLogo className="auth-brand-panel__logo" decorative />
          <span className="auth-brand-panel__label">IIT Assistant</span>
          <h2>Votre assistant académique IIT</h2>
          <p>Orientation, admission et informations académiques dans un espace personnel.</p>
          <ul>
            <li>Explorez les formations</li>
            <li>Vérifiez votre admissibilité</li>
            <li>Retrouvez vos conversations</li>
          </ul>
        </div>
      </aside>
    </main>
  );
}

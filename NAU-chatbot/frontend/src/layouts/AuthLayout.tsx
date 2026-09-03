import type { ReactNode } from "react";
import { Brand } from "../components/Brand";
import { Icon } from "../components/Icon";

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
          <div className="auth-panel__header">
            <Brand link="/login" />
          </div>

          <div className="auth-panel__heading">
            <span className="auth-pill-tag">{eyebrow}</span>
            <h1 id={titleId}>{title}</h1>
            <p>{subtitle}</p>
          </div>

          {children}
          {footer}
        </div>
      </section>

      <aside className="auth-brand-panel" aria-label="Présentation de l'assistant IIT">
        <div className="auth-brand-panel__glow" aria-hidden="true" />
        <div className="auth-brand-panel__content">
          <div className="auth-brand-panel__brand">
            <Brand link="/login" />
          </div>

          <span className="auth-hero-badge">
            <Icon name="sparkles" />
            <span>Assistant Académique &amp; Orientation IA</span>
          </span>

          <p>
            Rejoignez l'Institut International de Technologie pour explorer vos futures formations,
            vérifier votre éligibilité et échanger avec votre assistant sur-mesure.
          </p>

          <div className="auth-features">
            <div className="auth-feature-card">
              <div className="auth-feature-card__icon" aria-hidden="true">
                <Icon name="sparkles" />
              </div>
              <div className="auth-feature-card__text">
                <strong>Orientation &amp; Diagnostic</strong>
                <span>Identifiez les spécialités adaptées à votre profil et vos objectifs.</span>
              </div>
            </div>

            <div className="auth-feature-card">
              <div className="auth-feature-card__icon" aria-hidden="true">
                <Icon name="database" />
              </div>
              <div className="auth-feature-card__text">
                <strong>Catalogue &amp; Cycles d'Ingénieur</strong>
                <span>Accédez aux maquettes, tarifs, débouchés et accréditations.</span>
              </div>
            </div>

            <div className="auth-feature-card">
              <div className="auth-feature-card__icon" aria-hidden="true">
                <Icon name="chat" />
              </div>
              <div className="auth-feature-card__text">
                <strong>Discussions &amp; Accompagnement</strong>
                <span>Conservez l'historique de vos échanges et suivez votre préinscription.</span>
              </div>
            </div>
          </div>

          <div className="auth-trust-badge">
            <span className="auth-trust-dot" aria-hidden="true" />
            <span>Diplômes agréés par l'État · Reconnaissance internationale</span>
          </div>
        </div>
      </aside>
    </main>
  );
}

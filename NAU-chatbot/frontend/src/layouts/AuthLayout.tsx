import type { ReactNode } from "react";
import { Brand } from "../components/Brand";

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
    </main>
  );
}

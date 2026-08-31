import { Component, type ErrorInfo, type ReactNode } from "react";

interface ErrorBoundaryState {
  failed: boolean;
}

export class ErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  state: ErrorBoundaryState = { failed: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { failed: true };
  }

  componentDidCatch(_error: Error, _info: ErrorInfo): void {
    // Runtime details intentionally stay out of the UI.
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <main className="fatal-error">
        <div className="empty-state">
          <h1>L’application n’a pas pu s’afficher</h1>
          <p>Rechargez la page. Si le problème persiste, réessayez plus tard.</p>
          <button className="button button--primary" type="button" onClick={() => window.location.reload()}>
            Recharger
          </button>
        </div>
      </main>
    );
  }
}

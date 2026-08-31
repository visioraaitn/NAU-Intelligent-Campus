import { type FormEvent, useEffect, useRef, useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { Brand } from "../components/Brand";
import { Icon } from "../components/Icon";
import { useAuth } from "../features/auth/AuthContext";
import { errorMessage } from "../utils/errors";

interface LocationState {
  from?: string;
}

export function LoginPage() {
  const { status, isAuthenticated, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const usernameRef = useRef<HTMLInputElement>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => usernameRef.current?.focus(), []);

  if (isAuthenticated) return <Navigate to="/admin" replace />;

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await login(username.trim(), password);
      const requested = (location.state as LocationState | null)?.from;
      navigate(requested?.startsWith("/admin/") ? requested : "/admin", { replace: true });
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="login-page">
      <section className="login-panel" aria-labelledby="login-title">
        <Brand link="/" />
        <div className="login-panel__heading">
          <span className="eyebrow">Espace sécurisé</span>
          <h1 id="login-title">Administration académique</h1>
          <p>Connectez-vous pour gérer le catalogue publié et son indexation.</p>
        </div>

        {error && <div className="alert alert--error" role="alert">{error}</div>}

        <form className="auth-form" onSubmit={handleSubmit}>
          <label className="field">
            <span>Identifiant</span>
            <input
              ref={usernameRef}
              autoComplete="username"
              maxLength={100}
              name="username"
              required
              value={username}
              onChange={(event) => setUsername(event.target.value)}
            />
          </label>
          <label className="field">
            <span>Mot de passe</span>
            <input
              autoComplete="current-password"
              maxLength={256}
              name="password"
              required
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          <button className="button button--primary button--wide" disabled={busy || status === "checking"} type="submit">
            {busy && <span className="spinner spinner--small" aria-hidden="true" />}
            {busy ? "Connexion…" : "Se connecter"}
          </button>
        </form>
        <Link className="back-link" to="/">
          <Icon name="chevron-left" /> Retour à l’assistant
        </Link>
      </section>
      <aside className="login-aside" aria-hidden="true">
        <div className="login-aside__orb" />
        <div className="login-aside__copy">
          <span className="eyebrow">IIT Knowledge</span>
          <h2>Une source fiable, une information toujours à jour.</h2>
        </div>
      </aside>
    </main>
  );
}

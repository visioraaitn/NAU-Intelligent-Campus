import { type FormEvent, useEffect, useRef, useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../features/auth/AuthContext";
import { AuthLayout } from "../layouts/AuthLayout";
import { errorMessage } from "../utils/errors";

interface LocationState {
  from?: string;
}

export function LoginPage() {
  const { status, isAuthenticated, user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const usernameRef = useRef<HTMLInputElement>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => usernameRef.current?.focus(), []);

  if (isAuthenticated) return <Navigate to={user?.role === "ADMIN" ? "/admin" : "/chat"} replace />;

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const authenticatedUser = await login(username.trim(), password);
      const requested = (location.state as LocationState | null)?.from;
      const home = authenticatedUser.role === "ADMIN" ? "/admin" : "/chat";
      const allowedRequest = authenticatedUser.role === "ADMIN"
        ? requested?.startsWith("/admin")
        : requested?.startsWith("/chat");
      navigate(allowedRequest && requested ? requested : home, { replace: true });
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthLayout
      titleId="login-title"
      eyebrow="IIT Assistant"
      title="Bienvenue"
      subtitle="Accédez à votre assistant académique IIT."
      footer={<p className="auth-switch">Pas encore de compte ? <Link to="/signup">Créer un compte</Link></p>}
    >
        {error && <div className="alert alert--error" role="alert">{error}</div>}

        <form className="auth-form" onSubmit={handleSubmit}>
          <label className="field">
            <span>Email ou identifiant</span>
            <input
              ref={usernameRef}
              autoComplete="username"
              maxLength={320}
              name="username"
              placeholder=" "
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
              placeholder=" "
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
    </AuthLayout>
  );
}

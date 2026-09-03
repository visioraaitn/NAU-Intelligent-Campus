import { type FormEvent, useEffect, useRef, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../features/auth/AuthContext";
import { AuthLayout } from "../layouts/AuthLayout";
import { errorMessage } from "../utils/errors";

export function SignupPage() {
  const { status, isAuthenticated, user, signup } = useAuth();
  const navigate = useNavigate();
  const nameRef = useRef<HTMLInputElement>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => nameRef.current?.focus(), []);
  if (isAuthenticated) return <Navigate to={user?.role === "ADMIN" ? "/admin" : "/chat"} replace />;

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (busy) return;
    if (password !== confirmation) {
      setError("Les mots de passe ne correspondent pas.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await signup({ name, email, password, password_confirmation: confirmation });
      navigate("/chat", { replace: true });
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthLayout
      titleId="signup-title"
      eyebrow="IIT Assistant"
      title="Créer un compte"
      subtitle="Enregistrez vos échanges et reprenez votre orientation à tout moment."
      footer={<p className="auth-switch">Déjà inscrit ? <Link to="/login">Se connecter</Link></p>}
    >
        {error && <div className="alert alert--error" role="alert">{error}</div>}
        <form className="auth-form" onSubmit={handleSubmit}>
          <label className="field">
            <span>Nom</span>
            <input ref={nameRef} autoComplete="name" maxLength={120} placeholder=" " required value={name} onChange={(event) => setName(event.target.value)} />
          </label>
          <label className="field">
            <span>Email</span>
            <input autoComplete="email" maxLength={320} placeholder=" " required type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
          </label>
          <label className="field">
            <span>Mot de passe</span>
            <input autoComplete="new-password" minLength={8} maxLength={256} placeholder=" " required type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
          </label>
          <label className="field">
            <span>Confirmer le mot de passe</span>
            <input autoComplete="new-password" minLength={8} maxLength={256} placeholder=" " required type="password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} />
          </label>
          <button className="button button--primary button--wide" disabled={busy || status === "checking"} type="submit">{busy ? "Création…" : "Créer mon compte"}</button>
        </form>
    </AuthLayout>
  );
}

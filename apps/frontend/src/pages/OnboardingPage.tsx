import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { bootstrapAdmin } from "../api/auth";
import { useAuth } from "../hooks/useAuth";

export function OnboardingPage() {
  const [email, setEmail] = useState("admin@example.com");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();
  const { markBootstrapCompleted } = useAuth();

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      await bootstrapAdmin(email, password);
      markBootstrapCompleted();
      navigate("/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bootstrap failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      <form className="card form-card" onSubmit={onSubmit}>
        <h2>First-run Admin Setup</h2>
        <p>Create the initial local administrator account.</p>
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          Password (min 12 chars)
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={12}
            required
          />
        </label>
        {error ? <div className="error">{error}</div> : null}
        <button className="btn" type="submit" disabled={submitting}>
          {submitting ? "Creating..." : "Create Admin"}
        </button>
      </form>
    </div>
  );
}

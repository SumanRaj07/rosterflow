import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { auth, errMsg } from "../api";
import { Btn, ErrorBox, inputCls } from "../components/ui";

const DEMOS = [
  { label: "Admin", email: "admin@rosterflow.local", password: "Admin@123" },
  { label: "Manager", email: "manager@rosterflow.local", password: "Manager@123" },
  { label: "Pod Lead", email: "lead.a@rosterflow.local", password: "Lead@123" },
  { label: "Employee", email: "aarav.sharma@example.com", password: "Emp@123" },
];

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const res = await auth.login(email, password);
      localStorage.setItem("rosterflow_token", res.token);
      localStorage.setItem("rosterflow_user", JSON.stringify(res.user));
      navigate("/");
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="bg-surface border border-border rounded-lg shadow-sm p-6 w-full max-w-md">
        <h1 className="text-xl font-bold text-ink">RosterFlow</h1>
        <p className="text-sm text-muted mt-1 mb-4">
          Smart Roster Management System
        </p>
        <ErrorBox message={error} />
        <form onSubmit={submit} className="space-y-3">
          <div>
            <label className="text-sm text-muted">Email</label>
            <input
              className={inputCls}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="text-sm text-muted">Password</label>
            <input
              type="password"
              className={inputCls}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <Btn type="submit" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </Btn>
        </form>
        <div className="mt-5">
          <p className="text-xs text-muted mb-2">Demo accounts (click to fill):</p>
          <div className="flex flex-wrap gap-2">
            {DEMOS.map((d) => (
              <Btn
                key={d.label}
                tone="secondary"
                small
                onClick={() => {
                  setEmail(d.email);
                  setPassword(d.password);
                }}
              >
                {d.label}
              </Btn>
            ))}
          </div>
          <p className="text-xs text-muted mt-3">
            Employee demo uses the first seeded employee (EMP001, Aarav Sharma).
          </p>
        </div>
      </div>
    </div>
  );
}

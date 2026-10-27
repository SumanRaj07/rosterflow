import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { brandsApi, errMsg, podsApi, processesApi, rostersApi } from "../api";
import type { Brand, Pod, Process, Roster } from "../api";
import { Btn, Card, ErrorBox, Field, inputCls } from "../components/ui";

export default function Generator() {
  const [brands, setBrands] = useState<Brand[]>([]);
  const [pods, setPods] = useState<Pod[]>([]);
  const [procs, setProcs] = useState<Process[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Roster | null>(null);
  const [form, setForm] = useState({
    month: 11,
    year: 2026,
    brand_id: "",
    pod_id: "",
    process_id: "",
    strategy: "balanced",
    preferences_applied: true,
    generate_plans: true,
  });

  useEffect(() => {
    brandsApi.list({ limit: 100 }).then((d) => setBrands(d.items)).catch(() => undefined);
    podsApi.list().then((d) => setPods(d.items)).catch(() => undefined);
    processesApi.list({ limit: 100 }).then((d) => setProcs(d.items)).catch(() => undefined);
  }, []);

  async function generate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const r = await rostersApi.generate({
        month: form.month,
        year: form.year,
        brand_id: form.brand_id ? Number(form.brand_id) : null,
        pod_id: form.pod_id ? Number(form.pod_id) : null,
        process_id: form.process_id ? Number(form.process_id) : null,
        strategy: form.strategy,
        preferences_applied: form.preferences_applied,
        generate_plans: form.generate_plans,
      });
      setResult(r);
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setBusy(false);
    }
  }

  const m = result?.metrics;
  const perEmp = m
    ? Object.entries(m.per_employee).sort((a, b) => b[1].workdays - a[1].workdays)
    : [];

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Roster Generator</h1>
      <ErrorBox message={error} />
      <Card title="Generate a monthly roster" subtitle="Deterministic greedy engine: hard constraints (leave, availability, qualification, consecutive days, workload caps) are never violated.">
        <form onSubmit={generate} className="space-y-3">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Field label="Month">
              <select className={inputCls} value={form.month} onChange={(e) => setForm({ ...form, month: Number(e.target.value) })}>
                {Array.from({ length: 12 }, (_, i) => (
                  <option key={i + 1} value={i + 1}>
                    {new Date(form.year, i, 1).toLocaleString("en", { month: "long" })}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Year">
              <input className={inputCls} type="number" value={form.year} onChange={(e) => setForm({ ...form, year: Number(e.target.value) })} />
            </Field>
            <Field label="Strategy">
              <select className={inputCls} value={form.strategy} onChange={(e) => setForm({ ...form, strategy: e.target.value })}>
                <option value="balanced">Balanced (workload-first)</option>
                <option value="preference">Preference-first</option>
                <option value="weekend_fair">Weekend-fair</option>
              </select>
            </Field>
            <Field label="Brand (optional)">
              <select className={inputCls} value={form.brand_id} onChange={(e) => setForm({ ...form, brand_id: e.target.value })}>
                <option value="">All brands</option>
                {brands.map((b) => (
                  <option key={b.id} value={b.id}>{b.name}</option>
                ))}
              </select>
            </Field>
            <Field label="Pod (optional)">
              <select className={inputCls} value={form.pod_id} onChange={(e) => setForm({ ...form, pod_id: e.target.value })}>
                <option value="">All pods</option>
                {pods.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </Field>
            <Field label="Process (optional)">
              <select className={inputCls} value={form.process_id} onChange={(e) => setForm({ ...form, process_id: e.target.value })}>
                <option value="">All processes</option>
                {procs.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </Field>
          </div>
          <div className="flex gap-4 text-sm">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={form.preferences_applied} onChange={(e) => setForm({ ...form, preferences_applied: e.target.checked })} />
              Apply employee preferences
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={form.generate_plans} onChange={(e) => setForm({ ...form, generate_plans: e.target.checked })} />
              Also generate 3 alternative plans
            </label>
          </div>
          <Btn type="submit" disabled={busy}>{busy ? "Generating…" : "Generate roster"}</Btn>
        </form>
      </Card>

      {result && m && (
        <Card title={`Roster #${result.id} — ${result.month}/${result.year} (${result.status})`}>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm mb-4">
            <div className="bg-bg rounded-md p-3">
              <div className="text-xl font-bold">{Math.round(m.coverage_rate * 1000) / 10}%</div>
              <div className="text-muted">Coverage ({m.filled_slots}/{m.required_slots} slots)</div>
            </div>
            <div className="bg-bg rounded-md p-3">
              <div className="text-xl font-bold">{Math.round(m.fairness_score * 1000) / 10}%</div>
              <div className="text-muted">Fairness (scheduled staff)</div>
            </div>
            <div className="bg-bg rounded-md p-3">
              <div className="text-xl font-bold">{m.gap_count}</div>
              <div className="text-muted">Coverage gaps</div>
            </div>
            <div className="bg-bg rounded-md p-3">
              <div className="text-xl font-bold">{Math.round(m.preference_satisfied_rate * 1000) / 10}%</div>
              <div className="text-muted">Preference satisfaction ({m.preference_conflicts} conflicts)</div>
            </div>
          </div>
          <p className="text-sm text-muted mb-3">
            Workdays: mean {m.workday_mean}, std {m.workday_std}. Fairness across all
            employees (including unused backup pool):{" "}
            {Math.round(m.fairness_score_all_employees * 1000) / 10}%.
          </p>
          <div className="text-sm">
            <h4 className="font-semibold mb-1">Per-employee workdays</h4>
            <p className="text-muted">
              {perEmp.map(([id, v]) => `#${id}: ${v.workdays}d`).join(" · ")}
            </p>
          </div>
          <div className="mt-4 flex gap-2">
            <Link to={`/roster?id=${result.id}`} className="text-primary text-sm font-medium">
              Open roster calendar →
            </Link>
            <Link to="/approvals" className="text-primary text-sm font-medium">
              Send for approval →
            </Link>
            {form.generate_plans && (
              <Link to={`/plans?month=${result.month}&year=${result.year}`} className="text-primary text-sm font-medium">
                Compare alternative plans →
              </Link>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}

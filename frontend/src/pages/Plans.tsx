import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { errMsg, plansApi } from "../api";
import type { Plan } from "../api";
import { Badge, Btn, Card, Empty, ErrorBox, inputCls } from "../components/ui";

export default function Plans() {
  const [params] = useSearchParams();
  const [list, setList] = useState<Plan[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [month, setMonth] = useState(params.get("month") || "");
  const [year, setYear] = useState(params.get("year") || "");
  const [applied, setApplied] = useState<string | null>(null);

  function load() {
    plansApi
      .list({
        ...(month ? { month: Number(month) } : {}),
        ...(year ? { year: Number(year) } : {}),
      })
      .then(setList)
      .catch((e) => setError(errMsg(e)));
  }

  useEffect(load, [month, year]);

  async function apply(p: Plan) {
    try {
      const r = await plansApi.apply(p.id);
      setApplied(`Plan "${p.name}" applied as draft roster #${r.id}.`);
      load();
    } catch (err) {
      setError(errMsg(err));
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Alternative Plans</h1>
      <ErrorBox message={error} />
      {applied && (
        <div className="bg-green-50 border border-green-200 text-success text-sm rounded-md px-3 py-2">
          {applied}
        </div>
      )}
      <Card>
        <div className="flex gap-2 mb-4">
          <input className={inputCls} placeholder="Month (e.g. 11)" value={month} onChange={(e) => setMonth(e.target.value)} />
          <input className={inputCls} placeholder="Year (e.g. 2026)" value={year} onChange={(e) => setYear(e.target.value)} />
        </div>
        {list.length === 0 ? (
          <Empty text="No alternative plans. Generate a roster with 'Also generate 3 alternative plans' checked." />
        ) : (
          <div className="grid md:grid-cols-3 gap-4">
            {list.map((p) => (
              <div key={p.id} className="border border-border rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold">{p.name}</h3>
                  {p.is_selected && <Badge tone="blue">selected</Badge>}
                </div>
                <p className="text-sm text-muted">
                  {p.month}/{p.year} · strategy: {p.strategy}
                </p>
                {p.metrics && (
                  <dl className="text-sm mt-3 space-y-1">
                    <div className="flex justify-between">
                      <dt className="text-muted">Coverage</dt>
                      <dd className="font-medium">{Math.round(p.metrics.coverage_rate * 1000) / 10}%</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-muted">Fairness</dt>
                      <dd className="font-medium">{Math.round(p.metrics.fairness_score * 1000) / 10}%</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-muted">Gaps</dt>
                      <dd className="font-medium">{p.metrics.gap_count}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-muted">Preference satisfaction</dt>
                      <dd className="font-medium">{Math.round(p.metrics.preference_satisfied_rate * 1000) / 10}%</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-muted">Work assignments</dt>
                      <dd className="font-medium">{p.metrics.total_work_assignments}</dd>
                    </div>
                  </dl>
                )}
                <Btn small onClick={() => apply(p)} disabled={p.is_selected}>
                  {p.is_selected ? "Applied" : "Apply as draft roster"}
                </Btn>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

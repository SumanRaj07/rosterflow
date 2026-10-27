import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { conflictsApi, employeesApi, errMsg } from "../api";
import type { Conflict, Employee } from "../api";
import { Badge, Btn, Card, Empty, ErrorBox, inputCls } from "../components/ui";

export default function Conflicts() {
  const [list, setList] = useState<Conflict[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState("open");
  const [severity, setSeverity] = useState("");
  const [emps, setEmps] = useState<Employee[]>([]);

  function load() {
    conflictsApi
      .list({ status, ...(severity ? { severity } : {}) })
      .then(setList)
      .catch((e) => setError(errMsg(e)));
  }

  useEffect(load, [status, severity]);
  useEffect(() => {
    employeesApi.list({ limit: 200 }).then((d) => setEmps(d.items)).catch(() => undefined);
  }, []);

  const empName = (id: number | null) =>
    id === null ? "—" : emps.find((e) => e.id === id)?.full_name || `#${id}`;

  async function resolve(id: number) {
    try {
      await conflictsApi.resolve(id);
      load();
    } catch (err) {
      setError(errMsg(err));
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Conflict Center</h1>
      <ErrorBox message={error} />
      <Card>
        <div className="flex gap-2 mb-4">
          <select className={inputCls} value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All statuses</option>
            <option value="open">Open</option>
            <option value="resolved">Resolved</option>
          </select>
          <select className={inputCls} value={severity} onChange={(e) => setSeverity(e.target.value)}>
            <option value="">All severities</option>
            <option value="critical">Critical</option>
            <option value="warning">Warning</option>
          </select>
        </div>
        {list.length === 0 ? (
          <Empty text="No conflicts match these filters." />
        ) : (
          <ul className="space-y-3">
            {list.map((c) => (
              <li key={c.id} className="border border-border rounded-lg p-3 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={c.severity === "critical" ? "red" : "amber"}>{c.severity}</Badge>
                  <span className="font-semibold">{c.type}</span>
                  {c.date && <span className="text-muted">{c.date}</span>}
                  {c.roster_id && (
                    <Link to={`/roster?id=${c.roster_id}`} className="text-primary">
                      Roster #{c.roster_id}
                    </Link>
                  )}
                  {c.employee_id && <span className="text-muted">{empName(c.employee_id)}</span>}
                  <span className="ml-auto">
                    <Badge tone={c.status === "open" ? "amber" : "green"}>{c.status}</Badge>
                  </span>
                </div>
                {c.rule && <p className="text-muted mt-1">Rule: {c.rule}</p>}
                <p className="mt-1">{c.explanation}</p>
                {c.recommendation && (
                  <p className="text-muted mt-1">Recommendation: {c.recommendation}</p>
                )}
                {c.status === "open" && (
                  <div className="mt-2 flex gap-2">
                    <Btn small onClick={() => resolve(c.id)}>Mark resolved</Btn>
                    {c.roster_id && (
                      <Link to={`/backups?roster_id=${c.roster_id}`} className="text-primary text-xs font-medium py-1">
                        View backup recommendations →
                      </Link>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

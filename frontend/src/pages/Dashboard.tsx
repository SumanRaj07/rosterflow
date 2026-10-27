import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { dashboardApi, errMsg } from "../api";
import type { DashboardData } from "../api";
import { Badge, Card, Empty, ErrorBox } from "../components/ui";

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    dashboardApi.get().then(setData).catch((e) => setError(errMsg(e)));
  }, []);

  if (error) return <ErrorBox message={error} />;
  if (!data) return <p className="text-sm text-muted">Loading…</p>;

  const kpis = [
    { label: "Active employees", value: data.active_employees, to: "/employees" },
    { label: "Active brands", value: data.active_brands, to: "/brands" },
    { label: "Open conflicts", value: data.open_conflicts, to: "/conflicts" },
    { label: "Critical conflicts", value: data.critical_conflicts, to: "/conflicts" },
    { label: "Pending leave", value: data.pending_leave, to: "/leave" },
    { label: "Rosters in review", value: data.pending_review_rosters, to: "/approvals" },
    { label: "Published rosters", value: data.published_rosters, to: "/approvals" },
    {
      label: "Latest roster coverage",
      value:
        data.latest_roster_coverage === null
          ? "—"
          : `${Math.round(data.latest_roster_coverage * 1000) / 10}%`,
      to: "/reports",
    },
  ];

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Dashboard</h1>
      {data.brands_without_employees.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 text-warning text-sm rounded-md px-3 py-2">
          Brands without any assigned employees:{" "}
          {data.brands_without_employees.join(", ")} — assign staff before
          generating a roster for them.
        </div>
      )}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {kpis.map((k) => (
          <Link key={k.label} to={k.to}>
            <div className="bg-surface border border-border rounded-lg p-4 hover:border-primary">
              <div className="text-2xl font-bold text-ink">{k.value}</div>
              <div className="text-sm text-muted">{k.label}</div>
            </div>
          </Link>
        ))}
      </div>
      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Recent open conflicts">
          {data.recent_conflicts.length === 0 ? (
            <Empty text="No open conflicts." />
          ) : (
            <ul className="space-y-2">
              {data.recent_conflicts.map((c) => (
                <li key={c.id} className="text-sm border-b border-border pb-2">
                  <Badge tone={c.severity === "critical" ? "red" : "amber"}>
                    {c.severity}
                  </Badge>{" "}
                  <span className="text-muted">{c.type}</span>
                  {c.date && <span className="text-muted"> · {c.date}</span>}
                  <p className="text-ink mt-1">{c.explanation}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Pending leave requests">
          {data.pending_leave_items.length === 0 ? (
            <Empty text="No pending leave requests." />
          ) : (
            <ul className="space-y-2">
              {data.pending_leave_items.map((l) => (
                <li key={l.id} className="text-sm flex justify-between">
                  <span>
                    Employee #{l.employee_id} · {l.leave_type}
                  </span>
                  <span className="text-muted">
                    {l.start_date} → {l.end_date}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <Link to="/leave" className="text-sm text-primary mt-3 inline-block">
            Review all leave →
          </Link>
        </Card>
      </div>
    </div>
  );
}

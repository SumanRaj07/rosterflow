import { useEffect, useState } from "react";
import { downloadFile, errMsg, reportsApi, rostersApi } from "../api";
import type { Roster } from "../api";
import { Btn, Card, Empty, ErrorBox, inputCls } from "../components/ui";

export default function Reports() {
  const [rosters, setRosters] = useState<Roster[]>([]);
  const [rosterId, setRosterId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [coverage, setCoverage] = useState<unknown>(null);
  const [workload, setWorkload] = useState<Record<string, unknown>[]>([]);

  useEffect(() => {
    rostersApi.list().then(setRosters).catch((e) => setError(errMsg(e)));
  }, []);

  useEffect(() => {
    const params = rosterId ? { roster_id: Number(rosterId) } : undefined;
    reportsApi.coverage(rosterId ? Number(rosterId) : undefined).then(setCoverage).catch((e) => setError(errMsg(e)));
    reportsApi.workload(rosterId ? Number(rosterId) : undefined).then(setWorkload).catch(() => undefined);
    void params;
  }, [rosterId]);

  const coverageRows = (() => {
    if (!coverage) return [];
    if (Array.isArray(coverage)) return coverage as Record<string, unknown>[];
    return [coverage as Record<string, unknown>];
  })();

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Reports &amp; Exports</h1>
      <ErrorBox message={error} />
      <Card>
        <div className="flex gap-2 mb-4 flex-wrap">
          <select className={inputCls} value={rosterId} onChange={(e) => setRosterId(e.target.value)}>
            <option value="">All rosters</option>
            {rosters.map((r) => (
              <option key={r.id} value={r.id}>
                #{r.id} — {r.month}/{r.year} ({r.status})
              </option>
            ))}
          </select>
          {rosterId && (
            <>
              <Btn tone="secondary" onClick={() => downloadFile(`/api/exports/roster.csv?roster_id=${rosterId}`, `roster_${rosterId}.csv`)}>Download CSV</Btn>
              <Btn tone="secondary" onClick={() => downloadFile(`/api/exports/roster.xlsx?roster_id=${rosterId}`, `roster_${rosterId}.xlsx`)}>Download Excel</Btn>
            </>
          )}
        </div>
        <h3 className="font-semibold mb-2">Coverage</h3>
        {coverageRows.length === 0 ? (
          <Empty text="No coverage data." />
        ) : (
          <table className="w-full text-sm mb-4">
            <thead>
              <tr className="text-left text-muted border-b border-border">
                <th className="py-2 pr-3">Roster</th>
                <th className="py-2 pr-3">Status</th>
                <th className="py-2 pr-3">Coverage</th>
                <th className="py-2 pr-3">Gaps</th>
                <th className="py-2 pr-3">Fairness</th>
              </tr>
            </thead>
            <tbody>
              {coverageRows.map((row, i) => {
                const m = row.metrics as Record<string, number> | null;
                return (
                  <tr key={i} className="border-b border-border last:border-0">
                    <td className="py-2 pr-3">#{String(row.roster_id)} {row.month ? `(${String(row.month)}/${String(row.year)})` : ""}</td>
                    <td className="py-2 pr-3">{String(row.status || "—")}</td>
                    <td className="py-2 pr-3">{m ? `${Math.round(m.coverage_rate * 1000) / 10}%` : "—"}</td>
                    <td className="py-2 pr-3">{m ? m.gap_count : "—"}</td>
                    <td className="py-2 pr-3">{m ? `${Math.round(m.fairness_score * 1000) / 10}%` : "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
        <h3 className="font-semibold mb-2">Workload (workdays / offs)</h3>
        {workload.length === 0 ? (
          <Empty text="No workload data." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted border-b border-border">
                <th className="py-2 pr-3">Employee</th>
                <th className="py-2 pr-3">Workdays</th>
                <th className="py-2 pr-3">Offs</th>
              </tr>
            </thead>
            <tbody>
              {workload.map((w, i) => (
                <tr key={i} className="border-b border-border last:border-0">
                  <td className="py-2 pr-3">{String(w.employee_name)}</td>
                  <td className="py-2 pr-3">{String(w.workdays)}</td>
                  <td className="py-2 pr-3">{String(w.offs)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}

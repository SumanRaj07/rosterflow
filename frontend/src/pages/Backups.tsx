import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { backupsApi, brandsApi, employeesApi, errMsg, processesApi, rostersApi } from "../api";
import type { Backup, Brand, Employee, Process, Roster } from "../api";
import { Badge, Btn, Card, Empty, ErrorBox, inputCls } from "../components/ui";

export default function Backups() {
  const [params, setParams] = useSearchParams();
  const [list, setList] = useState<Backup[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [rosters, setRosters] = useState<Roster[]>([]);
  const [emps, setEmps] = useState<Employee[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [procs, setProcs] = useState<Process[]>([]);
  const rosterId = params.get("roster_id") ? Number(params.get("roster_id")) : undefined;

  function load() {
    backupsApi.list(rosterId).then(setList).catch((e) => setError(errMsg(e)));
  }

  useEffect(load, [rosterId]);
  useEffect(() => {
    rostersApi.list().then(setRosters).catch(() => undefined);
    employeesApi.list({ limit: 200 }).then((d) => setEmps(d.items)).catch(() => undefined);
    brandsApi.list({ limit: 100 }).then((d) => setBrands(d.items)).catch(() => undefined);
    processesApi.list({ limit: 100 }).then((d) => setProcs(d.items)).catch(() => undefined);
  }, []);

  const empName = (id: number) => emps.find((e) => e.id === id)?.full_name || `#${id}`;
  const brandName = (id: number) => brands.find((b) => b.id === id)?.name || `#${id}`;
  const procName = (id: number) => procs.find((p) => p.id === id)?.name || `#${id}`;

  async function apply(b: Backup) {
    try {
      await backupsApi.apply(b.id);
      load();
    } catch (err) {
      setError(errMsg(err));
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Backup Recommendations</h1>
      <ErrorBox message={error} />
      <Card>
        <div className="mb-3">
          <select
            className={inputCls}
            value={rosterId || ""}
            onChange={(e) => setParams(e.target.value ? { roster_id: e.target.value } : {})}
          >
            <option value="">All rosters</option>
            {rosters.map((r) => (
              <option key={r.id} value={r.id}>
                #{r.id} — {r.month}/{r.year} ({r.status})
              </option>
            ))}
          </select>
        </div>
        {list.length === 0 ? (
          <Empty text="No backup recommendations. Generate a roster with coverage gaps, or validate a roster to refresh recommendations." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted border-b border-border">
                <th className="py-2 pr-3">Date</th>
                <th className="py-2 pr-3">Brand / Process</th>
                <th className="py-2 pr-3">Candidate</th>
                <th className="py-2 pr-3">Score</th>
                <th className="py-2 pr-3">Why</th>
                <th className="py-2 pr-3">Status</th>
                <th className="py-2" />
              </tr>
            </thead>
            <tbody>
              {list.map((b) => (
                <tr key={b.id} className="border-b border-border last:border-0">
                  <td className="py-2 pr-3">{b.date}</td>
                  <td className="py-2 pr-3">{brandName(b.brand_id)} / {procName(b.process_id)}</td>
                  <td className="py-2 pr-3 font-medium">{empName(b.employee_id)}</td>
                  <td className="py-2 pr-3">{b.score}</td>
                  <td className="py-2 pr-3 text-muted max-w-[320px]">{b.reason}</td>
                  <td className="py-2 pr-3">
                    <Badge tone={b.status === "accepted" ? "green" : "gray"}>{b.status}</Badge>
                  </td>
                  <td className="py-2">
                    {b.status === "pending" && (
                      <Btn small onClick={() => apply(b)}>Apply</Btn>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p className="text-xs text-muted mt-2">
          Applying a recommendation assigns that employee to the gap (creating the brand
          assignment first if they were only certification-qualified) and revalidates the roster.
          Published rosters need a new version first.
        </p>
      </Card>
    </div>
  );
}

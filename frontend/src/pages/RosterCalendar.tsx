import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  brandsApi, employeesApi, errMsg, processesApi, rostersApi,
} from "../api";
import type { Brand, Employee, Process, Roster, RosterEntry } from "../api";
import { Badge, Btn, Card, Empty, ErrorBox, Field, inputCls, Modal, statusTone } from "../components/ui";

const CELL: Record<string, string> = {
  work: "bg-blue-100 text-blue-900",
  off: "bg-gray-100 text-gray-600",
  leave: "bg-amber-100 text-amber-900",
  holiday: "bg-violet-100 text-violet-900",
};
const LETTER: Record<string, string> = { work: "W", off: "O", leave: "L", holiday: "H" };

export default function RosterCalendar() {
  const [params, setParams] = useSearchParams();
  const [rosters, setRosters] = useState<Roster[]>([]);
  const [roster, setRoster] = useState<Roster | null>(null);
  const [emps, setEmps] = useState<Employee[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [procs, setProcs] = useState<Process[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [edit, setEdit] = useState<RosterEntry | null>(null);
  const [editForm, setEditForm] = useState({ entry_type: "work", brand_id: "", process_id: "", note: "", reason: "" });
  const [validateMsg, setValidateMsg] = useState<string | null>(null);

  const rosterId = params.get("id") ? Number(params.get("id")) : null;

  function loadRoster(id: number) {
    rostersApi.get(id).then(setRoster).catch((e) => setError(errMsg(e)));
  }

  useEffect(() => {
    rostersApi.list().then(setRosters).catch((e) => setError(errMsg(e)));
    employeesApi.list({ limit: 200 }).then((d) => setEmps(d.items)).catch(() => undefined);
    brandsApi.list({ limit: 100 }).then((d) => setBrands(d.items)).catch(() => undefined);
    processesApi.list({ limit: 100 }).then((d) => setProcs(d.items)).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (rosterId) loadRoster(rosterId);
  }, [rosterId]);

  const days = useMemo(() => {
    if (!roster) return [];
    const n = new Date(roster.year, roster.month, 0).getDate();
    return Array.from({ length: n }, (_, i) => {
      const d = new Date(roster.year, roster.month - 1, i + 1);
      return d.toISOString().slice(0, 10);
    });
  }, [roster]);

  const byKey = useMemo(() => {
    const m = new Map<string, RosterEntry>();
    for (const e of roster?.entries || []) m.set(`${e.employee_id}|${e.date}`, e);
    return m;
  }, [roster]);

  const empIds = useMemo(() => {
    const s = new Set<number>();
    for (const e of roster?.entries || []) s.add(e.employee_id);
    return [...s].sort((a, b) => a - b);
  }, [roster]);

  const empName = (id: number) => emps.find((e) => e.id === id)?.full_name || `#${id}`;
  const brandName = (id: number | null) =>
    id === null ? "" : brands.find((b) => b.id === id)?.name || `#${id}`;
  const procName = (id: number | null) =>
    id === null ? "" : procs.find((p) => p.id === id)?.name || `#${id}`;

  function openEdit(e: RosterEntry) {
    setEdit(e);
    setEditForm({
      entry_type: e.entry_type,
      brand_id: e.brand_id ? String(e.brand_id) : "",
      process_id: e.process_id ? String(e.process_id) : "",
      note: e.note || "",
      reason: "",
    });
  }

  async function saveEdit(ev: React.FormEvent) {
    ev.preventDefault();
    if (!roster || !edit) return;
    try {
      await rostersApi.patchEntry(roster.id, edit.id, {
        entry_type: editForm.entry_type,
        brand_id: editForm.brand_id ? Number(editForm.brand_id) : null,
        process_id: editForm.process_id ? Number(editForm.process_id) : null,
        note: editForm.note || null,
        reason: editForm.reason || null,
      });
      setEdit(null);
      setValidateMsg("Entry saved and roster revalidated.");
      loadRoster(roster.id);
    } catch (err) {
      setError(errMsg(err));
    }
  }

  async function validate() {
    if (!roster) return;
    try {
      const res = await rostersApi.validate(roster.id) as unknown as { conflicts: number; critical: number; status: string };
      setValidateMsg(`Validation: ${res.conflicts} conflict(s), ${res.critical} critical. Status: ${res.status}.`);
      loadRoster(roster.id);
    } catch (err) {
      setError(errMsg(err));
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="text-xl font-bold">Roster Calendar</h1>
        <div className="flex gap-2">
          <select
            className={inputCls}
            value={rosterId || ""}
            onChange={(e) => setParams(e.target.value ? { id: e.target.value } : {})}
          >
            <option value="">Select a roster…</option>
            {rosters.map((r) => (
              <option key={r.id} value={r.id}>
                #{r.id} — {r.month}/{r.year} v{r.version} ({r.status})
              </option>
            ))}
          </select>
          {roster && <Btn tone="secondary" onClick={validate}>Revalidate</Btn>}
        </div>
      </div>
      <ErrorBox message={error} />
      {validateMsg && (
        <div className="bg-blue-50 border border-blue-200 text-primary text-sm rounded-md px-3 py-2">
          {validateMsg}
        </div>
      )}
      {!roster && <Empty text="Select a roster to view its calendar." />}
      {roster && (
        <>
          <Card
            title={`Roster #${roster.id} — ${roster.month}/${roster.year} (v${roster.version})`}
            subtitle={`Strategy: ${roster.strategy || "—"}${roster.preferences_applied !== undefined ? ` · Preferences applied: ${roster.preferences_applied ? "yes" : "no"}` : ""}`}
            actions={<Badge tone={statusTone(roster.status)}>{roster.status}</Badge>}
          >
            {roster.metrics && (
              <div className="flex flex-wrap gap-4 text-sm">
                <span>Coverage: <b>{Math.round(roster.metrics.coverage_rate * 1000) / 10}%</b></span>
                <span>Fairness: <b>{Math.round(roster.metrics.fairness_score * 1000) / 10}%</b></span>
                <span>Gaps: <b>{roster.metrics.gap_count}</b></span>
                <span>Work assignments: <b>{roster.metrics.total_work_assignments}</b></span>
              </div>
            )}
            <p className="text-xs text-muted mt-2">
              Click any cell to edit it. Published rosters cannot be edited directly — create a
              new version from the Approvals page. W = work, O = weekly off, L = leave, H = holiday.
            </p>
          </Card>

          <Card title="Employee schedule">
            <div className="overflow-x-auto">
              <table className="text-xs border-collapse">
                <thead>
                  <tr>
                    <th className="sticky left-0 bg-surface text-left pr-2 py-1 min-w-[140px]">Employee</th>
                    {days.map((d) => (
                      <th key={d} className="px-1 py-1 text-muted font-normal">
                        {d.slice(8)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {empIds.map((eid) => (
                    <tr key={eid}>
                      <td className="sticky left-0 bg-surface pr-2 py-0.5 font-medium whitespace-nowrap">
                        {empName(eid)}
                      </td>
                      {days.map((d) => {
                        const e = byKey.get(`${eid}|${d}`);
                        if (!e) return <td key={d} className="px-1" />;
                        return (
                          <td key={d} className="px-0.5 py-0.5">
                            <button
                              title={`${d}: ${e.entry_type}${e.brand_id ? ` — ${brandName(e.brand_id)} / ${procName(e.process_id)}` : ""}${e.is_manual ? " (manual)" : ""}`}
                              onClick={() => openEdit(e)}
                              className={`w-6 h-6 rounded text-[11px] font-semibold ${CELL[e.entry_type] || "bg-gray-100"}`}
                            >
                              {LETTER[e.entry_type] || "?"}
                            </button>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <Card title={`Conflicts (${roster.conflicts?.length || 0})`}>
            {!roster.conflicts?.length ? (
              <Empty text="No conflicts for this roster." />
            ) : (
              <ul className="space-y-2 text-sm">
                {roster.conflicts.map((c) => (
                  <li key={c.id} className="border-b border-border pb-2">
                    <Badge tone={c.severity === "critical" ? "red" : "amber"}>{c.severity}</Badge>{" "}
                    <span className="font-medium">{c.type}</span>
                    {c.date && <span className="text-muted"> · {c.date}</span>}
                    <p className="mt-1">{c.explanation}</p>
                    {c.recommendation && <p className="text-muted">Recommendation: {c.recommendation}</p>}
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </>
      )}

      {edit && (
        <Modal title={`Edit entry — ${edit.date}`} onClose={() => setEdit(null)}>
          <form onSubmit={saveEdit} className="space-y-3">
            <Field label="Entry type">
              <select className={inputCls} value={editForm.entry_type} onChange={(e) => setEditForm({ ...editForm, entry_type: e.target.value })}>
                <option value="work">Work</option>
                <option value="off">Weekly off</option>
                <option value="leave">Leave</option>
                <option value="holiday">Holiday</option>
              </select>
            </Field>
            <Field label="Brand">
              <select className={inputCls} value={editForm.brand_id} onChange={(e) => setEditForm({ ...editForm, brand_id: e.target.value })}>
                <option value="">None</option>
                {brands.map((b) => (
                  <option key={b.id} value={b.id}>{b.name}</option>
                ))}
              </select>
            </Field>
            <Field label="Process">
              <select className={inputCls} value={editForm.process_id} onChange={(e) => setEditForm({ ...editForm, process_id: e.target.value })}>
                <option value="">None</option>
                {procs.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </Field>
            <Field label="Note">
              <input className={inputCls} value={editForm.note} onChange={(e) => setEditForm({ ...editForm, note: e.target.value })} />
            </Field>
            <Field label="Reason (recorded in change history)">
              <input className={inputCls} value={editForm.reason} onChange={(e) => setEditForm({ ...editForm, reason: e.target.value })} />
            </Field>
            <Btn type="submit">Save &amp; revalidate</Btn>
          </form>
        </Modal>
      )}
    </div>
  );
}

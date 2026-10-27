import { useEffect, useState } from "react";
import {
  availabilityApi, compoffApi, currentUser, employeesApi, errMsg, leaveApi,
  preferencesApi,
} from "../api";
import type { Availability, CompOff, Employee, Leave, Preference } from "../api";
import { Badge, Btn, Card, Empty, ErrorBox, Field, inputCls, Modal, statusTone } from "../components/ui";

const WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function LeavePage() {
  const user = currentUser();
  const canReview = user?.role === "admin" || user?.role === "manager";
  const [leaves, setLeaves] = useState<Leave[]>([]);
  const [avails, setAvails] = useState<Availability[]>([]);
  const [prefs, setPrefs] = useState<Preference[]>([]);
  const [compoffs, setCompoffs] = useState<CompOff[]>([]);
  const [emps, setEmps] = useState<Employee[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showLeave, setShowLeave] = useState(false);
  const [showAvail, setShowAvail] = useState(false);
  const [showPref, setShowPref] = useState(false);
  const [showComp, setShowComp] = useState(false);
  const [leaveForm, setLeaveForm] = useState({ employee_id: "", start_date: "", end_date: "", leave_type: "annual", reason: "" });
  const [availForm, setAvailForm] = useState({ employee_id: "", date: "", weekday: "", kind: "unavailable", note: "" });
  const [prefForm, setPrefForm] = useState({ employee_id: "", preferred_off_weekday: "", shift_preference: "", notes: "" });
  const [compForm, setCompForm] = useState({ employee_id: "", earned_date: "", reason: "" });
  const [reviewComment, setReviewComment] = useState("");

  function load() {
    leaveApi.list().then(setLeaves).catch((e) => setError(errMsg(e)));
    availabilityApi.list().then(setAvails).catch(() => undefined);
    preferencesApi.list().then(setPrefs).catch(() => undefined);
    compoffApi.list().then(setCompoffs).catch(() => undefined);
    employeesApi.list({ limit: 200 }).then((d) => setEmps(d.items)).catch(() => undefined);
  }
  useEffect(load, []);

  const empName = (id: number) => emps.find((e) => e.id === id)?.full_name || `#${id}`;
  const defaultEmp = user?.employee_id ? String(user.employee_id) : "";

  async function createLeave(e: React.FormEvent) {
    e.preventDefault();
    try {
      await leaveApi.create({ ...leaveForm, employee_id: Number(leaveForm.employee_id) });
      setShowLeave(false);
      load();
    } catch (err) {
      setError(errMsg(err));
    }
  }

  async function reviewLeave(id: number, decision: string) {
    try {
      const res = await leaveApi.review(id, decision, reviewComment || undefined) as unknown as { affected_rosters?: number[] };
      if (decision === "approved" && res.affected_rosters?.length) {
        alert(`Leave approved. Revalidation affected rosters: ${res.affected_rosters.join(", ")}`);
      }
      load();
    } catch (err) {
      setError(errMsg(err));
    }
  }

  async function createAvail(e: React.FormEvent) {
    e.preventDefault();
    try {
      await availabilityApi.create({
        employee_id: Number(availForm.employee_id),
        date: availForm.date || null,
        weekday: availForm.weekday === "" ? null : Number(availForm.weekday),
        kind: availForm.kind,
        note: availForm.note || null,
      });
      setShowAvail(false);
      load();
    } catch (err) {
      setError(errMsg(err));
    }
  }

  async function createPref(e: React.FormEvent) {
    e.preventDefault();
    try {
      await preferencesApi.upsert({
        employee_id: Number(prefForm.employee_id),
        preferred_off_weekday: prefForm.preferred_off_weekday === "" ? null : Number(prefForm.preferred_off_weekday),
        shift_preference: prefForm.shift_preference || null,
        notes: prefForm.notes || null,
      });
      setShowPref(false);
      load();
    } catch (err) {
      setError(errMsg(err));
    }
  }

  async function createComp(e: React.FormEvent) {
    e.preventDefault();
    try {
      await compoffApi.create({ ...compForm, employee_id: Number(compForm.employee_id) });
      setShowComp(false);
      load();
    } catch (err) {
      setError(errMsg(err));
    }
  }

  async function useComp(id: number, usedDate: string) {
    try {
      await compoffApi.update(id, { status: "used", used_date: usedDate });
      load();
    } catch (err) {
      setError(errMsg(err));
    }
  }

  const empSelect = (value: string, onChange: (v: string) => void) => (
    <select className={inputCls} required value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">Select employee…</option>
      {emps.map((e) => (
        <option key={e.id} value={e.id}>{e.full_name}</option>
      ))}
    </select>
  );

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Leave &amp; Availability</h1>
      <ErrorBox message={error} />

      <Card
        title="Leave requests"
        actions={
          <div className="flex gap-2">
            <Btn onClick={() => { setLeaveForm({ ...leaveForm, employee_id: defaultEmp }); setShowLeave(true); }}>Request leave</Btn>
          </div>
        }
      >
        {canReview && (
          <div className="mb-3">
            <input className={inputCls} placeholder="Review comment (applied to approve/reject)…" value={reviewComment} onChange={(e) => setReviewComment(e.target.value)} />
          </div>
        )}
        {leaves.length === 0 ? (
          <Empty text="No leave requests." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted border-b border-border">
                <th className="py-2 pr-3">Employee</th>
                <th className="py-2 pr-3">Period</th>
                <th className="py-2 pr-3">Type</th>
                <th className="py-2 pr-3">Status</th>
                <th className="py-2" />
              </tr>
            </thead>
            <tbody>
              {leaves.map((l) => (
                <tr key={l.id} className="border-b border-border last:border-0">
                  <td className="py-2 pr-3">{empName(l.employee_id)}</td>
                  <td className="py-2 pr-3">{l.start_date} → {l.end_date}</td>
                  <td className="py-2 pr-3">{l.leave_type}</td>
                  <td className="py-2 pr-3"><Badge tone={statusTone(l.status)}>{l.status}</Badge></td>
                  <td className="py-2 flex gap-2">
                    {canReview && l.status === "pending" && (
                      <>
                        <Btn small onClick={() => reviewLeave(l.id, "approved")}>Approve</Btn>
                        <Btn small tone="danger" onClick={() => reviewLeave(l.id, "rejected")}>Reject</Btn>
                      </>
                    )}
                    {l.status === "pending" && (
                      <Btn small tone="secondary" onClick={() => leaveApi.cancel(l.id).then(load).catch((err) => setError(errMsg(err)))}>Cancel</Btn>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p className="text-xs text-muted mt-2">
          Approving leave revalidates affected rosters: work entries on leave days become conflicts
          (published rosters are never silently changed).
        </p>
      </Card>

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Availability" actions={<Btn small onClick={() => { setAvailForm({ ...availForm, employee_id: defaultEmp }); setShowAvail(true); }}>Add</Btn>}>
          {avails.length === 0 ? (
            <Empty text="No availability records." />
          ) : (
            <ul className="space-y-1 text-sm">
              {avails.map((a) => (
                <li key={a.id} className="flex justify-between border-b border-border pb-1">
                  <span>
                    {empName(a.employee_id)}: {a.kind} —{" "}
                    {a.date || (a.weekday !== null ? `every ${WEEKDAY_NAMES[a.weekday]}` : "—")}
                  </span>
                  <Btn small tone="danger" onClick={() => availabilityApi.remove(a.id).then(load).catch((err) => setError(errMsg(err)))}>Delete</Btn>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Preferences" actions={<Btn small onClick={() => { setPrefForm({ ...prefForm, employee_id: defaultEmp }); setShowPref(true); }}>Set preference</Btn>}>
          {prefs.length === 0 ? (
            <Empty text="No preferences recorded." />
          ) : (
            <ul className="space-y-1 text-sm">
              {prefs.map((p) => (
                <li key={p.id} className="border-b border-border pb-1">
                  {empName(p.employee_id)}: preferred off{" "}
                  {p.preferred_off_weekday !== null ? WEEKDAY_NAMES[p.preferred_off_weekday] : "—"}
                  {p.shift_preference ? ` · shift: ${p.shift_preference}` : ""}
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card title="Comp-off records" actions={user?.role === "admin" ? <Btn small onClick={() => setShowComp(true)}>Add comp-off</Btn> : undefined}>
        {compoffs.length === 0 ? (
          <Empty text="No comp-off records." />
        ) : (
          <ul className="space-y-1 text-sm">
            {compoffs.map((c) => (
              <li key={c.id} className="flex justify-between border-b border-border pb-1">
                <span>
                  {empName(c.employee_id)}: earned {c.earned_date} — {c.status}
                  {c.reason ? ` (${c.reason})` : ""}
                </span>
                {canReview && c.status === "available" && (
                  <Btn small onClick={() => useComp(c.id, new Date().toISOString().slice(0, 10))}>Mark used</Btn>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>

      {showLeave && (
        <Modal title="Request leave" onClose={() => setShowLeave(false)}>
          <form onSubmit={createLeave} className="space-y-3">
            <Field label="Employee">{empSelect(leaveForm.employee_id, (v) => setLeaveForm({ ...leaveForm, employee_id: v }))}</Field>
            <Field label="Start date">
              <input className={inputCls} type="date" required value={leaveForm.start_date} onChange={(e) => setLeaveForm({ ...leaveForm, start_date: e.target.value })} />
            </Field>
            <Field label="End date">
              <input className={inputCls} type="date" required value={leaveForm.end_date} onChange={(e) => setLeaveForm({ ...leaveForm, end_date: e.target.value })} />
            </Field>
            <Field label="Leave type">
              <select className={inputCls} value={leaveForm.leave_type} onChange={(e) => setLeaveForm({ ...leaveForm, leave_type: e.target.value })}>
                <option value="annual">Annual</option>
                <option value="casual">Casual</option>
                <option value="sick">Sick</option>
              </select>
            </Field>
            <Field label="Reason">
              <input className={inputCls} value={leaveForm.reason} onChange={(e) => setLeaveForm({ ...leaveForm, reason: e.target.value })} />
            </Field>
            <Btn type="submit">Submit request</Btn>
          </form>
        </Modal>
      )}
      {showAvail && (
        <Modal title="Add availability" onClose={() => setShowAvail(false)}>
          <form onSubmit={createAvail} className="space-y-3">
            <Field label="Employee">{empSelect(availForm.employee_id, (v) => setAvailForm({ ...availForm, employee_id: v }))}</Field>
            <Field label="Kind">
              <select className={inputCls} value={availForm.kind} onChange={(e) => setAvailForm({ ...availForm, kind: e.target.value })}>
                <option value="unavailable">Unavailable (mandatory)</option>
                <option value="preferred_off">Preferred off</option>
                <option value="preferred_work">Preferred work</option>
              </select>
            </Field>
            <Field label="Date (leave blank for recurring weekday)">
              <input className={inputCls} type="date" value={availForm.date} onChange={(e) => setAvailForm({ ...availForm, date: e.target.value })} />
            </Field>
            <Field label="Recurring weekday">
              <select className={inputCls} value={availForm.weekday} onChange={(e) => setAvailForm({ ...availForm, weekday: e.target.value })}>
                <option value="">None</option>
                {WEEKDAY_NAMES.map((w, i) => (
                  <option key={i} value={i}>{w}</option>
                ))}
              </select>
            </Field>
            <Field label="Note">
              <input className={inputCls} value={availForm.note} onChange={(e) => setAvailForm({ ...availForm, note: e.target.value })} />
            </Field>
            <Btn type="submit">Add</Btn>
          </form>
        </Modal>
      )}
      {showPref && (
        <Modal title="Set preference" onClose={() => setShowPref(false)}>
          <form onSubmit={createPref} className="space-y-3">
            <Field label="Employee">{empSelect(prefForm.employee_id, (v) => setPrefForm({ ...prefForm, employee_id: v }))}</Field>
            <Field label="Preferred off weekday">
              <select className={inputCls} value={prefForm.preferred_off_weekday} onChange={(e) => setPrefForm({ ...prefForm, preferred_off_weekday: e.target.value })}>
                <option value="">None</option>
                {WEEKDAY_NAMES.map((w, i) => (
                  <option key={i} value={i}>{w}</option>
                ))}
              </select>
            </Field>
            <Field label="Shift preference">
              <input className={inputCls} value={prefForm.shift_preference} onChange={(e) => setPrefForm({ ...prefForm, shift_preference: e.target.value })} />
            </Field>
            <Btn type="submit">Save</Btn>
          </form>
        </Modal>
      )}
      {showComp && (
        <Modal title="Add comp-off" onClose={() => setShowComp(false)}>
          <form onSubmit={createComp} className="space-y-3">
            <Field label="Employee">{empSelect(compForm.employee_id, (v) => setCompForm({ ...compForm, employee_id: v }))}</Field>
            <Field label="Earned date">
              <input className={inputCls} type="date" required value={compForm.earned_date} onChange={(e) => setCompForm({ ...compForm, earned_date: e.target.value })} />
            </Field>
            <Field label="Reason">
              <input className={inputCls} value={compForm.reason} onChange={(e) => setCompForm({ ...compForm, reason: e.target.value })} />
            </Field>
            <Btn type="submit">Add</Btn>
          </form>
        </Modal>
      )}
    </div>
  );
}

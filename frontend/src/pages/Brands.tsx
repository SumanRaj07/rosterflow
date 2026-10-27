import { useEffect, useState } from "react";
import { brandsApi, currentUser, employeesApi, errMsg, processesApi, staffingApi } from "../api";
import type { Brand, Employee, Process, Staffing } from "../api";
import { Badge, Btn, Card, Empty, ErrorBox, Field, inputCls, Modal } from "../components/ui";

export default function Brands() {
  const user = currentUser();
  const [list, setList] = useState<Brand[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<Brand | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [emps, setEmps] = useState<Employee[]>([]);
  const [procs, setProcs] = useState<Process[]>([]);
  const [form, setForm] = useState({ code: "", name: "", description: "" });
  const [staffForm, setStaffForm] = useState({ process_id: "", min_staff: 1, applies: "all" });

  function load() {
    brandsApi
      .list({ limit: 100 })
      .then((d) => setList(d.items))
      .catch((e) => setError(errMsg(e)));
    employeesApi.list({ limit: 200 }).then((d) => setEmps(d.items)).catch(() => undefined);
    processesApi.list({ limit: 100 }).then((d) => setProcs(d.items)).catch(() => undefined);
  }

  useEffect(load, []);

  const empName = (id: number) => emps.find((e) => e.id === id)?.full_name || `#${id}`;
  const procName = (id: number) => procs.find((p) => p.id === id)?.name || `#${id}`;

  async function create(e: React.FormEvent) {
    e.preventDefault();
    try {
      await brandsApi.create(form);
      setShowCreate(false);
      setForm({ code: "", name: "", description: "" });
      load();
    } catch (err) {
      setError(errMsg(err));
    }
  }

  async function addStaffing(e: React.FormEvent) {
    e.preventDefault();
    if (!detail) return;
    try {
      await staffingApi.create({
        brand_id: detail.id,
        process_id: Number(staffForm.process_id),
        min_staff: staffForm.min_staff,
        applies: staffForm.applies,
      });
      const fresh = await brandsApi.get(detail.id);
      setDetail(fresh);
      load();
    } catch (err) {
      setError(errMsg(err));
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Brands</h1>
        {user?.role === "admin" && <Btn onClick={() => setShowCreate(true)}>Add brand</Btn>}
      </div>
      <ErrorBox message={error} />
      <Card>
        {list.length === 0 ? (
          <Empty text="No brands yet." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted border-b border-border">
                <th className="py-2 pr-3">Code</th>
                <th className="py-2 pr-3">Name</th>
                <th className="py-2 pr-3">Active</th>
                <th className="py-2" />
              </tr>
            </thead>
            <tbody>
              {list.map((b) => (
                <tr key={b.id} className="border-b border-border last:border-0">
                  <td className="py-2 pr-3">{b.code}</td>
                  <td className="py-2 pr-3 font-medium">{b.name}</td>
                  <td className="py-2 pr-3">
                    <Badge tone={b.is_active ? "green" : "gray"}>
                      {b.is_active ? "yes" : "no"}
                    </Badge>
                  </td>
                  <td className="py-2">
                    <Btn
                      tone="secondary"
                      small
                      onClick={() =>
                        brandsApi.get(b.id).then(setDetail).catch((err) => setError(errMsg(err)))
                      }
                    >
                      Details
                    </Btn>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {showCreate && (
        <Modal title="Add brand" onClose={() => setShowCreate(false)}>
          <form onSubmit={create} className="space-y-3">
            <Field label="Code">
              <input className={inputCls} required value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
            </Field>
            <Field label="Name">
              <input className={inputCls} required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </Field>
            <Field label="Description">
              <input className={inputCls} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </Field>
            <Btn type="submit">Create</Btn>
          </form>
        </Modal>
      )}

      {detail && (
        <Modal title={`${detail.name} (${detail.code})`} onClose={() => setDetail(null)}>
          <div className="space-y-4 text-sm">
            <p className="text-muted">{detail.description || "No description."}</p>
            <div>
              <h4 className="font-semibold mb-1">Staffing requirements</h4>
              {detail.staffing?.length ? (
                <ul className="list-disc pl-5">
                  {detail.staffing.map((s: Staffing) => (
                    <li key={s.id}>
                      {procName(s.process_id)}: min {s.min_staff} ({s.applies})
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted">None yet.</p>
              )}
            </div>
            <div>
              <h4 className="font-semibold mb-1">Assigned employees</h4>
              {detail.assigned_employee_ids?.length ? (
                <p>{detail.assigned_employee_ids.map(empName).join(", ")}</p>
              ) : (
                <p className="text-muted">No eligible employees — this brand cannot be staffed.</p>
              )}
            </div>
            {user?.role === "admin" && (
              <form onSubmit={addStaffing} className="space-y-2 border-t border-border pt-3">
                <h4 className="font-semibold">Add staffing requirement</h4>
                <div className="grid grid-cols-3 gap-2">
                  <select className={inputCls} required value={staffForm.process_id} onChange={(e) => setStaffForm({ ...staffForm, process_id: e.target.value })}>
                    <option value="">Process…</option>
                    {procs.map((p) => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                  <input className={inputCls} type="number" min={0} value={staffForm.min_staff} onChange={(e) => setStaffForm({ ...staffForm, min_staff: Number(e.target.value) })} />
                  <select className={inputCls} value={staffForm.applies} onChange={(e) => setStaffForm({ ...staffForm, applies: e.target.value })}>
                    <option value="all">All days</option>
                    <option value="weekday">Weekdays</option>
                    <option value="weekend">Weekends</option>
                    <option value="sunday">Sundays</option>
                    <option value="holiday">Holidays</option>
                  </select>
                </div>
                <Btn type="submit" small>Add requirement</Btn>
              </form>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
}

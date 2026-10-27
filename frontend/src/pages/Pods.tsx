import { useEffect, useState } from "react";
import { currentUser, employeesApi, errMsg, podsApi } from "../api";
import type { Employee, Pod } from "../api";
import { Badge, Btn, Card, Empty, ErrorBox, Field, inputCls, Modal } from "../components/ui";

export default function Pods() {
  const user = currentUser();
  const [list, setList] = useState<Pod[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<Pod | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [emps, setEmps] = useState<Employee[]>([]);
  const [form, setForm] = useState({ code: "", name: "" });
  const [addEmp, setAddEmp] = useState("");

  function load() {
    podsApi.list().then((d) => setList(d.items)).catch((e) => setError(errMsg(e)));
    employeesApi.list({ limit: 200 }).then((d) => setEmps(d.items)).catch(() => undefined);
  }
  useEffect(load, []);

  const empName = (id: number) => emps.find((e) => e.id === id)?.full_name || `#${id}`;

  async function create(e: React.FormEvent) {
    e.preventDefault();
    try {
      await podsApi.create(form);
      setShowCreate(false);
      setForm({ code: "", name: "" });
      load();
    } catch (err) {
      setError(errMsg(err));
    }
  }

  async function addMember() {
    if (!detail || !addEmp) return;
    try {
      await podsApi.addMember(detail.id, Number(addEmp));
      const fresh = await podsApi.get(detail.id);
      setDetail(fresh);
      load();
    } catch (err) {
      setError(errMsg(err));
    }
  }

  async function removeMember(empId: number) {
    if (!detail) return;
    try {
      await podsApi.removeMember(detail.id, empId);
      const fresh = await podsApi.get(detail.id);
      setDetail(fresh);
      load();
    } catch (err) {
      setError(errMsg(err));
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Pods</h1>
        {user?.role === "admin" && <Btn onClick={() => setShowCreate(true)}>Add pod</Btn>}
      </div>
      <ErrorBox message={error} />
      <Card>
        {list.length === 0 ? (
          <Empty text="No pods yet." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted border-b border-border">
                <th className="py-2 pr-3">Code</th>
                <th className="py-2 pr-3">Name</th>
                <th className="py-2 pr-3">Lead user</th>
                <th className="py-2 pr-3">Active</th>
                <th className="py-2" />
              </tr>
            </thead>
            <tbody>
              {list.map((p) => (
                <tr key={p.id} className="border-b border-border last:border-0">
                  <td className="py-2 pr-3">{p.code}</td>
                  <td className="py-2 pr-3 font-medium">{p.name}</td>
                  <td className="py-2 pr-3 text-muted">{p.lead_id ? `user #${p.lead_id}` : "—"}</td>
                  <td className="py-2 pr-3">
                    <Badge tone={p.is_active ? "green" : "gray"}>{p.is_active ? "yes" : "no"}</Badge>
                  </td>
                  <td className="py-2">
                    <Btn tone="secondary" small onClick={() => podsApi.get(p.id).then(setDetail).catch((err) => setError(errMsg(err)))}>
                      Members
                    </Btn>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
      {showCreate && (
        <Modal title="Add pod" onClose={() => setShowCreate(false)}>
          <form onSubmit={create} className="space-y-3">
            <Field label="Code">
              <input className={inputCls} required value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
            </Field>
            <Field label="Name">
              <input className={inputCls} required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </Field>
            <Btn type="submit">Create</Btn>
          </form>
        </Modal>
      )}
      {detail && (
        <Modal title={`${detail.name} (${detail.code})`} onClose={() => setDetail(null)}>
          <div className="space-y-3 text-sm">
            <h4 className="font-semibold">Members ({detail.member_employee_ids?.length || 0})</h4>
            {detail.member_employee_ids?.length ? (
              <ul className="space-y-1">
                {detail.member_employee_ids.map((id) => (
                  <li key={id} className="flex justify-between">
                    <span>{empName(id)}</span>
                    {user?.role === "admin" && (
                      <Btn tone="danger" small onClick={() => removeMember(id)}>Remove</Btn>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-muted">No members.</p>
            )}
            {user?.role === "admin" && (
              <div className="flex gap-2 pt-2 border-t border-border">
                <select className={inputCls} value={addEmp} onChange={(e) => setAddEmp(e.target.value)}>
                  <option value="">Add employee…</option>
                  {emps.map((e) => (
                    <option key={e.id} value={e.id}>{e.full_name}</option>
                  ))}
                </select>
                <Btn onClick={addMember} disabled={!addEmp}>Add</Btn>
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
}

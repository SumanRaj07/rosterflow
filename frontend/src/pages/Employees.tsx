import { useEffect, useState } from "react";
import { currentUser, employeesApi, errMsg } from "../api";
import type { Employee } from "../api";
import { Badge, Btn, Card, Empty, ErrorBox, Field, inputCls, Modal } from "../components/ui";

export default function Employees() {
  const user = currentUser();
  const [list, setList] = useState<Employee[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [detail, setDetail] = useState<Employee | null>(null);
  const [form, setForm] = useState({
    employee_code: "",
    full_name: "",
    email: "",
    phone: "",
    role_title: "Associate",
    status: "active",
  });

  function load() {
    employeesApi
      .list({ search, status, limit: 100 })
      .then((d) => {
        setList(d.items);
        setTotal(d.total);
      })
      .catch((e) => setError(errMsg(e)));
  }

  useEffect(load, [search, status]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    try {
      await employeesApi.create(form);
      setShowCreate(false);
      load();
    } catch (err) {
      setError(errMsg(err));
    }
  }

  async function deactivate(id: number) {
    if (!window.confirm("Deactivate this employee? History is preserved.")) return;
    try {
      await employeesApi.deactivate(id);
      load();
    } catch (err) {
      setError(errMsg(err));
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Employees ({total})</h1>
        {user?.role === "admin" && (
          <Btn onClick={() => setShowCreate(true)}>Add employee</Btn>
        )}
      </div>
      <ErrorBox message={error} />
      <Card>
        <div className="flex gap-3 mb-3">
          <input
            className={inputCls}
            placeholder="Search name or code…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select
            className={inputCls}
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>
        {list.length === 0 ? (
          <Empty text="No employees found." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted border-b border-border">
                  <th className="py-2 pr-3">Code</th>
                  <th className="py-2 pr-3">Name</th>
                  <th className="py-2 pr-3">Email</th>
                  <th className="py-2 pr-3">Role</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2" />
                </tr>
              </thead>
              <tbody>
                {list.map((e) => (
                  <tr key={e.id} className="border-b border-border last:border-0">
                    <td className="py-2 pr-3">{e.employee_code}</td>
                    <td className="py-2 pr-3 font-medium">{e.full_name}</td>
                    <td className="py-2 pr-3 text-muted">{e.email}</td>
                    <td className="py-2 pr-3">{e.role_title}</td>
                    <td className="py-2 pr-3">
                      <Badge tone={e.status === "active" ? "green" : "gray"}>
                        {e.status}
                      </Badge>
                    </td>
                    <td className="py-2 flex gap-2">
                      <Btn
                        tone="secondary"
                        small
                        onClick={() =>
                          employeesApi
                            .get(e.id)
                            .then(setDetail)
                            .catch((err) => setError(errMsg(err)))
                        }
                      >
                        Details
                      </Btn>
                      {user?.role === "admin" && e.status === "active" && (
                        <Btn tone="danger" small onClick={() => deactivate(e.id)}>
                          Deactivate
                        </Btn>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {showCreate && (
        <Modal title="Add employee" onClose={() => setShowCreate(false)}>
          <form onSubmit={create} className="space-y-3">
            <Field label="Employee code">
              <input
                className={inputCls}
                required
                value={form.employee_code}
                onChange={(e) => setForm({ ...form, employee_code: e.target.value })}
              />
            </Field>
            <Field label="Full name">
              <input
                className={inputCls}
                required
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              />
            </Field>
            <Field label="Email">
              <input
                className={inputCls}
                required
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </Field>
            <Field label="Phone">
              <input
                className={inputCls}
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
              />
            </Field>
            <Field label="Role title">
              <input
                className={inputCls}
                value={form.role_title}
                onChange={(e) => setForm({ ...form, role_title: e.target.value })}
              />
            </Field>
            <Btn type="submit">Create</Btn>
          </form>
        </Modal>
      )}

      {detail && (
        <Modal title={`${detail.full_name} (${detail.employee_code})`} onClose={() => setDetail(null)}>
          <div className="space-y-4 text-sm">
            <p className="text-muted">
              {detail.email} · {detail.role_title} · {detail.status}
            </p>
            <div>
              <h4 className="font-semibold mb-1">Assignments</h4>
              {detail.assignments?.length ? (
                <ul className="list-disc pl-5">
                  {detail.assignments.map((a) => (
                    <li key={a.id}>
                      Brand #{a.brand_id}, process #{a.process_id ?? "any"}
                      {a.is_primary ? " (primary)" : " (backup)"} —{" "}
                      {a.is_active ? "active" : "inactive"}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted">None.</p>
              )}
            </div>
            <div>
              <h4 className="font-semibold mb-1">Leave requests</h4>
              {detail.leaves?.length ? (
                <ul className="list-disc pl-5">
                  {detail.leaves.map((l) => (
                    <li key={l.id}>
                      {l.start_date} → {l.end_date} ({l.leave_type}): {l.status}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted">None.</p>
              )}
            </div>
            <div>
              <h4 className="font-semibold mb-1">Recent roster entries</h4>
              {detail.recent_entries?.length ? (
                <ul className="list-disc pl-5">
                  {detail.recent_entries.slice(0, 15).map((r, i) => (
                    <li key={i}>
                      {r.date}: {r.entry_type}
                      {r.brand_id ? ` (brand #${r.brand_id})` : ""}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted">None.</p>
              )}
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

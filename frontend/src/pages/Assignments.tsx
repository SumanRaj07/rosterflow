import { useEffect, useState } from "react";
import { assignmentsApi, brandsApi, currentUser, employeesApi, errMsg, processesApi } from "../api";
import type { Assignment, Brand, Employee, Process } from "../api";
import { Badge, Btn, Card, Empty, ErrorBox, Field, inputCls, Modal } from "../components/ui";

export default function Assignments() {
  const user = currentUser();
  const [list, setList] = useState<Assignment[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [emps, setEmps] = useState<Employee[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [procs, setProcs] = useState<Process[]>([]);
  const [filterBrand, setFilterBrand] = useState("");
  const [form, setForm] = useState({
    employee_id: "",
    brand_id: "",
    process_id: "",
    is_primary: false,
  });

  function load() {
    assignmentsApi
      .list({ limit: 200, ...(filterBrand ? { brand_id: Number(filterBrand) } : {}) })
      .then((d) => setList(d.items))
      .catch((e) => setError(errMsg(e)));
  }

  useEffect(() => {
    employeesApi.list({ limit: 200 }).then((d) => setEmps(d.items)).catch(() => undefined);
    brandsApi.list({ limit: 100 }).then((d) => setBrands(d.items)).catch(() => undefined);
    processesApi.list({ limit: 100 }).then((d) => setProcs(d.items)).catch(() => undefined);
  }, []);

  useEffect(load, [filterBrand]);

  const empName = (id: number) => emps.find((e) => e.id === id)?.full_name || `#${id}`;
  const brandName = (id: number) => brands.find((b) => b.id === id)?.name || `#${id}`;
  const procName = (id: number | null) =>
    id === null ? "any process" : procs.find((p) => p.id === id)?.name || `#${id}`;

  async function create(e: React.FormEvent) {
    e.preventDefault();
    try {
      await assignmentsApi.create({
        employee_id: Number(form.employee_id),
        brand_id: Number(form.brand_id),
        process_id: form.process_id ? Number(form.process_id) : null,
        is_primary: form.is_primary,
      });
      setShowCreate(false);
      setForm({ employee_id: "", brand_id: "", process_id: "", is_primary: false });
      load();
    } catch (err) {
      setError(errMsg(err));
    }
  }

  async function toggleActive(a: Assignment) {
    try {
      await assignmentsApi.update(a.id, { is_active: !a.is_active });
      load();
    } catch (err) {
      setError(errMsg(err));
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Assignments</h1>
        {user?.role === "admin" && <Btn onClick={() => setShowCreate(true)}>Add assignment</Btn>}
      </div>
      <ErrorBox message={error} />
      <Card>
        <div className="mb-3">
          <select className={inputCls} value={filterBrand} onChange={(e) => setFilterBrand(e.target.value)}>
            <option value="">All brands</option>
            {brands.map((b) => (
              <option key={b.id} value={b.id}>{b.name}</option>
            ))}
          </select>
        </div>
        {list.length === 0 ? (
          <Empty text="No assignments found." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted border-b border-border">
                <th className="py-2 pr-3">Employee</th>
                <th className="py-2 pr-3">Brand</th>
                <th className="py-2 pr-3">Process</th>
                <th className="py-2 pr-3">Primary</th>
                <th className="py-2 pr-3">Active</th>
                <th className="py-2" />
              </tr>
            </thead>
            <tbody>
              {list.map((a) => (
                <tr key={a.id} className="border-b border-border last:border-0">
                  <td className="py-2 pr-3">{empName(a.employee_id)}</td>
                  <td className="py-2 pr-3">{brandName(a.brand_id)}</td>
                  <td className="py-2 pr-3">{procName(a.process_id)}</td>
                  <td className="py-2 pr-3">
                    <Badge tone={a.is_primary ? "blue" : "gray"}>{a.is_primary ? "primary" : "backup"}</Badge>
                  </td>
                  <td className="py-2 pr-3">
                    <Badge tone={a.is_active ? "green" : "gray"}>{a.is_active ? "yes" : "no"}</Badge>
                  </td>
                  <td className="py-2">
                    {user?.role === "admin" && (
                      <Btn tone="secondary" small onClick={() => toggleActive(a)}>
                        {a.is_active ? "Deactivate" : "Activate"}
                      </Btn>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
      {showCreate && (
        <Modal title="Add assignment" onClose={() => setShowCreate(false)}>
          <form onSubmit={create} className="space-y-3">
            <Field label="Employee">
              <select className={inputCls} required value={form.employee_id} onChange={(e) => setForm({ ...form, employee_id: e.target.value })}>
                <option value="">Select…</option>
                {emps.map((e) => (
                  <option key={e.id} value={e.id}>{e.full_name}</option>
                ))}
              </select>
            </Field>
            <Field label="Brand">
              <select className={inputCls} required value={form.brand_id} onChange={(e) => setForm({ ...form, brand_id: e.target.value })}>
                <option value="">Select…</option>
                {brands.map((b) => (
                  <option key={b.id} value={b.id}>{b.name}</option>
                ))}
              </select>
            </Field>
            <Field label="Process (leave blank for any process of the brand)">
              <select className={inputCls} value={form.process_id} onChange={(e) => setForm({ ...form, process_id: e.target.value })}>
                <option value="">Any process</option>
                {procs.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </Field>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.is_primary} onChange={(e) => setForm({ ...form, is_primary: e.target.checked })} />
              Primary assignee (scheduled first; others are the backup pool)
            </label>
            <Btn type="submit">Create</Btn>
          </form>
        </Modal>
      )}
    </div>
  );
}

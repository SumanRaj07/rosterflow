import { useEffect, useState } from "react";
import { currentUser, errMsg, processesApi } from "../api";
import type { Process } from "../api";
import { Badge, Btn, Card, Empty, ErrorBox, Field, inputCls, Modal } from "../components/ui";

export default function Processes() {
  const user = currentUser();
  const [list, setList] = useState<Process[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ code: "", name: "", description: "" });

  function load() {
    processesApi.list({ limit: 100 }).then((d) => setList(d.items)).catch((e) => setError(errMsg(e)));
  }
  useEffect(load, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    try {
      await processesApi.create(form);
      setShowCreate(false);
      setForm({ code: "", name: "", description: "" });
      load();
    } catch (err) {
      setError(errMsg(err));
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Processes</h1>
        {user?.role === "admin" && <Btn onClick={() => setShowCreate(true)}>Add process</Btn>}
      </div>
      <ErrorBox message={error} />
      <Card>
        {list.length === 0 ? (
          <Empty text="No processes yet." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted border-b border-border">
                <th className="py-2 pr-3">Code</th>
                <th className="py-2 pr-3">Name</th>
                <th className="py-2 pr-3">Description</th>
                <th className="py-2 pr-3">Active</th>
              </tr>
            </thead>
            <tbody>
              {list.map((p) => (
                <tr key={p.id} className="border-b border-border last:border-0">
                  <td className="py-2 pr-3">{p.code}</td>
                  <td className="py-2 pr-3 font-medium">{p.name}</td>
                  <td className="py-2 pr-3 text-muted">{p.description || "—"}</td>
                  <td className="py-2 pr-3">
                    <Badge tone={p.is_active ? "green" : "gray"}>{p.is_active ? "yes" : "no"}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
      {showCreate && (
        <Modal title="Add process" onClose={() => setShowCreate(false)}>
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
    </div>
  );
}

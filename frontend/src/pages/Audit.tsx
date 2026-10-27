import { useEffect, useState } from "react";
import { auditApi, errMsg } from "../api";
import type { AuditEntry } from "../api";
import { Card, Empty, ErrorBox, inputCls } from "../components/ui";

export default function Audit() {
  const [list, setList] = useState<AuditEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [action, setAction] = useState("");
  const [entityType, setEntityType] = useState("");

  function load() {
    auditApi
      .list({
        ...(action ? { action } : {}),
        ...(entityType ? { entity_type: entityType } : {}),
      })
      .then(setList)
      .catch((e) => setError(errMsg(e)));
  }
  useEffect(load, [action, entityType]);

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Audit Log</h1>
      <ErrorBox message={error} />
      <Card>
        <div className="flex gap-2 mb-4">
          <input className={inputCls} placeholder="Filter by action (e.g. roster.publish)…" value={action} onChange={(e) => setAction(e.target.value)} />
          <input className={inputCls} placeholder="Filter by entity type…" value={entityType} onChange={(e) => setEntityType(e.target.value)} />
        </div>
        {list.length === 0 ? (
          <Empty text="No audit entries match these filters. Note: only managers and admins can view the audit log." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted border-b border-border">
                <th className="py-2 pr-3">Time</th>
                <th className="py-2 pr-3">User</th>
                <th className="py-2 pr-3">Action</th>
                <th className="py-2 pr-3">Entity</th>
                <th className="py-2 pr-3">Details</th>
              </tr>
            </thead>
            <tbody>
              {list.map((a) => (
                <tr key={a.id} className="border-b border-border last:border-0">
                  <td className="py-2 pr-3 text-muted">{a.created_at || "—"}</td>
                  <td className="py-2 pr-3">{a.user_id ? `#${a.user_id}` : "system"}</td>
                  <td className="py-2 pr-3 font-medium">{a.action}</td>
                  <td className="py-2 pr-3">{a.entity_type} #{a.entity_id ?? "—"}</td>
                  <td className="py-2 pr-3 text-muted">{a.details ? JSON.stringify(a.details) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}

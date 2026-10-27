import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { currentUser, errMsg, rostersApi } from "../api";
import type { Roster } from "../api";
import { Badge, Btn, Card, Empty, ErrorBox, Field, inputCls, Modal, statusTone } from "../components/ui";

export default function Approvals() {
  const user = currentUser();
  const canApprove = user?.role === "admin" || user?.role === "manager";
  const [list, setList] = useState<Roster[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [publishTarget, setPublishTarget] = useState<Roster | null>(null);
  const [justification, setJustification] = useState("");
  const [comment, setComment] = useState("");
  const [history, setHistory] = useState<{ approvals: unknown[]; changes: unknown[] } | null>(null);
  const [historyId, setHistoryId] = useState<number | null>(null);

  function load() {
    rostersApi
      .list(statusFilter ? { status: statusFilter } : undefined)
      .then(setList)
      .catch((e) => setError(errMsg(e)));
  }
  useEffect(load, [statusFilter]);

  async function review(r: Roster, decision: string) {
    try {
      await rostersApi.review(r.id, decision, comment || undefined);
      load();
    } catch (err) {
      setError(errMsg(err));
    }
  }

  async function publish() {
    if (!publishTarget) return;
    try {
      await rostersApi.publish(publishTarget.id, justification || undefined);
      setPublishTarget(null);
      setJustification("");
      load();
    } catch (err) {
      setError(errMsg(err));
    }
  }

  async function newVersion(r: Roster) {
    try {
      await rostersApi.newVersion(r.id);
      load();
    } catch (err) {
      setError(errMsg(err));
    }
  }

  async function showHistory(r: Roster) {
    try {
      const [approvals, changes] = await Promise.all([
        rostersApi.approvals(r.id),
        rostersApi.changes(r.id),
      ]);
      setHistory({ approvals, changes });
      setHistoryId(r.id);
    } catch (err) {
      setError(errMsg(err));
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Approvals</h1>
      <p className="text-sm text-muted">
        Workflow: Draft → Pod Lead Review → Manager Approval → Published. Publishing is blocked
        while critical conflicts are open unless an exception justification is recorded.
      </p>
      <ErrorBox message={error} />
      <Card>
        <div className="flex gap-2 mb-3">
          <select className={inputCls} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All statuses</option>
            <option value="draft">Draft</option>
            <option value="validated">Validated</option>
            <option value="pending_review">Pending review</option>
            <option value="approved">Approved</option>
            <option value="published">Published</option>
            <option value="superseded">Superseded</option>
          </select>
          <input className={inputCls} placeholder="Comment for review decisions…" value={comment} onChange={(e) => setComment(e.target.value)} />
        </div>
        {list.length === 0 ? (
          <Empty text="No rosters found." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted border-b border-border">
                <th className="py-2 pr-3">Roster</th>
                <th className="py-2 pr-3">Period</th>
                <th className="py-2 pr-3">Status</th>
                <th className="py-2 pr-3">Coverage</th>
                <th className="py-2" />
              </tr>
            </thead>
            <tbody>
              {list.map((r) => (
                <tr key={r.id} className="border-b border-border last:border-0">
                  <td className="py-2 pr-3">#{r.id} v{r.version}</td>
                  <td className="py-2 pr-3">{r.month}/{r.year}</td>
                  <td className="py-2 pr-3"><Badge tone={statusTone(r.status)}>{r.status}</Badge></td>
                  <td className="py-2 pr-3">
                    {r.metrics ? `${Math.round(r.metrics.coverage_rate * 1000) / 10}%` : "—"}
                  </td>
                  <td className="py-2 flex flex-wrap gap-1">
                    <Link to={`/roster?id=${r.id}`} className="text-primary text-xs font-medium py-1 px-1">View</Link>
                    {(r.status === "draft" || r.status === "validated") && (
                      <Btn small tone="secondary" onClick={() => review(r, "submitted")}>Submit for review</Btn>
                    )}
                    {r.status === "pending_review" && canApprove && (
                      <>
                        <Btn small onClick={() => review(r, "approved")}>Approve</Btn>
                        <Btn small tone="danger" onClick={() => review(r, "rejected")}>Reject</Btn>
                        <Btn small tone="secondary" onClick={() => review(r, "changes_requested")}>Request changes</Btn>
                      </>
                    )}
                    {r.status === "approved" && canApprove && (
                      <Btn small onClick={() => setPublishTarget(r)}>Publish…</Btn>
                    )}
                    {r.status === "published" && (
                      <Btn small tone="secondary" onClick={() => newVersion(r)}>New version</Btn>
                    )}
                    <Btn small tone="ghost" onClick={() => showHistory(r)}>History</Btn>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {publishTarget && (
        <Modal title={`Publish roster #${publishTarget.id}`} onClose={() => setPublishTarget(null)}>
          <div className="space-y-3">
            <p className="text-sm text-muted">
              If critical conflicts are still open, publishing requires an exception justification
              (recorded on the roster and in the audit log).
            </p>
            <Field label="Exception justification (optional if no critical conflicts)">
              <textarea className={inputCls} rows={3} value={justification} onChange={(e) => setJustification(e.target.value)} />
            </Field>
            <Btn onClick={publish}>Publish</Btn>
          </div>
        </Modal>
      )}

      {history && historyId !== null && (
        <Modal title={`History — roster #${historyId}`} onClose={() => setHistory(null)}>
          <div className="space-y-4 text-sm">
            <div>
              <h4 className="font-semibold mb-1">Approvals</h4>
              {history.approvals.length === 0 ? (
                <p className="text-muted">No approval actions yet.</p>
              ) : (
                <ul className="list-disc pl-5">
                  {history.approvals.map((a, i) => {
                    const rec = a as Record<string, unknown>;
                    return (
                      <li key={i}>
                        {String(rec.decision)} by user #{String(rec.reviewer_id)}
                        {rec.comment ? ` — ${String(rec.comment)}` : ""}
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
            <div>
              <h4 className="font-semibold mb-1">Changes</h4>
              {history.changes.length === 0 ? (
                <p className="text-muted">No manual changes yet.</p>
              ) : (
                <ul className="list-disc pl-5">
                  {history.changes.map((c, i) => {
                    const rec = c as Record<string, unknown>;
                    return (
                      <li key={i}>
                        {String(rec.date)}: employee #{String(rec.employee_id)} —{" "}
                        {String(rec.old_value)} → {String(rec.new_value)}
                        {rec.reason ? ` (${String(rec.reason)})` : ""}
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

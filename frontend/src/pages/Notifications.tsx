import { useEffect, useState } from "react";
import { errMsg, notificationsApi } from "../api";
import type { NotificationItem } from "../api";
import { Badge, Btn, Card, Empty, ErrorBox } from "../components/ui";

export default function Notifications() {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unread, setUnread] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [unreadOnly, setUnreadOnly] = useState(false);

  function load() {
    notificationsApi
      .list(unreadOnly)
      .then((d) => {
        setItems(d.items);
        setUnread(d.unread_count);
      })
      .catch((e) => setError(errMsg(e)));
  }
  useEffect(load, [unreadOnly]);

  async function markRead(id: number) {
    try {
      await notificationsApi.markRead(id);
      load();
    } catch (err) {
      setError(errMsg(err));
    }
  }

  async function readAll() {
    try {
      await notificationsApi.readAll();
      load();
    } catch (err) {
      setError(errMsg(err));
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Notifications ({unread} unread)</h1>
        <div className="flex gap-2">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={unreadOnly} onChange={(e) => setUnreadOnly(e.target.checked)} />
            Unread only
          </label>
          <Btn tone="secondary" small onClick={readAll}>Mark all read</Btn>
        </div>
      </div>
      <ErrorBox message={error} />
      <Card>
        {items.length === 0 ? (
          <Empty text="No notifications." />
        ) : (
          <ul className="space-y-2">
            {items.map((n) => (
              <li key={n.id} className="flex justify-between gap-4 border-b border-border pb-2 text-sm">
                <div>
                  <Badge tone={n.is_read ? "gray" : "blue"}>{n.type}</Badge>
                  <p className="mt-1">{n.message}</p>
                  {n.created_at && <p className="text-muted text-xs">{n.created_at}</p>}
                </div>
                {!n.is_read && (
                  <Btn small tone="secondary" onClick={() => markRead(n.id)}>Mark read</Btn>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

import { useEffect, useMemo, useState } from "react";
import { currentUser, errMsg, holidaysApi } from "../api";
import type { Holiday } from "../api";
import { Btn, Card, Empty, ErrorBox, Field, inputCls, Modal } from "../components/ui";

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function CalendarPage() {
  const user = currentUser();
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [holidays, setHolidays] = useState<Holiday[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ date: "", name: "", is_mandatory_off: true });

  function load() {
    holidaysApi.list(year).then(setHolidays).catch((e) => setError(errMsg(e)));
  }
  useEffect(load, [year]);

  const cells = useMemo(() => {
    const first = new Date(year, month - 1, 1);
    const daysInMonth = new Date(year, month, 0).getDate();
    const startOffset = (first.getDay() + 6) % 7; // Monday-first
    const out: (number | null)[] = Array(startOffset).fill(null);
    for (let d = 1; d <= daysInMonth; d++) out.push(d);
    return out;
  }, [year, month]);

  const holByDay = useMemo(() => {
    const m = new Map<number, Holiday>();
    for (const h of holidays) {
      const d = new Date(h.date + "T00:00:00");
      if (d.getFullYear() === year && d.getMonth() + 1 === month) m.set(d.getDate(), h);
    }
    return m;
  }, [holidays, year, month]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    try {
      await holidaysApi.create(form);
      setShowCreate(false);
      setForm({ date: "", name: "", is_mandatory_off: true });
      load();
    } catch (err) {
      setError(errMsg(err));
    }
  }

  async function remove(id: number) {
    if (!window.confirm("Delete this holiday?")) return;
    try {
      await holidaysApi.remove(id);
      load();
    } catch (err) {
      setError(errMsg(err));
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Calendar &amp; Holidays</h1>
        {user?.role === "admin" && <Btn onClick={() => setShowCreate(true)}>Add holiday</Btn>}
      </div>
      <ErrorBox message={error} />
      <Card>
        <div className="flex gap-2 mb-4">
          <select className={inputCls} value={month} onChange={(e) => setMonth(Number(e.target.value))}>
            {Array.from({ length: 12 }, (_, i) => (
              <option key={i + 1} value={i + 1}>
                {new Date(year, i, 1).toLocaleString("en", { month: "long" })}
              </option>
            ))}
          </select>
          <select className={inputCls} value={year} onChange={(e) => setYear(Number(e.target.value))}>
            {[2025, 2026, 2027].map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>
        <div className="grid grid-cols-7 gap-1 text-sm">
          {WEEKDAYS.map((d) => (
            <div key={d} className="font-semibold text-muted text-center py-1">{d}</div>
          ))}
          {cells.map((d, i) => {
            const h = d ? holByDay.get(d) : undefined;
            return (
              <div
                key={i}
                className={`border border-border rounded-md p-2 min-h-[56px] ${
                  h ? "bg-violet-50 border-violet-200" : ""
                }`}
              >
                <div className="font-medium">{d ?? ""}</div>
                {h && <div className="text-xs text-violet-800">{h.name}</div>}
              </div>
            );
          })}
        </div>
      </Card>
      <Card title={`Holidays in ${year}`}>
        {holidays.length === 0 ? (
          <Empty text="No holidays recorded for this year." />
        ) : (
          <ul className="space-y-1 text-sm">
            {holidays.map((h) => (
              <li key={h.id} className="flex justify-between border-b border-border pb-1">
                <span>{h.date} — {h.name}{h.is_mandatory_off ? " (mandatory off)" : ""}</span>
                {user?.role === "admin" && (
                  <Btn tone="danger" small onClick={() => remove(h.id)}>Delete</Btn>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
      {showCreate && (
        <Modal title="Add holiday" onClose={() => setShowCreate(false)}>
          <form onSubmit={create} className="space-y-3">
            <Field label="Date">
              <input className={inputCls} type="date" required value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
            </Field>
            <Field label="Name">
              <input className={inputCls} required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </Field>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.is_mandatory_off} onChange={(e) => setForm({ ...form, is_mandatory_off: e.target.checked })} />
              Mandatory off
            </label>
            <Btn type="submit">Create</Btn>
          </form>
        </Modal>
      )}
    </div>
  );
}

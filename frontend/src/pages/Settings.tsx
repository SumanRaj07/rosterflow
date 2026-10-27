import { useEffect, useState } from "react";
import { currentUser, errMsg, rulesApi } from "../api";
import { Btn, Card, ErrorBox, Field, inputCls } from "../components/ui";

const RULE_META: Record<string, string> = {
  max_consecutive_days: "Maximum consecutive working days before a forced off",
  max_monthly_workdays: "Maximum working days per employee per month",
  min_weekly_offs: "Minimum weekly offs expected per employee",
  sunday_off: "Sundays are weekly offs when no requirement applies",
  holiday_off: "Holidays are mandatory offs when no requirement applies",
};

export default function Settings() {
  const user = currentUser();
  const [rules, setRules] = useState<Record<string, unknown>>({});
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    rulesApi.get().then(setRules).catch((e) => setError(errMsg(e)));
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    try {
      await rulesApi.save(rules);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError(errMsg(err));
    }
  }

  function setValue(key: string, raw: string) {
    const cur = rules[key];
    let val: unknown = raw;
    if (typeof cur === "number") val = Number(raw);
    if (typeof cur === "boolean") val = raw === "true";
    setRules({ ...rules, [key]: val });
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Settings</h1>
      <ErrorBox message={error} />
      {saved && (
        <div className="bg-green-50 border border-green-200 text-success text-sm rounded-md px-3 py-2">
          Working rules saved.
        </div>
      )}
      <Card title="Working rules" subtitle="These rules drive roster generation and validation.">
        {user?.role !== "admin" && (
          <p className="text-sm text-muted mb-3">Only admins can change working rules.</p>
        )}
        <form onSubmit={save} className="space-y-3">
          {Object.entries(rules).map(([key, val]) => (
            <Field key={key} label={`${key} — ${RULE_META[key] || ""}`}>
              {typeof val === "boolean" ? (
                <select
                  className={inputCls}
                  value={String(val)}
                  disabled={user?.role !== "admin"}
                  onChange={(e) => setValue(key, e.target.value)}
                >
                  <option value="true">true</option>
                  <option value="false">false</option>
                </select>
              ) : (
                <input
                  className={inputCls}
                  type="number"
                  value={String(val)}
                  disabled={user?.role !== "admin"}
                  onChange={(e) => setValue(key, e.target.value)}
                />
              )}
            </Field>
          ))}
          {user?.role === "admin" && <Btn type="submit">Save rules</Btn>}
        </form>
      </Card>
      <Card title="Seeded demo accounts" subtitle="Created by the backend seed script. Passwords are demo-only.">
        <ul className="text-sm space-y-1">
          <li>Admin — admin@rosterflow.local / Admin@123</li>
          <li>Manager — manager@rosterflow.local / Manager@123</li>
          <li>Pod leads — lead.a@rosterflow.local, lead.b@…, lead.c@…, lead.d@… / Lead@123</li>
          <li>Employees — first employees&apos; emails (see Employees page) / Emp@123</li>
        </ul>
        <p className="text-sm text-muted mt-3">
          Demo month: November 2026 (Diwali on 2026-11-08). Ion Energy is deliberately tight:
          3 staff for a 3-person daily requirement, so the 6-consecutive-day rule produces
          Saturday coverage gaps with certification-based backup recommendations.
        </p>
      </Card>
    </div>
  );
}

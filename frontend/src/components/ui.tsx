import type { ReactNode } from "react";

export function Card({
  title,
  subtitle,
  actions,
  children,
}: {
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="bg-surface border border-border rounded-lg p-4 shadow-sm">
      {(title || actions) && (
        <div className="flex items-start justify-between gap-4 mb-3">
          <div>
            {title && <h2 className="text-base font-semibold text-ink">{title}</h2>}
            {subtitle && <p className="text-sm text-muted mt-0.5">{subtitle}</p>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

export function Badge({ tone, children }: { tone: string; children: ReactNode }) {
  const tones: Record<string, string> = {
    gray: "bg-gray-100 text-gray-700",
    blue: "bg-blue-50 text-primary",
    green: "bg-green-50 text-success",
    amber: "bg-amber-50 text-warning",
    red: "bg-red-50 text-danger",
  };
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
        tones[tone] || tones.gray
      }`}
    >
      {children}
    </span>
  );
}

export function statusTone(status: string): string {
  switch (status) {
    case "published":
      return "green";
    case "approved":
      return "blue";
    case "pending_review":
      return "amber";
    case "rejected":
      return "red";
    case "draft":
    case "pending":
      return "gray";
    default:
      return "gray";
  }
}

export function Btn({
  children,
  onClick,
  tone = "primary",
  disabled,
  type,
  small,
}: {
  children: ReactNode;
  onClick?: () => void;
  tone?: "primary" | "secondary" | "danger" | "ghost";
  disabled?: boolean;
  type?: "button" | "submit";
  small?: boolean;
}) {
  const tones: Record<string, string> = {
    primary: "bg-primary text-white hover:bg-blue-800",
    secondary: "bg-white border border-border text-ink hover:bg-bg",
    danger: "bg-danger text-white hover:bg-red-800",
    ghost: "text-primary hover:bg-blue-50",
  };
  return (
    <button
      type={type || "button"}
      disabled={disabled}
      onClick={onClick}
      className={`${small ? "px-2 py-1 text-xs" : "px-3 py-1.5 text-sm"} rounded-md font-medium disabled:opacity-50 ${tones[tone]}`}
    >
      {children}
    </button>
  );
}

export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="block text-sm">
      <span className="text-muted">{label}</span>
      <div className="mt-1">{children}</div>
    </label>
  );
}

export const inputCls =
  "w-full border border-border rounded-md px-2.5 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary/40";

export function ErrorBox({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div className="bg-red-50 border border-red-200 text-danger text-sm rounded-md px-3 py-2 mb-3">
      {message}
    </div>
  );
}

export function Empty({ text }: { text: string }) {
  return <p className="text-sm text-muted py-4 text-center">{text}</p>;
}

export function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-surface rounded-lg shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-5">
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-semibold text-ink">{title}</h3>
          <button onClick={onClose} className="text-muted text-xl leading-none">
            ×
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { Bell, LogOut } from "lucide-react";
import { currentUser, logout, notificationsApi } from "../api";

const NAV = [
  { to: "/", label: "Dashboard" },
  { to: "/employees", label: "Employees" },
  { to: "/brands", label: "Brands" },
  { to: "/processes", label: "Processes" },
  { to: "/pods", label: "Pods" },
  { to: "/assignments", label: "Assignments" },
  { to: "/calendar", label: "Calendar" },
  { to: "/leave", label: "Leave & Availability" },
  { to: "/generate", label: "Roster Generator" },
  { to: "/roster", label: "Roster Calendar" },
  { to: "/conflicts", label: "Conflicts" },
  { to: "/backups", label: "Backups" },
  { to: "/plans", label: "Alternative Plans" },
  { to: "/approvals", label: "Approvals" },
  { to: "/notifications", label: "Notifications" },
  { to: "/reports", label: "Reports & Exports" },
  { to: "/audit", label: "Audit Log" },
  { to: "/settings", label: "Settings" },
];

export default function Layout() {
  const user = currentUser();
  const navigate = useNavigate();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    notificationsApi
      .list(true)
      .then((d) => setUnread(d.unread_count))
      .catch(() => undefined);
  }, []);

  return (
    <div className="min-h-screen flex">
      <aside className="w-56 shrink-0 bg-ink text-white flex flex-col">
        <div className="px-4 py-4 border-b border-white/10">
          <div className="font-bold text-lg tracking-tight">RosterFlow</div>
          <div className="text-xs text-white/60">Smart Roster Management</div>
        </div>
        <nav className="flex-1 overflow-y-auto py-2">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `block px-4 py-2 text-sm ${
                  isActive ? "bg-white/15 font-medium" : "text-white/75 hover:bg-white/10"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="px-4 py-3 border-t border-white/10 text-xs text-white/60">
          {user?.email}
          <br />
          Role: {user?.role}
        </div>
      </aside>
      <div className="flex-1 min-w-0 flex flex-col">
        <header className="bg-surface border-b border-border px-5 py-3 flex items-center justify-between sticky top-0 z-10">
          <div className="font-semibold text-ink">RosterFlow</div>
          <div className="flex items-center gap-3">
            <Link
              to="/notifications"
              className="relative text-muted hover:text-ink"
              title="Notifications"
            >
              <Bell size={20} />
              {unread > 0 && (
                <span className="absolute -top-2 -right-2 bg-danger text-white text-[10px] rounded-full px-1.5 py-0.5">
                  {unread}
                </span>
              )}
            </Link>
            <button
              onClick={() => {
                logout();
                navigate("/login");
              }}
              className="flex items-center gap-1 text-sm text-muted hover:text-ink"
            >
              <LogOut size={16} /> Sign out
            </button>
          </div>
        </header>
        <main className="p-5 space-y-4 max-w-[1400px] w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

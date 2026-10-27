import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { currentUser } from "./api";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Employees from "./pages/Employees";
import Brands from "./pages/Brands";
import Processes from "./pages/Processes";
import Pods from "./pages/Pods";
import Assignments from "./pages/Assignments";
import CalendarPage from "./pages/Calendar";
import LeavePage from "./pages/Leave";
import Generator from "./pages/Generator";
import RosterCalendar from "./pages/RosterCalendar";
import Conflicts from "./pages/Conflicts";
import Backups from "./pages/Backups";
import Plans from "./pages/Plans";
import Approvals from "./pages/Approvals";
import Notifications from "./pages/Notifications";
import Reports from "./pages/Reports";
import Audit from "./pages/Audit";
import Settings from "./pages/Settings";

function Guard({ children }: { children: React.ReactNode }) {
  if (!currentUser()) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          element={
            <Guard>
              <Layout />
            </Guard>
          }
        >
          <Route path="/" element={<Dashboard />} />
          <Route path="/employees" element={<Employees />} />
          <Route path="/brands" element={<Brands />} />
          <Route path="/processes" element={<Processes />} />
          <Route path="/pods" element={<Pods />} />
          <Route path="/assignments" element={<Assignments />} />
          <Route path="/calendar" element={<CalendarPage />} />
          <Route path="/leave" element={<LeavePage />} />
          <Route path="/generate" element={<Generator />} />
          <Route path="/roster" element={<RosterCalendar />} />
          <Route path="/conflicts" element={<Conflicts />} />
          <Route path="/backups" element={<Backups />} />
          <Route path="/plans" element={<Plans />} />
          <Route path="/approvals" element={<Approvals />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/audit" element={<Audit />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

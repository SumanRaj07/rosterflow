import axios from "axios";
import type { AxiosResponse } from "axios";

// Deployment: set VITE_API_URL in the hosting dashboard (e.g. Vercel) to the
// deployed backend URL. Local dev falls back to the local backend.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000",
});

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem("rosterflow_token");
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

export function errMsg(e: unknown): string {
  if (axios.isAxiosError(e)) {
    const d = e.response?.data as { detail?: string } | undefined;
    if (d?.detail) return d.detail;
    if (e.response?.status) return `Request failed (${e.response.status})`;
    return e.message;
  }
  return e instanceof Error ? e.message : "Unknown error";
}

export interface User {
  id: number;
  email: string;
  role: string;
  employee_id: number | null;
  is_active: boolean;
}

export interface Employee {
  id: number;
  employee_code: string;
  full_name: string;
  email: string;
  phone?: string | null;
  role_title: string;
  status: string;
  joining_date?: string | null;
  max_monthly_workdays?: number | null;
  notes?: string | null;
  assignments?: Assignment[];
  leaves?: Leave[];
  availabilities?: Availability[];
  recent_entries?: RosterEntryLite[];
}

export interface RosterEntryLite {
  roster_id: number;
  date: string;
  entry_type: string;
  brand_id: number | null;
  process_id: number | null;
}

export interface Brand {
  id: number;
  code: string;
  name: string;
  description?: string | null;
  is_active: boolean;
  staffing?: Staffing[];
  assigned_employee_ids?: number[];
  has_eligible_employees?: boolean;
}

export interface Process {
  id: number;
  code: string;
  name: string;
  description?: string | null;
  is_active: boolean;
}

export interface Pod {
  id: number;
  code: string;
  name: string;
  lead_id: number | null;
  is_active: boolean;
  member_employee_ids?: number[];
}

export interface Assignment {
  id: number;
  employee_id: number;
  brand_id: number;
  process_id: number | null;
  pod_id: number | null;
  start_date?: string | null;
  end_date?: string | null;
  is_active: boolean;
  is_primary: boolean;
}

export interface Staffing {
  id: number;
  brand_id: number;
  process_id: number;
  min_staff: number;
  applies: string;
  is_active: boolean;
}

export interface Holiday {
  id: number;
  date: string;
  name: string;
  is_mandatory_off: boolean;
}

export interface Availability {
  id: number;
  employee_id: number;
  date: string | null;
  weekday: number | null;
  kind: string;
  note: string | null;
}

export interface Preference {
  id: number;
  employee_id: number;
  preferred_off_weekday: number | null;
  shift_preference: string | null;
  notes: string | null;
}

export interface Leave {
  id: number;
  employee_id: number;
  start_date: string;
  end_date: string;
  leave_type: string;
  reason: string | null;
  status: string;
  reviewer_id: number | null;
  review_comment: string | null;
}

export interface CompOff {
  id: number;
  employee_id: number;
  earned_date: string;
  reason: string | null;
  status: string;
  used_date: string | null;
}

export interface RosterMetrics {
  coverage_rate: number;
  required_slots: number;
  filled_slots: number;
  gap_count: number;
  total_work_assignments: number;
  fairness_score: number;
  fairness_score_all_employees: number;
  workday_mean: number;
  workday_std: number;
  preference_satisfied_rate: number;
  preference_conflicts: number;
  per_employee: Record<string, { workdays: number; offs: number; weekend_days: number }>;
}

export interface RosterEntry {
  id: number;
  employee_id: number;
  date: string;
  entry_type: string;
  brand_id: number | null;
  process_id: number | null;
  is_manual: boolean;
  note: string | null;
}

export interface Conflict {
  id: number;
  roster_id: number | null;
  month: number;
  year: number;
  type: string;
  severity: string;
  date: string | null;
  brand_id: number | null;
  process_id: number | null;
  employee_id: number | null;
  rule: string | null;
  explanation: string;
  recommendation: string | null;
  status: string;
}

export interface Roster {
  id: number;
  month: number;
  year: number;
  status: string;
  brand_id: number | null;
  pod_id: number | null;
  process_id: number | null;
  version: number;
  parent_id: number | null;
  metrics: RosterMetrics | null;
  strategy: string | null;
  preferences_applied?: boolean;
  published_at: string | null;
  exception_justification: string | null;
  entries?: RosterEntry[];
  conflicts?: Conflict[];
}

export interface Plan {
  id: number;
  month: number;
  year: number;
  name: string;
  strategy: string;
  metrics: RosterMetrics | null;
  entries?: RosterEntryLite[];
  is_selected: boolean;
}

export interface Backup {
  id: number;
  conflict_id: number | null;
  roster_id: number | null;
  date: string;
  brand_id: number;
  process_id: number;
  employee_id: number;
  score: number;
  reason: string | null;
  status: string;
}

export interface NotificationItem {
  id: number;
  type: string;
  message: string;
  related_type: string | null;
  related_id: number | null;
  is_read: boolean;
  created_at: string | null;
}

export interface AuditEntry {
  id: number;
  user_id: number | null;
  action: string;
  entity_type: string;
  entity_id: number | null;
  details: Record<string, unknown> | null;
  created_at: string | null;
}

export interface DashboardData {
  active_employees: number;
  active_brands: number;
  open_conflicts: number;
  critical_conflicts: number;
  pending_leave: number;
  pending_review_rosters: number;
  published_rosters: number;
  latest_roster_coverage: number | null;
  brands_without_employees: string[];
  recent_conflicts: { id: number; type: string; severity: string; date: string | null; explanation: string }[];
  pending_leave_items: { id: number; employee_id: number; start_date: string; end_date: string; leave_type: string }[];
}

export interface Paged<T> {
  items: T[];
  total: number;
}

async function unwrap<T>(p: Promise<AxiosResponse<T>>): Promise<T> {
  return (await p).data;
}

export const get = <T>(url: string, params?: Record<string, unknown>) =>
  unwrap<T>(api.get(url, { params }));
export const post = <T>(url: string, body?: unknown) =>
  unwrap<T>(api.post(url, body));
export const patch = <T>(url: string, body?: unknown) =>
  unwrap<T>(api.patch(url, body));
export const del = <T>(url: string) => unwrap<T>(api.delete(url));

export async function downloadFile(url: string, filename: string) {
  const res = await api.get(url, { responseType: "blob" });
  const blobUrl = window.URL.createObjectURL(new Blob([res.data]));
  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = filename;
  a.click();
  window.URL.revokeObjectURL(blobUrl);
}

export function currentUser(): User | null {
  const raw = localStorage.getItem("rosterflow_user");
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}

export function logout() {
  localStorage.removeItem("rosterflow_token");
  localStorage.removeItem("rosterflow_user");
}

export const auth = {
  login: (email: string, password: string) =>
    post<{ token: string; user: User }>("/api/auth/login", { email, password }),
  me: () => get<User>("/api/auth/me"),
};

export const employeesApi = {
  list: (params?: Record<string, unknown>) =>
    get<Paged<Employee>>("/api/employees", params),
  get: (id: number) => get<Employee>(`/api/employees/${id}`),
  create: (body: unknown) => post<Employee>("/api/employees", body),
  update: (id: number, body: unknown) => patch<Employee>(`/api/employees/${id}`, body),
  deactivate: (id: number) => del(`/api/employees/${id}`),
};

export const brandsApi = {
  list: (params?: Record<string, unknown>) => get<Paged<Brand>>("/api/brands", params),
  get: (id: number) => get<Brand>(`/api/brands/${id}`),
  create: (body: unknown) => post<Brand>("/api/brands", body),
  update: (id: number, body: unknown) => patch<Brand>(`/api/brands/${id}`, body),
};

export const processesApi = {
  list: (params?: Record<string, unknown>) =>
    get<Paged<Process>>("/api/processes", params),
  create: (body: unknown) => post<Process>("/api/processes", body),
  update: (id: number, body: unknown) => patch<Process>(`/api/processes/${id}`, body),
};

export const podsApi = {
  list: () => get<Paged<Pod>>("/api/pods"),
  get: (id: number) => get<Pod>(`/api/pods/${id}`),
  create: (body: unknown) => post<Pod>("/api/pods", body),
  update: (id: number, body: unknown) => patch<Pod>(`/api/pods/${id}`, body),
  addMember: (podId: number, employeeId: number) =>
    post(`/api/pods/${podId}/members`, { employee_id: employeeId }),
  removeMember: (podId: number, employeeId: number) =>
    del(`/api/pods/${podId}/members/${employeeId}`),
};

export const assignmentsApi = {
  list: (params?: Record<string, unknown>) =>
    get<Paged<Assignment>>("/api/assignments", params),
  create: (body: unknown) => post<Assignment>("/api/assignments", body),
  update: (id: number, body: unknown) =>
    patch<Assignment>(`/api/assignments/${id}`, body),
};

export const staffingApi = {
  list: () => get<Staffing[]>("/api/staffing"),
  create: (body: unknown) => post<Staffing>("/api/staffing", body),
  update: (id: number, body: unknown) => patch<Staffing>(`/api/staffing/${id}`, body),
};

export const rulesApi = {
  get: () => get<Record<string, unknown>>("/api/rules"),
  save: (body: Record<string, unknown>) => api.put("/api/rules", body).then((r) => r.data),
};

export const holidaysApi = {
  list: (year?: number) => get<Holiday[]>("/api/holidays", year ? { year } : undefined),
  create: (body: unknown) => post<Holiday>("/api/holidays", body),
  remove: (id: number) => del(`/api/holidays/${id}`),
};

export const availabilityApi = {
  list: (employeeId?: number) =>
    get<Availability[]>("/api/availability", employeeId ? { employee_id: employeeId } : undefined),
  create: (body: unknown) => post<Availability>("/api/availability", body),
  remove: (id: number) => del(`/api/availability/${id}`),
};

export const preferencesApi = {
  list: (employeeId?: number) =>
    get<Preference[]>("/api/preferences", employeeId ? { employee_id: employeeId } : undefined),
  upsert: (body: unknown) => post<Preference>("/api/preferences", body),
};

export const leaveApi = {
  list: (params?: Record<string, unknown>) => get<Leave[]>("/api/leave", params),
  create: (body: unknown) => post<Leave>("/api/leave", body),
  review: (id: number, decision: string, comment?: string) =>
    patch(`/api/leave/${id}`, { decision, comment }),
  cancel: (id: number) => del(`/api/leave/${id}`),
};

export const compoffApi = {
  list: (employeeId?: number) =>
    get<CompOff[]>("/api/compoff", employeeId ? { employee_id: employeeId } : undefined),
  create: (body: unknown) => post<CompOff>("/api/compoff", body),
  update: (id: number, body: unknown) => patch<CompOff>(`/api/compoff/${id}`, body),
};

export const rostersApi = {
  generate: (body: unknown) => post<Roster>("/api/rosters/generate", body),
  list: (params?: Record<string, unknown>) => get<Roster[]>("/api/rosters", params),
  get: (id: number) => get<Roster>(`/api/rosters/${id}`),
  validate: (id: number) => post(`/api/rosters/${id}/validate`),
  patchEntry: (rosterId: number, entryId: number, body: unknown) =>
    patch(`/api/rosters/${rosterId}/entries/${entryId}`, body),
  review: (id: number, decision: string, comment?: string) =>
    post<Roster>(`/api/rosters/${id}/review`, { decision, comment }),
  publish: (id: number, justification?: string) =>
    post<Roster>(`/api/rosters/${id}/publish`, {
      exception_justification: justification || null,
    }),
  newVersion: (id: number) => post<Roster>(`/api/rosters/${id}/new-version`),
  changes: (id: number) => get<Record<string, unknown>[]>(`/api/rosters/${id}/changes`),
  approvals: (id: number) =>
    get<Record<string, unknown>[]>(`/api/rosters/${id}/approvals`),
};

export const plansApi = {
  list: (params?: Record<string, unknown>) => get<Plan[]>("/api/plans", params),
  get: (id: number) => get<Plan>(`/api/plans/${id}`),
  apply: (id: number) => post<Roster>(`/api/plans/${id}/apply`),
};

export const conflictsApi = {
  list: (params?: Record<string, unknown>) => get<Conflict[]>("/api/conflicts", params),
  resolve: (id: number) => post(`/api/conflicts/${id}/resolve`),
};

export const backupsApi = {
  list: (rosterId?: number) =>
    get<Backup[]>("/api/backups", rosterId ? { roster_id: rosterId } : undefined),
  apply: (id: number) => post(`/api/backups/${id}/apply`),
};

export const notificationsApi = {
  list: (unreadOnly?: boolean) =>
    get<{ items: NotificationItem[]; unread_count: number }>("/api/notifications", {
      unread_only: unreadOnly || false,
    }),
  markRead: (id: number) => patch(`/api/notifications/${id}`, { is_read: true }),
  readAll: () => post("/api/notifications/read-all"),
};

export const auditApi = {
  list: (params?: Record<string, unknown>) => get<AuditEntry[]>("/api/audit", params),
};

export const reportsApi = {
  coverage: (rosterId?: number) =>
    get("/api/reports/coverage", rosterId ? { roster_id: rosterId } : undefined),
  workload: (rosterId?: number) =>
    get<Record<string, unknown>[]>("/api/reports/workload", rosterId ? { roster_id: rosterId } : undefined),
};

export const dashboardApi = {
  get: () => get<DashboardData>("/api/dashboard"),
};

export const qualificationsApi = {
  list: () => get<{ id: number; code: string; name: string }[]>("/api/qualifications"),
  create: (body: unknown) => post("/api/qualifications", body),
  addToEmployee: (employeeId: number, qualificationId: number) =>
    post(`/api/employees/${employeeId}/qualifications`, {
      qualification_id: qualificationId,
    }),
};

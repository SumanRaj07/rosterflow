# RosterFlow — Smart Roster Management System

A complete, working full-stack roster management system built for the
DataStraw Technologies internship assessment. It covers the whole roster
lifecycle: master data (employees, brands, processes, pods, assignments),
working rules, holidays, leave and availability, a deterministic monthly
roster engine, conflict detection with template-based explanations, backup
recommendations, up to three alternative plans, an approval workflow, audit
history, CSV/Excel exports, and role-based access enforced on the backend.

## Live demo

**https://rosterflow-five.vercel.app** — frontend and backend on one Vercel
domain (see "Deploy on Vercel" below), backed by a free Supabase Postgres
database. Log in with any demo account below (e.g.
`admin@rosterflow.local` / `Admin@123`) and generate November 2026 to see
the full demo. API docs: https://rosterflow-five.vercel.app/docs

## Quick start

### Backend (FastAPI + SQLAlchemy, SQLite by default)

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m app.seed      # creates rosterflow.db with demo data
.venv/bin/uvicorn app.main:app --port 8000

Note: on first startup with an empty database, the backend seeds the demo data
automatically (and loads a `backend/.env` file if present), so the seed step is
optional on fresh deployments.
```

## Deploy on Vercel (frontend + backend, one domain)

`vercel.json` declares two services: `frontend` (Vite, served on `/`) and
`backend` (FastAPI, served on `/api`). The backend accepts requests with or
without the `/api` prefix, so the same code also works on Render/Railway/
PythonAnywhere. Vercel functions are stateless, so the backend needs a real
Postgres database — SQLite will not persist. Steps:

1. Create a free project on Supabase (no card) and copy its **Session pooler**
   connection string.
2. Import this repo on Vercel and choose **Import multi-service project**.
3. Set environment variables: `DATABASE_URL` = the Supabase pooler URL,
   `VITE_API_URL` = `/` (same-origin API calls, so no CORS setup is needed).
4. Deploy. The first API request creates the tables and seeds the demo data
   automatically — log in with `admin@rosterflow.local` / `Admin@123`.

Notes: Supabase free projects pause after 7 days of inactivity (resume them
from the Supabase dashboard); Vercel functions cold-start, so the first
request after idle takes a few seconds.

API docs: http://127.0.0.1:8000/docs

### Frontend (React + TypeScript + Vite + Tailwind)

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (API at http://127.0.0.1:8000)
```

### Docker (PostgreSQL + backend + frontend)

```bash
docker compose up --build
# backend: http://localhost:8000, frontend: http://localhost:5173
# seed inside the backend container: docker compose exec backend python -m app.seed
```

## Demo accounts (seeded)

| Role | Email | Password |
| --- | --- | --- |
| Operations Administrator | admin@rosterflow.local | Admin@123 |
| Operations Manager | manager@rosterflow.local | Manager@123 |
| Pod Lead | lead.a@rosterflow.local (also b/c/d) | Lead@123 |
| Employee | aarav.sharma@example.com | Emp@123 |

Demo month: **November 2026** — generate it from Roster Generator (or it is
already present if the seed ran). It demonstrates every feature below.

## What the demo data shows

- **36 employees, 10 brands, 7 processes, 4 pods.** 8 brands run on
  single-resource weekday processes (one primary assignee each); Jade Fashion
  rotates 3 primaries for a 2-person daily requirement; Ion Energy is
  deliberately tight (3 staff for a 3-person daily requirement).
- **Ion Energy Saturday gaps:** with exactly 3 staff and the
  6-consecutive-day rule, the whole team is forced off on Saturdays
  (Nov 7, 14, 21, 28). These appear as critical `understaffed` conflicts
  with template-based explanations and ranked backup recommendations —
  including certification-based backups (TS-certified staff from other
  brands who are free on Saturdays).
- **Approved leave:** EMP001 on leave Nov 10–12 is covered by a backup
  assignee; EMP030 is on leave the whole month (0 workdays, legitimately).
- **Recurring unavailability:** EMP005 is unavailable every Monday; the
  engine never schedules him on Mondays and a backup covers.
- **Preferences:** preferred weekly-off weekdays are honoured where possible;
  remaining conflicts are counted in the preference-satisfaction metric.
- **Holiday:** Diwali, Nov 8, 2026 (a Sunday) is a mandatory holiday.

## Scheduling engine (`backend/app/engine.py`)

Pure functions over plain data — no database access — so the rules are
unit-tested directly (see `backend/tests/test_engine.py`).

**Hard constraints (never violated by generation):** approved leave,
mandatory unavailability, assignment-based qualification, inactive
employees, one work assignment per employee per day, max consecutive working
days (default 6), max monthly workdays (default 26, per-employee override).

**Scheduling order:** for each day, each applicable requirement is staffed
from the eligible pool sorted by: primary assignees first, then (strategy)
— *Balanced* sorts by workdays, weekend days, preference penalty, id;
*Preference-first* sorts by preference penalty first; *Weekend-fair* sorts by
weekend days first. Deterministic: identical inputs always produce identical
rosters (tested).

**Fairness pass:** after staffing, employees below the minimum weekly offs
(default 4) get workdays swapped to other eligible employees who are off that
day and hold surplus offs. Coverage is preserved — the slot stays filled,
only the worker changes. A swap never takes an off away from someone already
at or below the minimum (no ping-pong).

**Metrics per roster:** coverage rate (filled ÷ required slots), gap count,
fairness score, preference-satisfaction rate, per-employee workdays/offs/
weekend days. Fairness is measured across *scheduled* staff (workdays > 0):
backup-pool employees who were not needed work 0 days by design, and
including them would punish the score for the pool existing at all; the
all-employee figure is also stored as `fairness_score_all_employees`.

**Validation** (`validate_entries`) re-checks any roster — including manual
edits — against the same hard constraints plus minimum-staffing coverage,
and reports weekly-off shortfalls as warnings.

**Backups:** for each understaffed gap, candidates are ranked by a score
(100 − 2×workdays − 5×weekend days − 15×preferred-off clash). Candidates may
qualify by assignment *or* by process certification. Applying a backup on a
draft creates the missing assignment first, so revalidation stays clean.

## Approval workflow

`Draft → (submit) → Pod Lead Review → (approve) → Manager Approval →
(publish) → Published`. Publishing is blocked while critical conflicts are
open unless an exception justification is recorded. Published rosters are
immutable: edits require a new version (`POST /rosters/{id}/new-version`),
and publishing the new version marks the old one `superseded`. Every manual
edit is recorded in `roster_changes`; every approval decision in
`roster_approvals`; every significant action in `audit_logs`.

Leave approval triggers revalidation: rosters overlapping the leave get
`leave_violation` conflicts and manager notifications, but published
rosters are never silently changed.

## Design decisions

Short answers to the assessment's design questions, grounded in the code
(`backend/app/models.py`, `backend/app/engine.py`, `backend/app/services.py`).

**1. How did you model employees, brands, processes, pods, and their
relationships?** Employees are people (unique code and email, role title,
active flag, optional monthly-workday override). Brands are clients;
processes are the work types inside a brand. Pods are teams: a lead user
plus `PodMembership` rows joining employees to pods. The many-to-many glue
is `Assignment`: one row links an employee to a brand and optionally a
process (a NULL process means every process of that brand), with an
`is_primary` flag, an active flag, and a date range. Around that sit
`StaffingRequirement` (brand + process + minimum staff + day pattern:
all/weekday/weekend/sunday/holiday), `WorkingRule` (max consecutive days,
max monthly workdays, minimum weekly offs), `Holiday`, `Availability`
(recurring weekday blocks), `EmployeePreference` (preferred off weekday),
and `LeaveRequest`. A `Roster` owns `RosterEntry` rows — exactly one per
employee per day (unique constraint), marked work/off/leave/holiday — plus
alternative `RosterPlan`s, `Conflict`s, `BackupRecommendation`s, approvals,
changes, and an audit log.

**2. How does your system generate a roster and determine whether it
satisfies the required constraints?** The engine (`engine.py`) is pure
functions over plain data — no database access — so it is unit-testable and
deterministic: identical inputs always produce identical rosters. For each
day it staffs each applicable requirement from the eligible pool, sorted
primary-first, then by strategy (Balanced: workdays, weekend days,
preference penalty; Preference-first and Weekend-fair reorder those keys).
Hard constraints are never violated by generation: approved leave,
unavailability, assignment qualification, inactive employees, one assignment
per employee per day, max consecutive days (default 6), max monthly workdays
(default 26). A fairness pass then swaps workdays to employees short of
minimum weekly offs without ever breaking coverage. Afterwards,
`validate_entries` re-checks the whole roster against the same constraints
plus minimum-staffing coverage, and reports coverage rate, gap count, a
fairness score, and preference satisfaction — November 2026 scores 0.9753
coverage (474/486 slots).

**3. How did you handle the difference between single-resource brands and
brands with multiple employees?** Both are expressed the same way: a
`StaffingRequirement` with `min_staff`. Single-resource brands
(`min_staff = 1`) are filled by their primary assignee — 8 demo brands run
this way on weekdays. Multi-resource brands just need more seats per day:
Jade Fashion rotates 3 primaries for a 2-person daily requirement, and Ion
Energy needs 3 people daily. The engine fills seats in the same primary-first
order until `min_staff` is reached, then stops — so the only difference is
the seat count, not the logic. The one-entry-per-employee-per-day rule
guarantees nobody is double-booked across brands.

**4. What happens when an employee manages all processes for a brand but is
unavailable on a required working day?** There is deliberately no single
point of failure: coverage falls first to secondary assignees for that
brand/process, then to process-certified backups (staff certified for the
process, even from another brand). The demo shows this: EMP001's Nov 10–12
leave is covered by a backup assignee, and EMP005's Monday unavailability
is covered the same way. If nobody is available, the engine does not invent
coverage — it leaves a gap, records a critical `understaffed` conflict with
a template explanation, and ranks backup candidates. A manager then resolves
it by applying a backup (which creates the missing assignment first, so
revalidation stays clean), editing the draft, or recording an exception.

**5. How does your system handle conflicting requirements or insufficient
staffing?** It never silently produces an invalid roster. Validation reports
every violation as a conflict with a severity (critical vs warning), the
rule it breaks, a plain-language explanation, and a recommendation.
Insufficient staffing shows up as `understaffed` gaps with ranked backup
recommendations. Publishing is blocked while any critical conflict is open,
unless a manager records an exception justification (stored on the roster
and audited). Published rosters are immutable — fixes go through a new
version, and publishing it supersedes the old one. Leave approved after
publishing never rewrites history: it adds `leave_violation` conflicts and
manager notifications to the affected rosters instead.

**6. Which parts of the process did you automate, and which did you leave
under human control? Why?** Automated: roster generation, constraint
validation, conflict detection and explanations, backup ranking, three
alternative plans, coverage/fairness/preference metrics, CSV/Excel exports,
audit logging, and notifications. Human: submitting, approving, and
publishing rosters; exception justifications; manual draft edits; leave
approvals; and working-rule changes. Reason: generation is combinatorial
and error-prone, so it belongs to the machine — but a roster decides
people's working days and client commitments, so the final commitment, and
every exception to the rules, must be owned and auditable by a named human.
Published immutability exists for the same reason: nobody's schedule changes
without a visible decision.

**7. If the company doubled its team and brand count, what would you change
about your solution?** The architecture already survives this in one
respect: the API is stateless and the database is Postgres, so capacity
scales horizontally. What I would change is the generation path: today it
runs synchronously inside the request, which is fine for 36 employees but
risks function timeouts at 72+ employees and 20 brands. I would move
generation to a background job with progress tracking, precompute per-day
eligibility maps instead of scanning pools repeatedly, and add indexes on
the hot queries (entries by roster/day, conflicts by roster/status). The
engine itself stays pure and deterministic, so it can also be sharded by pod
and run in parallel. Nothing about the data model needs to change.

**8. If you had one additional week to work on this, what would you improve
first?** Background generation with progress tracking, for the reason
above: it is the single change that removes the serverless timeout risk,
unblocks larger teams, and replaces a blocking wait with live progress in
the UI. After that, in order: email notifications (today notifications are
in-app only) and a manager dashboard for exception trends.

## Roles (enforced in the backend, not just the UI)

| Capability | Admin | Manager | Pod Lead | Employee |
| --- | --- | --- | --- | --- |
| Master data (brands, processes, pods, assignments, rules, holidays) | ✓ | — | — | — |
| Generate / validate / edit drafts / submit | ✓ | ✓ | own pods only | — |
| Approve / reject / publish | ✓ | ✓ | — | — |
| Leave approval | ✓ | ✓ | — | — |
| Own leave / availability / preferences | ✓ | ✓ | ✓ | own only |
| View rosters / conflicts / reports | ✓ | ✓ | own pods | own entries |

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./rosterflow.db` | SQLAlchemy URL; set to a PostgreSQL URL for deployment |
| Frontend API base | `http://127.0.0.1:8000` | `frontend/src/api.ts` |

Working rules are editable at runtime (Settings page / `PUT /api/rules`):
`max_consecutive_days`, `max_monthly_workdays`, `min_weekly_offs`,
`sunday_off`, `holiday_off`.

## Project structure

```
rosterflow/
  backend/
    app/
      main.py       # FastAPI app, all routes, RBAC
      models.py     # SQLAlchemy models (26 tables)
      engine.py     # deterministic scheduling engine (pure functions)
      services.py   # generation orchestration, workflow, notifications, audit
      seed.py       # deterministic demo data (36 employees, 10 brands, 4 pods)
      auth.py       # PBKDF2 password hashing, bearer tokens, role checks
      schemas.py    # Pydantic request/response models
    tests/          # pytest: engine rules + API workflow
    requirements.txt
  frontend/         # React + TS + Vite + Tailwind (see frontend/README if present)
  docker-compose.yml
  docs/REPORT.md    # implementation + verification report (spec section 36)
```

## Tests

```bash
cd backend
.venv/bin/python -m pytest tests/ -q
```

## Known limitations (honest list)

- **Auth is demo-grade:** PBKDF2-HMAC password hashing (stdlib) with opaque
  bearer tokens stored in the database. There is no SSO, no refresh-token
  rotation, and no rate limiting. Do not use as-is for production auth.
- **Live deployment:** https://rosterflow-five.vercel.app (Vercel services
  for frontend + backend, free Supabase Postgres). Docker files are also
  provided and the compose stack was verified locally.
- **Alembic:** the schema is created with SQLAlchemy `create_all` on startup
  plus a checked-in initial migration (see `backend/alembic/`); the migration
  path is verified on a fresh database, but `create_all` remains the default
  for local development.
- **Notifications are in-app only** (no email/SMS gateway wired).
- **Exports** are per-roster CSV/Excel; there is no scheduled report mailer.

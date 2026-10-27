"""RosterFlow API. All authorization is enforced here, in the backend."""
import csv
import io
from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from . import schemas as S
from . import services as svc
from .auth import (create_token, get_current_user, require_roles,
                   verify_password, visible_pod_ids)
from .db import get_db, init_db
from .models import (
    Assignment, Availability, Brand, CompOffRecord, Conflict, Employee,
    EmployeePreference, EmployeeQualification, Holiday, LeaveRequest,
    Notification, Pod, PodMembership, Process, Qualification, Roster,
    RosterApproval, RosterChange, RosterEntry, RosterPlan,
    StaffingRequirement, User, WorkingRule, AuditLog, BackupRecommendation,
)

app = FastAPI(title="RosterFlow API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

ADMIN = require_roles("admin")
MANAGER = require_roles("admin", "manager")
STAFF = require_roles("admin", "manager", "pod_lead")


def page_params(limit: int = Query(50, le=200), offset: int = Query(0, ge=0)):
    return limit, offset


def _paginate(query, limit, offset):
    total = query.count()
    return {"items": query.offset(offset).limit(limit).all(), "total": total}


def _emp_out(e: Employee):
    return S.EmployeeOut.model_validate(e)


@app.on_event("startup")
def _startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "RosterFlow"}


# ---------------- auth ----------------
@app.post("/api/auth/login")
def login(body: S.LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    tok = create_token(db, user)
    return {"token": tok.token, "user": S.UserOut.model_validate(user)}


@app.get("/api/auth/me")
def me(user: User = Depends(get_current_user)):
    return S.UserOut.model_validate(user)


# ---------------- employees ----------------
@app.get("/api/employees")
def list_employees(search: str = "", status: str = "", pod_id: int = 0,
                   sort: str = "full_name", pg: tuple = Depends(page_params),
                   db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    limit, offset = pg
    q = db.query(Employee)
    if user.role == "employee" and user.employee_id:
        q = q.filter(Employee.id == user.employee_id)
    if user.role == "pod_lead":
        pods = visible_pod_ids(user, db) or set()
        member_ids = {m.employee_id for m in db.query(PodMembership).filter(
            PodMembership.pod_id.in_(pods)).all()} if pods else set()
        q = q.filter(Employee.id.in_(member_ids))
    if search:
        q = q.filter(Employee.full_name.ilike(f"%{search}%") |
                     Employee.employee_code.ilike(f"%{search}%"))
    if status:
        q = q.filter(Employee.status == status)
    if pod_id:
        member_ids = {m.employee_id for m in db.query(PodMembership).filter(
            PodMembership.pod_id == pod_id).all()}
        q = q.filter(Employee.id.in_(member_ids))
    if sort == "employee_code":
        q = q.order_by(Employee.employee_code)
    else:
        q = q.order_by(Employee.full_name)
    res = _paginate(q, limit, offset)
    res["items"] = [S.EmployeeOut.model_validate(e) for e in res["items"]]
    return res


@app.post("/api/employees", status_code=201)
def create_employee(body: S.EmployeeIn, db: Session = Depends(get_db),
                    user: User = Depends(ADMIN)):
    if db.query(Employee).filter(Employee.employee_code == body.employee_code).first():
        raise HTTPException(400, "Employee code already exists")
    if db.query(Employee).filter(Employee.email == body.email).first():
        raise HTTPException(400, "Email already exists")
    e = Employee(**body.model_dump())
    db.add(e)
    svc.audit(db, user, "employee.create", "employee", None, {"code": e.employee_code})
    db.commit()
    db.refresh(e)
    return S.EmployeeOut.model_validate(e)


@app.get("/api/employees/{employee_id}")
def get_employee(employee_id: int, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    e = db.query(Employee).filter(Employee.id == employee_id).first()
    if not e:
        raise HTTPException(404, "Employee not found")
    if user.role == "employee" and user.employee_id != employee_id:
        raise HTTPException(403, "Cannot view other employees")
    assigns = db.query(Assignment).filter(Assignment.employee_id == employee_id).all()
    leaves = db.query(LeaveRequest).filter(LeaveRequest.employee_id == employee_id).all()
    avails = db.query(Availability).filter(Availability.employee_id == employee_id).all()
    entries = db.query(RosterEntry).filter(
        RosterEntry.employee_id == employee_id).order_by(
        RosterEntry.date.desc()).limit(60).all()
    out = S.EmployeeOut.model_validate(e).model_dump()
    out["assignments"] = [S.AssignmentOut.model_validate(a) for a in assigns]
    out["leaves"] = [S.LeaveOut.model_validate(x) for x in leaves]
    out["availabilities"] = [S.AvailabilityOut.model_validate(x) for x in avails]
    out["recent_entries"] = [{"roster_id": x.roster_id, "date": x.date.isoformat(),
                              "entry_type": x.entry_type, "brand_id": x.brand_id,
                              "process_id": x.process_id} for x in entries]
    return out


@app.patch("/api/employees/{employee_id}")
def patch_employee(employee_id: int, body: S.EmployeePatch,
                   db: Session = Depends(get_db), user: User = Depends(ADMIN)):
    e = db.query(Employee).filter(Employee.id == employee_id).first()
    if not e:
        raise HTTPException(404, "Employee not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(e, k, v)
    svc.audit(db, user, "employee.update", "employee", e.id, {})
    db.commit()
    return S.EmployeeOut.model_validate(e)


@app.delete("/api/employees/{employee_id}")
def deactivate_employee(employee_id: int, db: Session = Depends(get_db),
                        user: User = Depends(ADMIN)):
    """Deactivation, never hard deletion: history is preserved."""
    e = db.query(Employee).filter(Employee.id == employee_id).first()
    if not e:
        raise HTTPException(404, "Employee not found")
    e.status = "inactive"
    svc.audit(db, user, "employee.deactivate", "employee", e.id, {})
    db.commit()
    return {"status": "deactivated", "id": e.id}


# ---------------- brands / processes / pods ----------------
def _crud_list(model, out_schema, search_field="name"):
    def _list(search: str = "", pg: tuple = Depends(page_params),
              db: Session = Depends(get_db), user: User = Depends(get_current_user)):
        limit, offset = pg
        q = db.query(model)
        if search:
            q = q.filter(getattr(model, search_field).ilike(f"%{search}%"))
        res = _paginate(q, limit, offset)
        res["items"] = [out_schema.model_validate(x) for x in res["items"]]
        return res
    return _list


@app.get("/api/brands")
def list_brands(search: str = "", pg: tuple = Depends(page_params),
                db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    limit, offset = pg
    q = db.query(Brand)
    if search:
        q = q.filter(Brand.name.ilike(f"%{search}%"))
    res = _paginate(q, limit, offset)
    res["items"] = [S.BrandOut.model_validate(x) for x in res["items"]]
    return res


@app.post("/api/brands", status_code=201)
def create_brand(body: S.BrandIn, db: Session = Depends(get_db), user: User = Depends(ADMIN)):
    if db.query(Brand).filter(Brand.code == body.code).first():
        raise HTTPException(400, "Brand code already exists")
    b = Brand(**body.model_dump())
    db.add(b)
    svc.audit(db, user, "brand.create", "brand", None, {"code": b.code})
    db.commit()
    db.refresh(b)
    return S.BrandOut.model_validate(b)


@app.get("/api/brands/{brand_id}")
def get_brand(brand_id: int, db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    b = db.query(Brand).filter(Brand.id == brand_id).first()
    if not b:
        raise HTTPException(404, "Brand not found")
    reqs = db.query(StaffingRequirement).filter(
        StaffingRequirement.brand_id == brand_id).all()
    assigned = db.query(Assignment).filter(
        Assignment.brand_id == brand_id, Assignment.is_active == True).all()  # noqa
    out = S.BrandOut.model_validate(b).model_dump()
    out["staffing"] = [S.StaffingOut.model_validate(r) for r in reqs]
    out["assigned_employee_ids"] = sorted({a.employee_id for a in assigned})
    out["has_eligible_employees"] = len(out["assigned_employee_ids"]) > 0
    return out


@app.patch("/api/brands/{brand_id}")
def patch_brand(brand_id: int, body: S.BrandIn, db: Session = Depends(get_db),
                user: User = Depends(ADMIN)):
    b = db.query(Brand).filter(Brand.id == brand_id).first()
    if not b:
        raise HTTPException(404, "Brand not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(b, k, v)
    svc.audit(db, user, "brand.update", "brand", b.id, {})
    db.commit()
    return S.BrandOut.model_validate(b)


@app.get("/api/processes")
def list_processes(search: str = "", pg: tuple = Depends(page_params),
                   db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    limit, offset = pg
    q = db.query(Process)
    if search:
        q = q.filter(Process.name.ilike(f"%{search}%"))
    res = _paginate(q, limit, offset)
    res["items"] = [S.ProcessOut.model_validate(x) for x in res["items"]]
    return res


@app.post("/api/processes", status_code=201)
def create_process(body: S.ProcessIn, db: Session = Depends(get_db),
                   user: User = Depends(ADMIN)):
    if db.query(Process).filter(Process.code == body.code).first():
        raise HTTPException(400, "Process code already exists")
    p = Process(**body.model_dump())
    db.add(p)
    svc.audit(db, user, "process.create", "process", None, {"code": p.code})
    db.commit()
    db.refresh(p)
    return S.ProcessOut.model_validate(p)


@app.patch("/api/processes/{process_id}")
def patch_process(process_id: int, body: S.ProcessIn, db: Session = Depends(get_db),
                  user: User = Depends(ADMIN)):
    p = db.query(Process).filter(Process.id == process_id).first()
    if not p:
        raise HTTPException(404, "Process not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    return S.ProcessOut.model_validate(p)


@app.get("/api/pods")
def list_pods(pg: tuple = Depends(page_params), db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    limit, offset = pg
    q = db.query(Pod)
    if user.role == "pod_lead":
        pods = visible_pod_ids(user, db) or set()
        q = q.filter(Pod.id.in_(pods))
    res = _paginate(q, limit, offset)
    res["items"] = [S.PodOut.model_validate(x) for x in res["items"]]
    return res


@app.post("/api/pods", status_code=201)
def create_pod(body: S.PodIn, db: Session = Depends(get_db), user: User = Depends(ADMIN)):
    if db.query(Pod).filter(Pod.code == body.code).first():
        raise HTTPException(400, "Pod code already exists")
    p = Pod(**body.model_dump())
    db.add(p)
    svc.audit(db, user, "pod.create", "pod", None, {"code": p.code})
    db.commit()
    db.refresh(p)
    return S.PodOut.model_validate(p)


@app.get("/api/pods/{pod_id}")
def get_pod(pod_id: int, db: Session = Depends(get_db),
            user: User = Depends(get_current_user)):
    p = db.query(Pod).filter(Pod.id == pod_id).first()
    if not p:
        raise HTTPException(404, "Pod not found")
    if user.role == "pod_lead" and p.lead_id != user.id:
        raise HTTPException(403, "Not authorized for this pod")
    members = db.query(PodMembership).filter(PodMembership.pod_id == pod_id).all()
    out = S.PodOut.model_validate(p).model_dump()
    out["member_employee_ids"] = [m.employee_id for m in members]
    return out


@app.patch("/api/pods/{pod_id}")
def patch_pod(pod_id: int, body: S.PodIn, db: Session = Depends(get_db),
              user: User = Depends(ADMIN)):
    p = db.query(Pod).filter(Pod.id == pod_id).first()
    if not p:
        raise HTTPException(404, "Pod not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    return S.PodOut.model_validate(p)


@app.post("/api/pods/{pod_id}/members", status_code=201)
def add_pod_member(pod_id: int, body: S.PodMemberIn, db: Session = Depends(get_db),
                   user: User = Depends(ADMIN)):
    if not db.query(Pod).filter(Pod.id == pod_id).first():
        raise HTTPException(404, "Pod not found")
    if not db.query(Employee).filter(Employee.id == body.employee_id).first():
        raise HTTPException(404, "Employee not found")
    if db.query(PodMembership).filter(PodMembership.pod_id == pod_id,
                                      PodMembership.employee_id == body.employee_id).first():
        raise HTTPException(400, "Already a member")
    db.add(PodMembership(pod_id=pod_id, employee_id=body.employee_id))
    db.commit()
    return {"status": "added"}


@app.delete("/api/pods/{pod_id}/members/{employee_id}")
def remove_pod_member(pod_id: int, employee_id: int, db: Session = Depends(get_db),
                      user: User = Depends(ADMIN)):
    m = db.query(PodMembership).filter(PodMembership.pod_id == pod_id,
                                       PodMembership.employee_id == employee_id).first()
    if not m:
        raise HTTPException(404, "Membership not found")
    db.delete(m)
    db.commit()
    return {"status": "removed"}


# ---------------- qualifications ----------------
@app.get("/api/qualifications")
def list_quals(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [{"id": q.id, "code": q.code, "name": q.name}
            for q in db.query(Qualification).all()]


@app.post("/api/qualifications", status_code=201)
def create_qual(body: S.QualificationIn, db: Session = Depends(get_db),
                user: User = Depends(ADMIN)):
    q = Qualification(**body.model_dump())
    db.add(q)
    db.commit()
    db.refresh(q)
    return {"id": q.id, "code": q.code, "name": q.name}


@app.post("/api/employees/{employee_id}/qualifications", status_code=201)
def add_emp_qual(employee_id: int, body: dict, db: Session = Depends(get_db),
                 user: User = Depends(ADMIN)):
    if not db.query(Employee).filter(Employee.id == employee_id).first():
        raise HTTPException(404, "Employee not found")
    if db.query(EmployeeQualification).filter(
            EmployeeQualification.employee_id == employee_id,
            EmployeeQualification.qualification_id == body["qualification_id"]).first():
        raise HTTPException(400, "Already assigned")
    db.add(EmployeeQualification(employee_id=employee_id,
                                 qualification_id=body["qualification_id"]))
    db.commit()
    return {"status": "added"}


# ---------------- assignments / staffing ----------------
@app.get("/api/assignments")
def list_assignments(employee_id: int = 0, brand_id: int = 0, process_id: int = 0,
                     pg: tuple = Depends(page_params), db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    limit, offset = pg
    q = db.query(Assignment)
    if employee_id:
        q = q.filter(Assignment.employee_id == employee_id)
    if brand_id:
        q = q.filter(Assignment.brand_id == brand_id)
    if process_id:
        q = q.filter(Assignment.process_id == process_id)
    res = _paginate(q, limit, offset)
    res["items"] = [S.AssignmentOut.model_validate(x) for x in res["items"]]
    return res


@app.post("/api/assignments", status_code=201)
def create_assignment(body: S.AssignmentIn, db: Session = Depends(get_db),
                      user: User = Depends(ADMIN)):
    emp = db.query(Employee).filter(Employee.id == body.employee_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")
    if emp.status != "active":
        raise HTTPException(400, "Cannot assign an inactive employee")
    if not db.query(Brand).filter(Brand.id == body.brand_id).first():
        raise HTTPException(404, "Brand not found")
    if body.process_id and not db.query(Process).filter(
            Process.id == body.process_id).first():
        raise HTTPException(404, "Process not found")
    if db.query(Assignment).filter(
            Assignment.employee_id == body.employee_id,
            Assignment.brand_id == body.brand_id,
            Assignment.process_id == body.process_id).first():
        raise HTTPException(400, "Assignment already exists")
    a = Assignment(**body.model_dump())
    db.add(a)
    svc.audit(db, user, "assignment.create", "assignment", None,
              {"employee_id": a.employee_id, "brand_id": a.brand_id})
    db.commit()
    db.refresh(a)
    return S.AssignmentOut.model_validate(a)


@app.patch("/api/assignments/{assignment_id}")
def patch_assignment(assignment_id: int, body: dict, db: Session = Depends(get_db),
                     user: User = Depends(ADMIN)):
    a = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not a:
        raise HTTPException(404, "Assignment not found")
    for k in ("is_active", "end_date", "pod_id", "is_primary"):
        if k in body:
            setattr(a, k, body[k])
    db.commit()
    return S.AssignmentOut.model_validate(a)


@app.get("/api/staffing")
def list_staffing(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [S.StaffingOut.model_validate(r)
            for r in db.query(StaffingRequirement).all()]


@app.post("/api/staffing", status_code=201)
def create_staffing(body: S.StaffingIn, db: Session = Depends(get_db),
                    user: User = Depends(ADMIN)):
    if not db.query(Brand).filter(Brand.id == body.brand_id).first():
        raise HTTPException(404, "Brand not found")
    if not db.query(Process).filter(Process.id == body.process_id).first():
        raise HTTPException(404, "Process not found")
    r = StaffingRequirement(**body.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    return S.StaffingOut.model_validate(r)


@app.patch("/api/staffing/{staffing_id}")
def patch_staffing(staffing_id: int, body: dict, db: Session = Depends(get_db),
                   user: User = Depends(ADMIN)):
    r = db.query(StaffingRequirement).filter(StaffingRequirement.id == staffing_id).first()
    if not r:
        raise HTTPException(404, "Not found")
    for k in ("min_staff", "applies", "is_active"):
        if k in body:
            setattr(r, k, body[k])
    db.commit()
    return S.StaffingOut.model_validate(r)


# ---------------- rules / holidays ----------------
@app.get("/api/rules")
def list_rules(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    out = dict(svc.DEFAULT_RULES)
    for r in db.query(WorkingRule).all():
        out[r.key] = r.value
    return out


@app.put("/api/rules")
def put_rules(body: dict, db: Session = Depends(get_db), user: User = Depends(ADMIN)):
    for k, v in body.items():
        if k not in svc.DEFAULT_RULES:
            raise HTTPException(400, f"Unknown rule: {k}")
        row = db.query(WorkingRule).filter(WorkingRule.key == k).first()
        if row:
            row.value = v
        else:
            db.add(WorkingRule(key=k, value=v))
    svc.audit(db, user, "rules.update", "working_rule", None, body)
    db.commit()
    return {"status": "saved"}


@app.get("/api/holidays")
def list_holidays(year: int = 0, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    q = db.query(Holiday)
    if year:
        q = q.filter(Holiday.date >= date(year, 1, 1),
                     Holiday.date <= date(year, 12, 31))
    return [S.HolidayOut.model_validate(h) for h in q.order_by(Holiday.date).all()]


@app.post("/api/holidays", status_code=201)
def create_holiday(body: S.HolidayIn, db: Session = Depends(get_db),
                   user: User = Depends(ADMIN)):
    if db.query(Holiday).filter(Holiday.date == body.date).first():
        raise HTTPException(400, "Holiday already exists for this date")
    h = Holiday(**body.model_dump())
    db.add(h)
    db.commit()
    db.refresh(h)
    return S.HolidayOut.model_validate(h)


@app.delete("/api/holidays/{holiday_id}")
def delete_holiday(holiday_id: int, db: Session = Depends(get_db),
                   user: User = Depends(ADMIN)):
    h = db.query(Holiday).filter(Holiday.id == holiday_id).first()
    if not h:
        raise HTTPException(404, "Not found")
    db.delete(h)
    db.commit()
    return {"status": "deleted"}


# ---------------- availability / preferences ----------------
@app.get("/api/availability")
def list_availability(employee_id: int = 0, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    q = db.query(Availability)
    if employee_id:
        q = q.filter(Availability.employee_id == employee_id)
    if user.role == "employee" and user.employee_id:
        q = q.filter(Availability.employee_id == user.employee_id)
    return [S.AvailabilityOut.model_validate(a) for a in q.all()]


@app.post("/api/availability", status_code=201)
def create_availability(body: S.AvailabilityIn, db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    if user.role == "employee" and user.employee_id != body.employee_id:
        raise HTTPException(403, "Can only set your own availability")
    if not body.date and body.weekday is None:
        raise HTTPException(400, "Provide a date or a weekday")
    a = Availability(**body.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)
    return S.AvailabilityOut.model_validate(a)


@app.delete("/api/availability/{availability_id}")
def delete_availability(availability_id: int, db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    a = db.query(Availability).filter(Availability.id == availability_id).first()
    if not a:
        raise HTTPException(404, "Not found")
    if user.role == "employee" and user.employee_id != a.employee_id:
        raise HTTPException(403, "Cannot delete others' availability")
    db.delete(a)
    db.commit()
    return {"status": "deleted"}


@app.get("/api/preferences")
def list_preferences(employee_id: int = 0, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    q = db.query(EmployeePreference)
    if employee_id:
        q = q.filter(EmployeePreference.employee_id == employee_id)
    return [S.PreferenceOut.model_validate(p) for p in q.all()]


@app.post("/api/preferences", status_code=201)
def upsert_preference(body: S.PreferenceIn, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    if user.role == "employee" and user.employee_id != body.employee_id:
        raise HTTPException(403, "Can only set your own preferences")
    p = db.query(EmployeePreference).filter(
        EmployeePreference.employee_id == body.employee_id).first()
    if p:
        p.preferred_off_weekday = body.preferred_off_weekday
        p.shift_preference = body.shift_preference
        p.notes = body.notes
    else:
        p = EmployeePreference(**body.model_dump())
        db.add(p)
    db.commit()
    db.refresh(p)
    return S.PreferenceOut.model_validate(p)


# ---------------- leave / comp-off ----------------
@app.get("/api/leave")
def list_leave(employee_id: int = 0, status: str = "", db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    q = db.query(LeaveRequest)
    if employee_id:
        q = q.filter(LeaveRequest.employee_id == employee_id)
    if status:
        q = q.filter(LeaveRequest.status == status)
    if user.role == "employee" and user.employee_id:
        q = q.filter(LeaveRequest.employee_id == user.employee_id)
    return [S.LeaveOut.model_validate(x)
            for x in q.order_by(LeaveRequest.start_date.desc()).all()]


@app.post("/api/leave", status_code=201)
def create_leave(body: S.LeaveIn, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    if user.role == "employee" and user.employee_id != body.employee_id:
        raise HTTPException(403, "Can only request your own leave")
    if body.end_date < body.start_date:
        raise HTTPException(400, "End date must be on or after start date")
    if not db.query(Employee).filter(Employee.id == body.employee_id).first():
        raise HTTPException(404, "Employee not found")
    lv = LeaveRequest(**body.model_dump())
    db.add(lv)
    svc.audit(db, user, "leave.create", "leave", None,
              {"employee_id": lv.employee_id})
    db.commit()
    db.refresh(lv)
    return S.LeaveOut.model_validate(lv)


@app.patch("/api/leave/{leave_id}")
def review_leave(leave_id: int, body: S.LeaveReviewIn, db: Session = Depends(get_db),
                 user: User = Depends(MANAGER)):
    from datetime import datetime
    lv = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not lv:
        raise HTTPException(404, "Leave request not found")
    if lv.status != "pending":
        raise HTTPException(400, f"Leave is already {lv.status}")
    if body.decision not in ("approved", "rejected"):
        raise HTTPException(400, "Decision must be approved or rejected")
    lv.status = body.decision
    lv.reviewer_id = user.id
    lv.review_comment = body.comment
    lv.reviewed_at = datetime.utcnow()
    svc.audit(db, user, f"leave.{body.decision}", "leave", lv.id, {})
    db.commit()
    affected = []
    if body.decision == "approved":
        affected = svc.revalidate_after_leave(db, lv)
        notify = svc.notify
        notify(db, "leave_approved",
               f"Your leave {lv.start_date} to {lv.end_date} was approved.",
               employee_id=lv.employee_id, related_type="leave", related_id=lv.id)
        db.commit()
    return {"leave": S.LeaveOut.model_validate(lv), "affected_rosters": affected}


@app.delete("/api/leave/{leave_id}")
def cancel_leave(leave_id: int, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    lv = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not lv:
        raise HTTPException(404, "Not found")
    if user.role == "employee" and user.employee_id != lv.employee_id:
        raise HTTPException(403, "Cannot cancel others' leave")
    lv.status = "cancelled"
    db.commit()
    return {"status": "cancelled"}


@app.get("/api/compoff")
def list_compoff(employee_id: int = 0, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    q = db.query(CompOffRecord)
    if employee_id:
        q = q.filter(CompOffRecord.employee_id == employee_id)
    return [S.CompOffOut.model_validate(x) for x in q.all()]


@app.post("/api/compoff", status_code=201)
def create_compoff(body: S.CompOffIn, db: Session = Depends(get_db),
                   user: User = Depends(ADMIN)):
    r = CompOffRecord(**body.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    return S.CompOffOut.model_validate(r)


@app.patch("/api/compoff/{record_id}")
def use_compoff(record_id: int, body: dict, db: Session = Depends(get_db),
                user: User = Depends(MANAGER)):
    r = db.query(CompOffRecord).filter(CompOffRecord.id == record_id).first()
    if not r:
        raise HTTPException(404, "Not found")
    if body.get("status") == "used" and r.status != "available":
        raise HTTPException(400, "Comp-off is not available for use")
    if "status" in body:
        r.status = body["status"]
    if "used_date" in body:
        from datetime import date as _d
        r.used_date = _d.fromisoformat(body["used_date"]) if body["used_date"] else None
    db.commit()
    return S.CompOffOut.model_validate(r)


# ---------------- rosters ----------------
@app.post("/api/rosters/generate", status_code=201)
def generate(body: S.GenerateIn, db: Session = Depends(get_db),
             user: User = Depends(STAFF)):
    if user.role == "pod_lead" and body.pod_id:
        pods = visible_pod_ids(user, db) or set()
        if body.pod_id not in pods:
            raise HTTPException(403, "Not authorized for this pod")
    roster = svc.generate_roster(db, user, body)
    return S.RosterOut.model_validate(roster)


@app.get("/api/rosters")
def list_rosters(status: str = "", month: int = 0, year: int = 0,
                 db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(Roster)
    if status:
        q = q.filter(Roster.status == status)
    if month:
        q = q.filter(Roster.month == month)
    if year:
        q = q.filter(Roster.year == year)
    if user.role == "pod_lead":
        pods = visible_pod_ids(user, db) or set()
        q = q.filter(Roster.pod_id.in_(pods)) if pods else q.filter(False)
    if user.role == "employee" and user.employee_id:
        sub = db.query(RosterEntry.roster_id).filter(
            RosterEntry.employee_id == user.employee_id).subquery()
        q = q.filter(Roster.id.in_(sub))
    return [S.RosterOut.model_validate(r)
            for r in q.order_by(Roster.year.desc(), Roster.month.desc(),
                                Roster.id.desc()).all()]


def _roster_or_404(db, roster_id):
    r = db.query(Roster).filter(Roster.id == roster_id).first()
    if not r:
        raise HTTPException(404, "Roster not found")
    return r


@app.get("/api/rosters/{roster_id}")
def get_roster(roster_id: int, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    r = _roster_or_404(db, roster_id)
    entries = db.query(RosterEntry).filter(RosterEntry.roster_id == roster_id).all()
    conflicts = db.query(Conflict).filter(Conflict.roster_id == roster_id).all()
    out = S.RosterOut.model_validate(r).model_dump()
    out["entries"] = [{"id": e.id, "employee_id": e.employee_id,
                       "date": e.date.isoformat(), "entry_type": e.entry_type,
                       "brand_id": e.brand_id, "process_id": e.process_id,
                       "is_manual": e.is_manual, "note": e.note} for e in entries]
    out["conflicts"] = [{"id": c.id, "type": c.type, "severity": c.severity,
                         "date": c.date.isoformat() if c.date else None,
                         "brand_id": c.brand_id, "process_id": c.process_id,
                         "employee_id": c.employee_id, "rule": c.rule,
                         "explanation": c.explanation,
                         "recommendation": c.recommendation,
                         "status": c.status} for c in conflicts]
    return out


@app.post("/api/rosters/{roster_id}/validate")
def validate(roster_id: int, db: Session = Depends(get_db),
             user: User = Depends(STAFF)):
    r = _roster_or_404(db, roster_id)
    conflicts = svc.validate_roster(db, r)
    return {"conflicts": len(conflicts),
            "critical": sum(1 for c in conflicts if c.severity == "critical"),
            "status": r.status}


@app.patch("/api/rosters/{roster_id}/entries/{entry_id}")
def patch_entry(roster_id: int, entry_id: int, body: S.EntryPatch,
                db: Session = Depends(get_db), user: User = Depends(STAFF)):
    r = _roster_or_404(db, roster_id)
    e = db.query(RosterEntry).filter(RosterEntry.id == entry_id,
                                     RosterEntry.roster_id == roster_id).first()
    if not e:
        raise HTTPException(404, "Entry not found")
    try:
        conflicts = svc.apply_entry_patch(db, user, r, e, body)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"conflicts": len(conflicts),
            "critical": sum(1 for c in conflicts if c.severity == "critical"),
            "status": r.status}


@app.post("/api/rosters/{roster_id}/review")
def review_roster(roster_id: int, body: S.ApprovalIn, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    r = _roster_or_404(db, roster_id)
    db.add(RosterApproval(roster_id=roster_id, reviewer_id=user.id,
                          decision=body.decision, comment=body.comment))
    if body.decision == "submitted":
        if r.status not in ("draft", "validated"):
            raise HTTPException(400, f"Cannot submit from {r.status}")
        r.status = "pending_review"
    elif body.decision == "approved":
        if user.role not in ("admin", "manager"):
            raise HTTPException(403, "Only managers can approve")
        if r.status != "pending_review":
            raise HTTPException(400, f"Cannot approve from {r.status}")
        r.status = "approved"
    elif body.decision == "rejected":
        if user.role not in ("admin", "manager"):
            raise HTTPException(403, "Only managers can reject")
        r.status = "draft"
    elif body.decision == "changes_requested":
        r.status = "draft"
    else:
        raise HTTPException(400, "Unknown decision")
    svc.audit(db, user, f"roster.{body.decision}", "roster", r.id, {})
    if body.decision == "approved":
        for admin in db.query(User).filter(User.role.in_(["admin", "manager"])).all():
            svc.notify(db, "roster_approved", f"Roster {r.month}/{r.year} was approved.",
                       user_id=admin.id, related_type="roster", related_id=r.id)
    db.commit()
    return S.RosterOut.model_validate(r)


@app.post("/api/rosters/{roster_id}/publish")
def publish(roster_id: int, body: S.PublishIn, db: Session = Depends(get_db),
            user: User = Depends(MANAGER)):
    r = _roster_or_404(db, roster_id)
    if r.status != "approved":
        raise HTTPException(400, f"Only approved rosters can be published (now {r.status})")
    try:
        svc.publish_roster(db, user, r, body.exception_justification)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return S.RosterOut.model_validate(r)


@app.post("/api/rosters/{roster_id}/new-version", status_code=201)
def new_version(roster_id: int, db: Session = Depends(get_db),
                user: User = Depends(STAFF)):
    old = _roster_or_404(db, roster_id)
    if old.status != "published":
        raise HTTPException(400, "Only published rosters get a new version")
    new = Roster(month=old.month, year=old.year, status="draft",
                 brand_id=old.brand_id, pod_id=old.pod_id,
                 process_id=old.process_id, version=old.version + 1,
                 parent_id=old.id, preferences_applied=old.preferences_applied,
                 strategy=old.strategy, created_by=user.id)
    db.add(new)
    db.flush()
    for e in db.query(RosterEntry).filter(RosterEntry.roster_id == old.id).all():
        db.add(RosterEntry(roster_id=new.id, employee_id=e.employee_id, date=e.date,
                           entry_type=e.entry_type, brand_id=e.brand_id,
                           process_id=e.process_id, pod_id=e.pod_id,
                           is_manual=e.is_manual, note=e.note))
    svc.audit(db, user, "roster.new_version", "roster", new.id,
              {"parent_id": old.id})
    db.commit()
    db.refresh(new)
    return S.RosterOut.model_validate(new)


@app.get("/api/rosters/{roster_id}/changes")
def roster_changes(roster_id: int, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    _roster_or_404(db, roster_id)
    out = []
    for c in db.query(RosterChange).filter(
            RosterChange.roster_id == roster_id).order_by(
            RosterChange.created_at.desc()).all():
        out.append({"id": c.id, "employee_id": c.employee_id,
                    "date": c.date.isoformat(), "field": c.field,
                    "old_value": c.old_value, "new_value": c.new_value,
                    "reason": c.reason, "changed_by": c.changed_by,
                    "created_at": c.created_at.isoformat() if c.created_at else None})
    return out


@app.get("/api/rosters/{roster_id}/approvals")
def roster_approvals(roster_id: int, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    _roster_or_404(db, roster_id)
    return [{"id": a.id, "reviewer_id": a.reviewer_id, "decision": a.decision,
             "comment": a.comment,
             "created_at": a.created_at.isoformat() if a.created_at else None}
            for a in db.query(RosterApproval).filter(
                RosterApproval.roster_id == roster_id).order_by(
                RosterApproval.created_at.desc()).all()]


# ---------------- plans ----------------
@app.get("/api/plans")
def list_plans(month: int = 0, year: int = 0, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    q = db.query(RosterPlan)
    if month:
        q = q.filter(RosterPlan.month == month)
    if year:
        q = q.filter(RosterPlan.year == year)
    return [{"id": p.id, "month": p.month, "year": p.year, "name": p.name,
             "strategy": p.strategy, "metrics": p.metrics,
             "is_selected": p.is_selected}
            for p in q.order_by(RosterPlan.id.desc()).all()]


@app.get("/api/plans/{plan_id}")
def get_plan(plan_id: int, db: Session = Depends(get_db),
             user: User = Depends(get_current_user)):
    p = db.query(RosterPlan).filter(RosterPlan.id == plan_id).first()
    if not p:
        raise HTTPException(404, "Plan not found")
    return {"id": p.id, "month": p.month, "year": p.year, "name": p.name,
            "strategy": p.strategy, "metrics": p.metrics, "entries": p.entries,
            "is_selected": p.is_selected}


@app.post("/api/plans/{plan_id}/apply", status_code=201)
def apply_plan(plan_id: int, db: Session = Depends(get_db),
               user: User = Depends(STAFF)):
    p = db.query(RosterPlan).filter(RosterPlan.id == plan_id).first()
    if not p:
        raise HTTPException(404, "Plan not found")
    roster = Roster(month=p.month, year=p.year, status="draft",
                    strategy=p.strategy, created_by=user.id)
    db.add(roster)
    db.flush()
    for e in (p.entries or []):
        db.add(RosterEntry(roster_id=roster.id, employee_id=e["employee_id"],
                           date=date.fromisoformat(e["date"]),
                           entry_type=e["entry_type"], brand_id=e["brand_id"],
                           process_id=e["process_id"]))
    roster.metrics = p.metrics
    p.is_selected = True
    svc.audit(db, user, "plan.apply", "roster", roster.id, {"plan_id": p.id})
    db.commit()
    db.refresh(roster)
    return S.RosterOut.model_validate(roster)


# ---------------- conflicts / backups ----------------
@app.get("/api/conflicts")
def list_conflicts(status: str = "", severity: str = "", roster_id: int = 0,
                   db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(Conflict)
    if status:
        q = q.filter(Conflict.status == status)
    if severity:
        q = q.filter(Conflict.severity == severity)
    if roster_id:
        q = q.filter(Conflict.roster_id == roster_id)
    return [{"id": c.id, "roster_id": c.roster_id, "month": c.month, "year": c.year,
             "type": c.type, "severity": c.severity,
             "date": c.date.isoformat() if c.date else None,
             "brand_id": c.brand_id, "process_id": c.process_id,
             "employee_id": c.employee_id, "rule": c.rule,
             "explanation": c.explanation, "recommendation": c.recommendation,
             "status": c.status}
            for c in q.order_by(Conflict.created_at.desc()).limit(200).all()]


@app.post("/api/conflicts/{conflict_id}/resolve")
def resolve_conflict(conflict_id: int, db: Session = Depends(get_db),
                     user: User = Depends(STAFF)):
    c = db.query(Conflict).filter(Conflict.id == conflict_id).first()
    if not c:
        raise HTTPException(404, "Conflict not found")
    c.status = "resolved"
    svc.audit(db, user, "conflict.resolve", "conflict", c.id, {})
    db.commit()
    return {"status": "resolved"}


@app.get("/api/backups")
def list_backups(roster_id: int = 0, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    q = db.query(BackupRecommendation)
    if roster_id:
        q = q.filter(BackupRecommendation.roster_id == roster_id)
    return [{"id": b.id, "conflict_id": b.conflict_id, "roster_id": b.roster_id,
             "date": b.date.isoformat(), "brand_id": b.brand_id,
             "process_id": b.process_id, "employee_id": b.employee_id,
             "score": b.score, "reason": b.reason, "status": b.status}
            for b in q.order_by(BackupRecommendation.score.desc()).limit(200).all()]


@app.post("/api/backups/{backup_id}/apply")
def apply_backup(backup_id: int, db: Session = Depends(get_db),
                 user: User = Depends(MANAGER)):
    b = db.query(BackupRecommendation).filter(BackupRecommendation.id == backup_id).first()
    if not b:
        raise HTTPException(404, "Recommendation not found")
    if b.status != "pending":
        raise HTTPException(400, f"Recommendation already {b.status}")
    roster = db.query(Roster).filter(Roster.id == b.roster_id).first()
    if not roster:
        raise HTTPException(404, "Roster not found")
    if roster.status in ("published", "superseded"):
        raise HTTPException(400, "Create a new version of a published roster first")
    # Certification-only backups need a real assignment to pass revalidation.
    if not db.query(Assignment).filter(
            Assignment.employee_id == b.employee_id,
            Assignment.brand_id == b.brand_id,
            Assignment.process_id == b.process_id).first():
        db.add(Assignment(employee_id=b.employee_id, brand_id=b.brand_id,
                          process_id=b.process_id, is_primary=False))
    entry = db.query(RosterEntry).filter(
        RosterEntry.roster_id == roster.id, RosterEntry.date == b.date,
        RosterEntry.employee_id == b.employee_id).first()
    if not entry:
        db.add(RosterEntry(roster_id=roster.id, employee_id=b.employee_id,
                           date=b.date, entry_type="work", brand_id=b.brand_id,
                           process_id=b.process_id, is_manual=True,
                           note="Applied from backup recommendation"))
    else:
        entry.entry_type = "work"
        entry.brand_id = b.brand_id
        entry.process_id = b.process_id
        entry.is_manual = True
    b.status = "accepted"
    svc.audit(db, user, "backup.apply", "backup_recommendation", b.id, {})
    db.commit()
    svc.validate_roster(db, roster)
    return {"status": "applied"}


# ---------------- notifications / audit ----------------
@app.get("/api/notifications")
def list_notifications(unread_only: bool = False, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    q = db.query(Notification)
    if user.role == "employee":
        q = q.filter((Notification.user_id == user.id) |
                     (Notification.employee_id == user.employee_id))
    elif user.role == "pod_lead":
        q = q.filter(Notification.user_id == user.id)
    if unread_only:
        q = q.filter(Notification.is_read == False)  # noqa
    items = q.order_by(Notification.created_at.desc()).limit(100).all()
    unread = db.query(Notification).filter(Notification.is_read == False).count()  # noqa
    return {"items": [{"id": n.id, "type": n.type, "message": n.message,
                       "related_type": n.related_type, "related_id": n.related_id,
                       "is_read": n.is_read,
                       "created_at": n.created_at.isoformat() if n.created_at else None}
                      for n in items],
            "unread_count": unread}


@app.patch("/api/notifications/{notification_id}")
def read_notification(notification_id: int, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    n = db.query(Notification).filter(Notification.id == notification_id).first()
    if not n:
        raise HTTPException(404, "Not found")
    n.is_read = True
    db.commit()
    return {"status": "read"}


@app.post("/api/notifications/read-all")
def read_all(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.query(Notification).filter(Notification.is_read == False).update(  # noqa
        {"is_read": True})
    db.commit()
    return {"status": "all read"}


@app.get("/api/audit")
def list_audit(action: str = "", entity_type: str = "", db: Session = Depends(get_db),
               user: User = Depends(MANAGER)):
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action.ilike(f"%{action}%"))
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    return [{"id": a.id, "user_id": a.user_id, "action": a.action,
             "entity_type": a.entity_type, "entity_id": a.entity_id,
             "details": a.details,
             "created_at": a.created_at.isoformat() if a.created_at else None}
            for a in q.order_by(AuditLog.created_at.desc()).limit(200).all()]


# ---------------- reports / exports / dashboard ----------------
def _roster_rows(roster_id):
    from .db import SessionLocal
    db = SessionLocal()
    try:
        entries = db.query(RosterEntry).filter(
            RosterEntry.roster_id == roster_id).all()
        emps = {e.id: e for e in db.query(Employee).all()}
        brands = {b.id: b.name for b in db.query(Brand).all()}
        procs = {p.id: p.name for p in db.query(Process).all()}
        rows = []
        for e in sorted(entries, key=lambda x: (x.date, x.employee_id)):
            emp = emps.get(e.employee_id)
            rows.append({"date": e.date.isoformat(),
                         "employee_code": emp.employee_code if emp else "",
                         "employee_name": emp.full_name if emp else "",
                         "entry_type": e.entry_type,
                         "brand": brands.get(e.brand_id, ""),
                         "process": procs.get(e.process_id, ""),
                         "is_manual": e.is_manual})
        return rows
    finally:
        db.close()


@app.get("/api/reports/coverage")
def report_coverage(roster_id: int = 0, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    if roster_id:
        r = _roster_or_404(db, roster_id)
        return {"roster_id": roster_id, "metrics": r.metrics}
    rosters = db.query(Roster).all()
    return [{"roster_id": r.id, "month": r.month, "year": r.year,
             "status": r.status, "metrics": r.metrics} for r in rosters]


@app.get("/api/reports/workload")
def report_workload(roster_id: int = 0, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    q = db.query(RosterEntry)
    if roster_id:
        q = q.filter(RosterEntry.roster_id == roster_id)
    from collections import Counter
    work = Counter()
    offs = Counter()
    for e in q.all():
        if e.entry_type == "work":
            work[e.employee_id] += 1
        elif e.entry_type == "off":
            offs[e.employee_id] += 1
    emps = {e.id: e for e in db.query(Employee).all()}
    return [{"employee_id": eid,
             "employee_name": emps[eid].full_name if eid in emps else "",
             "workdays": work.get(eid, 0), "offs": offs.get(eid, 0)}
            for eid in sorted(set(list(work) + list(offs)))]


@app.get("/api/exports/roster.csv")
def export_csv(roster_id: int, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    _roster_or_404(db, roster_id)
    rows = _roster_rows(roster_id)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["date", "employee_code", "employee_name",
                                        "entry_type", "brand", "process",
                                        "is_manual"])
    w.writeheader()
    w.writerows(rows)
    return Response(content=buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition":
                             f"attachment; filename=roster_{roster_id}.csv"})


@app.get("/api/exports/roster.xlsx")
def export_xlsx(roster_id: int, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    from openpyxl import Workbook
    _roster_or_404(db, roster_id)
    rows = _roster_rows(roster_id)
    wb = Workbook()
    ws = wb.active
    ws.title = "Roster"
    ws.append(["Date", "Employee Code", "Employee Name", "Type", "Brand",
               "Process", "Manual Edit"])
    for r in rows:
        ws.append([r["date"], r["employee_code"], r["employee_name"],
                   r["entry_type"], r["brand"], r["process"], r["is_manual"]])
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 20
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return Response(content=buf.read(),
                    media_type="application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet",
                    headers={"Content-Disposition":
                             f"attachment; filename=roster_{roster_id}.xlsx"})


@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from sqlalchemy import func
    open_conflicts = db.query(Conflict).filter(Conflict.status == "open").count()
    critical = db.query(Conflict).filter(Conflict.status == "open",
                                         Conflict.severity == "critical").count()
    pending_leave = db.query(LeaveRequest).filter(
        LeaveRequest.status == "pending").count()
    pending_review = db.query(Roster).filter(
        Roster.status == "pending_review").count()
    active_emps = db.query(Employee).filter(Employee.status == "active").count()
    brands = db.query(Brand).filter(Brand.is_active == True).count()  # noqa
    published = db.query(Roster).filter(Roster.status == "published").count()
    latest = db.query(Roster).order_by(Roster.id.desc()).first()
    coverage = None
    if latest and latest.metrics:
        coverage = latest.metrics.get("coverage_rate")
    uncovered_brands = []
    for b in db.query(Brand).filter(Brand.is_active == True).all():  # noqa
        n = db.query(Assignment).filter(Assignment.brand_id == b.id,
                                        Assignment.is_active == True).count()  # noqa
        if n == 0:
            uncovered_brands.append(b.name)
    return {
        "active_employees": active_emps,
        "active_brands": brands,
        "open_conflicts": open_conflicts,
        "critical_conflicts": critical,
        "pending_leave": pending_leave,
        "pending_review_rosters": pending_review,
        "published_rosters": published,
        "latest_roster_coverage": coverage,
        "brands_without_employees": uncovered_brands,
        "recent_conflicts": [{"id": c.id, "type": c.type, "severity": c.severity,
                              "date": c.date.isoformat() if c.date else None,
                              "explanation": c.explanation[:220]}
                             for c in db.query(Conflict).filter(
                                 Conflict.status == "open").order_by(
                                 Conflict.created_at.desc()).limit(5).all()],
        "pending_leave_items": [{"id": l.id, "employee_id": l.employee_id,
                                 "start_date": l.start_date.isoformat(),
                                 "end_date": l.end_date.isoformat(),
                                 "leave_type": l.leave_type}
                                for l in db.query(LeaveRequest).filter(
                                    LeaveRequest.status == "pending").limit(5).all()],
    }

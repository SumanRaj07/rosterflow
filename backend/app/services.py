"""Service layer: loads DB state into the engine, persists results, and
owns the roster lifecycle, revalidation, notifications and audit trail."""
from datetime import date

from sqlalchemy.orm import Session

from . import engine as eng
from .models import (
    Assignment, AuditLog, Availability, BackupRecommendation, Brand,
    CompOffRecord, Conflict, Employee, EmployeePreference,
    EmployeeQualification, Holiday, LeaveRequest, Notification, PodMembership,
    Process, Qualification, Roster, RosterApproval, RosterChange, RosterEntry,
    RosterPlan, StaffingRequirement, User, WorkingRule,
)

DEFAULT_RULES = {
    "max_consecutive_days": 6,
    "max_monthly_workdays": 26,
    "min_weekly_offs": 4,
    "sunday_off": True,
    "holiday_off": True,
}


def audit(db: Session, user, action, entity_type, entity_id, details=None):
    db.add(AuditLog(user_id=user.id if user else None, action=action,
                    entity_type=entity_type, entity_id=entity_id,
                    details=details or {}))


def notify(db: Session, type_, message, user_id=None, employee_id=None,
           related_type=None, related_id=None):
    db.add(Notification(user_id=user_id, employee_id=employee_id, type=type_,
                        message=message, related_type=related_type,
                        related_id=related_id))


def load_rules(db: Session) -> eng.Rules:
    vals = dict(DEFAULT_RULES)
    for r in db.query(WorkingRule).all():
        if r.key in vals:
            vals[r.key] = r.value
    return eng.Rules(**vals)


def load_inputs(db: Session, year, month, brand_id=None, pod_id=None,
                process_id=None, preferences_applied=True):
    days = eng.month_days(year, month)
    dayset = set(days)
    employees = db.query(Employee).all()
    if pod_id:
        member_ids = {m.employee_id for m in
                      db.query(PodMembership).filter(PodMembership.pod_id == pod_id).all()}
        employees = [e for e in employees if e.id in member_ids]
    assigns = db.query(Assignment).filter(Assignment.is_active == True).all()  # noqa
    if brand_id:
        assigns = [a for a in assigns if a.brand_id == brand_id]
        emp_ids = {a.employee_id for a in assigns}
        employees = [e for e in employees if e.id in emp_ids]
    if process_id:
        assigns = [a for a in assigns if a.process_id in (None, process_id)]
    assignment_set = {(a.employee_id, a.brand_id, a.process_id) for a in assigns}
    primary_set = {(a.employee_id, a.brand_id, a.process_id) for a in assigns
                   if a.is_primary}
    # certification -> process mapping by code convention, e.g. TS_CERT -> TS
    proc_by_code = {p.code: p.id for p in db.query(Process).all()}
    cert_qualified = {}
    for eq in db.query(EmployeeQualification).all():
        qual = db.query(Qualification).filter(Qualification.id == eq.qualification_id).first()
        if not qual:
            continue
        pcode = qual.code.replace("_CERT", "")
        if pcode in proc_by_code:
            cert_qualified.setdefault(eq.employee_id, set()).add(proc_by_code[pcode])
    reqs = db.query(StaffingRequirement).filter(
        StaffingRequirement.is_active == True).all()  # noqa
    if brand_id:
        reqs = [r for r in reqs if r.brand_id == brand_id]
    if process_id:
        reqs = [r for r in reqs if r.process_id == process_id]
    requirements = [{"brand_id": r.brand_id, "process_id": r.process_id,
                     "min_staff": r.min_staff, "applies": r.applies} for r in reqs]
    leave_days = {}
    for lv in db.query(LeaveRequest).filter(LeaveRequest.status == "approved").all():
        d = lv.start_date
        while d <= lv.end_date:
            if d in dayset:
                leave_days.setdefault(lv.employee_id, set()).add(d)
            d = date.fromordinal(d.toordinal() + 1)
    unavailable = {}
    for av in db.query(Availability).filter(Availability.kind == "unavailable").all():
        if av.date and av.date in dayset:
            unavailable.setdefault(av.employee_id, set()).add(av.date)
        elif av.weekday is not None:
            for d in days:
                if d.weekday() == av.weekday:
                    unavailable.setdefault(av.employee_id, set()).add(d)
    preferred_off = {}
    if preferences_applied:
        for p in db.query(EmployeePreference).all():
            if p.preferred_off_weekday is not None:
                preferred_off[p.employee_id] = p.preferred_off_weekday
        for av in db.query(Availability).filter(
                Availability.kind == "preferred_off").all():
            if av.weekday is not None and av.employee_id not in preferred_off:
                preferred_off[av.employee_id] = av.weekday
    holidays = {h.date for h in db.query(Holiday).all() if h.date in dayset}
    brand_names = {b.id: b.name for b in db.query(Brand).all()}
    process_names = {p.id: p.name for p in db.query(Process).all()}
    emp_dicts = [{"id": e.id, "active": e.status == "active",
                  "max_monthly_workdays": e.max_monthly_workdays} for e in employees]
    return {"employees": emp_dicts, "assignments": assignment_set,
            "primary": primary_set, "cert_qualified": cert_qualified,
            "requirements": requirements, "leave_days": leave_days,
            "unavailable_days": unavailable, "preferred_off": preferred_off,
            "holidays": holidays, "brand_names": brand_names,
            "process_names": process_names, "days": days}


def _persist_generation(db: Session, roster: Roster, result):
    for en in result["entries"]:
        db.add(RosterEntry(roster_id=roster.id, employee_id=en["employee_id"],
                           date=en["date"], entry_type=en["entry_type"],
                           brand_id=en["brand_id"], process_id=en["process_id"]))
    for c in result["conflicts"]:
        db.add(Conflict(roster_id=roster.id, month=roster.month, year=roster.year,
                        type=c["type"], severity=c["severity"], date=c["date"],
                        brand_id=c["brand_id"], process_id=c["process_id"],
                        rule=c["rule"], explanation=c["explanation"],
                        recommendation=c["recommendation"]))
    db.flush()
    conf_map = {(c.date, c.brand_id, c.process_id): c.id
                for c in db.query(Conflict).filter(Conflict.roster_id == roster.id).all()}
    for b in result["backups"]:
        db.add(BackupRecommendation(
            conflict_id=conf_map.get((b["date"], b["brand_id"], b["process_id"])),
            roster_id=roster.id, date=b["date"], brand_id=b["brand_id"],
            process_id=b["process_id"], employee_id=b["employee_id"],
            score=b["score"], reason=b["reason"]))
    roster.metrics = result["metrics"]


def generate_roster(db: Session, user, payload) -> Roster:
    rules = load_rules(db)
    inputs = load_inputs(db, payload.year, payload.month, payload.brand_id,
                         payload.pod_id, payload.process_id,
                         payload.preferences_applied)
    roster = Roster(month=payload.month, year=payload.year, status="draft",
                    brand_id=payload.brand_id, pod_id=payload.pod_id,
                    process_id=payload.process_id,
                    preferences_applied=payload.preferences_applied,
                    strategy=payload.strategy, created_by=user.id)
    db.add(roster)
    db.flush()
    result = eng.generate(payload.year, payload.month, inputs["employees"],
                          inputs["assignments"], inputs["requirements"],
                          inputs["leave_days"], inputs["unavailable_days"],
                          inputs["preferred_off"], inputs["holidays"], rules,
                          strategy=payload.strategy,
                          brand_names=inputs["brand_names"],
                          process_names=inputs["process_names"],
                          primary=inputs["primary"],
                          cert_qualified=inputs["cert_qualified"])
    _persist_generation(db, roster, result)
    if payload.generate_plans:
        for name, strat in [("Balanced", "balanced"),
                            ("Preference-first", "preference"),
                            ("Weekend-fair", "weekend_fair")]:
            r = eng.generate(payload.year, payload.month, inputs["employees"],
                             inputs["assignments"], inputs["requirements"],
                             inputs["leave_days"], inputs["unavailable_days"],
                             inputs["preferred_off"], inputs["holidays"], rules,
                             strategy=strat, brand_names=inputs["brand_names"],
                             process_names=inputs["process_names"],
                             primary=inputs["primary"],
                             cert_qualified=inputs["cert_qualified"])
            db.add(RosterPlan(month=payload.month, year=payload.year, name=name,
                              strategy=strat, metrics=r["metrics"],
                              entries=[{**e, "date": e["date"].isoformat()}
                                       for e in r["entries"]],
                              is_selected=(strat == payload.strategy)))
    audit(db, user, "roster.generate", "roster", roster.id,
          {"month": payload.month, "year": payload.year,
           "strategy": payload.strategy})
    db.commit()
    db.refresh(roster)
    return roster


def validate_roster(db: Session, roster: Roster):
    """Revalidate entries; replaces the roster's conflicts. Returns conflicts."""
    rules = load_rules(db)
    inputs = load_inputs(db, roster.year, roster.month)
    entries = [{"employee_id": e.employee_id, "date": e.date,
                "entry_type": e.entry_type, "brand_id": e.brand_id,
                "process_id": e.process_id}
               for e in db.query(RosterEntry).filter(
                   RosterEntry.roster_id == roster.id).all()]
    conflicts = eng.validate_entries(entries, inputs["employees"],
                                     inputs["assignments"],
                                     inputs["requirements"],
                                     inputs["leave_days"],
                                     inputs["unavailable_days"], rules,
                                     holidays=inputs["holidays"])
    db.query(Conflict).filter(Conflict.roster_id == roster.id).delete()
    for c in conflicts:
        db.add(Conflict(roster_id=roster.id, month=roster.month, year=roster.year,
                        type=c["type"], severity=c["severity"],
                        date=c.get("date"), brand_id=c.get("brand_id"),
                        process_id=c.get("process_id"),
                        employee_id=c.get("employee_id"), rule=c.get("rule"),
                        explanation=c["explanation"],
                        recommendation=c.get("recommendation")))
    # weekly-off shortfall as warning
    offs = {}
    for e in entries:
        if e["entry_type"] == "off":
            offs[e["employee_id"]] = offs.get(e["employee_id"], 0) + 1
    for emp in inputs["employees"]:
        if emp["active"] and offs.get(emp["id"], 0) < rules.min_weekly_offs:
            worked = sum(1 for e in entries
                         if e["employee_id"] == emp["id"] and e["entry_type"] == "work")
            if worked > 0:
                db.add(Conflict(roster_id=roster.id, month=roster.month,
                                year=roster.year, type="weekly_off_shortfall",
                                severity="warning", employee_id=emp["id"],
                                rule="Minimum weekly offs",
                                explanation=f"Employee {emp['id']} has only "
                                f"{offs.get(emp['id'], 0)} weekly offs, below the "
                                f"minimum {rules.min_weekly_offs}.",
                                recommendation="Swap a surplus workday for a weekly off."))
    critical = [c for c in conflicts if c["severity"] == "critical"]
    if roster.status == "draft":
        roster.status = "validated" if not critical else "draft"
    _regenerate_backups(db, roster, entries, inputs, rules)
    db.commit()
    return db.query(Conflict).filter(Conflict.roster_id == roster.id).all()


def _regenerate_backups(db: Session, roster: Roster, entries, inputs, rules):
    """Recompute backup recommendations for open understaffed conflicts from
    the roster's current entries, so draft versions and edited rosters also
    get actionable backups (generation-time backups belong to the old roster)."""
    db.flush()  # make freshly added conflicts visible (autoflush is off)
    db.query(BackupRecommendation).filter(
        BackupRecommendation.roster_id == roster.id).delete()
    work_by_emp = {}
    work_today = {}
    for e in entries:
        if e["entry_type"] == "work":
            work_by_emp[e["employee_id"]] = work_by_emp.get(e["employee_id"], 0) + 1
            work_today[(e["employee_id"], e["date"])] = True
    conflicts = db.query(Conflict).filter(
        Conflict.roster_id == roster.id, Conflict.type == "understaffed",
        Conflict.status == "open").all()
    emps = {e["id"]: e for e in inputs["employees"]}
    for c in conflicts:
        d = c.date
        cands = []
        for eid, emp in emps.items():
            if not emp["active"]:
                continue
            via_assignment = (eid, c.brand_id, c.process_id) in inputs["assignments"] \
                or (eid, c.brand_id, None) in inputs["assignments"]
            via_cert = c.process_id in inputs["cert_qualified"].get(eid, set())
            if not (via_assignment or via_cert):
                continue
            if d in inputs["leave_days"].get(eid, set()):
                continue
            if d in inputs["unavailable_days"].get(eid, set()):
                continue
            if work_today.get((eid, d)):
                continue
            wd = work_by_emp.get(eid, 0)
            if wd >= (emp["max_monthly_workdays"] or rules.max_monthly_workdays):
                continue
            pref_pen = 1 if inputs["preferred_off"].get(eid) == d.weekday() else 0
            score = max(0, 100 - 2 * wd - 15 * pref_pen)
            basis = ("Assigned to this brand/process" if via_assignment
                     else "Holds the certification for this process")
            cands.append((score, eid, f"{basis}, available on {d.isoformat()}, "
                                     f"{wd} workdays this month."))
        cands.sort(key=lambda x: (-x[0], x[1]))
        for score, eid, reason in cands[:5]:
            db.add(BackupRecommendation(conflict_id=c.id, roster_id=roster.id,
                                        date=d, brand_id=c.brand_id,
                                        process_id=c.process_id,
                                        employee_id=eid, score=score,
                                        reason=reason))


def apply_entry_patch(db: Session, user, roster: Roster, entry, patch):
    if roster.status in ("published", "superseded"):
        raise ValueError("Published rosters cannot be edited directly; create a new version.")
    old = {"entry_type": entry.entry_type, "brand_id": entry.brand_id,
           "process_id": entry.process_id}
    if patch.entry_type is not None:
        entry.entry_type = patch.entry_type
    if patch.brand_id is not None:
        entry.brand_id = patch.brand_id
    if patch.process_id is not None:
        entry.process_id = patch.process_id
    if patch.note is not None:
        entry.note = patch.note
    entry.is_manual = True
    db.add(RosterChange(roster_id=roster.id, employee_id=entry.employee_id,
                        date=entry.date, field="entry",
                        old_value=str(old),
                        new_value=str({"entry_type": entry.entry_type,
                                       "brand_id": entry.brand_id,
                                       "process_id": entry.process_id}),
                        reason=patch.reason or "Manual edit",
                        changed_by=user.id))
    audit(db, user, "roster.edit_entry", "roster_entry", entry.id,
          {"roster_id": roster.id, "employee_id": entry.employee_id,
           "date": entry.date.isoformat()})
    db.commit()
    return validate_roster(db, roster)


def revalidate_after_leave(db: Session, leave: LeaveRequest):
    """Find rosters overlapping the leave; flag work entries on leave days,
    create backup recommendations and notify managers. Published rosters are
    never silently changed."""
    rules = load_rules(db)
    rosters = db.query(Roster).filter(
        Roster.status.in_(["draft", "validated", "pending_review", "approved",
                           "published"])).all()
    affected = []
    for roster in rosters:
        if roster.year != leave.start_date.year or roster.month != leave.start_date.month:
            if not (roster.year == leave.end_date.year and roster.month == leave.end_date.month):
                continue
        entries = db.query(RosterEntry).filter(
            RosterEntry.roster_id == roster.id,
            RosterEntry.employee_id == leave.employee_id,
            RosterEntry.entry_type == "work",
            RosterEntry.date >= leave.start_date,
            RosterEntry.date <= leave.end_date).all()
        if not entries:
            continue
        inputs = load_inputs(db, roster.year, roster.month)
        for en in entries:
            db.add(Conflict(roster_id=roster.id, month=roster.month,
                            year=roster.year, type="leave_violation",
                            severity="critical", date=en.date,
                            brand_id=en.brand_id, process_id=en.process_id,
                            employee_id=en.employee_id,
                            rule="No work during approved leave",
                            explanation=f"Employee {en.employee_id} is on approved "
                            f"leave on {en.date} but has a work assignment in roster "
                            f"{roster.id}.",
                            recommendation="Apply an eligible backup recommendation."))
        affected.append(roster.id)
    for admin in db.query(User).filter(User.role.in_(["admin", "manager"])).all():
        notify(db, "leave_roster_impact",
               f"Approved leave for employee {leave.employee_id} affects "
               f"{len(affected)} roster(s); revalidation created conflicts.",
               user_id=admin.id, related_type="leave", related_id=leave.id)
    db.commit()
    return affected


def publish_roster(db: Session, user, roster: Roster, justification=None):
    critical = db.query(Conflict).filter(
        Conflict.roster_id == roster.id, Conflict.status == "open",
        Conflict.severity == "critical").count()
    if critical and not justification:
        raise ValueError(
            f"Cannot publish: {critical} unresolved critical conflict(s). "
            "Provide an exception justification to publish anyway.")
    if justification:
        roster.exception_justification = justification
    roster.status = "published"
    from datetime import datetime
    roster.published_at = datetime.utcnow()
    if roster.parent_id:
        parent = db.query(Roster).filter(Roster.id == roster.parent_id).first()
        if parent and parent.status == "published":
            parent.status = "superseded"
    audit(db, user, "roster.publish", "roster", roster.id,
          {"exception": bool(justification)})
    # notify employees with work entries
    emp_ids = {e.employee_id for e in db.query(RosterEntry).filter(
        RosterEntry.roster_id == roster.id,
        RosterEntry.entry_type == "work").all()}
    for eid in emp_ids:
        notify(db, "roster_published",
               f"Your roster for {roster.month}/{roster.year} has been published.",
               employee_id=eid, related_type="roster", related_id=roster.id)
    db.commit()
    return roster

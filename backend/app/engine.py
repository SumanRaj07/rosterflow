"""Deterministic scheduling engine.

Pure functions over plain data structures so the rules are unit-testable
without a database. The service layer (services.py) loads DB rows into these
structures and persists the results.

Hard constraints (never violated by generate()):
  * approved leave, mandatory unavailability
  * qualification via assignment (brand + process)
  * inactive employees
  * one work assignment per employee per day
  * max consecutive working days
  * max monthly working days
Soft goals (optimised, never overriding hard constraints):
  * fair weekly-off distribution, balanced workload, weekend fairness,
    employee preferred weekly-off weekday.
"""
import calendar as _cal
import statistics
from dataclasses import dataclass, field
from datetime import date


@dataclass
class Rules:
    max_consecutive_days: int = 6
    max_monthly_workdays: int = 26
    min_weekly_offs: int = 4
    sunday_off: bool = True
    holiday_off: bool = True


def month_days(year: int, month: int):
    _, ndays = _cal.monthrange(year, month)
    return [date(year, month, d) for d in range(1, ndays + 1)]


def requirement_applies(applies: str, d: date, is_holiday: bool) -> bool:
    wd = d.weekday()  # 0=Mon
    if applies == "all":
        return True
    if applies == "weekday":
        return wd < 5 and not is_holiday
    if applies == "weekend":
        return wd >= 5
    if applies == "sunday":
        return wd == 6
    if applies == "holiday":
        return is_holiday
    return False


def _qualified(assignments, emp_id, brand_id, process_id) -> bool:
    for (e, b, p) in assignments:
        if e == emp_id and b == brand_id and (p is None or p == process_id):
            return True
    return False


def generate(year, month, employees, assignments, requirements, leave_days,
             unavailable_days, preferred_off, holidays, rules: Rules,
             strategy="balanced", brand_names=None, process_names=None,
             primary=None, cert_qualified=None):
    """Returns dict(entries, conflicts, backups, metrics, gaps).

    employees: [{id, active, max_monthly_workdays|None}]
    assignments: set[(emp, brand, process|None)]
    requirements: [{brand_id, process_id, min_staff, applies}]
    leave_days / unavailable_days: {emp_id: set(date)}
    preferred_off: {emp_id: weekday|None}
    holidays: set(date)
    primary: set[(emp, brand, process|None)] scheduled before backup assignees
    cert_qualified: {emp_id: set(process_id)} - certification-based backup pool
    """
    brand_names = brand_names or {}
    process_names = process_names or {}
    primary = primary or set()
    cert_qualified = cert_qualified or {}
    days = month_days(year, month)
    emps = {e["id"]: e for e in employees if e.get("active", True)}
    workdays = {i: 0 for i in emps}
    weekend_days = {i: 0 for i in emps}
    consecutive = {i: 0 for i in emps}
    max_wd = {i: (emps[i].get("max_monthly_workdays") or rules.max_monthly_workdays)
              for i in emps}
    # assignment map: (emp, day) -> (brand, process) | None
    assign = {}
    req_counts = {}  # (day, brand, process) -> assigned count
    gaps = []

    def sort_key(eid, d):
        pref_pen = 1 if preferred_off.get(eid) == d.weekday() else 0
        wd = workdays[eid]
        we = weekend_days[eid]
        if strategy == "preference":
            return (pref_pen, wd, we, eid)
        if strategy == "weekend_fair":
            return (we, wd, pref_pen, eid)
        return (wd, we, pref_pen, eid)  # balanced

    for d in days:
        is_hol = d in holidays
        is_weekend = d.weekday() >= 5
        assigned_today = set()
        for req in sorted(requirements, key=lambda r: (r["brand_id"], r["process_id"])):
            if not requirement_applies(req["applies"], d, is_hol):
                continue
            b, p, need = req["brand_id"], req["process_id"], req["min_staff"]
            elig = []
            for eid in emps:
                if eid in assigned_today:
                    continue
                if not _qualified(assignments, eid, b, p):
                    continue
                if d in leave_days.get(eid, set()):
                    continue
                if d in unavailable_days.get(eid, set()):
                    continue
                if consecutive[eid] >= rules.max_consecutive_days:
                    continue
                if workdays[eid] >= max_wd[eid]:
                    continue
                elig.append(eid)
            elig.sort(key=lambda e: (
                0 if (e, b, p) in primary or (e, b, None) in primary else 1,
                *sort_key(e, d)))
            chosen = elig[:need]
            for eid in chosen:
                assign[(eid, d)] = (b, p)
                assigned_today.add(eid)
                workdays[eid] += 1
                if is_weekend:
                    weekend_days[eid] += 1
            req_counts[(d, b, p)] = len(chosen)
            if len(chosen) < need:
                gaps.append({"date": d, "brand_id": b, "process_id": p,
                             "required": need, "filled": len(chosen),
                             "shortfall": need - len(chosen)})
        for eid in emps:
            consecutive[eid] = consecutive[eid] + 1 if eid in assigned_today else 0

    # ---- fairness pass: lift employees below min weekly offs by SWAPPING a
    # workday to another eligible employee who is off that day. Coverage is
    # preserved (the slot stays filled); only the worker changes.
    offs = {i: 0 for i in emps}
    entries = {}
    for eid in emps:
        for d in days:
            if d in leave_days.get(eid, set()):
                entries[(eid, d)] = ("leave", None, None)
            elif (eid, d) in assign:
                entries[(eid, d)] = ("work",) + assign[(eid, d)]
            elif d in holidays and rules.holiday_off:
                entries[(eid, d)] = ("holiday", None, None)
            else:
                entries[(eid, d)] = ("off", None, None)
                offs[eid] += 1

    def trailing_run(eid, d):
        """Consecutive workdays ending the day before d, per current entries."""
        run = 0
        idx = days.index(d) - 1
        while idx >= 0 and entries.get((eid, days[idx]), ("off",))[0] == "work":
            run += 1
            idx -= 1
        return run

    needy = sorted([i for i in emps if workdays[i] > 0 and offs[i] < rules.min_weekly_offs],
                   key=lambda i: (offs[i], i))
    for eid in needy:
        while offs[eid] < rules.min_weekly_offs:
            swapped = False
            # prefer converting a preferred-off weekday first
            work_ds = sorted(
                [d for d in days if entries.get((eid, d), ("off",))[0] == "work"],
                key=lambda d: (0 if preferred_off.get(eid) == d.weekday() else 1, d))
            for d in work_ds:
                b, p = entries[(eid, d)][1], entries[(eid, d)][2]
                repls = []
                for oid in emps:
                    if oid == eid:
                        continue
                    # Never take an off away from someone at/below the minimum:
                    # that would just move the shortfall around (ping-pong).
                    if offs[oid] <= rules.min_weekly_offs:
                        continue
                    if entries.get((oid, d), ("off",))[0] == "work":
                        continue
                    if not _qualified(assignments, oid, b, p):
                        continue
                    if d in leave_days.get(oid, set()):
                        continue
                    if d in unavailable_days.get(oid, set()):
                        continue
                    if trailing_run(oid, d) >= rules.max_consecutive_days:
                        continue
                    if workdays[oid] >= max_wd[oid]:
                        continue
                    pref = 0 if preferred_off.get(oid) == d.weekday() else 1
                    repls.append((pref, workdays[oid], oid))
                if not repls:
                    continue
                repls.sort()
                oid = repls[0][2]
                entries[(eid, d)] = ("off", None, None)
                entries[(oid, d)] = ("work", b, p)
                workdays[eid] -= 1
                offs[eid] += 1
                workdays[oid] += 1
                offs[oid] -= 1
                if d.weekday() >= 5:
                    weekend_days[eid] -= 1
                    weekend_days[oid] += 1
                swapped = True
                break
            if not swapped:
                break

    # ---- metrics
    required_slots = 0
    for d in days:
        is_hol = d in holidays
        for req in requirements:
            if requirement_applies(req["applies"], d, is_hol):
                required_slots += req["min_staff"]
    filled_slots = required_slots - sum(g["shortfall"] for g in gaps)
    coverage = (filled_slots / required_slots) if required_slots else 1.0
    wd_vals = [workdays[i] for i in emps]
    mean_wd = statistics.mean(wd_vals) if wd_vals else 0
    std_wd = statistics.pstdev(wd_vals) if len(wd_vals) > 1 else 0
    fairness_all = max(0.0, 1.0 - (std_wd / mean_wd)) if mean_wd else 1.0
    # Fairness is measured across scheduled staff: backup-pool employees who
    # were not needed work 0 days by design, and including them would punish
    # the score for the pool existing at all.
    sched = [v for v in wd_vals if v > 0]
    mean_s = statistics.mean(sched) if sched else 0
    std_s = statistics.pstdev(sched) if len(sched) > 1 else 0
    fairness = max(0.0, 1.0 - (std_s / mean_s)) if mean_s else 1.0
    # NOTE: no separate weekend-fairness score is reported. Weekend days are
    # dominated by operating pattern (weekday-only brands work zero weekends),
    # so any single weekend-fairness number is misleading; the per-employee
    # weekend-day breakdown in `per_employee` is the honest view, and the
    # weekend-fair strategy's effect (more staff sharing weekend load) is
    # visible there.
    pref_conflicts = 0
    total_work = 0
    for (eid, d), v in entries.items():
        if v[0] == "work":
            total_work += 1
            if preferred_off.get(eid) == d.weekday():
                pref_conflicts += 1
    pref_rate = (1.0 - pref_conflicts / total_work) if total_work else 1.0

    out_entries = []
    for eid in emps:
        for d in days:
            typ, b, p = entries[(eid, d)]
            out_entries.append({"employee_id": eid, "date": d, "entry_type": typ,
                                "brand_id": b, "process_id": p})
    conflicts = []
    for g in gaps:
        bn = brand_names.get(g["brand_id"], f"Brand {g['brand_id']}")
        pn = process_names.get(g["process_id"], f"Process {g['process_id']}")
        conflicts.append({
            "type": "understaffed", "severity": "critical", "date": g["date"],
            "brand_id": g["brand_id"], "process_id": g["process_id"],
            "rule": "Minimum staffing requirement",
            "explanation": (
                f"{bn} requires {g['required']} eligible {pn} employee(s) on "
                f"{g['date'].isoformat()}, but only {g['filled']} could be assigned. "
                f"Shortfall: {g['shortfall']}. No other qualified, available employee "
                f"could cover this requirement without violating leave, availability, "
                f"qualification, workload or consecutive-day rules."),
            "recommendation": (
                "Review qualified employees from other permitted assignments, approve "
                "overtime/comp-off coverage, or escalate the shortage to the operations "
                "manager."),
        })
    backups = []
    for g in gaps:
        d = g["date"]
        cands = []
        for eid in emps:
            via_assignment = _qualified(assignments, eid, g["brand_id"],
                                        g["process_id"])
            via_cert = g["process_id"] in cert_qualified.get(eid, set())
            if not (via_assignment or via_cert):
                continue
            if d in leave_days.get(eid, set()):
                continue
            if d in unavailable_days.get(eid, set()):
                continue
            if entries.get((eid, d), ("off", None, None))[0] == "work":
                continue
            if workdays[eid] >= max_wd[eid]:
                continue
            pref_pen = 1 if preferred_off.get(eid) == d.weekday() else 0
            score = max(0, 100 - 2 * workdays[eid] - 5 * weekend_days[eid]
                        - 15 * pref_pen)
            basis = ("Assigned to this brand/process" if via_assignment
                     else "Holds the certification for this process")
            cands.append({"employee_id": eid, "score": score,
                          "workdays": workdays[eid],
                          "weekend_days": weekend_days[eid],
                          "preferred_off_conflict": bool(pref_pen),
                          "reason": (
                              f"{basis}, available on {d.isoformat()}, "
                              f"{workdays[eid]} workdays this month, "
                              f"{weekend_days[eid]} weekend days."
                              + (" Preferred weekly off falls on this day."
                                 if pref_pen else ""))})
        cands.sort(key=lambda c: (-c["score"], c["employee_id"]))
        for c in cands[:5]:
            c.update({"date": d, "brand_id": g["brand_id"],
                      "process_id": g["process_id"]})
            backups.append(c)
    metrics = {
        "coverage_rate": round(coverage, 4),
        "required_slots": required_slots,
        "filled_slots": filled_slots,
        "gap_count": len(gaps),
        "total_work_assignments": total_work,
        "fairness_score": round(fairness, 4),
        "fairness_score_all_employees": round(fairness_all, 4),
        "workday_mean": round(mean_wd, 2),
        "workday_std": round(std_wd, 2),
        "preference_satisfied_rate": round(pref_rate, 4),
        "preference_conflicts": pref_conflicts,
        "per_employee": {i: {"workdays": workdays[i], "offs": offs[i],
                             "weekend_days": weekend_days[i]} for i in emps},
    }
    return {"entries": out_entries, "conflicts": conflicts, "backups": backups,
            "metrics": metrics, "gaps": gaps}


def validate_entries(entries, employees, assignments, requirements, leave_days,
                     unavailable_days, rules: Rules, holidays=None):
    """Revalidate a set of roster entries. entries: [{employee_id, date,
    entry_type, brand_id, process_id}]. Returns list of conflict dicts."""
    holidays = holidays or set()
    emps = {e["id"]: e for e in employees}
    conflicts = []
    work_by_emp = {}
    work_by_day_req = {}
    for en in entries:
        eid, d = en["employee_id"], en["date"]
        if en["entry_type"] != "work":
            continue
        emp = emps.get(eid)
        if not emp or not emp.get("active", True):
            conflicts.append({"type": "inactive_employee", "severity": "critical",
                              "date": d, "employee_id": eid,
                              "rule": "Inactive employees cannot receive new assignments",
                              "explanation": f"Employee {eid} is inactive but has a work assignment on {d}.",
                              "recommendation": "Remove the assignment or reactivate the employee."})
            continue
        if d in leave_days.get(eid, set()):
            conflicts.append({"type": "leave_violation", "severity": "critical",
                              "date": d, "employee_id": eid,
                              "rule": "No work during approved leave",
                              "explanation": f"Employee {eid} is on approved leave on {d} but is assigned work.",
                              "recommendation": "Replace with an eligible backup employee."})
        if d in unavailable_days.get(eid, set()):
            conflicts.append({"type": "unavailability_violation", "severity": "critical",
                              "date": d, "employee_id": eid,
                              "rule": "Mandatory availability restriction",
                              "explanation": f"Employee {eid} is marked unavailable on {d} but is assigned work.",
                              "recommendation": "Replace with an eligible backup employee."})
        if not _qualified(assignments, eid, en.get("brand_id"), en.get("process_id")):
            conflicts.append({"type": "unqualified_assignment", "severity": "critical",
                              "date": d, "employee_id": eid,
                              "brand_id": en.get("brand_id"),
                              "process_id": en.get("process_id"),
                              "rule": "Employee must hold an active assignment for the brand/process",
                              "explanation": f"Employee {eid} has no active assignment for this brand/process on {d}.",
                              "recommendation": "Assign a qualified employee or create the assignment first."})
        work_by_emp.setdefault(eid, []).append(d)
        key = (d, en.get("brand_id"), en.get("process_id"))
        work_by_day_req[key] = work_by_day_req.get(key, 0) + 1
    for eid, ds in work_by_emp.items():
        ds = sorted(ds)
        if len(ds) > (emps[eid].get("max_monthly_workdays") or rules.max_monthly_workdays):
            conflicts.append({"type": "workload_limit", "severity": "critical",
                              "employee_id": eid,
                              "rule": "Maximum monthly workload",
                              "explanation": f"Employee {eid} has {len(ds)} workdays, exceeding the monthly limit.",
                              "recommendation": "Move some assignments to other eligible employees."})
        run = 1
        for i in range(1, len(ds)):
            if (ds[i] - ds[i - 1]).days == 1:
                run += 1
                if run > rules.max_consecutive_days:
                    conflicts.append({"type": "consecutive_days", "severity": "critical",
                                      "date": ds[i], "employee_id": eid,
                                      "rule": "Maximum consecutive working days",
                                      "explanation": f"Employee {eid} would work {run} consecutive days ending {ds[i]}.",
                                      "recommendation": "Insert a weekly off before the limit is exceeded."})
                    break
            else:
                run = 1
        offs = 0
        # offs counted by caller through entries; approximate from non-work days
        # in the same month is done by the service layer when needed.
    for req in requirements:
        for d in set(e["date"] for e in entries):
            if not requirement_applies(req["applies"], d, d in holidays):
                continue
            filled = work_by_day_req.get((d, req["brand_id"], req["process_id"]), 0)
            if filled < req["min_staff"]:
                conflicts.append({"type": "understaffed", "severity": "critical",
                                  "date": d, "brand_id": req["brand_id"],
                                  "process_id": req["process_id"],
                                  "rule": "Minimum staffing requirement",
                                  "explanation": f"Requirement needs {req['min_staff']} but only {filled} assigned on {d}.",
                                  "recommendation": "Assign an eligible backup employee."})
    return conflicts

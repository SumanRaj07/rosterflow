"""Deterministic seed data. Safe to run repeatedly (clears and rebuilds).
Demo month: November 2026 (contains Sundays + Diwali on 2026-11-08).

Design notes (see README for the full rationale):
  * 8 brands have single-resource weekday processes (one primary each);
    2 brands have multi-employee requirements (Jade Fashion: 3 primaries
    for min 2, all days; Ion Energy: exactly 3 staff for min 3, all days,
    so the 6-consecutive-day rule forces Saturday gaps -> understaffing
    demo with certification-based backup recommendations).
  * Extra assignees act as the backup pool; they do not change the
    single-resource shape of the 8 weekday requirements.
"""
from datetime import date

from sqlalchemy.orm import Session

from .auth import hash_password, new_salt
from .db import SessionLocal, init_db
from .models import (
    Assignment, Availability, Brand, CompOffRecord, Employee,
    EmployeePreference, Holiday, LeaveRequest, Pod, PodMembership, Process,
    Qualification, EmployeeQualification, StaffingRequirement, User,
)

NAMES = [
    ("Aarav Sharma", "Associate"), ("Priya Patel", "Associate"),
    ("Rohan Deshmukh", "Senior Associate"), ("Sneha Kulkarni", "Associate"),
    ("Vikram Singh", "Associate"), ("Ananya Iyer", "Senior Associate"),
    ("Kiran Reddy", "Associate"), ("Meera Nair", "Team Lead"),
    ("Arjun Mehta", "Associate"), ("Divya Joshi", "Senior Associate"),
    ("Nikhil Verma", "Associate"), ("Pooja Gupta", "Associate"),
    ("Aditya Rao", "Associate"), ("Ritu Malhotra", "Associate"),
    ("Sanjay Kumar", "Associate"), ("Kavya Menon", "Associate"),
    ("Manish Tiwari", "Senior Associate"), ("Neha Shah", "Associate"),
    ("Varun Pillai", "Associate"), ("Ishita Bose", "Associate"),
    ("Rajesh Khanna", "Associate"), ("Farah Khan", "Senior Associate"),
    ("Deepak Yadav", "Associate"), ("Lakshmi Prasad", "Associate"),
    ("Amit Joshi", "Associate"), ("Shreya Singh", "Associate"),
    ("Vivek Anand", "Associate"), ("Tanvi Desai", "Associate"),
    ("Rahul Kapoor", "Associate"), ("Geeta Rao", "Associate"),
    ("Mohammed Faiz", "Associate"), ("Anjali Verma", "Associate"),
    ("Suresh Babu", "Associate"), ("Nisha Patil", "Associate"),
    ("Karthik Raja", "Senior Associate"), ("Simran Kaur", "Associate"),
]

PROCESSES = [
    ("CS", "Customer Support"), ("ES", "Email Support"),
    ("OM", "Order Management"), ("DE", "Data Entry"),
    ("QA", "Quality Assurance"), ("OPS", "Operations"),
    ("TS", "Technical Support"),
]

# (code, name, [(process_code, min_staff, applies, primary_emp_index)])
# Weekday brands carry two single-resource processes each (one primary per
# process). Ion is deliberately tight: 3 staff for min 3 every day, so the
# 6-consecutive-day rule forces Saturday gaps. Jade rotates 3 primaries.
BRANDS = [
    ("APX", "Apex Retail", [("CS", 1, "weekday", 0), ("ES", 1, "weekday", 12)]),
    ("BCN", "Beacon Bank", [("CS", 1, "weekday", 1), ("OM", 1, "weekday", 13)]),
    ("CRS", "Cirrus Telecom", [("TS", 1, "weekday", 2), ("CS", 1, "weekday", 14)]),
    ("DLT", "Delta Logistics", [("OM", 1, "weekday", 3), ("DE", 1, "weekday", 15)]),
    ("EMB", "Ember Foods", [("DE", 1, "weekday", 4), ("QA", 1, "weekday", 16)]),
    ("FLC", "Falcon Insurance", [("QA", 1, "weekday", 5), ("CS", 1, "weekday", 17)]),
    ("GLC", "Glacier Health", [("CS", 1, "weekday", 6), ("ES", 1, "weekday", 18)]),
    ("HRB", "Harbor Travel", [("OPS", 1, "weekday", 7), ("CS", 1, "weekday", 19)]),
    ("ION", "Ion Energy", [("TS", 3, "all", 8)]),
    ("JDE", "Jade Fashion", [("ES", 2, "all", None)]),
]


def _user(db, email, password, role, employee_id=None):
    salt = new_salt()
    u = User(email=email, password_hash=hash_password(password, salt),
             password_salt=salt, role=role, employee_id=employee_id)
    db.add(u)
    db.flush()
    return u


def run(db: Session):
    # wipe (dev seed only) - children first
    from .models import (AuditLog, BackupRecommendation, Conflict, Notification,
                         Roster, RosterApproval, RosterChange, RosterEntry,
                         RosterPlan, Token)
    for m in [Notification, BackupRecommendation, Conflict, RosterChange,
              RosterApproval, RosterPlan, RosterEntry, Roster, AuditLog, Token,
              PodMembership, Assignment, StaffingRequirement, Availability,
              EmployeePreference, LeaveRequest, CompOffRecord,
              EmployeeQualification, Qualification, Pod, Brand, Process,
              Employee, User]:
        db.query(m).delete()
    db.commit()

    procs = {}
    for code, name in PROCESSES:
        p = Process(code=code, name=name)
        db.add(p)
        db.flush()
        procs[code] = p
    quals = {}
    for code, name in [("CS_CERT", "Customer Support Certified"),
                       ("TS_CERT", "Technical Support Certified"),
                       ("QA_CERT", "QA Certified")]:
        q = Qualification(code=code, name=name)
        db.add(q)
        db.flush()
        quals[code] = q

    emps = []
    for i, (name, title) in enumerate(NAMES):
        e = Employee(employee_code=f"EMP{i+1:03d}", full_name=name,
                     email=f"{name.lower().replace(' ', '.')}@example.com",
                     phone=f"98765{i:05d}", role_title=title,
                     joining_date=date(2024, 1, 15))
        db.add(e)
        db.flush()
        emps.append(e)
    # one employee on leave for the whole demo month is EMP030 (index 29)
    db.flush()

    brands = {}
    for code, name, reqs in BRANDS:
        b = Brand(code=code, name=name)
        db.add(b)
        db.flush()
        brands[code] = b
        for pcode, min_staff, applies, primary in reqs:
            db.add(StaffingRequirement(brand_id=b.id, process_id=procs[pcode].id,
                                       min_staff=min_staff, applies=applies))
            if primary is not None:
                db.add(Assignment(employee_id=emps[primary].id, brand_id=b.id,
                                  process_id=procs[pcode].id, is_primary=True))
    # Jade Fashion: 3 rotating primary staff
    for idx in (9, 10, 11):
        db.add(Assignment(employee_id=emps[idx].id, brand_id=brands["JDE"].id,
                          process_id=procs["ES"].id, is_primary=True))
    # Backup pool: secondaries for the weekday brands, Jade and Ion.
    # Primary-first scheduling keeps weekday processes single-staffed;
    # secondaries cover leave, caps and forced offs.
    pool = [
        (20, "JDE", "ES"), (21, "JDE", "ES"), (22, "ION", "TS"), (23, "ION", "TS"),
        (24, "APX", "CS"), (25, "BCN", "CS"), (26, "CRS", "TS"), (27, "DLT", "OM"),
        (28, "EMB", "DE"), (29, "FLC", "QA"), (30, "GLC", "CS"), (31, "HRB", "OPS"),
        (32, "JDE", "ES"), (33, "JDE", "ES"), (34, "APX", "CS"), (35, "BCN", "CS"),
    ]
    for idx, bcode, pcode in pool:
        db.add(Assignment(employee_id=emps[idx].id, brand_id=brands[bcode].id,
                          process_id=procs[pcode].id))

    # qualifications
    for idx in (0, 1, 6, 9, 12, 25, 29, 32):
        db.add(EmployeeQualification(employee_id=emps[idx].id,
                                     qualification_id=quals["CS_CERT"].id))
    for idx in (2, 8, 14, 22, 23, 26):
        db.add(EmployeeQualification(employee_id=emps[idx].id,
                                     qualification_id=quals["TS_CERT"].id))
    for idx in (5, 17, 28, 35):
        db.add(EmployeeQualification(employee_id=emps[idx].id,
                                     qualification_id=quals["QA_CERT"].id))

    # pods
    admin = _user(db, "admin@rosterflow.local", "Admin@123", "admin")
    manager = _user(db, "manager@rosterflow.local", "Manager@123", "manager")
    leads = []
    for i, (code, name) in enumerate([
            ("POD-A", "Customer Experience"), ("POD-B", "Technical Ops"),
            ("POD-C", "Back Office"), ("POD-D", "Quality & Support")]):
        lead = _user(db, f"lead.{'abcd'[i]}@rosterflow.local", "Lead@123", "pod_lead")
        leads.append(lead)
        pod = Pod(code=code, name=name, lead_id=lead.id)
        db.add(pod)
        db.flush()
        members = [emps[j] for j in range(i * 9, i * 9 + 9)]
        for m in members:
            db.add(PodMembership(pod_id=pod.id, employee_id=m.id))
    for idx in (0, 9):
        _user(db, emps[idx].email, "Emp@123", "employee", employee_id=emps[idx].id)

    # holidays 2026 (India)
    for d, name in [(date(2026, 1, 26), "Republic Day"),
                    (date(2026, 3, 3), "Holi"),
                    (date(2026, 5, 1), "Maharashtra Day"),
                    (date(2026, 8, 15), "Independence Day"),
                    (date(2026, 10, 2), "Gandhi Jayanti"),
                    (date(2026, 11, 8), "Diwali"),
                    (date(2026, 12, 25), "Christmas")]:
        db.add(Holiday(date=d, name=name))

    # leave: approved (demo month Nov 2026) + pending + full-month
    db.add(LeaveRequest(employee_id=emps[0].id, start_date=date(2026, 11, 10),
                        end_date=date(2026, 11, 12), leave_type="annual",
                        reason="Family function", status="approved",
                        reviewer_id=manager.id))
    db.add(LeaveRequest(employee_id=emps[9].id, start_date=date(2026, 11, 15),
                        end_date=date(2026, 11, 20), leave_type="sick",
                        reason="Medical rest", status="approved",
                        reviewer_id=manager.id))
    db.add(LeaveRequest(employee_id=emps[29].id, start_date=date(2026, 11, 1),
                        end_date=date(2026, 11, 30), leave_type="annual",
                        reason="Long vacation", status="approved",
                        reviewer_id=manager.id))
    db.add(LeaveRequest(employee_id=emps[1].id, start_date=date(2026, 11, 20),
                        end_date=date(2026, 11, 21), leave_type="casual",
                        reason="Personal work", status="pending"))
    db.add(LeaveRequest(employee_id=emps[10].id, start_date=date(2026, 12, 5),
                        end_date=date(2026, 12, 6), leave_type="casual",
                        reason="Travel", status="pending"))

    # availability + preferences
    db.add(Availability(employee_id=emps[4].id, weekday=0, kind="unavailable",
                        note="Unavailable every Monday"))
    db.add(Availability(employee_id=emps[6].id, weekday=6, kind="preferred_off",
                        note="Prefers Sundays off"))
    for idx, wd in [(7, 5), (9, 6), (10, 0), (11, 6), (13, 5), (20, 6)]:
        db.add(EmployeePreference(employee_id=emps[idx].id,
                                  preferred_off_weekday=wd))
    # NOTE: seed brand count below uses len(BRANDS) (10); the per-brand
    # process count is 16 weekday + Ion + Jade = 18 requirements.
    db.add(CompOffRecord(employee_id=emps[2].id, earned_date=date(2026, 10, 4),
                         reason="Sunday coverage", status="available"))
    db.add(CompOffRecord(employee_id=emps[10].id, earned_date=date(2026, 10, 11),
                         reason="Holiday coverage", status="available"))
    db.commit()
    return {"employees": len(NAMES), "brands": len(BRANDS)}


if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    print(run(db))

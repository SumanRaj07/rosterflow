"""SQLAlchemy models for RosterFlow. One row per employee per day in RosterEntry
keeps the calendar complete and makes fairness/coverage math straightforward."""
from datetime import datetime, date
from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, Integer, JSON, String,
    Text, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .db import Base


class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    password_salt = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False)  # admin | manager | pod_lead | employee
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    tokens = relationship("Token", back_populates="user", cascade="all, delete-orphan")


class Token(Base, TimestampMixin):
    __tablename__ = "tokens"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(128), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    user = relationship("User", back_populates="tokens")


class Employee(Base, TimestampMixin):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True)
    employee_code = Column(String(32), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(32), nullable=True)
    role_title = Column(String(128), nullable=False, default="Associate")
    status = Column(String(16), nullable=False, default="active")  # active | inactive
    joining_date = Column(Date, nullable=True)
    max_monthly_workdays = Column(Integer, nullable=True)  # None => rule default
    notes = Column(Text, nullable=True)


class Brand(Base, TimestampMixin):
    __tablename__ = "brands"
    id = Column(Integer, primary_key=True)
    code = Column(String(32), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)


class Process(Base, TimestampMixin):
    __tablename__ = "processes"
    id = Column(Integer, primary_key=True)
    code = Column(String(32), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)


class Pod(Base, TimestampMixin):
    __tablename__ = "pods"
    id = Column(Integer, primary_key=True)
    code = Column(String(32), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    lead_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)


class PodMembership(Base):
    __tablename__ = "pod_memberships"
    id = Column(Integer, primary_key=True)
    pod_id = Column(Integer, ForeignKey("pods.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    __table_args__ = (UniqueConstraint("pod_id", "employee_id", name="uq_pod_employee"),)


class Qualification(Base):
    __tablename__ = "qualifications"
    id = Column(Integer, primary_key=True)
    code = Column(String(64), unique=True, nullable=False)
    name = Column(String(255), nullable=False)


class EmployeeQualification(Base):
    __tablename__ = "employee_qualifications"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    qualification_id = Column(Integer, ForeignKey("qualifications.id"), nullable=False)
    __table_args__ = (UniqueConstraint("employee_id", "qualification_id", name="uq_emp_qual"),)


class Assignment(Base, TimestampMixin):
    """Employee is qualified/authorized for (brand, process). process_id NULL
    means authorized for every process of the brand (rare, kept explicit)."""
    __tablename__ = "assignments"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    process_id = Column(Integer, ForeignKey("processes.id"), nullable=True)
    pod_id = Column(Integer, ForeignKey("pods.id"), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    # Primary assignees are scheduled first; other assignees are the backup pool
    # and are only used when no primary is available (leave, limits, offs).
    is_primary = Column(Boolean, default=False, nullable=False)
    __table_args__ = (
        UniqueConstraint("employee_id", "brand_id", "process_id", name="uq_assignment"),
    )


class StaffingRequirement(Base):
    __tablename__ = "staffing_requirements"
    id = Column(Integer, primary_key=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    process_id = Column(Integer, ForeignKey("processes.id"), nullable=False)
    min_staff = Column(Integer, nullable=False, default=1)
    # all | weekday | weekend | sunday | holiday
    applies = Column(String(16), nullable=False, default="all")
    is_active = Column(Boolean, default=True, nullable=False)
    __table_args__ = (
        UniqueConstraint("brand_id", "process_id", "applies", name="uq_staffing"),
    )


class WorkingRule(Base):
    __tablename__ = "working_rules"
    id = Column(Integer, primary_key=True)
    key = Column(String(64), unique=True, nullable=False)
    value = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)


class Holiday(Base):
    __tablename__ = "holidays"
    id = Column(Integer, primary_key=True)
    date = Column(Date, unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    is_mandatory_off = Column(Boolean, default=True, nullable=False)


class Availability(Base, TimestampMixin):
    """kind: unavailable (mandatory) | preferred_off | preferred_work.
    Either a concrete date or a recurring weekday (0=Mon..6=Sun)."""
    __tablename__ = "availabilities"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(Date, nullable=True)
    weekday = Column(Integer, nullable=True)
    kind = Column(String(32), nullable=False)
    note = Column(Text, nullable=True)


class EmployeePreference(Base):
    __tablename__ = "employee_preferences"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, unique=True)
    preferred_off_weekday = Column(Integer, nullable=True)  # 0=Mon..6=Sun
    shift_preference = Column(String(64), nullable=True)
    notes = Column(Text, nullable=True)


class LeaveRequest(Base, TimestampMixin):
    __tablename__ = "leave_requests"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    leave_type = Column(String(64), nullable=False, default="annual")
    reason = Column(Text, nullable=True)
    status = Column(String(16), nullable=False, default="pending")
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_comment = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)


class CompOffRecord(Base, TimestampMixin):
    __tablename__ = "comp_off_records"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    earned_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(String(16), nullable=False, default="available")
    used_date = Column(Date, nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)


class Roster(Base, TimestampMixin):
    __tablename__ = "rosters"
    id = Column(Integer, primary_key=True)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False, default="draft")
    # draft | validated | pending_review | approved | published | superseded
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)
    pod_id = Column(Integer, ForeignKey("pods.id"), nullable=True)
    process_id = Column(Integer, ForeignKey("processes.id"), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    parent_id = Column(Integer, ForeignKey("rosters.id"), nullable=True)
    metrics = Column(JSON, nullable=True)
    preferences_applied = Column(Boolean, default=True)
    strategy = Column(String(32), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    published_at = Column(DateTime, nullable=True)
    exception_justification = Column(Text, nullable=True)


class RosterEntry(Base):
    __tablename__ = "roster_entries"
    id = Column(Integer, primary_key=True)
    roster_id = Column(Integer, ForeignKey("rosters.id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(Date, nullable=False)
    entry_type = Column(String(16), nullable=False)  # work | off | leave | holiday
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)
    process_id = Column(Integer, ForeignKey("processes.id"), nullable=True)
    pod_id = Column(Integer, ForeignKey("pods.id"), nullable=True)
    is_manual = Column(Boolean, default=False, nullable=False)
    note = Column(Text, nullable=True)
    __table_args__ = (
        UniqueConstraint("roster_id", "employee_id", "date", name="uq_roster_entry"),
    )


class RosterPlan(Base, TimestampMixin):
    """Alternative plan snapshot; entries stored as JSON rows."""
    __tablename__ = "roster_plans"
    id = Column(Integer, primary_key=True)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    name = Column(String(128), nullable=False)
    strategy = Column(String(32), nullable=False)
    metrics = Column(JSON, nullable=True)
    entries = Column(JSON, nullable=True)
    is_selected = Column(Boolean, default=False, nullable=False)


class RosterApproval(Base, TimestampMixin):
    __tablename__ = "roster_approvals"
    id = Column(Integer, primary_key=True)
    roster_id = Column(Integer, ForeignKey("rosters.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    decision = Column(String(32), nullable=False)
    comment = Column(Text, nullable=True)


class RosterChange(Base, TimestampMixin):
    __tablename__ = "roster_changes"
    id = Column(Integer, primary_key=True)
    roster_id = Column(Integer, ForeignKey("rosters.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(Date, nullable=False)
    field = Column(String(64), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)


class Conflict(Base, TimestampMixin):
    __tablename__ = "conflicts"
    id = Column(Integer, primary_key=True)
    roster_id = Column(Integer, ForeignKey("rosters.id"), nullable=True)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    type = Column(String(64), nullable=False)  # understaffed | leave_violation | ...
    severity = Column(String(16), nullable=False, default="warning")
    date = Column(Date, nullable=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)
    process_id = Column(Integer, ForeignKey("processes.id"), nullable=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    rule = Column(String(255), nullable=True)
    explanation = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=True)
    status = Column(String(16), nullable=False, default="open")


class BackupRecommendation(Base, TimestampMixin):
    __tablename__ = "backup_recommendations"
    id = Column(Integer, primary_key=True)
    conflict_id = Column(Integer, ForeignKey("conflicts.id"), nullable=True)
    roster_id = Column(Integer, ForeignKey("rosters.id"), nullable=True)
    date = Column(Date, nullable=False)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    process_id = Column(Integer, ForeignKey("processes.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    score = Column(Integer, nullable=False, default=0)
    reason = Column(Text, nullable=True)
    status = Column(String(16), nullable=False, default="pending")


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    type = Column(String(64), nullable=False)
    message = Column(Text, nullable=False)
    related_type = Column(String(64), nullable=True)
    related_id = Column(Integer, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(128), nullable=False)
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)

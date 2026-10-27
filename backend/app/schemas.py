"""Pydantic request/response models. Responses use from_attributes so ORM
objects serialize directly."""
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- auth ----------
class LoginIn(BaseModel):
    email: str
    password: str


class UserOut(ORMModel):
    id: int
    email: str
    role: str
    employee_id: Optional[int] = None
    is_active: bool


# ---------- employees ----------
class EmployeeIn(BaseModel):
    employee_code: str
    full_name: str
    email: str
    phone: Optional[str] = None
    role_title: str = "Associate"
    status: str = "active"
    joining_date: Optional[date] = None
    max_monthly_workdays: Optional[int] = None
    notes: Optional[str] = None


class EmployeePatch(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role_title: Optional[str] = None
    status: Optional[str] = None
    max_monthly_workdays: Optional[int] = None
    notes: Optional[str] = None


class EmployeeOut(ORMModel):
    id: int
    employee_code: str
    full_name: str
    email: str
    phone: Optional[str] = None
    role_title: str
    status: str
    joining_date: Optional[date] = None
    max_monthly_workdays: Optional[int] = None
    notes: Optional[str] = None


# ---------- brands / processes / pods ----------
class BrandIn(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    is_active: bool = True


class BrandOut(ORMModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    is_active: bool


class ProcessIn(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    is_active: bool = True


class ProcessOut(ORMModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    is_active: bool


class PodIn(BaseModel):
    code: str
    name: str
    lead_id: Optional[int] = None
    is_active: bool = True


class PodOut(ORMModel):
    id: int
    code: str
    name: str
    lead_id: Optional[int] = None
    is_active: bool


class PodMemberIn(BaseModel):
    employee_id: int


# ---------- assignments / staffing / rules / holidays ----------
class AssignmentIn(BaseModel):
    employee_id: int
    brand_id: int
    process_id: Optional[int] = None
    pod_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: bool = True
    is_primary: bool = False


class AssignmentOut(ORMModel):
    id: int
    employee_id: int
    brand_id: int
    process_id: Optional[int] = None
    pod_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: bool
    is_primary: bool = False


class StaffingIn(BaseModel):
    brand_id: int
    process_id: int
    min_staff: int = Field(ge=0)
    applies: str = "all"
    is_active: bool = True


class StaffingOut(ORMModel):
    id: int
    brand_id: int
    process_id: int
    min_staff: int
    applies: str
    is_active: bool


class RuleIn(BaseModel):
    key: str
    value: object
    description: Optional[str] = None


class RuleOut(ORMModel):
    id: int
    key: str
    value: object
    description: Optional[str] = None


class HolidayIn(BaseModel):
    date: date
    name: str
    is_mandatory_off: bool = True


class HolidayOut(ORMModel):
    id: int
    date: date
    name: str
    is_mandatory_off: bool


# ---------- availability / preferences / leave / comp-off ----------
class AvailabilityIn(BaseModel):
    employee_id: int
    date: Optional[date] = None
    weekday: Optional[int] = None
    kind: str
    note: Optional[str] = None


class AvailabilityOut(ORMModel):
    id: int
    employee_id: int
    date: Optional[date] = None
    weekday: Optional[int] = None
    kind: str
    note: Optional[str] = None


class PreferenceIn(BaseModel):
    employee_id: int
    preferred_off_weekday: Optional[int] = None
    shift_preference: Optional[str] = None
    notes: Optional[str] = None


class PreferenceOut(ORMModel):
    id: int
    employee_id: int
    preferred_off_weekday: Optional[int] = None
    shift_preference: Optional[str] = None
    notes: Optional[str] = None


class LeaveIn(BaseModel):
    employee_id: int
    start_date: date
    end_date: date
    leave_type: str = "annual"
    reason: Optional[str] = None


class LeaveOut(ORMModel):
    id: int
    employee_id: int
    start_date: date
    end_date: date
    leave_type: str
    reason: Optional[str] = None
    status: str
    reviewer_id: Optional[int] = None
    review_comment: Optional[str] = None


class LeaveReviewIn(BaseModel):
    decision: str  # approved | rejected
    comment: Optional[str] = None


class CompOffIn(BaseModel):
    employee_id: int
    earned_date: date
    reason: Optional[str] = None


class CompOffOut(ORMModel):
    id: int
    employee_id: int
    earned_date: date
    reason: Optional[str] = None
    status: str
    used_date: Optional[date] = None


# ---------- rosters ----------
class GenerateIn(BaseModel):
    month: int
    year: int
    brand_id: Optional[int] = None
    pod_id: Optional[int] = None
    process_id: Optional[int] = None
    preferences_applied: bool = True
    strategy: str = "balanced"
    generate_plans: bool = False


class RosterOut(ORMModel):
    id: int
    month: int
    year: int
    status: str
    brand_id: Optional[int] = None
    pod_id: Optional[int] = None
    process_id: Optional[int] = None
    version: int
    parent_id: Optional[int] = None
    metrics: Optional[object] = None
    strategy: Optional[str] = None
    preferences_applied: bool = False
    published_at: Optional[datetime] = None
    exception_justification: Optional[str] = None


class EntryPatch(BaseModel):
    entry_type: Optional[str] = None
    brand_id: Optional[int] = None
    process_id: Optional[int] = None
    note: Optional[str] = None
    reason: Optional[str] = None


class ApprovalIn(BaseModel):
    decision: str  # submitted | approved | rejected | changes_requested
    comment: Optional[str] = None


class PublishIn(BaseModel):
    exception_justification: Optional[str] = None


class NotificationPatch(BaseModel):
    is_read: bool = True


class QualificationIn(BaseModel):
    code: str
    name: str

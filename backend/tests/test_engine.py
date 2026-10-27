"""Pure engine tests: hard constraints must never break, whatever the inputs."""
from datetime import date

from app.engine import Rules, generate, month_days, validate_entries

NOV = [(2026, 11)]


def _base(days=30, **over):
    kw = dict(year=2026, month=11,
              employees=[{"id": 1, "active": True, "max_monthly_workdays": None}],
              assignments={(1, 1, 1)},
              requirements=[{"brand_id": 1, "process_id": 1, "min_staff": 1,
                             "applies": "all"}],
              leave_days={}, unavailable_days={}, preferred_off={},
              holidays=set(), rules=Rules())
    kw.update(over)
    return kw


def test_leave_never_violated():
    leave = {d for d in month_days(2026, 11)[:10]}
    res = generate(**_base(leave_days={1: leave}))
    worked = {e["date"] for e in res["entries"]
              if e["employee_id"] == 1 and e["entry_type"] == "work"}
    assert not (worked & leave)
    assert all(e["entry_type"] == "leave" for e in res["entries"]
               if e["date"] in leave)


def test_consecutive_day_limit():
    res = generate(**_base())
    worked = sorted(e["date"] for e in res["entries"]
                    if e["entry_type"] == "work")
    run, worst = 1, 1
    for i in range(1, len(worked)):
        run = run + 1 if (worked[i] - worked[i - 1]).days == 1 else 1
        worst = max(worst, run)
    assert worst <= 6
    # 30 days, 1 staff, min 1/day: must take forced offs (26 cap also binds)
    assert len(worked) <= 26


def test_primary_scheduled_first():
    res = generate(**_base(
        employees=[{"id": 1, "active": True, "max_monthly_workdays": None},
                   {"id": 2, "active": True, "max_monthly_workdays": None}],
        assignments={(1, 1, 1), (2, 1, 1)},
        requirements=[{"brand_id": 1, "process_id": 1, "min_staff": 1,
                       "applies": "weekday"}],
        primary={(1, 1, 1)}))
    per = res["metrics"]["per_employee"]
    assert per[1]["workdays"] == 21  # all Nov 2026 weekdays except Diwali? no:
    # Nov 2026 has 21 weekdays; Diwali (Nov 8) is a Sunday, so all 21 are staffed.
    assert per[2]["workdays"] == 0


def test_understaffed_gap_and_cert_backup():
    res = generate(**_base(
        employees=[{"id": 1, "active": True, "max_monthly_workdays": None},
                   {"id": 2, "active": True, "max_monthly_workdays": None}],
        assignments={(1, 1, 1)},
        requirements=[{"brand_id": 1, "process_id": 1, "min_staff": 2,
                       "applies": "all"}],
        cert_qualified={2: {1}}))
    assert res["metrics"]["gap_count"] == 30
    assert res["conflicts"] and all(c["type"] == "understaffed"
                                    for c in res["conflicts"])
    # cert-qualified employee 2 is recommended even without an assignment
    assert any(b["employee_id"] == 2 for b in res["backups"])


def test_validation_catches_leave_violation():
    d = date(2026, 11, 5)
    entries = [{"employee_id": 1, "date": d, "entry_type": "work",
                "brand_id": 1, "process_id": 1}]
    conflicts = validate_entries(
        entries, [{"id": 1, "active": True, "max_monthly_workdays": None}],
        {(1, 1, 1)}, [], {1: {d}}, {}, Rules())
    assert any(c["type"] == "leave_violation" for c in conflicts)


def test_fairness_pass_swaps_workdays_to_offs():
    # Primary-first scheduling fills 2 daily slots with the 2 primaries, so
    # they start near the 26-day cap with ~4 offs. The fairness pass must
    # swap some of their workdays to the idle secondaries (coverage preserved)
    # until they reach the 12-off minimum.
    res = generate(**_base(
        employees=[{"id": i, "active": True, "max_monthly_workdays": None}
                   for i in (1, 2, 3, 4)],
        assignments={(i, 1, 1) for i in (1, 2, 3, 4)},
        requirements=[{"brand_id": 1, "process_id": 1, "min_staff": 2,
                       "applies": "all"}],
        rules=Rules(min_weekly_offs=12),
        primary={(1, 1, 1), (2, 1, 1)}))
    per = res["metrics"]["per_employee"]
    assert per[1]["offs"] >= 12
    assert per[2]["offs"] >= 12
    assert res["metrics"]["gap_count"] == 0  # swaps preserve coverage


def test_deterministic_same_input_same_output():
    a = generate(**_base())
    b = generate(**_base())
    assert a["entries"] == b["entries"]
    assert a["metrics"] == b["metrics"]

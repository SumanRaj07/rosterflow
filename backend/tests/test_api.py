"""API tests: auth, RBAC, generation, approval workflow, exports."""


def _auth(h, token):
    h = dict(h)
    h["Authorization"] = f"Bearer {token}"
    return h


def test_login_bad_password(client):
    r = client.post("/api/auth/login",
                    json={"email": "admin@rosterflow.local", "password": "wrong"})
    assert r.status_code == 401


def test_unauthenticated_blocked(client):
    assert client.get("/api/employees").status_code == 401


def test_employee_cannot_create_brand(client, employee_token):
    r = client.post("/api/brands", json={"code": "TST", "name": "Test"},
                    headers=_auth({}, employee_token))
    assert r.status_code == 403


def test_generate_roster(client, admin_token):
    r = client.post("/api/rosters/generate",
                    json={"month": 11, "year": 2026, "generate_plans": True},
                    headers=_auth({}, admin_token))
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["metrics"]["coverage_rate"] > 0.9
    assert d["metrics"]["required_slots"] > 0
    r = client.get(f"/api/rosters/{d['id']}", headers=_auth({}, admin_token))
    assert r.status_code == 200
    # 36 employees x 30 days = one entry per employee per day
    assert len(r.json()["entries"]) == 36 * 30
    assert r.json()["conflicts"], "seeded Ion Energy gaps must appear"


def test_approval_workflow_and_publish_guard(client, admin_token):
    h = _auth({}, admin_token)
    rid = client.post("/api/rosters/generate",
                      json={"month": 12, "year": 2026},
                      headers=h).json()["id"]
    r = client.post(f"/api/rosters/{rid}/publish", json={}, headers=h)
    assert r.status_code == 400, "unapproved roster must not publish"
    for decision in ("submitted", "approved"):
        r = client.post(f"/api/rosters/{rid}/review",
                        json={"decision": decision}, headers=h)
        assert r.status_code == 200, r.text
    # December has no seeded Ion gaps? Ion still gaps on Saturdays, so publish
    # without justification must fail if critical conflicts are open.
    r = client.get(f"/api/rosters/{rid}", headers=h).json()
    critical = [c for c in r["conflicts"] if c["severity"] == "critical"]
    r = client.post(f"/api/rosters/{rid}/publish", json={}, headers=h)
    if critical:
        assert r.status_code == 400
        r = client.post(f"/api/rosters/{rid}/publish",
                        json={"exception_justification": "demo exception"},
                        headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "published"
    # published rosters are immutable; a new version is the only edit path
    entry_id = client.get(f"/api/rosters/{rid}", headers=h).json()["entries"][0]["id"]
    r = client.patch(f"/api/rosters/{rid}/entries/{entry_id}",
                     json={"entry_type": "off"}, headers=h)
    assert r.status_code == 400
    r = client.post(f"/api/rosters/{rid}/new-version", headers=h)
    assert r.status_code == 201
    assert r.json()["version"] == 2


def test_leave_approval_revalidates(client, admin_token):
    h = _auth({}, admin_token)
    pending = [x for x in client.get("/api/leave?status=pending", headers=h).json()]
    assert pending, "seed must provide a pending leave request"
    lv = pending[0]
    r = client.patch(f"/api/leave/{lv['id']}",
                     json={"decision": "approved", "comment": "ok"}, headers=h)
    assert r.status_code == 200
    assert r.json()["leave"]["status"] == "approved"


def test_exports_and_dashboard(client, admin_token):
    h = _auth({}, admin_token)
    rid = client.get("/api/rosters", headers=h).json()[0]["id"]
    r = client.get(f"/api/exports/roster.csv?roster_id={rid}", headers=h)
    assert r.status_code == 200
    assert r.text.splitlines()[0].startswith("date,employee_code")
    r = client.get(f"/api/exports/roster.xlsx?roster_id={rid}", headers=h)
    assert r.status_code == 200
    assert "spreadsheet" in r.headers["content-type"]
    r = client.get("/api/dashboard", headers=h)
    assert r.status_code == 200
    d = r.json()
    assert d["active_employees"] == 36
    assert d["active_brands"] == 10


def test_manual_edit_revalidation_flags_violation(client, admin_token):
    h = _auth({}, admin_token)
    rid = client.post("/api/rosters/generate",
                      json={"month": 11, "year": 2026}, headers=h).json()["id"]
    roster = client.get(f"/api/rosters/{rid}", headers=h).json()
    # EMP001 (id 1) is on approved leave Nov 10-12; force a work entry there.
    target = [e for e in roster["entries"]
              if e["employee_id"] == 1 and e["date"] == "2026-11-11"][0]
    r = client.patch(f"/api/rosters/{rid}/entries/{target['id']}",
                     json={"entry_type": "work", "brand_id": 1, "process_id": 1,
                           "reason": "test violation"}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["critical"] >= 1
    roster = client.get(f"/api/rosters/{rid}", headers=h).json()
    assert any(c["type"] == "leave_violation" for c in roster["conflicts"])

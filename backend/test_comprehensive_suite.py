"""Comprehensive Backend Test Suite.

Executes live tests against real PostgreSQL database and Flask backend.
Validates:
1. GET /api/equipment (filters, pagination, compatibility)
2. GET /api/tickets (list, query params)
3. GET /api/safety-alerts (list, query params)
4. GET /api/dashboard/summary
5. GET /api/dashboard/live-feed
6. GET /api/dashboard/asset-health
7. Create inspection
8. Create observation & validate
9. Create & update maintenance ticket (PATCH)
10. Create & update safety alert (PATCH)
11. Complete inspection & lifecycle transitions
12. Generate comprehensive report
13. Error cases & status codes:
    - Nonexistent equipment (404)
    - Nonexistent inspection (404)
    - Invalid ticket status (400)
    - Invalid alert status (400)
    - Invalid observation field/value (400)
    - Invalid inspection lifecycle transitions (409)
    - Duplicate event idempotency
"""

import sys
from app import create_app
from database.connection import test_connection

PASSED = 0
FAILED = 0


def report(name, passed, detail=""):
    global PASSED, FAILED
    if passed:
        PASSED += 1
        print(f"  PASS: {name}")
    else:
        FAILED += 1
        print(f"  FAIL: {name} -- {detail}")


def run_comprehensive_tests():
    print("\n" + "=" * 60)
    print("STARTING LIVE BACKEND COMPREHENSIVE VERIFICATION")
    print("=" * 60 + "\n")

    # Verify real DB connection
    db_ok = test_connection()
    report("PostgreSQL database connection reachable", db_ok)
    if not db_ok:
        print("FATAL: Database connection failed. Aborting tests.")
        sys.exit(1)

    app = create_app()
    client = app.test_client()

    # ---------------------------------------------------------
    # 1. GET /api/equipment
    # ---------------------------------------------------------
    r_eq = client.get("/api/equipment")
    report(
        "GET /api/equipment returns 200 array for backward compatibility",
        r_eq.status_code == 200 and isinstance(r_eq.json, list) and len(r_eq.json) == 20,
        f"status={r_eq.status_code}, count={len(r_eq.json) if isinstance(r_eq.json, list) else None}",
    )
    report(
        "GET /api/equipment includes X-Total-Count header",
        r_eq.headers.get("X-Total-Count") == "20",
        f"headers={r_eq.headers}",
    )

    # Equipment query filters
    r_search = client.get("/api/equipment?search=pump")
    report(
        "GET /api/equipment?search=pump filters correctly",
        r_search.status_code == 200 and all("pump" in (x["asset_code"] + x["name"] + x["equipment_type"]).lower() for x in r_search.json),
        f"count={len(r_search.json)}",
    )

    r_type = client.get("/api/equipment?type=HVAC")
    report(
        "GET /api/equipment?type=HVAC filters by equipment_type",
        r_type.status_code == 200 and all(x["equipment_type"].lower() == "hvac" for x in r_type.json),
        f"count={len(r_type.json)}",
    )

    r_loc = client.get("/api/equipment?location=Building%20A")
    report(
        "GET /api/equipment?location=Building A filters by location",
        r_loc.status_code == 200 and all("building a" in x["location"].lower() for x in r_loc.json),
        f"count={len(r_loc.json)}",
    )

    r_status = client.get("/api/equipment?status=normal")
    report(
        "GET /api/equipment?status=normal filters by dynamic status",
        r_status.status_code == 200 and all(x["status"] == "normal" for x in r_status.json),
        f"count={len(r_status.json)}",
    )

    # Pagination
    r_page = client.get("/api/equipment?page=2&limit=5")
    data_page = r_page.json
    report(
        "GET /api/equipment?page=2&limit=5 returns paginated metadata",
        r_page.status_code == 200
        and data_page.get("success") is True
        and data_page.get("pagination", {}).get("page") == 2
        and data_page.get("pagination", {}).get("limit") == 5
        and len(data_page.get("data", [])) == 5,
        f"pagination={data_page.get('pagination')}",
    )

    # ---------------------------------------------------------
    # 2. GET /api/tickets
    # ---------------------------------------------------------
    r_tix = client.get("/api/tickets")
    report(
        "GET /api/tickets returns 200 list",
        r_tix.status_code == 200 and isinstance(r_tix.json, list),
        f"status={r_tix.status_code}",
    )

    r_tix_open = client.get("/api/tickets?status=open")
    report(
        "GET /api/tickets?status=open filters by status",
        r_tix_open.status_code == 200 and all(t["status"] == "open" for t in r_tix_open.json),
        f"count={len(r_tix_open.json)}",
    )

    # ---------------------------------------------------------
    # 3. GET /api/safety-alerts
    # ---------------------------------------------------------
    r_alr = client.get("/api/safety-alerts")
    report(
        "GET /api/safety-alerts returns 200 list",
        r_alr.status_code == 200 and isinstance(r_alr.json, list),
        f"status={r_alr.status_code}",
    )

    r_alr_open = client.get("/api/safety-alerts?status=open")
    report(
        "GET /api/safety-alerts?status=open filters by status",
        r_alr_open.status_code == 200 and all(a["status"] == "open" for a in r_alr_open.json),
        f"count={len(r_alr_open.json)}",
    )

    # ---------------------------------------------------------
    # 4. GET /api/dashboard/summary
    # ---------------------------------------------------------
    r_dash_sum = client.get("/api/dashboard/summary")
    sum_data = r_dash_sum.json
    report(
        "GET /api/dashboard/summary returns exact schema with database values",
        r_dash_sum.status_code == 200
        and sum_data.get("success") is True
        and "active_inspections" in sum_data.get("data", {})
        and "completed_today" in sum_data.get("data", {})
        and "open_work_orders" in sum_data.get("data", {})
        and "safety_hazards" in sum_data.get("data", {}),
        f"summary_data={sum_data}",
    )

    # ---------------------------------------------------------
    # 5. GET /api/dashboard/live-feed
    # ---------------------------------------------------------
    r_dash_feed = client.get("/api/dashboard/live-feed")
    feed_data = r_dash_feed.json
    feed_items = feed_data.get("data", [])
    report(
        "GET /api/dashboard/live-feed returns inspection activity feed",
        r_dash_feed.status_code == 200
        and feed_data.get("success") is True
        and isinstance(feed_items, list)
        and (len(feed_items) == 0 or all(
            "inspection_id" in item
            and "equipment_id" in item
            and "equipment_name" in item
            and "status" in item
            and "started_time" in item
            for item in feed_items
        )),
        f"feed_count={len(feed_items)}",
    )

    # ---------------------------------------------------------
    # 6. GET /api/dashboard/asset-health
    # ---------------------------------------------------------
    r_dash_health = client.get("/api/dashboard/asset-health")
    health_data = r_dash_health.json
    health_items = health_data.get("data", [])
    report(
        "GET /api/dashboard/asset-health returns dynamic health states",
        r_dash_health.status_code == 200
        and health_data.get("success") is True
        and len(health_items) == 20
        and any(x["status"] in ("safety_alert", "maintenance_required") for x in health_items)
        and any(x["status"] == "normal" for x in health_items),
        f"count={len(health_items)}",
    )

    # ---------------------------------------------------------
    # 7. Create Inspection
    # ---------------------------------------------------------
    # Use PUMP-001 (id 6) for our live test workflow
    r_create_insp = client.post("/api/inspections", json={"equipment_id": 6, "inspection_type": "routine"})
    insp_info = r_create_insp.json
    test_insp_id = insp_info.get("inspection_id")
    report(
        "POST /api/inspections creates new inspection in 'started' state",
        r_create_insp.status_code == 201
        and insp_info.get("success") is True
        and isinstance(test_insp_id, int)
        and insp_info.get("status") == "started",
        f"status={r_create_insp.status_code}, data={insp_info}",
    )

    # ---------------------------------------------------------
    # 8. Create Observation & Validate
    # ---------------------------------------------------------
    # Save a normal temperature observation (PUMP-001 range is 2-25 C)
    r_obs_normal = client.post("/api/observations", json={
        "inspection_id": test_insp_id,
        "field_name": "temperature",
        "value": "15",
        "unit": "C",
        "evidence_text": "Temperature 15 C is stable and normal",
    })
    normal_obs_data = r_obs_normal.json
    report(
        "POST /api/observations validates normal reading (15 C) as 'normal'",
        r_obs_normal.status_code == 201
        and normal_obs_data.get("success") is True
        and normal_obs_data.get("validation", {}).get("status") == "normal",
        f"data={normal_obs_data}",
    )

    # Save out_of_range observation (vibration 12 mm/s, PUMP-001 max is 7 mm/s)
    # This also contains keyword 'smoke' to test automated safety alert!
    r_obs_oor = client.post("/api/observations", json={
        "inspection_id": test_insp_id,
        "field_name": "vibration",
        "value": "12",
        "unit": "mm_s",
        "evidence_text": "Vibration gauge shows 12 mm/s and smoke observed near bearing",
    })
    oor_data = r_obs_oor.json
    report(
        "POST /api/observations validates out_of_range reading (12 mm/s)",
        r_obs_oor.status_code == 201
        and oor_data.get("validation", {}).get("status") == "out_of_range",
        f"val={oor_data.get('validation')}",
    )

    # Verify automated ticket was created for out_of_range observation
    r_insp_tix = client.get(f"/api/inspections/{test_insp_id}/tickets")
    insp_tix = r_insp_tix.json
    auto_ticket = next((t for t in insp_tix if "vibration" in t["issue"].lower()), None)
    report(
        "Automated maintenance ticket created upon out_of_range validation",
        auto_ticket is not None and auto_ticket["status"] == "open",
        f"tickets={insp_tix}",
    )

    # Verify automated safety alert was created due to 'smoke' keyword
    r_insp_alrs = client.get(f"/api/inspections/{test_insp_id}/alerts")
    insp_alrs = r_insp_alrs.json
    auto_alert = next((a for a in insp_alrs if "smoke" in a["hazard"].lower()), None)
    report(
        "Automated safety alert created upon hazard keyword detection",
        auto_alert is not None and auto_alert["status"] == "open",
        f"alerts={insp_alrs}",
    )

    # ---------------------------------------------------------
    # 9. Create & Update Ticket (PATCH)
    # ---------------------------------------------------------
    # Explicit ticket creation
    r_exp_tix = client.post("/api/tickets", json={
        "inspection_id": test_insp_id,
        "issue": "Oil seal replacement scheduled",
        "priority": "medium",
    })
    report(
        "POST /api/tickets creates explicit maintenance ticket",
        r_exp_tix.status_code == 201 and r_exp_tix.json.get("success") is True,
        f"res={r_exp_tix.json}",
    )
    exp_ticket_id = r_exp_tix.json.get("ticket", {}).get("id")

    # PATCH ticket status
    r_patch_tix = client.patch(f"/api/tickets/{exp_ticket_id}", json={
        "status": "in_progress",
        "priority": "high",
    })
    patch_tix_data = r_patch_tix.json
    report(
        "PATCH /api/tickets/<id> updates status to 'in_progress' and priority to 'high'",
        r_patch_tix.status_code == 200
        and patch_tix_data.get("ticket", {}).get("status") == "in_progress"
        and patch_tix_data.get("ticket", {}).get("priority") == "high",
        f"data={patch_tix_data}",
    )

    # ---------------------------------------------------------
    # 10. Create & Update Safety Alert (PATCH)
    # ---------------------------------------------------------
    # Explicit alert creation
    r_exp_alr = client.post("/api/safety-alerts", json={
        "inspection_id": test_insp_id,
        "hazard": "Slippery puddle near foundation",
        "severity": "medium",
    })
    report(
        "POST /api/safety-alerts creates explicit safety alert",
        r_exp_alr.status_code == 201 and r_exp_alr.json.get("success") is True,
        f"res={r_exp_alr.json}",
    )
    exp_alert_id = r_exp_alr.json.get("alert", {}).get("id")

    # PATCH alert status to resolved
    r_patch_alr = client.patch(f"/api/safety-alerts/{exp_alert_id}", json={
        "status": "resolved",
    })
    patch_alr_data = r_patch_alr.json
    report(
        "PATCH /api/safety-alerts/<id> updates status to 'resolved' with resolved_at timestamp",
        r_patch_alr.status_code == 200
        and patch_alr_data.get("alert", {}).get("status") == "resolved"
        and patch_alr_data.get("alert", {}).get("resolved_at") is not None,
        f"data={patch_alr_data}",
    )

    # ---------------------------------------------------------
    # 11. Complete Inspection & Lifecycle Transitions
    # ---------------------------------------------------------
    r_comp = client.post(f"/api/inspections/{test_insp_id}/complete", json={
        "summary": "Pump inspection completed with repairs scheduled."
    })
    comp_data = r_comp.json
    report(
        "POST /api/inspections/<id>/complete transitions status to 'completed'",
        r_comp.status_code == 200
        and comp_data.get("success") is True
        and comp_data.get("inspection", {}).get("status") == "completed"
        and comp_data.get("inspection", {}).get("completed_at") is not None,
        f"data={comp_data}",
    )

    # Test lifecycle status update on another inspection (cancel workflow)
    r_insp_cancel = client.post("/api/inspections", json={"equipment_id": 1, "inspection_type": "emergency"})
    cancel_id = r_insp_cancel.json["inspection_id"]
    r_patch_cancel = client.patch(f"/api/inspections/{cancel_id}/status", json={
        "status": "cancelled",
        "summary": "Inspection cancelled due to plant shutdown",
    })
    report(
        "PATCH /api/inspections/<id>/status transitions status to 'cancelled'",
        r_patch_cancel.status_code == 200
        and r_patch_cancel.json.get("inspection", {}).get("status") == "cancelled",
        f"res={r_patch_cancel.json}",
    )

    # ---------------------------------------------------------
    # 12. Generate Report
    # ---------------------------------------------------------
    r_rep = client.get(f"/api/reports/{test_insp_id}")
    rep_data = r_rep.json
    report(
        "GET /api/reports/<id> returns complete integrated inspection report",
        r_rep.status_code == 200
        and "inspection" in rep_data
        and "equipment" in rep_data
        and "checklist" in rep_data
        and "observations" in rep_data
        and "maintenance_tickets" in rep_data
        and "safety_alerts" in rep_data
        and "summary" in rep_data
        and rep_data["summary"]["maintenance_ticket_count"] >= 1
        and rep_data["summary"]["safety_alert_count"] >= 1
        and rep_data["inspection"]["duration"] is not None,
        f"report_keys={list(rep_data.keys())}",
    )

    # ---------------------------------------------------------
    # 13. Error Cases & Robustness
    # ---------------------------------------------------------
    # Nonexistent equipment (404)
    r_err_eq = client.get("/api/equipment/999999")
    report(
        "Nonexistent equipment returns clean 404 JSON",
        r_err_eq.status_code == 404
        and r_err_eq.json.get("success") is False
        and r_err_eq.json.get("error", {}).get("code") == "RESOURCE_NOT_FOUND",
        f"res={r_err_eq.json}",
    )

    # Nonexistent inspection (404)
    r_err_insp = client.get("/api/inspections/999999")
    report(
        "Nonexistent inspection returns clean 404 JSON",
        r_err_insp.status_code == 404
        and r_err_insp.json.get("success") is False
        and r_err_insp.json.get("error", {}).get("code") == "RESOURCE_NOT_FOUND",
        f"res={r_err_insp.json}",
    )

    # Invalid ticket status (400)
    r_err_tix_status = client.patch(f"/api/tickets/{exp_ticket_id}", json={"status": "invalid_status_xyz"})
    report(
        "Invalid ticket status returns clean 400 Bad Request",
        r_err_tix_status.status_code == 400 and r_err_tix_status.json.get("success") is False,
        f"res={r_err_tix_status.json}",
    )

    # Invalid alert status (400)
    r_err_alr_status = client.patch(f"/api/safety-alerts/{exp_alert_id}", json={"status": "bogus_status"})
    report(
        "Invalid safety alert status returns clean 400 Bad Request",
        r_err_alr_status.status_code == 400 and r_err_alr_status.json.get("success") is False,
        f"res={r_err_alr_status.json}",
    )

    # Invalid observation field on active inspection (400 Bad Request)
    r_active_insp = client.post("/api/inspections", json={"equipment_id": 6, "inspection_type": "routine"})
    active_insp_id = r_active_insp.json["inspection_id"]
    r_err_obs = client.post("/api/observations", json={
        "inspection_id": active_insp_id,
        "field_name": "nonexistent_field_not_on_equipment",
        "value": "100",
    })
    report(
        "Invalid observation field returns clean 400 Bad Request",
        r_err_obs.status_code == 400 and r_err_obs.json.get("success") is False,
        f"res={r_err_obs.json}",
    )

    # Adding observation to completed inspection returns 409 Conflict
    r_err_obs_comp = client.post("/api/observations", json={
        "inspection_id": test_insp_id,
        "field_name": "temperature",
        "value": "15",
    })
    report(
        "Adding observation to completed inspection returns clean 409 Conflict",
        r_err_obs_comp.status_code == 409 and r_err_obs_comp.json.get("success") is False,
        f"res={r_err_obs_comp.json}",
    )

    # Invalid inspection transitions:
    # 1. Completed inspection cannot be completed again (409)
    r_err_comp_comp = client.post(f"/api/inspections/{test_insp_id}/complete", json={})
    report(
        "Invalid transition (completed -> completed) returns clean 409 Conflict",
        r_err_comp_comp.status_code == 409
        and r_err_comp_comp.json.get("success") is False
        and r_err_comp_comp.json.get("error", {}).get("code") == "STATE_CONFLICT",
        f"res={r_err_comp_comp.json}",
    )

    # 2. Completed inspection cannot transition to in_progress (409)
    r_err_comp_prog = client.patch(f"/api/inspections/{test_insp_id}/status", json={"status": "in_progress"})
    report(
        "Invalid transition (completed -> in_progress) returns clean 409 Conflict",
        r_err_comp_prog.status_code == 409
        and r_err_comp_prog.json.get("success") is False
        and r_err_comp_prog.json.get("error", {}).get("code") == "STATE_CONFLICT",
        f"res={r_err_comp_prog.json}",
    )

    # 3. Cancelled inspection cannot transition to completed (409)
    r_err_canc_comp = client.post(f"/api/inspections/{cancel_id}/complete", json={})
    report(
        "Invalid transition (cancelled -> completed) returns clean 409 Conflict",
        r_err_canc_comp.status_code == 409
        and r_err_canc_comp.json.get("success") is False
        and r_err_canc_comp.json.get("error", {}).get("code") == "STATE_CONFLICT",
        f"res={r_err_canc_comp.json}",
    )

    # Duplicate ticket idempotency
    r_dup_tix = client.post("/api/tickets", json={
        "inspection_id": test_insp_id,
        "issue": "Oil seal replacement scheduled",
    })
    report(
        "Duplicate ticket creation is idempotent (returns duplicate=True and existing ticket)",
        r_dup_tix.status_code == 200
        and r_dup_tix.json.get("duplicate") is True
        and r_dup_tix.json.get("ticket", {}).get("id") == exp_ticket_id,
        f"res={r_dup_tix.json}",
    )

    # Duplicate alert idempotency
    r_dup_alr = client.post("/api/safety-alerts", json={
        "inspection_id": test_insp_id,
        "hazard": "Slippery puddle near foundation",
    })
    report(
        "Duplicate safety alert creation is idempotent (returns duplicate=True and existing alert)",
        r_dup_alr.status_code == 200
        and r_dup_alr.json.get("duplicate") is True
        and r_dup_alr.json.get("alert", {}).get("id") == exp_alert_id,
        f"res={r_dup_alr.json}",
    )

    print("\n" + "=" * 60)
    print(f"COMPREHENSIVE TEST RESULTS: {PASSED} PASSED | {FAILED} FAILED")
    print("=" * 60 + "\n")

    if FAILED > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_comprehensive_tests()

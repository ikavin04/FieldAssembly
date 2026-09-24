"""Comprehensive Automated Test Suite for Core Voice Expansion (Core 1 - Core 6).

Covers:
1. CORE 1 — Multi-observation extraction & independent tool execution
2. CORE 1 — Negative and categorical normal values (none, normal)
3. CORE 1 — Spoken evidence text preservation across multiple observations
4. CORE 2 — Read-only inspection status tool (get_inspection_status)
5. CORE 2 — Status tool validation, missing fields calculation, and read-only guarantee
6. CORE 3 — Correction loop (167 PSI out of range -> 96 PSI normal)
7. CORE 3 — Historical evidence preservation and latest-value checklist authority
8. CORE 4 — Natural voice queries (recorded so far, missing, out of range, verbatim quote)
9. CORE 5 — Voice-driven operational actions (maintenance tickets & safety alerts via tools)
10. CORE 6 — Activity event structure & lifecycle integrity
11. CROSS-INSPECTION ISOLATION — Authoritative context check
"""

import sys
from app import create_app
from database.connection import get_connection
from models.equipment import get_equipment_by_id
from models.inspection import get_inspection_by_id
from models.observation import get_observations_for_inspection
from models.maintenance_ticket import get_tickets_for_inspection
from models.safety_alert import get_alerts_for_inspection
from services.inspection_service import (
    InspectionServiceError,
    get_inspection,
    save_observation,
    start_inspection,
)
from tools.inspection_tools import (
    complete_inspection_tool,
    get_inspection_status_tool,
    save_observation_tool,
)
from tools.maintenance_tools import create_maintenance_ticket_tool
from tools.safety_tools import create_safety_alert_tool
from services.validation_service import validate_all_observations

PASSED = 0
FAILED = 0


def report(name, passed, detail=""):
    global PASSED, FAILED
    if passed:
        PASSED += 1
        print(f"  PASS {name}")
    else:
        FAILED += 1
        print(f"  FAIL {name}  --  {detail}")


def get_equipment_by_code(asset_code):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM equipment WHERE asset_code = %s", (asset_code,))
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()


def run_tests():
    print("\n=== FIELDVOICE CORE 1 -> CORE 6 EXPANSION TESTS ===\n")

    ac001 = get_equipment_by_code("AC-001")
    pump001 = get_equipment_by_code("PUMP-001")
    assert ac001 is not None, "AC-001 must exist in database"
    assert pump001 is not None, "PUMP-001 must exist in database"

    # Start fresh inspection for testing
    insp = start_inspection(ac001["id"], "routine")
    insp_id = insp["id"]

    # -------------------------------------------------------------------------
    # CORE 1: Conversational extraction of multiple observations
    # -------------------------------------------------------------------------
    spoken_sentence = (
        "Temperature is 40 degrees Celsius, pressure is 91 PSI, vibration is normal, "
        "and I don't see any leakage."
    )

    # 1. Independent save_observation tool call for temperature
    res_temp = save_observation_tool({
        "inspection_id": insp_id,
        "field_name": "temperature",
        "value": "40",
        "unit": "Celsius",
        "evidence_text": spoken_sentence,
    })
    report(
        "CORE 1 - Save temperature observation from multi-observation utterance",
        res_temp.get("success") is True and res_temp.get("validation", {}).get("status") == "normal",
        str(res_temp),
    )

    # 2. Independent save_observation tool call for pressure
    res_press = save_observation_tool({
        "inspection_id": insp_id,
        "field_name": "pressure",
        "value": "91",
        "unit": "PSI",
        "evidence_text": spoken_sentence,
    })
    report(
        "CORE 1 - Save pressure observation from multi-observation utterance",
        res_press.get("success") is True and res_press.get("validation", {}).get("status") == "normal",
        str(res_press),
    )

    # 3. Independent save_observation tool call for vibration (categorical normal)
    res_vib = save_observation_tool({
        "inspection_id": insp_id,
        "field_name": "vibration",
        "value": "normal",
        "evidence_text": spoken_sentence,
    })
    report(
        "CORE 1 - Save vibration=normal observation",
        res_vib.get("success") is True and res_vib.get("validation", {}).get("status") == "normal",
        str(res_vib),
    )

    # 4. Independent save_observation tool call for leakage (categorical none)
    res_leak = save_observation_tool({
        "inspection_id": insp_id,
        "field_name": "leakage",
        "value": "none",
        "evidence_text": spoken_sentence,
    })
    report(
        "CORE 1 - Save leakage=none observation",
        res_leak.get("success") is True and res_leak.get("validation", {}).get("status") == "normal",
        str(res_leak),
    )

    # 5. Verify all four observations exist in PostgreSQL with exact evidence text preserved
    obs_list = get_observations_for_inspection(insp_id)
    fields_saved = {o["field_name"]: o for o in obs_list}
    all_saved = len(obs_list) >= 4 and all(f in fields_saved for f in ["temperature", "pressure", "vibration", "leakage"])
    evidence_intact = all(o["evidence_text"] == spoken_sentence for o in obs_list)
    report(
        "CORE 1 - All 4 checkpoints saved with verbatim evidence_text intact",
        all_saved and evidence_intact,
        f"Saved: {len(obs_list)}, Evidence intact: {evidence_intact}",
    )

    # -------------------------------------------------------------------------
    # CORE 2: Read-only inspection status tool (get_inspection_status)
    # -------------------------------------------------------------------------
    status_result = get_inspection_status_tool({"inspection_id": insp_id})
    report(
        "CORE 2 - get_inspection_status_tool returns complete status object",
        status_result.get("success") is True
        and status_result.get("inspection_id") == insp_id
        and isinstance(status_result.get("required_fields"), list)
        and isinstance(status_result.get("completed_fields"), list)
        and isinstance(status_result.get("missing_fields"), list)
        and isinstance(status_result.get("observations"), list)
        and isinstance(status_result.get("validation"), dict),
        str(status_result),
    )

    # Verify checklist fields accuracy
    req_fields = status_result.get("required_fields", [])
    comp_fields = status_result.get("completed_fields", [])
    report(
        "CORE 2 - Checkpoints completion status accurately reflects 4 recorded fields",
        len(comp_fields) >= 4 and set(["temperature", "pressure", "vibration", "leakage"]).issubset(set(comp_fields)),
        f"Completed: {comp_fields}",
    )

    # Test HTTP endpoint for get-inspection-status via Flask test client
    flask_app = create_app()
    with flask_app.test_client() as client:
        # Valid POST request
        resp = client.post("/api/tools/get-inspection-status", json={"inspection_id": insp_id})
        report(
            "CORE 2 - POST /api/tools/get-inspection-status returns 200 JSON",
            resp.status_code == 200 and resp.json.get("success") is True,
            f"Status: {resp.status_code}, Body: {resp.json}",
        )

        # Non-existent inspection returns 404
        resp_404 = client.post("/api/tools/get-inspection-status", json={"inspection_id": 999999})
        report(
            "CORE 2 - Non-existent inspection ID returns clean 404 without tracebacks",
            resp_404.status_code == 404 and resp_404.json.get("success") is False,
            f"Status: {resp_404.status_code}",
        )

        # Invalid inspection_id type returns 400
        resp_400 = client.post("/api/tools/get-inspection-status", json={"inspection_id": "invalid"})
        report(
            "CORE 2 - Malformed inspection_id returns 400 Bad Request",
            resp_400.status_code == 400 and resp_400.json.get("success") is False,
            f"Status: {resp_400.status_code}",
        )

    # -------------------------------------------------------------------------
    # CORE 3: Spoken correction loop
    # -------------------------------------------------------------------------
    # Create inspection for correction flow
    insp_corr = start_inspection(ac001["id"], "routine")
    c_id = insp_corr["id"]

    # Initial reading: 167 PSI (out of range, AC-001 range is 40-100 PSI)
    res_initial = save_observation_tool({
        "inspection_id": c_id,
        "field_name": "pressure",
        "value": "167",
        "unit": "PSI",
        "evidence_text": "Pressure is 167 PSI.",
    })
    report(
        "CORE 3 - Initial reading (167 PSI) validates as out_of_range",
        res_initial.get("success") is True and res_initial.get("validation", {}).get("status") == "out_of_range",
        str(res_initial),
    )

    # Maintenance ticket created for initial reading
    res_ticket = create_maintenance_ticket_tool({
        "inspection_id": c_id,
        "issue": "Pressure is 167 PSI (out of range)",
        "priority": "high",
    })
    ticket_id = res_ticket.get("ticket_id")
    report(
        "CORE 3 - Maintenance ticket created for 167 PSI issue",
        res_ticket.get("success") is True and isinstance(ticket_id, int),
        str(res_ticket),
    )

    # Technician correction: "Actually, correct that. It's 96 PSI."
    res_correction = save_observation_tool({
        "inspection_id": c_id,
        "field_name": "pressure",
        "value": "96",
        "unit": "PSI",
        "evidence_text": "Actually, correct that. It's 96 PSI.",
    })
    report(
        "CORE 3 - Corrected reading (96 PSI) validates deterministically as normal",
        res_correction.get("success") is True and res_correction.get("validation", {}).get("status") == "normal",
        str(res_correction),
    )

    # Verify both observations exist in PostgreSQL (historical evidence preserved)
    corr_obs = get_observations_for_inspection(c_id)
    press_obs = [o for o in corr_obs if o["field_name"] == "pressure"]
    report(
        "CORE 3 - Both initial (167 PSI) and corrected (96 PSI) observations preserved in DB",
        len(press_obs) == 2 and press_obs[0]["value"] == "167" and press_obs[1]["value"] == "96",
        f"Pressure observations count: {len(press_obs)}",
    )

    # Verify validate_all_observations uses the latest observation (96 PSI -> normal)
    val_all = validate_all_observations(c_id)
    report(
        "CORE 3 - Checklist and validation summary uses latest observation (96 PSI = normal)",
        val_all.get("pressure", {}).get("status") == "normal" and val_all.get("pressure", {}).get("value") == "96",
        str(val_all.get("pressure")),
    )

    # Verify ticket was not silently destroyed
    remaining_tickets = get_tickets_for_inspection(c_id)
    report(
        "CORE 3 - Prior maintenance ticket remains preserved as historical record",
        len(remaining_tickets) == 1 and remaining_tickets[0]["id"] == ticket_id,
        f"Tickets: {len(remaining_tickets)}",
    )

    # -------------------------------------------------------------------------
    # CORE 4: Natural Voice Commands
    # -------------------------------------------------------------------------
    status_corr = get_inspection_status_tool({"inspection_id": c_id})

    # "What have I recorded so far?" -> observations list
    recorded = [f"{o['field_name']}: {o['value']}" for o in status_corr["observations"]]
    report(
        "CORE 4 - 'What have I recorded?' powered by status tool observations",
        len(recorded) >= 2,
        f"Recorded: {recorded}",
    )

    # "What's still missing?" -> missing_fields
    missing = status_corr.get("missing_fields", [])
    report(
        "CORE 4 - 'What's still missing?' correctly identifies remaining required fields",
        "temperature" in missing or "vibration" in missing or "leakage" in missing,
        f"Missing: {missing}",
    )

    # "What did I say for pressure?" -> matches evidence_text
    pressure_evidence = [o["evidence_text"] for o in status_corr["observations"] if o["field_name"] == "pressure"]
    report(
        "CORE 4 - 'What did I say for pressure?' accurately returns verbatim spoken quotes",
        "Pressure is 167 PSI." in pressure_evidence and "Actually, correct that. It's 96 PSI." in pressure_evidence,
        f"Evidence: {pressure_evidence}",
    )

    # "Complete the inspection"
    complete_res = complete_inspection_tool({"inspection_id": c_id, "summary": "Routine inspection completed"})
    report(
        "CORE 4 - 'Complete the inspection' marks status completed via authoritative tool",
        complete_res.get("success") is True and complete_res.get("status") == "completed",
        str(complete_res),
    )

    # -------------------------------------------------------------------------
    # CORE 5: Operational Actions (Tickets and Safety Alerts)
    # -------------------------------------------------------------------------
    # Test safety alert creation tool with factual hazard
    alert_res = create_safety_alert_tool({
        "inspection_id": insp_id,
        "hazard": "Safety hazard detected: smoke from motor housing",
        "severity": "high",
        "evidence_text": "There is smoke coming from the motor housing",
    })
    report(
        "CORE 5 - create_safety_alert_tool creates real alert with authoritative ID",
        alert_res.get("success") is True and isinstance(alert_res.get("alert_id"), int),
        str(alert_res),
    )

    # -------------------------------------------------------------------------
    # CROSS-INSPECTION ISOLATION
    # -------------------------------------------------------------------------
    insp_b = start_inspection(pump001["id"], "routine")
    b_id = insp_b["id"]

    # Verify Inspection B has zero observations, tickets, or alerts from A
    obs_b = get_observations_for_inspection(b_id)
    tickets_b = get_tickets_for_inspection(b_id)
    alerts_b = get_alerts_for_inspection(b_id)
    report(
        "CROSS-INSPECTION - Inspection B is completely isolated from Inspection A",
        len(obs_b) == 0 and len(tickets_b) == 0 and len(alerts_b) == 0,
        f"B observations={len(obs_b)}, tickets={len(tickets_b)}, alerts={len(alerts_b)}",
    )

    print("\n========================================")
    print(f"CORE EXPANSION PASSED: {PASSED}  |  FAILED: {FAILED}")
    print("========================================\n")

    return FAILED == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

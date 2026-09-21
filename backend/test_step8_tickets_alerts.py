"""Step 8 — Maintenance Tickets + Safety Alerts Test Suite.

Covers:
1. Create maintenance ticket for valid inspection.
2. Retrieve maintenance tickets.
3. Create safety alert for valid inspection.
4. Retrieve safety alerts.
5. Invalid inspection -> 404.
6. Invalid observation reference -> 404.
7. Malformed input -> 400.
8. Duplicate ticket idempotency.
9. Duplicate alert idempotency.
10. Cross-inspection context integrity (Inspection A vs B isolation).
11. Evidence and reference traceability integrity.
12. Deterministic triggers:
    - 137 PSI triggers maintenance ticket need, but NOT safety condition.
    - 151 PSI triggers safety condition (> 150% of 100 PSI max limit).
    - Keyword matching on evidence (e.g. "gas leak", "smoke").
13. Step 7 regression: validation & 3-tuple return contract still work.
"""

import sys
import traceback
from database.connection import get_connection
from models.equipment import get_equipment_by_id
from models.inspection import create_inspection, get_inspection_by_id
from services.inspection_service import get_inspection, save_observation, start_inspection
from services.maintenance_ticket_service import (
	MaintenanceTicketServiceError,
	create_ticket,
	evaluate_ticket_need,
	get_ticket,
	get_tickets,
)
from services.safety_alert_service import (
	SafetyAlertServiceError,
	create_alert,
	evaluate_safety_condition,
	get_alert,
	get_alerts,
)
from services.validation_service import validate_observation

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


def get_ac001():
	conn = get_connection()
	try:
		cur = conn.cursor()
		cur.execute("SELECT * FROM equipment WHERE asset_code = 'AC-001'")
		return cur.fetchone()
	finally:
		cur.close()
		conn.close()


def get_pump001():
	conn = get_connection()
	try:
		cur = conn.cursor()
		cur.execute("SELECT * FROM equipment WHERE asset_code = 'PUMP-001'")
		return cur.fetchone()
	finally:
		cur.close()
		conn.close()


def run_tests():
	print("\n=== STEP 8 MAINTENANCE TICKETS & SAFETY ALERTS TESTS ===\n")
	ac001 = get_ac001()
	pump001 = get_pump001()

	if not ac001 or not pump001:
		print("ERROR: Seed equipment AC-001 or PUMP-001 missing.")
		sys.exit(1)

	# 1. Create maintenance ticket for valid inspection
	insp_a = start_inspection(ac001["id"], "routine")
	ticket_a, is_dup = create_ticket(
		inspection_id=insp_a["id"],
		issue="Pressure relief valve stuck at high reading",
		priority="high",
	)
	report(
		"TEST 1 - Create maintenance ticket for valid inspection",
		ticket_a is not None and ticket_a["id"] > 0 and not is_dup and ticket_a["inspection_id"] == insp_a["id"] and ticket_a["equipment_id"] == ac001["id"],
		f"ticket={ticket_a}",
	)

	# 2. Retrieve maintenance tickets
	tickets = get_tickets(inspection_id=insp_a["id"])
	single = get_ticket(ticket_a["id"])
	report(
		"TEST 2 - Retrieve maintenance tickets (list and single)",
		len(tickets) >= 1 and any(t["id"] == ticket_a["id"] for t in tickets) and single["id"] == ticket_a["id"] and single.get("equipment_asset_code") == "AC-001",
		f"tickets_len={len(tickets)}, single={single}",
	)

	# 3. Create safety alert for valid inspection
	alert_a, is_dup_alert = create_alert(
		inspection_id=insp_a["id"],
		hazard="Burning smell near motor housing",
		severity="high",
		evidence_text="Technician reported strong burning smell coming from the unit.",
	)
	report(
		"TEST 3 - Create safety alert for valid inspection",
		alert_a is not None and alert_a["id"] > 0 and not is_dup_alert and alert_a["inspection_id"] == insp_a["id"] and alert_a["equipment_id"] == ac001["id"],
		f"alert={alert_a}",
	)

	# 4. Retrieve safety alerts
	alerts = get_alerts(inspection_id=insp_a["id"])
	single_alert = get_alert(alert_a["id"])
	report(
		"TEST 4 - Retrieve safety alerts (list and single)",
		len(alerts) >= 1 and any(a["id"] == alert_a["id"] for a in alerts) and single_alert["id"] == alert_a["id"] and single_alert.get("equipment_asset_code") == "AC-001" and single_alert.get("evidence_text") is not None,
		f"alerts_len={len(alerts)}, single_alert={single_alert}",
	)

	# 5. Invalid inspection -> 404
	ticket_404_passed = False
	try:
		create_ticket(inspection_id=999999, issue="Phantom issue")
	except MaintenanceTicketServiceError as exc:
		ticket_404_passed = exc.status_code == 404

	alert_404_passed = False
	try:
		create_alert(inspection_id=999999, hazard="Phantom hazard")
	except SafetyAlertServiceError as exc:
		alert_404_passed = exc.status_code == 404

	report(
		"TEST 5 - Invalid inspection returns 404",
		ticket_404_passed and alert_404_passed,
		f"ticket_404={ticket_404_passed}, alert_404={alert_404_passed}",
	)

	# 6. Invalid observation reference -> 404
	obs_404_ticket_passed = False
	try:
		create_ticket(inspection_id=insp_a["id"], issue="", observation_id=999999)
	except MaintenanceTicketServiceError as exc:
		obs_404_ticket_passed = exc.status_code == 404

	obs_404_alert_passed = False
	try:
		create_alert(inspection_id=insp_a["id"], hazard="", observation_id=999999)
	except SafetyAlertServiceError as exc:
		obs_404_alert_passed = exc.status_code == 404

	report(
		"TEST 6 - Invalid observation reference returns 404",
		obs_404_ticket_passed and obs_404_alert_passed,
		f"ticket_obs_404={obs_404_ticket_passed}, alert_obs_404={obs_404_alert_passed}",
	)

	# 7. Malformed input -> 400
	malformed_ticket = False
	try:
		create_ticket(inspection_id=insp_a["id"], issue="   ")
	except MaintenanceTicketServiceError as exc:
		malformed_ticket = exc.status_code == 400

	malformed_alert = False
	try:
		create_alert(inspection_id=insp_a["id"], hazard="   ")
	except SafetyAlertServiceError as exc:
		malformed_alert = exc.status_code == 400

	report(
		"TEST 7 - Malformed input (empty issue/hazard) returns 400",
		malformed_ticket and malformed_alert,
		f"ticket_400={malformed_ticket}, alert_400={malformed_alert}",
	)

	# 8. Duplicate ticket behavior
	dup_ticket, is_dup_2 = create_ticket(
		inspection_id=insp_a["id"],
		issue="Pressure relief valve stuck at high reading",
		priority="high",
	)
	report(
		"TEST 8 - Duplicate ticket returns existing record with is_duplicate=True",
		is_dup_2 is True and dup_ticket["id"] == ticket_a["id"],
		f"dup_ticket={dup_ticket}, is_dup_2={is_dup_2}",
	)

	# 9. Duplicate alert behavior
	dup_alert, is_dup_alert_2 = create_alert(
		inspection_id=insp_a["id"],
		hazard="Burning smell near motor housing",
		severity="high",
	)
	report(
		"TEST 9 - Duplicate alert returns existing record with is_duplicate=True",
		is_dup_alert_2 is True and dup_alert["id"] == alert_a["id"],
		f"dup_alert={dup_alert}, is_dup_alert_2={is_dup_alert_2}",
	)

	# 10. Inspection context integrity across two inspections (Inspection A vs B isolation)
	insp_b = start_inspection(pump001["id"], "routine")
	tickets_b = get_tickets(inspection_id=insp_b["id"])
	alerts_b = get_alerts(inspection_id=insp_b["id"])
	report(
		"TEST 10 - Inspection context integrity: Inspection B has 0 tickets/alerts created from A",
		len(tickets_b) == 0 and len(alerts_b) == 0,
		f"tickets_b={len(tickets_b)}, alerts_b={len(alerts_b)}",
	)

	# 11. Evidence traceability integrity
	obs, is_dup_obs, val = save_observation(
		inspection_id=insp_a["id"],
		field_name="pressure",
		value="137",
		unit="PSI",
		evidence_text="137 PSI read from gauge.",
	)
	ticket_from_obs, _ = create_ticket(
		inspection_id=insp_a["id"],
		observation_id=obs["id"],
	)
	report(
		"TEST 11 - Evidence traceability: Ticket derived from observation inherits context",
		ticket_from_obs is not None and "pressure" in ticket_from_obs["issue"].lower() and "137" in ticket_from_obs["issue"],
		f"issue={ticket_from_obs['issue']}",
	)

	# 12. Deterministic trigger logic:
	# AC-001 operating limits: pressure min=40, max=100
	# - 137 PSI: out_of_range -> warrants maintenance ticket, but NOT safety condition (137 <= 100 * 1.5 = 150)
	# - 151 PSI: warrants safety condition (> 150)
	val_137 = validate_observation(ac001["id"], "pressure", "137", "PSI")
	ticket_need_137 = evaluate_ticket_need(val_137)
	safety_137 = evaluate_safety_condition(ac001, "pressure", "137", "PSI")

	val_151 = validate_observation(ac001["id"], "pressure", "151", "PSI")
	ticket_need_151 = evaluate_ticket_need(val_151)
	safety_151 = evaluate_safety_condition(ac001, "pressure", "151", "PSI")

	# Keyword hazard check:
	safety_kw = evaluate_safety_condition(ac001, "leakage", "none", evidence_text="there is a severe gas leak in the corridor")

	report(
		"TEST 12a - Deterministic trigger: 137 PSI triggers maintenance ticket need",
		ticket_need_137 is True and val_137["status"] == "out_of_range",
		f"val_137={val_137}",
	)
	report(
		"TEST 12b - Deterministic trigger: 137 PSI does NOT trigger safety condition (<= 150% of 100 max)",
		safety_137["triggered"] is False,
		f"safety_137={safety_137}",
	)
	report(
		"TEST 12c - Deterministic trigger: 151 PSI DOES trigger safety condition (> 150% of 100 max)",
		safety_151["triggered"] is True and safety_151["severity"] == "critical",
		f"safety_151={safety_151}",
	)
	report(
		"TEST 12d - Deterministic trigger: keyword 'gas leak' triggers safety condition",
		safety_kw["triggered"] is True and safety_kw["severity"] == "high",
		f"safety_kw={safety_kw}",
	)

	# 13. Step 7 regression: validation and 3-tuple return contract
	obs_reg, dup_reg, val_reg = save_observation(
		inspection_id=insp_a["id"],
		field_name="temperature",
		value="40",
		unit="Celsius",
		evidence_text="Temperature is 40 degrees Celsius.",
	)
	report(
		"TEST 13 - Step 7 regression: save_observation returns (obs, dup, val) with normal status",
		obs_reg["id"] > 0 and dup_reg is False and val_reg["status"] == "normal" and val_reg["normal"] is True,
		f"val_reg={val_reg}",
	)

	print("\n" + "=" * 40)
	print(f"PASSED: {PASSED}  |  FAILED: {FAILED}")
	print("=" * 40 + "\n")

	if FAILED > 0:
		sys.exit(1)


if __name__ == "__main__":
	try:
		run_tests()
	except Exception as exc:
		traceback.print_exc()
		sys.exit(1)

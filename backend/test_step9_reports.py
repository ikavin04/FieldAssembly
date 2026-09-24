"""Step 9 — Inspection Report Generation Test Suite.

Covers:
1. Generate report for valid inspection.
2. Report contains correct equipment metadata.
3. Report contains actual observations.
4. Evidence text is preserved.
5. Validation results are included.
6. Maintenance tickets are included.
7. Safety alerts are included.
8. Missing observations remain marked as missing.
9. Unknown inspection returns 404.
10. Cross-inspection integrity (Inspection A vs B isolation).
11. Completed inspection report structure (duration calculated when completed).
12. Incomplete inspection report structure (duration is None when in progress, never fabricated).
13. Step 7 regression: 26/26 validation tests passing.
14. Step 8 regression: 16/16 maintenance ticket & safety alert tests passing.
"""

import os
import subprocess
import sys
import traceback

from database.connection import get_connection
from services.inspection_service import (
	complete_inspection,
	save_observation,
	start_inspection,
)
from services.maintenance_ticket_service import create_ticket
from services.report_service import (
	ReportServiceError,
	generate_inspection_report,
)
from services.safety_alert_service import create_alert

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
	print("\n=== STEP 9 INSPECTION REPORT GENERATION TESTS ===\n")
	ac001 = get_ac001()
	pump001 = get_pump001()

	if not ac001 or not pump001:
		print("ERROR: Seed equipment AC-001 or PUMP-001 missing.")
		sys.exit(1)

	# 1. Generate report for valid inspection
	insp_1 = start_inspection(ac001["id"], "routine")
	rep_1 = generate_inspection_report(insp_1["id"])
	keys_expected = {
		"inspection",
		"equipment",
		"checklist",
		"observations",
		"maintenance_tickets",
		"safety_alerts",
		"summary",
		"generated_at",
	}
	report(
		"TEST 1 - Generate report for valid inspection contains all top-level keys",
		keys_expected.issubset(rep_1.keys()),
		f"missing_keys={keys_expected - rep_1.keys()}",
	)

	# 2. Report contains correct equipment metadata
	rep_eq = rep_1["equipment"]
	report(
		"TEST 2 - Report contains correct equipment metadata",
		rep_eq["asset_code"] == "AC-001"
		and rep_eq["name"] == ac001["name"]
		and rep_eq["equipment_type"] == ac001["equipment_type"]
		and rep_eq["location"] == ac001["location"],
		f"equipment={rep_eq}",
	)

	# 3. Report contains actual observations
	obs_1, _, _ = save_observation(
		inspection_id=insp_1["id"],
		field_name="pressure",
		value="137",
		unit="PSI",
		evidence_text="Pressure gauge reads 137 PSI.",
		confidence=0.96,
	)
	rep_with_obs = generate_inspection_report(insp_1["id"])
	obs_list = rep_with_obs["observations"]
	matching_obs = [o for o in obs_list if o["id"] == obs_1["id"]]
	report(
		"TEST 3 - Report contains actual observations saved in PostgreSQL",
		len(matching_obs) == 1 and matching_obs[0]["value"] == "137" and matching_obs[0]["unit"] == "PSI",
		f"matching_obs={matching_obs}",
	)

	# 4. Evidence text is preserved
	report(
		"TEST 4 - Verbatim evidence text and confidence are preserved",
		len(matching_obs) == 1
		and matching_obs[0]["evidence_text"] == "Pressure gauge reads 137 PSI."
		and matching_obs[0]["confidence"] == 0.96,
		f"matching_obs={matching_obs}",
	)

	# 5. Validation results are included in report observations
	val_result = matching_obs[0].get("validation", {})
	report(
		"TEST 5 - Deterministic validation results included for observations (137 PSI is out_of_range)",
		val_result.get("status") == "out_of_range"
		and val_result.get("normal") is False
		and val_result.get("limit") is not None,
		f"val_result={val_result}",
	)

	# 6. Maintenance tickets are included
	ticket_1, _ = create_ticket(
		inspection_id=insp_1["id"],
		issue="Pressure relief valve stuck (137 PSI)",
		priority="high",
	)
	rep_with_ticket = generate_inspection_report(insp_1["id"])
	tix_list = rep_with_ticket["maintenance_tickets"]
	matching_ticket = [t for t in tix_list if t["id"] == ticket_1["id"]]
	report(
		"TEST 6 - Maintenance tickets are included in report",
		len(matching_ticket) == 1
		and matching_ticket[0]["priority"] == "high"
		and rep_with_ticket["summary"]["maintenance_ticket_count"] >= 1,
		f"matching_ticket={matching_ticket}",
	)

	# 7. Safety alerts are included
	alert_1, _ = create_alert(
		inspection_id=insp_1["id"],
		hazard="Overpressure hazard: 137 PSI exceeds standard operating limit",
		severity="high",
		evidence_text="Technician reported 137 PSI reading on main valve.",
	)
	rep_with_alert = generate_inspection_report(insp_1["id"])
	alert_list = rep_with_alert["safety_alerts"]
	matching_alert = [a for a in alert_list if a["id"] == alert_1["id"]]
	report(
		"TEST 7 - Safety alerts are included in report",
		len(matching_alert) == 1
		and matching_alert[0]["severity"] == "high"
		and rep_with_alert["summary"]["safety_alert_count"] >= 1,
		f"matching_alert={matching_alert}",
	)

	# 8. Missing observations remain marked as missing
	chk = rep_with_alert["checklist"]
	required_count = len(chk["required_fields"])
	completed_count = len(chk["completed_fields"])
	missing_count = len(chk["missing_fields"])
	report(
		"TEST 8 - Missing observations remain marked as missing in checklist & summary",
		"temperature" in chk["missing_fields"]
		and "pressure" in chk["completed_fields"]
		and missing_count > 0
		and chk["complete"] is False
		and rep_with_alert["summary"]["missing_count"] == missing_count,
		f"chk={chk}, summary={rep_with_alert['summary']}",
	)

	# 9. Unknown inspection returns 404
	threw_404 = False
	try:
		generate_inspection_report(999999)
	except ReportServiceError as err:
		threw_404 = err.status_code == 404
	report(
		"TEST 9 - Unknown inspection ID returns 404 ReportServiceError",
		threw_404,
		f"threw_404={threw_404}",
	)

	# 10. Cross-inspection integrity (Inspection A vs B isolation)
	insp_b = start_inspection(pump001["id"], "routine")
	rep_b = generate_inspection_report(insp_b["id"])
	report(
		"TEST 10 - Cross-inspection integrity: Inspection B report contains no observations, tickets, or alerts from A",
		len(rep_b["observations"]) == 0
		and len(rep_b["maintenance_tickets"]) == 0
		and len(rep_b["safety_alerts"]) == 0
		and rep_b["equipment"]["asset_code"] == "PUMP-001",
		f"rep_b_summary={rep_b['summary']}",
	)

	# 11. Completed inspection report structure (duration calculated when completed)
	# Record all required fields for insp_1 and complete it
	save_observation(insp_1["id"], "temperature", "42", "Celsius", "Temperature is 42 C.")
	save_observation(insp_1["id"], "vibration", "none", None, "No vibration detected.")
	save_observation(insp_1["id"], "leakage", "none", None, "No leakage seen.")
	comp_insp = complete_inspection(insp_1["id"], summary="Routine check finished successfully.")
	rep_completed = generate_inspection_report(insp_1["id"])
	report(
		"TEST 11 - Completed inspection report structure: completed_at set, duration calculated, checklist complete",
		rep_completed["inspection"]["status"] == "completed"
		and rep_completed["inspection"]["completed_at"] is not None
		and rep_completed["inspection"]["duration"] is not None
		and rep_completed["checklist"]["complete"] is True
		and rep_completed["summary"]["status"] == "completed"
		and rep_completed["summary"]["missing_count"] == 0,
		f"inspection={rep_completed['inspection']}, checklist={rep_completed['checklist']}",
	)

	# 12. Incomplete inspection report structure (duration is None when in progress, never fabricated)
	insp_in_progress = start_inspection(ac001["id"], "routine")
	rep_in_progress = generate_inspection_report(insp_in_progress["id"])
	report(
		"TEST 12 - Incomplete inspection report structure: completed_at is None, duration is None (never fabricated)",
		rep_in_progress["inspection"]["status"] in ("started", "in_progress")
		and rep_in_progress["inspection"]["completed_at"] is None
		and rep_in_progress["inspection"]["duration"] is None
		and rep_in_progress["summary"]["status"] in ("started", "in_progress"),
		f"inspection={rep_in_progress['inspection']}",
	)

	# 13. Step 7 regression: python test_step7_validation.py
	print("\n--- Running Step 7 Regression Test Suite ---")
	script_dir = os.path.dirname(os.path.abspath(__file__))
	res_step7 = subprocess.run(
		[sys.executable, os.path.join(script_dir, "test_step7_validation.py")],
		cwd=script_dir,
		capture_output=True,
		text=True,
	)
	step7_passed = res_step7.returncode == 0 and "PASSED: 26" in res_step7.stdout
	report(
		"TEST 13 - Step 7 regression: 26/26 validation tests pass",
		step7_passed,
		f"stdout={res_step7.stdout[-300:] if res_step7.stdout else res_step7.stderr}",
	)

	# 14. Step 8 regression: python test_step8_tickets_alerts.py
	print("\n--- Running Step 8 Regression Test Suite ---")
	res_step8 = subprocess.run(
		[sys.executable, os.path.join(script_dir, "test_step8_tickets_alerts.py")],
		cwd=script_dir,
		capture_output=True,
		text=True,
	)
	step8_passed = res_step8.returncode == 0 and "PASSED: 16" in res_step8.stdout
	report(
		"TEST 14 - Step 8 regression: 16/16 tickets & alerts tests pass",
		step8_passed,
		f"stdout={res_step8.stdout[-300:] if res_step8.stdout else res_step8.stderr}",
	)

	print("\n" + "=" * 40)
	print(f"STEP 9 TOTAL PASSED: {PASSED}  |  FAILED: {FAILED}")
	print("=" * 40 + "\n")

	if FAILED > 0:
		sys.exit(1)


if __name__ == "__main__":
	try:
		run_tests()
	except Exception:
		traceback.print_exc()
		sys.exit(1)

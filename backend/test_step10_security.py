"""Step 10 — Security & Production Hardening Test Suite.

Verifies:
1. Mismatched inspection ID in tool calls is rejected / cannot corrupt other inspections.
2. Cross-inspection write isolation (Inspection A vs Inspection B).
3. Client cannot fabricate or override server-side deterministic validation.
4. Client cannot fabricate observations into reports or tickets.
5. Permanent AssemblyAI API key is never exposed by backend endpoints.
6. Malformed JSON, invalid types, and empty bodies return clean 400 JSON without tracebacks.
7. Non-existent resource IDs return clean 404 JSON without tracebacks.
8. Duplicate tool calls are idempotent (duplicate=True, same ID returned).
9. Cross-inspection observation references in tickets/alerts are rejected with 404.
"""

import json
import sys
import traceback
from app import create_app
from config import Config
from database.connection import get_connection
from services.inspection_service import save_observation, start_inspection

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


def get_equipment_ids():
	conn = get_connection()
	try:
		cur = conn.cursor()
		cur.execute("SELECT id, asset_code FROM equipment ORDER BY id;")
		rows = cur.fetchall()
		eq_map = {r["asset_code"]: r["id"] for r in rows}
		return eq_map
	finally:
		cur.close()
		conn.close()


def run_security_tests():
	print("\n=== STEP 10 SECURITY & PRODUCTION HARDENING TESTS ===\n")
	eq_map = get_equipment_ids()
	ac001_id = eq_map.get("AC-001")
	pump001_id = eq_map.get("PUMP-001")

	if not ac001_id or not pump001_id:
		print("ERROR: AC-001 or PUMP-001 missing.")
		sys.exit(1)

	app = create_app()
	client = app.test_client()

	# Start two distinct inspections
	insp_a = start_inspection(ac001_id, "routine")
	insp_b = start_inspection(pump001_id, "routine")

	# TEST 1: Malformed JSON body returns clean 400 JSON (no HTML, no traceback)
	res = client.post(
		"/api/tools/save-observation",
		data="not a json string",
		content_type="application/json",
	)
	data = res.get_json()
	report(
		"TEST 1 - Malformed JSON body returns clean 400 JSON with error message",
		res.status_code == 400 and isinstance(data, dict) and data.get("success") is False,
		f"status={res.status_code}, data={data}",
	)

	# TEST 2: Invalid inspection ID types return clean 400 JSON
	res_bool = client.post(
		"/api/tools/save-observation",
		json={"inspection_id": True, "field_name": "pressure", "value": "100"},
	)
	res_str = client.post(
		"/api/tools/save-observation",
		json={"inspection_id": "invalid_id", "field_name": "pressure", "value": "100"},
	)
	report(
		"TEST 2 - Boolean or string inspection_id returns clean 400 JSON",
		res_bool.status_code == 400 and res_str.status_code == 400,
		f"res_bool={res_bool.status_code}, res_str={res_str.status_code}",
	)

	# TEST 3: Non-existent inspection ID returns clean 404 JSON
	res_404 = client.post(
		"/api/tools/save-observation",
		json={"inspection_id": 999999, "field_name": "pressure", "value": "100"},
	)
	data_404 = res_404.get_json()
	report(
		"TEST 3 - Non-existent inspection ID returns clean 404 JSON without traceback",
		res_404.status_code == 404 and data_404.get("success") is False,
		f"status={res_404.status_code}, data={data_404}",
	)

	# TEST 4: Client cannot fabricate or override server-side deterministic validation
	# AC-001 pressure 137 PSI is out_of_range (limit 40-100). Client tries to claim it is 'normal'.
	res_val = client.post(
		"/api/tools/save-observation",
		json={
			"inspection_id": insp_a["id"],
			"field_name": "pressure",
			"value": "137",
			"unit": "PSI",
			"validation": {"status": "normal", "normal": True},
			"evidence_text": "137 PSI reading on gauge.",
		},
	)
	data_val = res_val.get_json()
	obs_val = data_val.get("validation", {})
	report(
		"TEST 4 - Backend enforces deterministic validation regardless of client payload (137 PSI is out_of_range)",
		res_val.status_code in (200, 201)
		and obs_val.get("status") == "out_of_range"
		and obs_val.get("normal") is False,
		f"status={res_val.status_code}, val={obs_val}",
	)

	# TEST 5: Cross-inspection observation reference in maintenance ticket is rejected with 404
	# Save observation in Inspection A
	obs_a, _, _ = save_observation(insp_a["id"], "temperature", "40", "Celsius", "40 C")
	# Attempt to create ticket in Inspection B using Observation A's ID
	res_cross_tix = client.post(
		"/api/tools/create-maintenance-ticket",
		json={
			"inspection_id": insp_b["id"],
			"observation_id": obs_a["id"],
			"issue": "Cross-inspection attempt",
		},
	)
	data_cross_tix = res_cross_tix.get_json()
	report(
		"TEST 5 - Maintenance ticket referencing observation from another inspection returns 404",
		res_cross_tix.status_code == 404 and data_cross_tix.get("success") is False,
		f"status={res_cross_tix.status_code}, data={data_cross_tix}",
	)

	# TEST 6: Cross-inspection observation reference in safety alert is rejected with 404
	res_cross_alr = client.post(
		"/api/tools/create-safety-alert",
		json={
			"inspection_id": insp_b["id"],
			"observation_id": obs_a["id"],
			"hazard": "Cross-inspection hazard",
		},
	)
	data_cross_alr = res_cross_alr.get_json()
	report(
		"TEST 6 - Safety alert referencing observation from another inspection returns 404",
		res_cross_alr.status_code == 404 and data_cross_alr.get("success") is False,
		f"status={res_cross_alr.status_code}, data={data_cross_alr}",
	)

	# TEST 7: Idempotency - duplicate maintenance ticket returns existing ID with duplicate=True
	res_tix_1 = client.post(
		"/api/tools/create-maintenance-ticket",
		json={
			"inspection_id": insp_a["id"],
			"issue": "Filter dirty and needs replacement",
			"priority": "medium",
		},
	)
	res_tix_2 = client.post(
		"/api/tools/create-maintenance-ticket",
		json={
			"inspection_id": insp_a["id"],
			"issue": "Filter dirty and needs replacement",
			"priority": "medium",
		},
	)
	data_tix_1 = res_tix_1.get_json()
	data_tix_2 = res_tix_2.get_json()
	report(
		"TEST 7 - Duplicate maintenance ticket tool call is idempotent (returns existing ticket_id and duplicate=True)",
		data_tix_2.get("duplicate") is True
		and data_tix_1.get("ticket_id") == data_tix_2.get("ticket_id"),
		f"tix1={data_tix_1}, tix2={data_tix_2}",
	)

	# TEST 8: Idempotency - duplicate safety alert returns existing ID with duplicate=True
	res_alr_1 = client.post(
		"/api/tools/create-safety-alert",
		json={
			"inspection_id": insp_a["id"],
			"hazard": "Exposed high voltage wire near panel",
			"severity": "critical",
		},
	)
	res_alr_2 = client.post(
		"/api/tools/create-safety-alert",
		json={
			"inspection_id": insp_a["id"],
			"hazard": "Exposed high voltage wire near panel",
			"severity": "critical",
		},
	)
	data_alr_1 = res_alr_1.get_json()
	data_alr_2 = res_alr_2.get_json()
	report(
		"TEST 8 - Duplicate safety alert tool call is idempotent (returns existing alert_id and duplicate=True)",
		data_alr_2.get("duplicate") is True
		and data_alr_1.get("alert_id") == data_alr_2.get("alert_id"),
		f"alr1={data_alr_1}, alr2={data_alr_2}",
	)

	# TEST 9: Permanent AssemblyAI API key is never exposed
	res_token = client.get("/api/voice-token")
	token_body = res_token.get_data(as_text=True)
	has_permanent_key = (
		Config.ASSEMBLYAI_API_KEY
		and Config.ASSEMBLYAI_API_KEY != "your_assemblyai_api_key_here"
		and Config.ASSEMBLYAI_API_KEY in token_body
	)
	report(
		"TEST 9 - Voice token endpoint never leaks permanent AssemblyAI API key",
		not has_permanent_key,
		f"token_response_length={len(token_body)}",
	)

	# TEST 10: Cross-inspection completion isolation
	# Completing inspection B does not affect inspection A
	client.post(
		"/api/tools/complete-inspection",
		json={"inspection_id": insp_b["id"], "summary": "Pump inspection completed."},
	)
	res_rep_a = client.get(f"/api/reports/{insp_a['id']}")
	data_rep_a = res_rep_a.get_json()
	report(
		"TEST 10 - Completing Inspection B does not alter Inspection A status or data",
		data_rep_a["inspection"]["status"] == "started"
		and data_rep_a["equipment"]["asset_code"] == "AC-001",
		f"insp_a_status={data_rep_a['inspection']['status']}",
	)

	print("\n" + "=" * 40)
	print(f"SECURITY TESTS PASSED: {PASSED}  |  FAILED: {FAILED}")
	print("=" * 40 + "\n")

	if FAILED > 0:
		sys.exit(1)


if __name__ == "__main__":
	try:
		run_security_tests()
	except Exception:
		traceback.print_exc()
		sys.exit(1)

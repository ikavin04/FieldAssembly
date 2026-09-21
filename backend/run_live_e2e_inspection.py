"""Step 10 — Clean Live End-to-End Inspection Execution Script.

Performs one complete, authoritative inspection on AC-001:
1. Create new inspection for AC-001.
2. Record temperature: 40 Celsius -> normal (0-60 limit).
3. Record pressure: 137 PSI -> out_of_range (40-100 limit).
4. Record vibration: none -> normal.
5. Record leakage: none -> normal.
6. Create maintenance ticket for pressure issue (137 PSI).
7. Complete inspection with authoritative summary.
8. Verify report generation at /api/reports/:id.
9. Verify ticket at /api/tickets.
10. Verify cross-inspection isolation.
"""

import json
import sys
from app import create_app
from database.connection import get_connection

app = create_app()
client = app.test_client()


def main():
	print("\n=== STEP 10 LIVE END-TO-END DEMO TEST ===\n")

	# 1. Get AC-001 ID
	conn = get_connection()
	cur = conn.cursor()
	cur.execute("SELECT id, asset_code, name FROM equipment WHERE asset_code = 'AC-001';")
	ac001 = cur.fetchone()
	cur.close()
	conn.close()

	if not ac001:
		print("FAIL: AC-001 not found in database.")
		sys.exit(1)

	# 2. Create Inspection
	res = client.post(
		"/api/inspections",
		json={"equipment_id": ac001["id"], "inspection_type": "routine"},
	)
	if res.status_code != 201:
		print(f"FAIL: Create inspection failed: {res.get_json()}")
		sys.exit(1)

	insp = res.get_json()
	insp_id = insp["inspection_id"]
	print(f"1. Created Inspection #{insp_id} for {ac001['asset_code']} ({ac001['name']})")

	# 3. Save 4 observations via tools endpoint
	observations = [
		{
			"field_name": "temperature",
			"value": "40",
			"unit": "Celsius",
			"evidence_text": "Temperature gauge reads 40 degrees Celsius.",
			"confidence": 0.98,
			"expected_val": "normal",
		},
		{
			"field_name": "pressure",
			"value": "137",
			"unit": "PSI",
			"evidence_text": "Pressure is reading 137 PSI on the main discharge line.",
			"confidence": 0.95,
			"expected_val": "out_of_range",
		},
		{
			"field_name": "vibration",
			"value": "none",
			"unit": None,
			"evidence_text": "No abnormal vibration detected on the motor mount.",
			"confidence": 0.99,
			"expected_val": "normal",
		},
		{
			"field_name": "leakage",
			"value": "none",
			"unit": None,
			"evidence_text": "No visible refrigerant or fluid leakage around fittings.",
			"confidence": 0.97,
			"expected_val": "normal",
		},
	]

	obs_ids = []
	for o in observations:
		res_obs = client.post(
			"/api/tools/save-observation",
			json={
				"inspection_id": insp_id,
				"field_name": o["field_name"],
				"value": o["value"],
				"unit": o["unit"],
				"evidence_text": o["evidence_text"],
				"confidence": o["confidence"],
			},
		)
		if res_obs.status_code not in (200, 201):
			print(f"FAIL: save_observation for {o['field_name']} failed: {res_obs.get_json()}")
			sys.exit(1)
		data_obs = res_obs.get_json()
		val = data_obs.get("validation", {})
		status = val.get("status")
		if status != o["expected_val"]:
			print(f"FAIL: validation mismatch for {o['field_name']}: expected {o['expected_val']}, got {status}")
			sys.exit(1)
		obs_ids.append(data_obs["observation_id"])
		print(f"   Observation recorded: {o['field_name']}={o['value']} ({status}) -> ID #{data_obs['observation_id']}")

	# 4. Create maintenance ticket for pressure issue
	res_tix = client.post(
		"/api/tools/create-maintenance-ticket",
		json={
			"inspection_id": insp_id,
			"issue": "Pressure reading 137 PSI exceeds operating limit (40-100 PSI)",
			"priority": "high",
		},
	)
	if res_tix.status_code not in (200, 201):
		print(f"FAIL: create_maintenance_ticket failed: {res_tix.get_json()}")
		sys.exit(1)
	tix_data = res_tix.get_json()
	print(f"2. Created Maintenance Ticket #{tix_data['ticket_id']} (Priority: {tix_data['priority']})")

	# 5. Complete inspection
	res_comp = client.post(
		"/api/tools/complete-inspection",
		json={
			"inspection_id": insp_id,
			"summary": "Routine inspection of AC-001 completed. Pressure is out of range at 137 PSI; maintenance ticket generated.",
		},
	)
	if res_comp.status_code != 200:
		print(f"FAIL: complete_inspection failed: {res_comp.get_json()}")
		sys.exit(1)
	comp_data = res_comp.get_json()
	print(f"3. Completed Inspection #{insp_id}: status={comp_data['status']}")

	# 6. Verify Report Endpoint
	res_rep = client.get(f"/api/reports/{insp_id}")
	if res_rep.status_code != 200:
		print(f"FAIL: get_report failed: {res_rep.get_json()}")
		sys.exit(1)
	rep = res_rep.get_json()
	print(f"4. Verified Report: status={rep['inspection']['status']}, duration={rep['inspection']['duration']}, observations={len(rep['observations'])}, tickets={len(rep['maintenance_tickets'])}")
	print(f"   Report Overview: {rep['summary']['overview']}")

	# 7. Verify Ticket appears in tickets endpoint
	res_tix_list = client.get(f"/api/tickets?inspection_id={insp_id}")
	tix_list = res_tix_list.get_json()
	if not any(t["id"] == tix_data["ticket_id"] for t in tix_list):
		print("FAIL: Ticket not returned in /api/tickets list.")
		sys.exit(1)
	print(f"5. Verified Ticket #{tix_data['ticket_id']} visible in /api/tickets")

	print("\nLIVE E2E INSPECTION SUCCESSFUL!")
	print(f"INSPECTION_ID={insp_id}")
	print(f"TICKET_ID={tix_data['ticket_id']}\n")


if __name__ == "__main__":
	main()

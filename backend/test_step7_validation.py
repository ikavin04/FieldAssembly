"""Step 7 — Deterministic Validation Tests

Tests the validation_service, inspection_service integration, and
the 3-tuple return contract across all callers.
"""

import json
import sys
import traceback

# Backend must be importable from CWD = backend/
from database.connection import get_connection
from models.equipment import get_equipment_by_id
from models.inspection import create_inspection, get_inspection_by_id
from services.inspection_service import (
    get_inspection,
    save_observation,
    start_inspection,
)
from services.validation_service import (
    validate_all_observations,
    validate_observation,
    validate_observation_for_inspection,
)

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


def get_ac001_id():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM equipment WHERE asset_code = 'AC-001'")
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row["id"] if row else None


def get_pump001_id():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM equipment WHERE asset_code = 'PUMP-001'")
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row["id"] if row else None


def test_1_normal_numeric():
    """91 PSI for AC-001 (range 40-100) -> normal"""
    eq_id = get_ac001_id()
    result = validate_observation(eq_id, "pressure", "91", "PSI")
    report("TEST 1 — normal numeric (91 PSI)",
           result["status"] == "normal" and result["normal"] is True,
           f"got status={result['status']}")


def test_2_low_out_of_range():
    """30 PSI for AC-001 (range 40-100) -> out_of_range"""
    eq_id = get_ac001_id()
    result = validate_observation(eq_id, "pressure", "30", "PSI")
    report("TEST 2 — low out-of-range (30 PSI)",
           result["status"] == "out_of_range" and result["normal"] is False,
           f"got status={result['status']}")


def test_3_high_out_of_range():
    """167 PSI for AC-001 (range 40-100) -> out_of_range"""
    eq_id = get_ac001_id()
    result = validate_observation(eq_id, "pressure", "167", "PSI")
    report("TEST 3 — high out-of-range (167 PSI)",
           result["status"] == "out_of_range" and result["normal"] is False,
           f"got status={result['status']}")


def test_4_boundary_minimum():
    """40 PSI for AC-001 (range 40-100) -> normal (inclusive)"""
    eq_id = get_ac001_id()
    result = validate_observation(eq_id, "pressure", "40", "PSI")
    report("TEST 4 — boundary minimum (40 PSI)",
           result["status"] == "normal" and result["normal"] is True,
           f"got status={result['status']}")


def test_5_boundary_maximum():
    """100 PSI for AC-001 (range 40-100) -> normal (inclusive)"""
    eq_id = get_ac001_id()
    result = validate_observation(eq_id, "pressure", "100", "PSI")
    report("TEST 5 — boundary maximum (100 PSI)",
           result["status"] == "normal" and result["normal"] is True,
           f"got status={result['status']}")


def test_6_missing_limit():
    """'airflow' for AC-001 has no limit -> unknown"""
    eq_id = get_ac001_id()
    result = validate_observation(eq_id, "airflow", "500", "CFM")
    report("TEST 6 — missing limit (airflow)",
           result["status"] == "unknown" and result["normal"] is None,
           f"got status={result['status']}")


def test_7_categorical_normal():
    """leakage='none' for AC-001 (no limits for leakage) -> normal via recognized set"""
    eq_id = get_ac001_id()
    result = validate_observation(eq_id, "leakage", "none")
    report("TEST 7 — categorical normal (leakage=none)",
           result["status"] == "normal" and result["normal"] is True,
           f"got status={result['status']}")


def test_8_categorical_unrecognized():
    """leakage='severe' for AC-001 (no explicit abnormal rule) -> unknown"""
    eq_id = get_ac001_id()
    result = validate_observation(eq_id, "leakage", "severe")
    report("TEST 8 — categorical unrecognized (leakage=severe)",
           result["status"] == "unknown" and result["normal"] is None,
           f"got status={result['status']}, normal={result['normal']}")


def test_9_context_integrity():
    """Two inspections, different equipment: validate correct limits."""
    ac001_id = get_ac001_id()
    pump001_id = get_pump001_id()

    # Create two inspections
    ins_a = create_inspection(ac001_id, "routine")
    ins_b = create_inspection(pump001_id, "routine")

    # AC-001 pressure range: 40-100
    # PUMP-001 pressure range: 20-90
    # 95 PSI is normal for AC-001 but out_of_range for PUMP-001
    result_a = validate_observation_for_inspection(ins_a["id"], "pressure", "95", "PSI")
    result_b = validate_observation_for_inspection(ins_b["id"], "pressure", "95", "PSI")

    report("TEST 9a — context: 95 PSI normal for AC-001",
           result_a["status"] == "normal",
           f"got status={result_a['status']}")
    report("TEST 9b — context: 95 PSI out_of_range for PUMP-001",
           result_b["status"] == "out_of_range",
           f"got status={result_b['status']}")

    # Verify observations on A don't appear on B
    obs_a, dup_a, val_a = save_observation(
        inspection_id=ins_a["id"],
        field_name="pressure",
        value="95",
        unit="PSI",
        evidence_text="Pressure is 95 PSI.",
    )
    # Check B has no observations
    obs_b = get_inspection(ins_b["id"])
    report("TEST 9c — context: inspection B has no observations",
           len(obs_b.get("completed_fields", [])) == 0,
           f"got completed_fields={obs_b.get('completed_fields')}")


def test_10_step6_regression():
    """Verify save_observation still returns (observation, duplicate, validation) with all fields."""
    ac001_id = get_ac001_id()
    ins = create_inspection(ac001_id, "routine")

    obs, dup, val = save_observation(
        inspection_id=ins["id"],
        field_name="temperature",
        value="40",
        unit="Celsius",
        evidence_text="Temperature is 40 degrees Celsius.",
        source_timestamp=12.5,
        confidence=0.95,
    )

    report("TEST 10a — regression: observation has id",
           obs.get("id") is not None,
           f"got obs={obs}")
    report("TEST 10b — regression: not duplicate",
           dup is False,
           f"got dup={dup}")
    report("TEST 10c — regression: evidence_text stored",
           obs.get("evidence_text") == "Temperature is 40 degrees Celsius.",
           f"got evidence={obs.get('evidence_text')}")
    report("TEST 10d — regression: validation returned",
           isinstance(val, dict) and "status" in val,
           f"got val type={type(val)}")
    report("TEST 10e — regression: temp 40C is normal for AC-001 (range 0-60)",
           val.get("status") == "normal",
           f"got val status={val.get('status')}")

    # Duplicate detection
    obs2, dup2, val2 = save_observation(
        inspection_id=ins["id"],
        field_name="temperature",
        value="40",
        unit="Celsius",
        evidence_text="Temperature is 40 degrees Celsius.",
    )
    report("TEST 10f — regression: duplicate detected",
           dup2 is True,
           f"got dup2={dup2}")
    report("TEST 10g — regression: validation on duplicate",
           isinstance(val2, dict) and val2.get("status") == "normal",
           f"got val2={val2}")


def test_vibration_categorical():
    """vibration='normal' should be recognized normal; vibration='moderate, 27 mm/s' -> depends on PUMP-001 limits."""
    ac001_id = get_ac001_id()
    result = validate_observation(ac001_id, "vibration", "normal")
    report("TEST EXTRA — vibration=normal -> normal",
           result["status"] == "normal" and result["normal"] is True,
           f"got status={result['status']}")

    result2 = validate_observation(ac001_id, "vibration", "none")
    report("TEST EXTRA — vibration=none -> normal",
           result2["status"] == "normal" and result2["normal"] is True,
           f"got status={result2['status']}")


def test_numeric_vibration_with_limits():
    """PUMP-001 has vibration_mm_s: {min: 0, max: 7}. Test numeric vibration."""
    pump_id = get_pump001_id()
    # 5 mm/s -> normal
    result = validate_observation(pump_id, "vibration", "5", "mm/s")
    report("TEST EXTRA — PUMP-001 vibration 5 mm/s -> normal",
           result["status"] == "normal",
           f"got status={result['status']}")

    # 10 mm/s -> out_of_range
    result2 = validate_observation(pump_id, "vibration", "10", "mm/s")
    report("TEST EXTRA — PUMP-001 vibration 10 mm/s -> out_of_range",
           result2["status"] == "out_of_range",
           f"got status={result2['status']}")


def test_validate_all_observations():
    """validate_all_observations returns per-field validation for an inspection."""
    ac001_id = get_ac001_id()
    ins = create_inspection(ac001_id, "routine")

    save_observation(inspection_id=ins["id"], field_name="temperature", value="40", unit="Celsius")
    save_observation(inspection_id=ins["id"], field_name="pressure", value="167", unit="PSI")
    save_observation(inspection_id=ins["id"], field_name="leakage", value="none")

    results = validate_all_observations(ins["id"])
    report("TEST EXTRA — validate_all: temperature normal",
           results.get("temperature", {}).get("status") == "normal",
           f"got={results.get('temperature')}")
    report("TEST EXTRA — validate_all: pressure out_of_range",
           results.get("pressure", {}).get("status") == "out_of_range",
           f"got={results.get('pressure')}")
    report("TEST EXTRA — validate_all: leakage normal",
           results.get("leakage", {}).get("status") == "normal",
           f"got={results.get('leakage')}")


def test_unit_mismatch():
    """If technician says 'bar' but limits are in PSI -> unknown (no unsafe conversion)."""
    ac001_id = get_ac001_id()
    result = validate_observation(ac001_id, "pressure", "3", "bar")
    report("TEST EXTRA — unit mismatch (bar vs PSI limits) -> unknown",
           result["status"] == "unknown" and result["normal"] is None,
           f"got status={result['status']}")


if __name__ == "__main__":
    print("\n=== STEP 7 VALIDATION TESTS ===\n")
    tests = [
        test_1_normal_numeric,
        test_2_low_out_of_range,
        test_3_high_out_of_range,
        test_4_boundary_minimum,
        test_5_boundary_maximum,
        test_6_missing_limit,
        test_7_categorical_normal,
        test_8_categorical_unrecognized,
        test_9_context_integrity,
        test_10_step6_regression,
        test_vibration_categorical,
        test_numeric_vibration_with_limits,
        test_validate_all_observations,
        test_unit_mismatch,
    ]
    for test_fn in tests:
        try:
            test_fn()
        except Exception:
            FAILED += 1
            print(f"  FAIL {test_fn.__name__} -- EXCEPTION")
            traceback.print_exc()

    print(f"\n{'='*40}")
    print(f"PASSED: {PASSED}  |  FAILED: {FAILED}")
    print(f"{'='*40}\n")
    sys.exit(0 if FAILED == 0 else 1)

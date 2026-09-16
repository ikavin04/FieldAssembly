"""
Seed Data

Inserts realistic HVAC / industrial-maintenance equipment for demos.
Run with:  python -m database.seed
"""

import json
import logging
from database.connection import get_connection

logger = logging.getLogger(__name__)

EQUIPMENT = [
    {
        "asset_code": "AC-001",
        "name": "Main Lobby Air Handler",
        "equipment_type": "HVAC",
        "location": "Building A — Lobby",
        "description": "Central air handling unit serving the main lobby area.",
        "operating_limits": {
            "temperature_c": {"min": 0, "max": 60},
            "pressure_psi": {"min": 40, "max": 100},
        },
        "required_inspection_fields": ["temperature", "pressure", "vibration", "leakage"],
    },
    {
        "asset_code": "AC-002",
        "name": "Server Room Precision Cooler",
        "equipment_type": "HVAC",
        "location": "Building A — Server Room",
        "description": "Precision cooling unit for the main server room.",
        "operating_limits": {
            "temperature_c": {"min": 15, "max": 30},
            "pressure_psi": {"min": 50, "max": 110},
        },
        "required_inspection_fields": ["temperature", "pressure", "vibration", "leakage", "refrigerant_level"],
    },
    {
        "asset_code": "AC-003",
        "name": "Warehouse Rooftop Unit",
        "equipment_type": "HVAC",
        "location": "Warehouse — Roof",
        "description": "Rooftop packaged HVAC unit for the warehouse.",
        "operating_limits": {
            "temperature_c": {"min": -5, "max": 70},
            "pressure_psi": {"min": 30, "max": 120},
        },
        "required_inspection_fields": ["temperature", "pressure", "vibration", "leakage"],
    },
    {
        "asset_code": "AC-004",
        "name": "Office Floor 2 Split System",
        "equipment_type": "HVAC",
        "location": "Building B — Floor 2",
        "description": "Split-system air conditioner for second-floor offices.",
        "operating_limits": {
            "temperature_c": {"min": 5, "max": 50},
            "pressure_psi": {"min": 40, "max": 100},
        },
        "required_inspection_fields": ["temperature", "pressure", "vibration", "leakage"],
    },
    {
        "asset_code": "AC-005",
        "name": "Laboratory Fume Hood Exhaust",
        "equipment_type": "HVAC",
        "location": "Building C — Lab 3",
        "description": "Exhaust system for the chemical laboratory fume hoods.",
        "operating_limits": {
            "temperature_c": {"min": 10, "max": 55},
            "pressure_psi": {"min": 20, "max": 80},
        },
        "required_inspection_fields": ["temperature", "pressure", "vibration", "leakage", "airflow"],
    },
    {
        "asset_code": "PUMP-001",
        "name": "Chilled Water Pump A",
        "equipment_type": "Pump",
        "location": "Building A — Mechanical Room",
        "description": "Primary chilled water circulation pump.",
        "operating_limits": {
            "temperature_c": {"min": 2, "max": 25},
            "pressure_psi": {"min": 20, "max": 90},
            "vibration_mm_s": {"min": 0, "max": 7},
        },
        "required_inspection_fields": ["temperature", "pressure", "vibration", "leakage"],
    },
    {
        "asset_code": "PUMP-002",
        "name": "Condenser Water Pump B",
        "equipment_type": "Pump",
        "location": "Building A — Mechanical Room",
        "description": "Condenser water loop circulation pump.",
        "operating_limits": {
            "temperature_c": {"min": 10, "max": 45},
            "pressure_psi": {"min": 15, "max": 85},
            "vibration_mm_s": {"min": 0, "max": 7},
        },
        "required_inspection_fields": ["temperature", "pressure", "vibration", "leakage"],
    },
    {
        "asset_code": "PUMP-003",
        "name": "Hot Water Circulation Pump",
        "equipment_type": "Pump",
        "location": "Building B — Boiler Room",
        "description": "Heating hot water circulation pump.",
        "operating_limits": {
            "temperature_c": {"min": 40, "max": 95},
            "pressure_psi": {"min": 10, "max": 60},
            "vibration_mm_s": {"min": 0, "max": 7},
        },
        "required_inspection_fields": ["temperature", "pressure", "vibration", "leakage"],
    },
    {
        "asset_code": "MTR-001",
        "name": "AHU Supply Fan Motor",
        "equipment_type": "Motor",
        "location": "Building A — Mechanical Room",
        "description": "Main supply fan motor for air handling unit AC-001.",
        "operating_limits": {
            "temperature_c": {"min": 10, "max": 80},
            "voltage_v": {"min": 380, "max": 420},
            "current_a": {"min": 0, "max": 30},
        },
        "required_inspection_fields": ["temperature", "vibration", "voltage", "current"],
    },
    {
        "asset_code": "MTR-002",
        "name": "Cooling Tower Fan Motor",
        "equipment_type": "Motor",
        "location": "Warehouse — Roof",
        "description": "Fan motor for the rooftop cooling tower.",
        "operating_limits": {
            "temperature_c": {"min": 10, "max": 85},
            "voltage_v": {"min": 380, "max": 420},
            "current_a": {"min": 0, "max": 25},
        },
        "required_inspection_fields": ["temperature", "vibration", "voltage", "current"],
    },
    {
        "asset_code": "CMP-001",
        "name": "Chiller Compressor Unit 1",
        "equipment_type": "Compressor",
        "location": "Building A — Chiller Plant",
        "description": "Centrifugal compressor in chiller unit 1.",
        "operating_limits": {
            "temperature_c": {"min": -10, "max": 100},
            "pressure_psi": {"min": 50, "max": 120},
            "vibration_mm_s": {"min": 0, "max": 5},
        },
        "required_inspection_fields": ["temperature", "pressure", "vibration", "leakage", "refrigerant_level"],
    },
    {
        "asset_code": "CMP-002",
        "name": "Chiller Compressor Unit 2",
        "equipment_type": "Compressor",
        "location": "Building A — Chiller Plant",
        "description": "Centrifugal compressor in chiller unit 2 (standby).",
        "operating_limits": {
            "temperature_c": {"min": -10, "max": 100},
            "pressure_psi": {"min": 50, "max": 120},
            "vibration_mm_s": {"min": 0, "max": 5},
        },
        "required_inspection_fields": ["temperature", "pressure", "vibration", "leakage", "refrigerant_level"],
    },
    {
        "asset_code": "BLR-001",
        "name": "Gas Boiler Unit 1",
        "equipment_type": "Boiler",
        "location": "Building B — Boiler Room",
        "description": "Natural gas fired hot water boiler.",
        "operating_limits": {
            "temperature_c": {"min": 50, "max": 110},
            "pressure_psi": {"min": 10, "max": 50},
        },
        "required_inspection_fields": ["temperature", "pressure", "leakage", "flue_gas"],
    },
    {
        "asset_code": "BLR-002",
        "name": "Gas Boiler Unit 2",
        "equipment_type": "Boiler",
        "location": "Building B — Boiler Room",
        "description": "Backup natural gas fired hot water boiler.",
        "operating_limits": {
            "temperature_c": {"min": 50, "max": 110},
            "pressure_psi": {"min": 10, "max": 50},
        },
        "required_inspection_fields": ["temperature", "pressure", "leakage", "flue_gas"],
    },
    {
        "asset_code": "CT-001",
        "name": "Cooling Tower A",
        "equipment_type": "Cooling Tower",
        "location": "Building A — Roof",
        "description": "Open-circuit cooling tower serving chiller plant.",
        "operating_limits": {
            "temperature_c": {"min": 15, "max": 45},
        },
        "required_inspection_fields": ["temperature", "vibration", "leakage", "water_quality"],
    },
    {
        "asset_code": "VLV-001",
        "name": "Chilled Water Control Valve 1",
        "equipment_type": "Valve",
        "location": "Building A — Mechanical Room",
        "description": "Motorized two-way control valve on chilled water supply.",
        "operating_limits": {
            "pressure_psi": {"min": 10, "max": 90},
        },
        "required_inspection_fields": ["pressure", "leakage", "actuator_response"],
    },
    {
        "asset_code": "EXH-001",
        "name": "Parking Garage Exhaust Fan",
        "equipment_type": "Exhaust Fan",
        "location": "Building A — Basement",
        "description": "CO exhaust ventilation fan for basement parking.",
        "operating_limits": {
            "temperature_c": {"min": 0, "max": 60},
            "current_a": {"min": 0, "max": 15},
        },
        "required_inspection_fields": ["temperature", "vibration", "current", "airflow"],
    },
    {
        "asset_code": "FCU-001",
        "name": "Conference Room Fan Coil Unit",
        "equipment_type": "Fan Coil",
        "location": "Building B — Floor 3, Room 310",
        "description": "Ceiling-concealed fan coil unit in the main conference room.",
        "operating_limits": {
            "temperature_c": {"min": 5, "max": 50},
        },
        "required_inspection_fields": ["temperature", "vibration", "leakage"],
    },
    {
        "asset_code": "GEN-001",
        "name": "Emergency Diesel Generator",
        "equipment_type": "Generator",
        "location": "Building A — Ground Floor, Generator Room",
        "description": "Standby diesel generator for emergency power.",
        "operating_limits": {
            "temperature_c": {"min": 20, "max": 100},
            "voltage_v": {"min": 380, "max": 420},
            "current_a": {"min": 0, "max": 200},
        },
        "required_inspection_fields": ["temperature", "voltage", "current", "fuel_level", "vibration"],
    },
    {
        "asset_code": "UPS-001",
        "name": "Server Room UPS",
        "equipment_type": "UPS",
        "location": "Building A — Server Room",
        "description": "Uninterruptible power supply protecting server room equipment.",
        "operating_limits": {
            "temperature_c": {"min": 15, "max": 35},
            "voltage_v": {"min": 380, "max": 420},
        },
        "required_inspection_fields": ["temperature", "voltage", "battery_status"],
    },
]


def seed():
    """Insert seed equipment into the database (skip existing asset codes)."""
    conn = get_connection()
    cur = conn.cursor()

    inserted = 0
    for eq in EQUIPMENT:
        cur.execute("SELECT 1 FROM equipment WHERE asset_code = %s", (eq["asset_code"],))
        if cur.fetchone():
            continue

        cur.execute(
            """
            INSERT INTO equipment
                (asset_code, name, equipment_type, location, description,
                 operating_limits, required_inspection_fields)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                eq["asset_code"],
                eq["name"],
                eq["equipment_type"],
                eq["location"],
                eq["description"],
                json.dumps(eq["operating_limits"]),
                json.dumps(eq["required_inspection_fields"]),
            ),
        )
        inserted += 1

    conn.commit()
    cur.close()
    conn.close()
    logger.info("Seeded %d equipment assets (%d total defined)", inserted, len(EQUIPMENT))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed()

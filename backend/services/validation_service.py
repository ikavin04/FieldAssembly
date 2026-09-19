"""
Validation Service

Deterministic measurement validation against equipment operating limits.

The backend is authoritative for all validation decisions.
The LLM / voice agent must NOT invent thresholds or decide range status.
operating_limits in PostgreSQL is the sole source of numeric limits.

Categorical fields without explicit operating_limits entries are validated
using a recognized-normal set only.  Unrecognized categorical values return
status='unknown', NOT 'out_of_range', unless an explicit categorical rule
exists in the equipment configuration.
"""

import logging

from models.equipment import get_equipment_by_id
from models.inspection import get_inspection_by_id
from models.observation import get_observations_for_inspection

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Recognized normal values for categorical (non-numeric) fields.
# These are the only values the system will affirmatively classify as normal
# when no operating_limits entry exists for the field.
# ---------------------------------------------------------------------------
RECOGNIZED_NORMAL_VALUES = frozenset({
    "none",
    "no",
    "normal",
    "no leakage",
    "no leak",
    "no leaks",
    "no vibration",
    "no abnormal vibration",
    "n/a",
    "not applicable",
    "ok",
    "good",
    "clear",
    "dry",
    "stable",
})

# ---------------------------------------------------------------------------
# Limit-key parsing
# ---------------------------------------------------------------------------

# Unit alias map — maps spoken/recorded units to the limit-key unit suffix.
_UNIT_ALIASES = {
    "celsius": "c",
    "°c": "c",
    "c": "c",
    "fahrenheit": "f",
    "°f": "f",
    "f": "f",
    "psi": "psi",
    "bar": "bar",
    "kpa": "kpa",
    "v": "v",
    "volt": "v",
    "volts": "v",
    "a": "a",
    "amp": "a",
    "amps": "a",
    "ampere": "a",
    "amperes": "a",
    "mm/s": "mm_s",
    "mm_s": "mm_s",
}


def _normalize_unit(unit):
    """Normalize a spoken/recorded unit to the limit-key suffix."""
    if unit is None:
        return None
    return _UNIT_ALIASES.get(unit.strip().lower())


# Known unit suffixes that appear in operating_limits keys.
# Used to disambiguate composite keys like 'vibration_mm_s'.
_KNOWN_UNIT_SUFFIXES = frozenset({
    "c",
    "f",
    "psi",
    "bar",
    "kpa",
    "v",
    "a",
    "mm_s",
})


def _parse_limit_keys(operating_limits):
    """Parse operating_limits keys into a lookup.

    Returns a dict mapping (field, unit_suffix) -> { min, max }.
    For example:
        'pressure_psi'    -> ('pressure', 'psi')
        'vibration_mm_s'  -> ('vibration', 'mm_s')
        'temperature_c'   -> ('temperature', 'c')
    """
    parsed = {}
    if not isinstance(operating_limits, dict):
        return parsed

    for key, value in operating_limits.items():
        if not isinstance(value, dict):
            continue

        # Try all possible split points, preferring the longest unit suffix
        parts = key.split("_")
        matched = False
        # Try from the shortest field prefix (1 part) to the longest
        for i in range(len(parts) - 1, 0, -1):
            candidate_suffix = "_".join(parts[i:])
            if candidate_suffix in _KNOWN_UNIT_SUFFIXES:
                field = "_".join(parts[:i])
                parsed[(field, candidate_suffix)] = value
                matched = True
                break

        if not matched:
            # Fallback: last segment as unit
            if len(parts) >= 2:
                field = "_".join(parts[:-1])
                unit_suffix = parts[-1]
                parsed[(field, unit_suffix)] = value
            else:
                parsed[(key, None)] = value

    return parsed


def _try_parse_numeric(value):
    """Attempt to parse a value as a float.  Returns (float, True) or (None, False)."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value), True
    if isinstance(value, str):
        cleaned = value.strip()
        try:
            return float(cleaned), True
        except (ValueError, OverflowError):
            return None, False
    return None, False


def _find_matching_limit(parsed_limits, field_name, unit):
    """Find the operating limit that matches this field_name + unit.

    Returns (limit_dict, matched_unit_suffix) or (None, None).
    """
    normalized_unit = _normalize_unit(unit)

    # 1. Try exact match: (field_name, normalized_unit)
    if normalized_unit is not None:
        key = (field_name.lower(), normalized_unit)
        if key in parsed_limits:
            return parsed_limits[key], normalized_unit

    # 2. If no unit was provided, try to find a unique limit for this field
    if normalized_unit is None:
        matching = [(k, v) for (k, v) in parsed_limits.items() if k[0] == field_name.lower()]
        if len(matching) == 1:
            return matching[0][1], matching[0][0][1]

    return None, None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_observation(equipment_id, field_name, value, unit=None):
    """Validate a single observation deterministically against equipment limits.

    Returns a dict:
      {
        "field_name": str,
        "value": <original value>,
        "unit": str | None,
        "status": "normal" | "out_of_range" | "unknown",
        "normal": True | False | None,
        "message": str,
        "limit": { "min": ..., "max": ... } | None
      }
    """
    base = {
        "field_name": field_name,
        "value": value,
        "unit": unit,
    }

    equipment = get_equipment_by_id(equipment_id)
    if equipment is None:
        return {
            **base,
            "status": "unknown",
            "normal": None,
            "message": "Equipment not found.",
            "limit": None,
        }

    operating_limits = equipment.get("operating_limits") or {}
    parsed_limits = _parse_limit_keys(operating_limits)

    # Find the matching limit for this field
    limit, matched_unit = _find_matching_limit(parsed_limits, field_name, unit)

    # --- Numeric validation (limit exists) ---
    if limit is not None:
        limit_min = limit.get("min")
        limit_max = limit.get("max")

        numeric_value, is_numeric = _try_parse_numeric(value)
        if is_numeric and limit_min is not None and limit_max is not None:
            if limit_min <= numeric_value <= limit_max:
                return {
                    **base,
                    "status": "normal",
                    "normal": True,
                    "message": "Value is within the configured operating range.",
                    "limit": {"min": limit_min, "max": limit_max},
                }
            else:
                return {
                    **base,
                    "status": "out_of_range",
                    "normal": False,
                    "message": "Value is outside the configured operating range.",
                    "limit": {"min": limit_min, "max": limit_max},
                }

        # Non-numeric value but limit exists — can't validate numerically
        # Fall through to categorical check below

    # --- Categorical validation (no numeric limit, or non-numeric value) ---
    normalized_value = str(value).strip().lower() if value is not None else ""

    if normalized_value in RECOGNIZED_NORMAL_VALUES:
        return {
            **base,
            "status": "normal",
            "normal": True,
            "message": "Recognized normal categorical value.",
            "limit": None,
        }

    # Unrecognized categorical value with no explicit abnormal rule → unknown
    return {
        **base,
        "status": "unknown",
        "normal": None,
        "message": "No applicable validation limit is available.",
        "limit": None,
    }


def validate_observation_for_inspection(inspection_id, field_name, value, unit=None):
    """Validate using the inspection's linked equipment — prevents wrong-asset validation."""
    inspection = get_inspection_by_id(inspection_id)
    if inspection is None:
        return {
            "field_name": field_name,
            "value": value,
            "unit": unit,
            "status": "unknown",
            "normal": None,
            "message": "Inspection not found.",
            "limit": None,
        }
    return validate_observation(inspection["equipment_id"], field_name, value, unit)


def validate_all_observations(inspection_id):
    """Validate all observations for an inspection, returning per-field results.

    Returns a dict of field_name -> validation result (latest observation per field).
    """
    inspection = get_inspection_by_id(inspection_id)
    if inspection is None:
        return {}

    equipment_id = inspection["equipment_id"]
    observations = get_observations_for_inspection(inspection_id)

    # Use the latest observation per field (last entry wins)
    latest_per_field = {}
    for obs in observations:
        latest_per_field[obs["field_name"]] = obs

    results = {}
    for field_name, obs in latest_per_field.items():
        result = validate_observation(
            equipment_id,
            obs["field_name"],
            obs["value"],
            obs.get("unit"),
        )
        results[field_name] = {
            "status": result["status"],
            "normal": result["normal"],
            "message": result["message"],
            "limit": result["limit"],
            "value": obs["value"],
            "unit": obs.get("unit"),
        }

    return results

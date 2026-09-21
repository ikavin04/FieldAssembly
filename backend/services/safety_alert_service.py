"""Safety alert business logic and deterministic trigger service."""

import logging
from models.equipment import get_equipment_by_id
from models.inspection import get_inspection_by_id
from models.observation import get_observations_for_inspection
from models.safety_alert import (
	create_safety_alert,
	find_duplicate_alert,
	get_alert_by_id,
	get_alerts_for_inspection,
	get_all_alerts,
)

logger = logging.getLogger(__name__)

VALID_SEVERITIES = frozenset({"low", "medium", "high", "critical"})
VALID_STATUSES = frozenset({"open", "in_progress", "resolved", "closed"})

# Controlled safety hazard keywords for evidence text matching
SAFETY_HAZARD_KEYWORDS = (
	"gas leak",
	"smoke",
	"fire",
	"burning smell",
	"spark",
	"exposed wire",
	"exposed wiring",
	"chemical leak",
	"explosion",
)


class SafetyAlertServiceError(Exception):
	"""Domain exception with HTTP status code mapping."""

	def __init__(self, message, status_code=400):
		super().__init__(message)
		self.message = message
		self.status_code = status_code


def evaluate_safety_condition(equipment, field_name, value, unit=None, evidence_text=None):
	"""Deterministic backend evaluation of safety conditions.

	Rules:
	1. Numeric overpressure:
	   value > (maximum_limit * 1.5) => severe safety condition
	   (e.g. AC-001 max 100 PSI: 150 PSI is a safety condition, while 137 PSI is not).
	   If no maximum operating limit exists, do not infer an overpressure safety condition.
	2. Controlled keyword matching against observation evidence_text and value.
	"""
	norm_field = (field_name or "").strip().lower()

	# 1. Numeric overpressure check
	if norm_field == "pressure" and equipment and isinstance(equipment.get("operating_limits"), dict):
		try:
			num_val = float(str(value).strip())
			limits = equipment["operating_limits"]
			# Find any pressure max limit (e.g. 'pressure', 'pressure_psi', 'pressure_bar')
			max_limit = None
			for k, v in limits.items():
				if k.startswith("pressure") and isinstance(v, dict) and "max" in v:
					max_limit = float(v["max"])
					break

			if max_limit is not None:
				threshold = max_limit * 1.5
				if num_val > threshold:
					unit_str = f" {unit}" if unit else ""
					return {
						"triggered": True,
						"severity": "critical",
						"hazard": (
							f"Extreme overpressure: {num_val}{unit_str} exceeds 150% "
							f"of maximum limit ({max_limit}{unit_str})"
						),
					}
		except (ValueError, TypeError):
			pass

	# 2. Controlled keyword matching on evidence text and value
	search_corpus = f"{evidence_text or ''} {value or ''}".lower()
	for kw in SAFETY_HAZARD_KEYWORDS:
		if kw in search_corpus:
			return {
				"triggered": True,
				"severity": "high",
				"hazard": f"Safety hazard detected: {kw}",
			}

	return {"triggered": False}


def create_alert(
	inspection_id,
	hazard=None,
	severity="medium",
	evidence_text=None,
	observation_id=None,
):
	"""Create a safety alert for an active inspection.

	observation_id is an OPTIONAL INPUT ONLY:
	- used to verify the referenced observation exists
	- used to verify it belongs to the active inspection
	- used to pull evidence_text and derive hazard context if needed
	- NEVER persisted directly to safety_alerts (schema has no such column)

	Returns:
	    (alert_dict, is_duplicate)
	"""
	if isinstance(inspection_id, bool) or not isinstance(inspection_id, int) or inspection_id <= 0:
		raise SafetyAlertServiceError("inspection_id must be a positive integer", 400)

	inspection = get_inspection_by_id(inspection_id)
	if inspection is None:
		raise SafetyAlertServiceError("Inspection not found", 404)

	equipment_id = inspection["equipment_id"]

	# If observation_id is provided, validate it belongs to this inspection
	if observation_id is not None:
		if isinstance(observation_id, bool) or not isinstance(observation_id, int) or observation_id <= 0:
			raise SafetyAlertServiceError("observation_id must be a positive integer", 400)

		observations = get_observations_for_inspection(inspection_id)
		matching_obs = next((obs for obs in observations if obs["id"] == observation_id), None)
		if matching_obs is None:
			raise SafetyAlertServiceError("Observation not found for this inspection", 404)

		if not evidence_text and matching_obs.get("evidence_text"):
			evidence_text = matching_obs["evidence_text"]

		if not hazard or not str(hazard).strip():
			hazard = f"Safety concern observed on {matching_obs['field_name']}: {matching_obs['value']}"

	if not hazard or not isinstance(hazard, str) or not hazard.strip():
		raise SafetyAlertServiceError("hazard description is required", 400)

	normalized_hazard = hazard.strip()
	normalized_severity = severity.strip().lower() if isinstance(severity, str) else "medium"
	if normalized_severity not in VALID_SEVERITIES:
		normalized_severity = "medium"

	# Idempotency check: avoid duplicate alerts for the same inspection & hazard
	duplicate = find_duplicate_alert(inspection_id, normalized_hazard)
	if duplicate is not None:
		logger.info(
			"Duplicate safety alert detected for inspection %s, alert %s",
			inspection_id,
			duplicate["id"],
		)
		return dict(duplicate), True

	created = create_safety_alert(
		inspection_id=inspection_id,
		equipment_id=equipment_id,
		hazard=normalized_hazard,
		severity=normalized_severity,
		evidence_text=evidence_text.strip() if isinstance(evidence_text, str) else None,
		status="open",
	)
	return dict(created), False


def get_alert(alert_id):
	"""Fetch a single safety alert enriched with equipment metadata."""
	if isinstance(alert_id, bool) or not isinstance(alert_id, int) or alert_id <= 0:
		raise SafetyAlertServiceError("alert_id must be a positive integer", 400)

	alert = get_alert_by_id(alert_id)
	if alert is None:
		raise SafetyAlertServiceError("Safety alert not found", 404)

	alert_dict = dict(alert)
	equipment = get_equipment_by_id(alert["equipment_id"])
	if equipment:
		alert_dict["equipment_asset_code"] = equipment.get("asset_code")
		alert_dict["equipment_name"] = equipment.get("name")
		alert_dict["equipment_location"] = equipment.get("location")
	return alert_dict


def get_alerts(inspection_id=None, status=None, severity=None):
	"""List safety alerts, optionally filtered by inspection_id, status, or severity."""
	if inspection_id is not None:
		if isinstance(inspection_id, bool) or not isinstance(inspection_id, int) or inspection_id <= 0:
			raise SafetyAlertServiceError("inspection_id must be a positive integer", 400)
		inspection = get_inspection_by_id(inspection_id)
		if inspection is None:
			raise SafetyAlertServiceError("Inspection not found", 404)
		alerts = get_alerts_for_inspection(inspection_id)
	else:
		alerts = get_all_alerts(status=status, severity=severity)

	enriched = []
	eq_cache = {}
	for a in alerts:
		ad = dict(a)
		eq_id = a["equipment_id"]
		if eq_id not in eq_cache:
			eq_cache[eq_id] = get_equipment_by_id(eq_id)
		eq = eq_cache[eq_id]
		if eq:
			ad["equipment_asset_code"] = eq.get("asset_code")
			ad["equipment_name"] = eq.get("name")
			ad["equipment_location"] = eq.get("location")
		enriched.append(ad)
	return enriched

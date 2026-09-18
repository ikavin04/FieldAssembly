"""Inspection lifecycle and observation capture services."""

from models.equipment import get_equipment_by_id
from models.inspection import create_inspection, get_inspection_by_id
from models.observation import (
	create_observation,
	find_duplicate_observation,
	get_observations_for_inspection,
)
from services.evidence_service import normalize_evidence


class InspectionServiceError(Exception):
	"""Expected request error with an HTTP-safe status and message."""

	def __init__(self, message, status_code=400):
		super().__init__(message)
		self.message = message
		self.status_code = status_code


def start_inspection(equipment_id, inspection_type="routine"):
	equipment = get_equipment_by_id(equipment_id)
	if equipment is None:
		raise InspectionServiceError("Equipment not found", 404)

	if inspection_type is None:
		inspection_type = "routine"
	if not isinstance(inspection_type, str) or not inspection_type.strip():
		raise InspectionServiceError("inspection_type must be a non-empty string")

	return create_inspection(equipment_id, inspection_type.strip())


def _required_fields(inspection):
	fields = inspection.get("required_inspection_fields") or []
	return [field.strip() for field in fields if isinstance(field, str) and field.strip()]


def get_inspection(inspection_id):
	inspection = get_inspection_by_id(inspection_id)
	if inspection is None:
		raise InspectionServiceError("Inspection not found", 404)

	required_fields = _required_fields(inspection)
	observations = get_observations_for_inspection(inspection_id)
	completed_fields = []
	for observation in observations:
		field_name = observation["field_name"]
		if field_name in required_fields and field_name not in completed_fields:
			completed_fields.append(field_name)

	return {
		"id": inspection["id"],
		"equipment_id": inspection["equipment_id"],
		"inspection_type": inspection["inspection_type"],
		"status": inspection["status"],
		"started_at": inspection["started_at"],
		"completed_at": inspection["completed_at"],
		"required_fields": required_fields,
		"completed_fields": completed_fields,
		"missing_fields": [field for field in required_fields if field not in completed_fields],
		"complete": len(completed_fields) == len(required_fields),
	}


def get_observations(inspection_id):
	if get_inspection_by_id(inspection_id) is None:
		raise InspectionServiceError("Inspection not found", 404)
	return get_observations_for_inspection(inspection_id)


def save_observation(
	inspection_id,
	field_name,
	value,
	unit=None,
	evidence_text=None,
	source_timestamp=None,
	confidence=None,
):
	inspection = get_inspection_by_id(inspection_id)
	if inspection is None:
		raise InspectionServiceError("Inspection not found", 404)

	if not isinstance(field_name, str) or not field_name.strip():
		raise InspectionServiceError("field_name is required")
	if not isinstance(value, (str, int, float)) or isinstance(value, bool) or not str(value).strip():
		raise InspectionServiceError("value must be non-empty")
	if unit is not None and (not isinstance(unit, str) or not unit.strip()):
		raise InspectionServiceError("unit must be a non-empty string or null")

	required_fields = _required_fields(inspection)
	field_lookup = {field.lower(): field for field in required_fields}
	canonical_field = field_lookup.get(field_name.strip().lower())
	if canonical_field is None:
		raise InspectionServiceError("field_name is not required for this equipment")

	try:
		evidence_text, source_timestamp, confidence = normalize_evidence(
			evidence_text, source_timestamp, confidence
		)
	except ValueError as exc:
		raise InspectionServiceError(str(exc)) from exc

	normalized_value = str(value).strip()
	normalized_unit = unit.strip() if isinstance(unit, str) else unit
	duplicate = find_duplicate_observation(
		inspection_id, canonical_field, normalized_value, evidence_text
	)
	if duplicate is not None:
		return duplicate, True

	return create_observation(
		inspection_id,
		canonical_field,
		normalized_value,
		normalized_unit,
		evidence_text,
		source_timestamp,
		confidence,
	), False

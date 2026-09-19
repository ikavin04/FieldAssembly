"""Inspection lifecycle and observation capture services."""

from models.equipment import get_equipment_by_id
from models.inspection import (
	complete_inspection,
	create_inspection,
	get_inspection_by_id,
)
from models.observation import (
	create_observation,
	find_duplicate_observation,
	get_observations_for_inspection,
)
from services.evidence_service import normalize_evidence
from services.validation_service import (
	validate_all_observations,
	validate_observation_for_inspection,
)


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


def finish_inspection(inspection_id, summary=None):
	"""Complete an inspection and return clean service-layer result."""
	if not isinstance(inspection_id, int) or isinstance(inspection_id, bool) or inspection_id <= 0:
		raise InspectionServiceError("inspection_id must be a positive integer", 400)

	inspection = get_inspection_by_id(inspection_id)
	if inspection is None:
		raise InspectionServiceError("Inspection not found", 404)

	if summary is not None and not isinstance(summary, str):
		raise InspectionServiceError("summary must be a string or null", 400)

	normalized_summary = summary.strip() if isinstance(summary, str) else None
	updated = complete_inspection(inspection_id, normalized_summary)
	if updated is None:
		raise InspectionServiceError("Inspection not found", 404)

	return {
		"id": updated["id"],
		"equipment_id": updated["equipment_id"],
		"inspection_type": updated["inspection_type"],
		"status": updated["status"],
		"started_at": updated["started_at"],
		"completed_at": updated["completed_at"],
		"summary": updated["summary"],
	}


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

	# Backend-authoritative validation summary per completed field
	validation = validate_all_observations(inspection_id)

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
		"validation": validation,
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
		validation = validate_observation_for_inspection(
			inspection_id, canonical_field, normalized_value, normalized_unit,
		)
		return duplicate, True, validation

	observation = create_observation(
		inspection_id,
		canonical_field,
		normalized_value,
		normalized_unit,
		evidence_text,
		source_timestamp,
		confidence,
	)
	validation = validate_observation_for_inspection(
		inspection_id, canonical_field, normalized_value, normalized_unit,
	)
	return observation, False, validation

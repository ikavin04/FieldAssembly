"""Inspection tools exposed through the browser-owned voice agent."""

from models.observation import get_observations_for_inspection
from services.inspection_service import (
	InspectionServiceError,
	finish_inspection,
	get_inspection,
	save_observation,
)


def save_observation_tool(arguments):
	"""Save a factual observation and return a compact tool result."""
	observation, duplicate, validation = save_observation(
		inspection_id=arguments.get("inspection_id"),
		field_name=arguments.get("field_name"),
		value=arguments.get("value"),
		unit=arguments.get("unit"),
		evidence_text=arguments.get("evidence_text"),
		source_timestamp=arguments.get("source_timestamp"),
		confidence=arguments.get("confidence"),
	)
	return {
		"success": True,
		"observation_id": observation["id"],
		"field_name": observation["field_name"],
		"duplicate": duplicate,
		"validation": {
			"status": validation["status"],
			"normal": validation["normal"],
			"message": validation["message"],
			"limit": validation["limit"],
		},
	}


def complete_inspection_tool(arguments):
	"""Complete an active inspection and return a compact tool result."""
	inspection = finish_inspection(
		inspection_id=arguments.get("inspection_id"),
		summary=arguments.get("summary"),
	)
	return {
		"success": True,
		"inspection_id": inspection["id"],
		"status": inspection["status"],
	}


def get_inspection_status_tool(arguments):
	"""Retrieve authoritative real-time inspection status (read-only)."""
	inspection_id = arguments.get("inspection_id")
	if isinstance(inspection_id, bool) or not isinstance(inspection_id, int) or inspection_id <= 0:
		raise InspectionServiceError("inspection_id must be a positive integer", 400)

	inspection = get_inspection(inspection_id)
	raw_obs = get_observations_for_inspection(inspection_id)

	observations = [
		{
			"id": obs["id"],
			"field_name": obs["field_name"],
			"value": obs["value"],
			"unit": obs["unit"],
			"evidence_text": obs["evidence_text"],
			"source_timestamp": obs["source_timestamp"],
			"confidence": obs["confidence"],
		}
		for obs in raw_obs
	]

	return {
		"success": True,
		"inspection_id": inspection["id"],
		"status": inspection["status"],
		"required_fields": inspection["required_fields"],
		"completed_fields": inspection["completed_fields"],
		"missing_fields": inspection["missing_fields"],
		"complete": inspection["complete"],
		"observations": observations,
		"validation": inspection["validation"],
	}


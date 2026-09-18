"""Inspection tools exposed through the browser-owned voice agent."""

from services.inspection_service import save_observation


def save_observation_tool(arguments):
	"""Save a factual observation and return a compact tool result."""
	observation, duplicate = save_observation(
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
	}

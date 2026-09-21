"""Safety tools exposed through the browser-owned voice agent."""

from services.safety_alert_service import create_alert


def create_safety_alert_tool(arguments):
	"""Create a safety alert and return a compact tool result."""
	alert, duplicate = create_alert(
		inspection_id=arguments.get("inspection_id"),
		hazard=arguments.get("hazard"),
		severity=arguments.get("severity", "medium"),
		evidence_text=arguments.get("evidence_text"),
		observation_id=arguments.get("observation_id"),
	)
	return {
		"success": True,
		"alert_id": alert["id"],
		"hazard": alert["hazard"],
		"severity": alert["severity"],
		"duplicate": duplicate,
	}

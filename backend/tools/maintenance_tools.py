"""Maintenance tools exposed through the browser-owned voice agent."""

from services.maintenance_ticket_service import create_ticket


def create_maintenance_ticket_tool(arguments):
	"""Create a maintenance ticket and return a compact tool result."""
	ticket, duplicate = create_ticket(
		inspection_id=arguments.get("inspection_id"),
		issue=arguments.get("issue"),
		priority=arguments.get("priority", "medium"),
		observation_id=arguments.get("observation_id"),
	)
	return {
		"success": True,
		"ticket_id": ticket["id"],
		"issue": ticket["issue"],
		"priority": ticket["priority"],
		"duplicate": duplicate,
	}

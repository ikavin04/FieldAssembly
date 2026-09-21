"""Maintenance ticket business logic and service layer."""

import logging
from models.equipment import get_equipment_by_id
from models.inspection import get_inspection_by_id
from models.maintenance_ticket import (
	create_maintenance_ticket,
	find_duplicate_ticket,
	get_all_tickets,
	get_ticket_by_id,
	get_tickets_for_inspection,
)
from models.observation import get_observations_for_inspection

logger = logging.getLogger(__name__)

VALID_PRIORITIES = frozenset({"low", "medium", "high", "critical"})
VALID_STATUSES = frozenset({"open", "in_progress", "resolved", "closed"})


class MaintenanceTicketServiceError(Exception):
	"""Domain exception with HTTP status code mapping."""

	def __init__(self, message, status_code=400):
		super().__init__(message)
		self.message = message
		self.status_code = status_code


def evaluate_ticket_need(validation):
	"""Deterministic check: does this validation result warrant a maintenance ticket?

	Returns True if the backend validation indicates the measurement is out of range.
	"""
	if not isinstance(validation, dict):
		return False
	return validation.get("status") == "out_of_range"


def create_ticket(
	inspection_id,
	issue=None,
	priority="medium",
	observation_id=None,
):
	"""Create a maintenance ticket for an active inspection.

	observation_id is an OPTIONAL INPUT ONLY:
	- used to verify the referenced observation exists
	- used to verify it belongs to the active inspection
	- used to derive issue description if issue is not explicitly provided
	- NEVER persisted directly to maintenance_tickets (schema has no such column)

	Returns:
	    (ticket_dict, is_duplicate)
	"""
	if isinstance(inspection_id, bool) or not isinstance(inspection_id, int) or inspection_id <= 0:
		raise MaintenanceTicketServiceError("inspection_id must be a positive integer", 400)

	inspection = get_inspection_by_id(inspection_id)
	if inspection is None:
		raise MaintenanceTicketServiceError("Inspection not found", 404)

	equipment_id = inspection["equipment_id"]

	# If observation_id is provided, validate it belongs to this inspection
	if observation_id is not None:
		if isinstance(observation_id, bool) or not isinstance(observation_id, int) or observation_id <= 0:
			raise MaintenanceTicketServiceError("observation_id must be a positive integer", 400)

		observations = get_observations_for_inspection(inspection_id)
		matching_obs = next((obs for obs in observations if obs["id"] == observation_id), None)
		if matching_obs is None:
			raise MaintenanceTicketServiceError("Observation not found for this inspection", 404)

		if not issue or not str(issue).strip():
			unit_str = f" {matching_obs['unit']}" if matching_obs.get("unit") else ""
			issue = f"{matching_obs['field_name']}: {matching_obs['value']}{unit_str} (out of range)"

	if not issue or not isinstance(issue, str) or not issue.strip():
		raise MaintenanceTicketServiceError("issue description is required", 400)

	normalized_issue = issue.strip()
	normalized_priority = priority.strip().lower() if isinstance(priority, str) else "medium"
	if normalized_priority not in VALID_PRIORITIES:
		normalized_priority = "medium"

	# Idempotency check: avoid duplicate tickets for the same inspection & issue
	duplicate = find_duplicate_ticket(inspection_id, normalized_issue)
	if duplicate is not None:
		logger.info(
			"Duplicate maintenance ticket detected for inspection %s, ticket %s",
			inspection_id,
			duplicate["id"],
		)
		return dict(duplicate), True

	created = create_maintenance_ticket(
		inspection_id=inspection_id,
		equipment_id=equipment_id,
		issue=normalized_issue,
		priority=normalized_priority,
		status="open",
	)
	return dict(created), False


def get_ticket(ticket_id):
	"""Fetch a single ticket enriched with equipment metadata."""
	if isinstance(ticket_id, bool) or not isinstance(ticket_id, int) or ticket_id <= 0:
		raise MaintenanceTicketServiceError("ticket_id must be a positive integer", 400)

	ticket = get_ticket_by_id(ticket_id)
	if ticket is None:
		raise MaintenanceTicketServiceError("Maintenance ticket not found", 404)

	ticket_dict = dict(ticket)
	equipment = get_equipment_by_id(ticket["equipment_id"])
	if equipment:
		ticket_dict["equipment_asset_code"] = equipment.get("asset_code")
		ticket_dict["equipment_name"] = equipment.get("name")
		ticket_dict["equipment_location"] = equipment.get("location")
	return ticket_dict


def get_tickets(inspection_id=None, status=None, priority=None):
	"""List maintenance tickets, optionally filtered by inspection_id, status, or priority."""
	if inspection_id is not None:
		if isinstance(inspection_id, bool) or not isinstance(inspection_id, int) or inspection_id <= 0:
			raise MaintenanceTicketServiceError("inspection_id must be a positive integer", 400)
		inspection = get_inspection_by_id(inspection_id)
		if inspection is None:
			raise MaintenanceTicketServiceError("Inspection not found", 404)
		tickets = get_tickets_for_inspection(inspection_id)
	else:
		tickets = get_all_tickets(status=status, priority=priority)

	enriched = []
	eq_cache = {}
	for t in tickets:
		td = dict(t)
		eq_id = t["equipment_id"]
		if eq_id not in eq_cache:
			eq_cache[eq_id] = get_equipment_by_id(eq_id)
		eq = eq_cache[eq_id]
		if eq:
			td["equipment_asset_code"] = eq.get("asset_code")
			td["equipment_name"] = eq.get("name")
			td["equipment_location"] = eq.get("location")
		enriched.append(td)
	return enriched

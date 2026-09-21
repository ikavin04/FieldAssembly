"""Inspection report generation service.

Assembles authoritative inspection reports dynamically from existing
PostgreSQL-backed data: inspections, equipment, observations,
maintenance tickets, and safety alerts.
"""

from datetime import datetime, timezone
import logging

from models.equipment import get_equipment_by_id
from models.inspection import get_inspection_by_id
from models.maintenance_ticket import get_tickets_for_inspection
from models.observation import get_observations_for_inspection
from models.safety_alert import get_alerts_for_inspection
from services.validation_service import validate_observation_for_inspection

logger = logging.getLogger(__name__)


class ReportServiceError(Exception):
	"""Domain exception with HTTP status code mapping."""

	def __init__(self, message, status_code=400):
		super().__init__(message)
		self.message = message
		self.status_code = status_code


def _iso(dt):
	if dt is None:
		return None
	if hasattr(dt, "isoformat"):
		return dt.isoformat()
	return str(dt)


def _format_duration(started_at, completed_at):
	"""Calculate duration between started_at and completed_at if both are available.

	Never fabricate a duration when completed_at is NULL.
	"""
	if not started_at or not completed_at:
		return None
	try:
		if isinstance(started_at, str):
			started_at = datetime.fromisoformat(started_at)
		if isinstance(completed_at, str):
			completed_at = datetime.fromisoformat(completed_at)
		delta = completed_at - started_at
		total_seconds = int(delta.total_seconds())
		if total_seconds < 0:
			return None
		minutes, seconds = divmod(total_seconds, 60)
		hours, minutes = divmod(minutes, 60)
		if hours > 0:
			return f"{hours}h {minutes}m {seconds}s"
		if minutes > 0:
			return f"{minutes}m {seconds}s"
		return f"{seconds}s"
	except Exception:
		return None


def generate_inspection_report(inspection_id):
	"""Dynamically generate a comprehensive, authoritative inspection report.

	Derived purely from real PostgreSQL records.
	"""
	if isinstance(inspection_id, bool) or not isinstance(inspection_id, int) or inspection_id <= 0:
		raise ReportServiceError("inspection_id must be a positive integer", 400)

	inspection = get_inspection_by_id(inspection_id)
	if inspection is None:
		raise ReportServiceError("Inspection not found", 404)

	equipment_id = inspection["equipment_id"]
	equipment = get_equipment_by_id(equipment_id)

	raw_observations = get_observations_for_inspection(inspection_id)
	raw_tickets = get_tickets_for_inspection(inspection_id)
	raw_alerts = get_alerts_for_inspection(inspection_id)

	# Checklist evaluation
	required_fields = inspection.get("required_inspection_fields") or (
		equipment.get("required_inspection_fields") if equipment else []
	) or []
	required_fields = [f.strip() for f in required_fields if isinstance(f, str) and f.strip()]

	completed_fields = []
	observations = []
	out_of_range_count = 0

	for obs in raw_observations:
		field_name = obs["field_name"]
		if field_name in required_fields and field_name not in completed_fields:
			completed_fields.append(field_name)

		# Validate observation deterministically
		val = validate_observation_for_inspection(
			inspection_id,
			field_name,
			obs["value"],
			obs.get("unit"),
		)
		if val.get("status") == "out_of_range":
			out_of_range_count += 1

		observations.append({
			"id": obs["id"],
			"field_name": obs["field_name"],
			"value": obs["value"],
			"unit": obs.get("unit"),
			"evidence_text": obs.get("evidence_text"),
			"source_timestamp": obs.get("source_timestamp"),
			"confidence": obs.get("confidence"),
			"created_at": _iso(obs.get("created_at")),
			"validation": {
				"status": val["status"],
				"normal": val["normal"],
				"message": val["message"],
				"limit": val["limit"],
			},
		})

	missing_fields = [f for f in required_fields if f not in completed_fields]
	is_complete = len(completed_fields) == len(required_fields) and len(required_fields) > 0

	# Serialized maintenance tickets
	tickets = []
	for t in raw_tickets:
		tickets.append({
			"id": t["id"],
			"inspection_id": t["inspection_id"],
			"equipment_id": t["equipment_id"],
			"issue": t["issue"],
			"priority": t["priority"],
			"status": t["status"],
			"created_at": _iso(t.get("created_at")),
			"updated_at": _iso(t.get("updated_at")),
		})

	# Serialized safety alerts
	alerts = []
	for a in raw_alerts:
		alerts.append({
			"id": a["id"],
			"inspection_id": a["inspection_id"],
			"equipment_id": a["equipment_id"],
			"hazard": a["hazard"],
			"severity": a["severity"],
			"evidence_text": a.get("evidence_text"),
			"status": a["status"],
			"created_at": _iso(a.get("created_at")),
			"resolved_at": _iso(a.get("resolved_at")),
		})

	# Deterministic summary
	status = inspection["status"]
	started_at = inspection.get("started_at")
	completed_at = inspection.get("completed_at")
	duration = _format_duration(started_at, completed_at)

	overview_parts = []
	if status == "completed":
		overview_parts.append(f"Inspection #{inspection_id} completed.")
	else:
		overview_parts.append(f"Inspection #{inspection_id} in progress.")

	overview_parts.append(f"{len(completed_fields)} of {len(required_fields)} required checkpoints recorded.")

	if out_of_range_count > 0:
		overview_parts.append(f"{out_of_range_count} observation(s) out of operating range.")
	else:
		overview_parts.append("All recorded measurements within operating limits.")

	if tickets:
		overview_parts.append(f"{len(tickets)} maintenance ticket(s) generated.")
	if alerts:
		overview_parts.append(f"{len(alerts)} safety alert(s) recorded.")

	overview = " ".join(overview_parts)

	return {
		"inspection": {
			"id": inspection["id"],
			"status": status,
			"inspection_type": inspection.get("inspection_type"),
			"started_at": _iso(started_at),
			"completed_at": _iso(completed_at),
			"duration": duration,
			"summary": inspection.get("summary"),
		},
		"equipment": {
			"id": equipment["id"] if equipment else equipment_id,
			"asset_code": equipment.get("asset_code") if equipment else None,
			"name": equipment.get("name") if equipment else None,
			"equipment_type": equipment.get("equipment_type") if equipment else None,
			"location": equipment.get("location") if equipment else None,
			"description": equipment.get("description") if equipment else None,
		},
		"checklist": {
			"required_fields": required_fields,
			"completed_fields": completed_fields,
			"missing_fields": missing_fields,
			"complete": is_complete,
		},
		"observations": observations,
		"maintenance_tickets": tickets,
		"safety_alerts": alerts,
		"summary": {
			"status": status,
			"required_count": len(required_fields),
			"completed_count": len(completed_fields),
			"missing_count": len(missing_fields),
			"out_of_range_count": out_of_range_count,
			"maintenance_ticket_count": len(tickets),
			"safety_alert_count": len(alerts),
			"overview": overview,
		},
		"generated_at": datetime.now(timezone.utc).isoformat(),
	}

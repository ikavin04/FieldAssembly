"""Maintenance ticket endpoints."""

import logging
from flask import Blueprint, jsonify, request

from services.maintenance_ticket_service import (
	MaintenanceTicketServiceError,
	create_ticket,
	get_ticket,
	get_tickets,
)

tickets_bp = Blueprint("tickets", __name__)
logger = logging.getLogger(__name__)


def _serialize_ticket(ticket):
	return {
		"id": ticket["id"],
		"inspection_id": ticket["inspection_id"],
		"equipment_id": ticket["equipment_id"],
		"issue": ticket["issue"],
		"priority": ticket["priority"],
		"status": ticket["status"],
		"created_at": ticket["created_at"].isoformat() if hasattr(ticket.get("created_at"), "isoformat") else ticket.get("created_at"),
		"updated_at": ticket["updated_at"].isoformat() if hasattr(ticket.get("updated_at"), "isoformat") else ticket.get("updated_at"),
		"equipment_asset_code": ticket.get("equipment_asset_code"),
		"equipment_name": ticket.get("equipment_name"),
		"equipment_location": ticket.get("equipment_location"),
	}


@tickets_bp.route("/api/tickets", methods=["POST"])
def create_ticket_endpoint():
	payload = request.get_json(silent=True)
	if not isinstance(payload, dict):
		return jsonify({"success": False, "error": "Request body must be a JSON object"}), 400

	inspection_id = payload.get("inspection_id")
	if isinstance(inspection_id, bool) or not isinstance(inspection_id, int) or inspection_id <= 0:
		return jsonify({"success": False, "error": "inspection_id must be a positive integer"}), 400

	try:
		ticket, duplicate = create_ticket(
			inspection_id=inspection_id,
			issue=payload.get("issue"),
			priority=payload.get("priority", "medium"),
			observation_id=payload.get("observation_id"),
		)
	except MaintenanceTicketServiceError as exc:
		return jsonify({"success": False, "error": exc.message}), exc.status_code
	except Exception:
		logger.exception("Ticket creation failed")
		return jsonify({"success": False, "error": "Unable to create maintenance ticket"}), 500

	return jsonify({
		"success": True,
		"ticket": _serialize_ticket(ticket),
		"duplicate": duplicate,
	}), 200 if duplicate else 201


@tickets_bp.route("/api/tickets", methods=["GET"])
def list_tickets_endpoint():
	raw_inspection_id = request.args.get("inspection_id")
	inspection_id = None
	if raw_inspection_id:
		try:
			inspection_id = int(raw_inspection_id)
		except ValueError:
			return jsonify({"success": False, "error": "inspection_id must be an integer"}), 400

	status = request.args.get("status")
	priority = request.args.get("priority")

	try:
		tickets = get_tickets(inspection_id=inspection_id, status=status, priority=priority)
		return jsonify([_serialize_ticket(t) for t in tickets])
	except MaintenanceTicketServiceError as exc:
		return jsonify({"success": False, "error": exc.message}), exc.status_code
	except Exception:
		logger.exception("Listing tickets failed")
		return jsonify({"success": False, "error": "Unable to retrieve tickets"}), 500


@tickets_bp.route("/api/tickets/<int:ticket_id>", methods=["GET"])
def get_ticket_endpoint(ticket_id):
	try:
		ticket = get_ticket(ticket_id)
		return jsonify(_serialize_ticket(ticket))
	except MaintenanceTicketServiceError as exc:
		return jsonify({"success": False, "error": exc.message}), exc.status_code
	except Exception:
		logger.exception("Ticket retrieval failed")
		return jsonify({"success": False, "error": "Unable to retrieve ticket"}), 500


@tickets_bp.route("/api/inspections/<int:inspection_id>/tickets", methods=["GET"])
def list_inspection_tickets_endpoint(inspection_id):
	try:
		tickets = get_tickets(inspection_id=inspection_id)
		return jsonify([_serialize_ticket(t) for t in tickets])
	except MaintenanceTicketServiceError as exc:
		return jsonify({"success": False, "error": exc.message}), exc.status_code
	except Exception:
		logger.exception("Listing inspection tickets failed")
		return jsonify({"success": False, "error": "Unable to retrieve tickets for inspection"}), 500

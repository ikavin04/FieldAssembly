"""Safety alert endpoints."""

import logging
from flask import Blueprint, jsonify, request

from services.safety_alert_service import (
	SafetyAlertServiceError,
	create_alert,
	get_alert,
	get_alerts,
)

alerts_bp = Blueprint("alerts", __name__)
logger = logging.getLogger(__name__)


def _serialize_alert(alert):
	return {
		"id": alert["id"],
		"inspection_id": alert["inspection_id"],
		"equipment_id": alert["equipment_id"],
		"hazard": alert["hazard"],
		"severity": alert["severity"],
		"evidence_text": alert.get("evidence_text"),
		"status": alert["status"],
		"created_at": alert["created_at"].isoformat() if hasattr(alert.get("created_at"), "isoformat") else alert.get("created_at"),
		"resolved_at": alert["resolved_at"].isoformat() if hasattr(alert.get("resolved_at"), "isoformat") else alert.get("resolved_at"),
		"equipment_asset_code": alert.get("equipment_asset_code"),
		"equipment_name": alert.get("equipment_name"),
		"equipment_location": alert.get("equipment_location"),
	}


@alerts_bp.route("/api/safety-alerts", methods=["POST"])
def create_alert_endpoint():
	payload = request.get_json(silent=True)
	if not isinstance(payload, dict):
		return jsonify({"success": False, "error": "Request body must be a JSON object"}), 400

	inspection_id = payload.get("inspection_id")
	if isinstance(inspection_id, bool) or not isinstance(inspection_id, int) or inspection_id <= 0:
		return jsonify({"success": False, "error": "inspection_id must be a positive integer"}), 400

	try:
		alert, duplicate = create_alert(
			inspection_id=inspection_id,
			hazard=payload.get("hazard"),
			severity=payload.get("severity", "medium"),
			evidence_text=payload.get("evidence_text"),
			observation_id=payload.get("observation_id"),
		)
	except SafetyAlertServiceError as exc:
		return jsonify({"success": False, "error": exc.message}), exc.status_code
	except Exception:
		logger.exception("Alert creation failed")
		return jsonify({"success": False, "error": "Unable to create safety alert"}), 500

	return jsonify({
		"success": True,
		"alert": _serialize_alert(alert),
		"duplicate": duplicate,
	}), 200 if duplicate else 201


@alerts_bp.route("/api/safety-alerts", methods=["GET"])
def list_alerts_endpoint():
	raw_inspection_id = request.args.get("inspection_id")
	inspection_id = None
	if raw_inspection_id:
		try:
			inspection_id = int(raw_inspection_id)
		except ValueError:
			return jsonify({"success": False, "error": "inspection_id must be an integer"}), 400

	status = request.args.get("status")
	severity = request.args.get("severity")

	try:
		alerts = get_alerts(inspection_id=inspection_id, status=status, severity=severity)
		return jsonify([_serialize_alert(a) for a in alerts])
	except SafetyAlertServiceError as exc:
		return jsonify({"success": False, "error": exc.message}), exc.status_code
	except Exception:
		logger.exception("Listing alerts failed")
		return jsonify({"success": False, "error": "Unable to retrieve safety alerts"}), 500


@alerts_bp.route("/api/safety-alerts/<int:alert_id>", methods=["GET"])
def get_alert_endpoint(alert_id):
	try:
		alert = get_alert(alert_id)
		return jsonify(_serialize_alert(alert))
	except SafetyAlertServiceError as exc:
		return jsonify({"success": False, "error": exc.message}), exc.status_code
	except Exception:
		logger.exception("Alert retrieval failed")
		return jsonify({"success": False, "error": "Unable to retrieve safety alert"}), 500


@alerts_bp.route("/api/inspections/<int:inspection_id>/alerts", methods=["GET"])
def list_inspection_alerts_endpoint(inspection_id):
	try:
		alerts = get_alerts(inspection_id=inspection_id)
		return jsonify([_serialize_alert(a) for a in alerts])
	except SafetyAlertServiceError as exc:
		return jsonify({"success": False, "error": exc.message}), exc.status_code
	except Exception:
		logger.exception("Listing inspection alerts failed")
		return jsonify({"success": False, "error": "Unable to retrieve alerts for inspection"}), 500

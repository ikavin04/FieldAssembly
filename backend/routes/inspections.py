"""Inspection lifecycle endpoints."""

import logging

from flask import Blueprint, jsonify, request

from services.inspection_service import (
	InspectionServiceError,
	finish_inspection,
	get_inspection,
	start_inspection,
)

inspections_bp = Blueprint("inspections", __name__)
logger = logging.getLogger(__name__)



@inspections_bp.route("/api/inspections", methods=["POST"])
def create_inspection_endpoint():
	payload = request.get_json(silent=True)
	if not isinstance(payload, dict):
		return jsonify({"success": False, "error": "Request body must be a JSON object"}), 400

	equipment_id = payload.get("equipment_id")
	if isinstance(equipment_id, bool) or not isinstance(equipment_id, int) or equipment_id <= 0:
		return jsonify({"success": False, "error": "equipment_id must be a positive integer"}), 400

	try:
		inspection = start_inspection(equipment_id, payload.get("inspection_type", "routine"))
	except InspectionServiceError as exc:
		return jsonify({"success": False, "error": exc.message}), exc.status_code
	except Exception:
		logger.exception("Inspection creation failed")
		return jsonify({"success": False, "error": "Unable to create inspection"}), 500

	return jsonify({
		"success": True,
		"inspection_id": inspection["id"],
		"equipment_id": inspection["equipment_id"],
		"status": inspection["status"],
		"started_at": inspection["started_at"],
	}), 201


@inspections_bp.route("/api/inspections/<int:inspection_id>", methods=["GET"])
def get_inspection_endpoint(inspection_id):
	try:
		return jsonify(get_inspection(inspection_id))
	except InspectionServiceError as exc:
		return jsonify({"success": False, "error": exc.message}), exc.status_code
	except Exception:
		logger.exception("Inspection retrieval failed")
		return jsonify({"success": False, "error": "Unable to retrieve inspection"}), 500


@inspections_bp.route("/api/inspections/<int:inspection_id>/complete", methods=["POST"])
def complete_inspection_endpoint(inspection_id):
	if isinstance(inspection_id, bool) or not isinstance(inspection_id, int) or inspection_id <= 0:
		return jsonify({"success": False, "error": "inspection_id must be a positive integer"}), 400

	payload = request.get_json(silent=True)
	if payload is not None and not isinstance(payload, dict):
		return jsonify({"success": False, "error": "Request body must be a JSON object"}), 400

	summary = payload.get("summary") if payload else None

	try:
		inspection = finish_inspection(inspection_id, summary)
	except InspectionServiceError as exc:
		return jsonify({"success": False, "error": exc.message}), exc.status_code
	except Exception:
		logger.exception("Inspection completion failed")
		return jsonify({"success": False, "error": "Unable to complete inspection"}), 500

	return jsonify({
		"success": True,
		"inspection": inspection,
	}), 200


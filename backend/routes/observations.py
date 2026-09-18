"""Observation and evidence endpoints."""

import logging

from flask import Blueprint, jsonify, request

from services.inspection_service import (
	InspectionServiceError,
	get_observations,
	save_observation,
)

observations_bp = Blueprint("observations", __name__)
logger = logging.getLogger(__name__)


def _serialize_observation(observation):
	return {
		"id": observation["id"],
		"inspection_id": observation["inspection_id"],
		"field_name": observation["field_name"],
		"value": observation["value"],
		"unit": observation["unit"],
		"evidence_text": observation["evidence_text"],
		"source_timestamp": observation["source_timestamp"],
		"confidence": observation["confidence"],
	}


@observations_bp.route("/api/observations", methods=["POST"])
def create_observation_endpoint():
	payload = request.get_json(silent=True)
	if not isinstance(payload, dict):
		return jsonify({"success": False, "error": "Request body must be a JSON object"}), 400

	inspection_id = payload.get("inspection_id")
	if isinstance(inspection_id, bool) or not isinstance(inspection_id, int) or inspection_id <= 0:
		return jsonify({"success": False, "error": "inspection_id must be a positive integer"}), 400

	try:
		observation, duplicate = save_observation(
			inspection_id=inspection_id,
			field_name=payload.get("field_name"),
			value=payload.get("value"),
			unit=payload.get("unit"),
			evidence_text=payload.get("evidence_text"),
			source_timestamp=payload.get("source_timestamp"),
			confidence=payload.get("confidence"),
		)
	except InspectionServiceError as exc:
		return jsonify({"success": False, "error": exc.message}), exc.status_code
	except Exception:
		logger.exception("Observation creation failed")
		return jsonify({"success": False, "error": "Unable to save observation"}), 500

	return jsonify({
		"success": True,
		"observation": _serialize_observation(observation),
		"duplicate": duplicate,
	}), 200 if duplicate else 201


@observations_bp.route("/api/inspections/<int:inspection_id>/observations", methods=["GET"])
def list_observations_endpoint(inspection_id):
	try:
		return jsonify([_serialize_observation(item) for item in get_observations(inspection_id)])
	except InspectionServiceError as exc:
		return jsonify({"success": False, "error": exc.message}), exc.status_code
	except Exception:
		logger.exception("Observation retrieval failed")
		return jsonify({"success": False, "error": "Unable to retrieve observations"}), 500

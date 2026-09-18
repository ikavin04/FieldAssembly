"""Backend endpoints used by the browser-owned voice agent tool calls."""

import logging

from flask import Blueprint, jsonify, request

from services.inspection_service import InspectionServiceError
from tools.equipment_tools import get_equipment_profile
from tools.inspection_tools import save_observation_tool

logger = logging.getLogger(__name__)

tools_bp = Blueprint("tools", __name__)


@tools_bp.route("/api/tools/get-equipment-profile", methods=["POST"])
def equipment_profile_tool():
    """Return authoritative equipment data for an active voice inspection."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"success": False, "error": "Request body must be a JSON object"}), 400

    asset_code = payload.get("asset_code")
    if not isinstance(asset_code, str) or not asset_code.strip():
        return jsonify({"success": False, "error": "asset_code must be a non-empty string"}), 400
    asset_code = asset_code.strip().upper()

    try:
        equipment = get_equipment_profile(asset_code)
    except Exception:
        logger.exception("[Tool] get_equipment_profile failed")
        return jsonify({"success": False, "error": "Unable to retrieve equipment profile"}), 500

    if equipment is None:
        return jsonify({"success": False, "error": "Equipment asset not found"}), 404

    logger.info("[Tool] get_equipment_profile asset_code=%s", asset_code)
    return jsonify({"success": True, "equipment": equipment})


@tools_bp.route("/api/tools/save-observation", methods=["POST"])
def save_observation_tool_endpoint():
    """Save a factual observation requested by the active voice session."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"success": False, "error": "Request body must be a JSON object"}), 400

    inspection_id = payload.get("inspection_id")
    if isinstance(inspection_id, bool) or not isinstance(inspection_id, int) or inspection_id <= 0:
        return jsonify({"success": False, "error": "inspection_id must be a positive integer"}), 400

    try:
        result = save_observation_tool(payload)
    except InspectionServiceError as exc:
        return jsonify({"success": False, "error": exc.message}), exc.status_code
    except Exception:
        logger.exception("[Tool] save_observation failed")
        return jsonify({"success": False, "error": "Unable to save observation"}), 500

    logger.info("[Tool] save_observation inspection_id=%s", inspection_id)
    return jsonify(result), 200 if result.get("duplicate") else 201
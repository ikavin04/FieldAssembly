"""Backend endpoints used by the browser-owned voice agent tool calls."""

import logging

from flask import Blueprint, jsonify, request

from services.inspection_service import InspectionServiceError
from services.maintenance_ticket_service import MaintenanceTicketServiceError
from services.safety_alert_service import SafetyAlertServiceError
from tools.equipment_tools import get_equipment_profile
from tools.inspection_tools import complete_inspection_tool, save_observation_tool
from tools.maintenance_tools import create_maintenance_ticket_tool
from tools.safety_tools import create_safety_alert_tool

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


@tools_bp.route("/api/tools/complete-inspection", methods=["POST"])
def complete_inspection_tool_endpoint():
    """Complete an active inspection requested by the voice session."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"success": False, "error": "Request body must be a JSON object"}), 400

    inspection_id = payload.get("inspection_id")
    if isinstance(inspection_id, bool) or not isinstance(inspection_id, int) or inspection_id <= 0:
        return jsonify({"success": False, "error": "inspection_id must be a positive integer"}), 400

    try:
        result = complete_inspection_tool(payload)
    except InspectionServiceError as exc:
        return jsonify({"success": False, "error": exc.message}), exc.status_code
    except Exception:
        logger.exception("[Tool] complete_inspection failed")
        return jsonify({"success": False, "error": "Unable to complete inspection"}), 500

    logger.info("[Tool] complete_inspection inspection_id=%s", inspection_id)
    return jsonify(result), 200


@tools_bp.route("/api/tools/create-maintenance-ticket", methods=["POST"])
def create_maintenance_ticket_tool_endpoint():
    """Create a maintenance ticket requested by the voice session."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"success": False, "error": "Request body must be a JSON object"}), 400

    inspection_id = payload.get("inspection_id")
    if isinstance(inspection_id, bool) or not isinstance(inspection_id, int) or inspection_id <= 0:
        return jsonify({"success": False, "error": "inspection_id must be a positive integer"}), 400

    try:
        result = create_maintenance_ticket_tool(payload)
    except MaintenanceTicketServiceError as exc:
        return jsonify({"success": False, "error": exc.message}), exc.status_code
    except Exception:
        logger.exception("[Tool] create_maintenance_ticket failed")
        return jsonify({"success": False, "error": "Unable to create maintenance ticket"}), 500

    logger.info("[Tool] create_maintenance_ticket inspection_id=%s", inspection_id)
    return jsonify(result), 200 if result.get("duplicate") else 201


@tools_bp.route("/api/tools/create-safety-alert", methods=["POST"])
def create_safety_alert_tool_endpoint():
    """Create a safety alert requested by the voice session."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"success": False, "error": "Request body must be a JSON object"}), 400

    inspection_id = payload.get("inspection_id")
    if isinstance(inspection_id, bool) or not isinstance(inspection_id, int) or inspection_id <= 0:
        return jsonify({"success": False, "error": "inspection_id must be a positive integer"}), 400

    try:
        result = create_safety_alert_tool(payload)
    except SafetyAlertServiceError as exc:
        return jsonify({"success": False, "error": exc.message}), exc.status_code
    except Exception:
        logger.exception("[Tool] create_safety_alert failed")
        return jsonify({"success": False, "error": "Unable to create safety alert"}), 500

    logger.info("[Tool] create_safety_alert inspection_id=%s", inspection_id)
    return jsonify(result), 200 if result.get("duplicate") else 201
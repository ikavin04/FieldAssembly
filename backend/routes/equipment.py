"""Equipment endpoints."""

from flask import Blueprint, jsonify
from models.equipment import get_all_equipment, get_equipment_by_id

equipment_bp = Blueprint("equipment", __name__)


@equipment_bp.route("/api/equipment", methods=["GET"])
def list_equipment():
    """Return all equipment assets from the database."""
    equipment = get_all_equipment()
    return jsonify(equipment)


@equipment_bp.route("/api/equipment/<int:equipment_id>", methods=["GET"])
def get_equipment(equipment_id):
    """Return a single equipment asset by ID."""
    item = get_equipment_by_id(equipment_id)
    if not item:
        return jsonify({"error": "Equipment not found"}), 404
    return jsonify(item)

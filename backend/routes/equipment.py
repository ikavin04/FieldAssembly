"""Equipment endpoints."""

from flask import Blueprint, jsonify, request
from models.equipment import get_all_equipment, get_equipment_by_id
from utils.responses import api_error

equipment_bp = Blueprint("equipment", __name__)


@equipment_bp.route("/api/equipment", methods=["GET"])
def list_equipment():
    """Return equipment assets from the database with filtering and pagination."""
    search = request.args.get("search")
    status = request.args.get("status")
    equipment_type = request.args.get("type")
    location = request.args.get("location")
    raw_page = request.args.get("page")
    raw_limit = request.args.get("limit")
    envelope = request.args.get("envelope") == "true"

    page = None
    limit = None
    if raw_page is not None or raw_limit is not None:
        try:
            page = max(1, int(raw_page)) if raw_page else 1
            limit = max(1, min(100, int(raw_limit))) if raw_limit else 20
        except ValueError:
            return api_error("page and limit must be positive integers", status_code=400)

    equipment, total = get_all_equipment(
        search=search,
        status=status,
        equipment_type=equipment_type,
        location=location,
        page=page,
        limit=limit,
    )

    total_pages = (total + limit - 1) // limit if (limit and total > 0) else 1

    if raw_page is not None or raw_limit is not None or envelope:
        resp = jsonify({
            "success": True,
            "data": equipment,
            "pagination": {
                "page": page or 1,
                "limit": limit or len(equipment),
                "total": total,
                "total_pages": total_pages,
                "has_next": (page or 1) < total_pages,
                "has_prev": (page or 1) > 1,
            },
        })
    else:
        # Default backward-compatible list response for existing consumers
        resp = jsonify(equipment)

    resp.headers["X-Total-Count"] = str(total)
    if page:
        resp.headers["X-Page"] = str(page)
        resp.headers["X-Limit"] = str(limit)
        resp.headers["X-Total-Pages"] = str(total_pages)

    return resp


@equipment_bp.route("/api/equipment/<int:equipment_id>", methods=["GET"])
def get_equipment(equipment_id):
    """Return a single equipment asset by ID."""
    item = get_equipment_by_id(equipment_id)
    if not item:
        return api_error("Equipment not found", code="RESOURCE_NOT_FOUND", status_code=404)
    return jsonify(item)

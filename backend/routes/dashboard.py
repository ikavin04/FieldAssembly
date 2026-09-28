"""Operations Dashboard Routes."""

import logging
from flask import Blueprint, jsonify, request
from services.dashboard_service import (
    get_asset_health,
    get_dashboard_summary,
    get_live_feed,
)
from utils.responses import api_error

dashboard_bp = Blueprint("dashboard", __name__)
logger = logging.getLogger(__name__)


@dashboard_bp.route("/api/dashboard/summary", methods=["GET"])
def dashboard_summary_endpoint():
    """GET /api/dashboard/summary — Return high-level operations KPIs from PostgreSQL."""
    try:
        summary_data = get_dashboard_summary()
        return jsonify({
            "success": True,
            "data": summary_data,
        }), 200
    except Exception:
        logger.exception("Failed to retrieve dashboard summary")
        return api_error("Unable to retrieve dashboard summary", status_code=500)


@dashboard_bp.route("/api/dashboard/live-feed", methods=["GET"])
def dashboard_live_feed_endpoint():
    """GET /api/dashboard/live-feed — Return recent inspection activity."""
    raw_limit = request.args.get("limit")
    limit = 15
    if raw_limit:
        try:
            limit = max(1, min(100, int(raw_limit)))
        except ValueError:
            return api_error("limit must be a positive integer", status_code=400)

    try:
        feed = get_live_feed(limit=limit)
        return jsonify({
            "success": True,
            "data": feed,
        }), 200
    except Exception:
        logger.exception("Failed to retrieve dashboard live feed")
        return api_error("Unable to retrieve live feed", status_code=500)


@dashboard_bp.route("/api/dashboard/asset-health", methods=["GET"])
def dashboard_asset_health_endpoint():
    """GET /api/dashboard/asset-health — Return equipment health states."""
    try:
        health = get_asset_health()
        return jsonify({
            "success": True,
            "data": health,
        }), 200
    except Exception:
        logger.exception("Failed to retrieve asset health")
        return api_error("Unable to retrieve asset health", status_code=500)

"""Inspection report endpoints."""

import logging
from flask import Blueprint, jsonify

from services.report_service import (
	ReportServiceError,
	generate_inspection_report,
)

reports_bp = Blueprint("reports", __name__)
logger = logging.getLogger(__name__)


@reports_bp.route("/api/reports/<int:inspection_id>", methods=["GET"])
def get_report_endpoint(inspection_id):
	"""Return dynamically generated inspection report data."""
	try:
		report = generate_inspection_report(inspection_id)
		return jsonify(report), 200
	except ReportServiceError as exc:
		return jsonify({"success": False, "error": exc.message}), exc.status_code
	except Exception:
		logger.exception("Report generation failed for inspection_id=%s", inspection_id)
		return jsonify({"success": False, "error": "Unable to generate inspection report"}), 500


@reports_bp.route("/api/reports/<int:inspection_id>/generate", methods=["POST"])
def generate_report_endpoint(inspection_id):
	"""Explicitly trigger report generation and return the structured report."""
	try:
		report = generate_inspection_report(inspection_id)
		return jsonify(report), 200
	except ReportServiceError as exc:
		return jsonify({"success": False, "error": exc.message}), exc.status_code
	except Exception:
		logger.exception("Report generation failed for inspection_id=%s", inspection_id)
		return jsonify({"success": False, "error": "Unable to generate inspection report"}), 500

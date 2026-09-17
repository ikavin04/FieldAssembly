"""Voice token endpoint — provides temporary AssemblyAI session tokens."""

import logging
from flask import Blueprint, jsonify
from services.assemblyai_service import generate_temporary_token

logger = logging.getLogger(__name__)

voice_bp = Blueprint("voice", __name__)


@voice_bp.route("/api/voice-token", methods=["GET"])
def get_voice_token():
    """GET /api/voice-token — generate a single-use temporary AssemblyAI token."""
    try:
        token = generate_temporary_token(expires_in_seconds=300)
        return jsonify({"token": token})
    except ValueError as ve:
        logger.warning("Voice token validation error: %s", ve)
        return jsonify({"error": "Unable to obtain voice session token"}), 400
    except Exception as exc:
        logger.error("Error generating voice token: %s", exc)
        return jsonify({"error": "Unable to obtain voice session token"}), 500

"""
FieldVoice Backend Application

Flask API server for the FieldVoice voice-first inspection platform.
"""

import logging
from flask import Flask
from flask_cors import CORS
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app():
    """Application factory for the Flask backend."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Validate environment before serving requests
    Config.validate()

    # CORS — restrict to the configured frontend origin
    CORS(app, resources={r"/api/*": {"origins": Config.FRONTEND_ORIGIN}})

    # ------------------------------------------------------------------
    # Register route blueprints
    # ------------------------------------------------------------------
    from routes.health import health_bp
    from routes.voice import voice_bp
    from routes.equipment import equipment_bp
    from routes.inspections import inspections_bp
    from routes.observations import observations_bp
    from routes.tickets import tickets_bp
    from routes.alerts import alerts_bp
    from routes.reports import reports_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(voice_bp)
    app.register_blueprint(equipment_bp)
    app.register_blueprint(inspections_bp)
    app.register_blueprint(observations_bp)
    app.register_blueprint(tickets_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(reports_bp)

    logger.info("FieldVoice backend ready")
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)

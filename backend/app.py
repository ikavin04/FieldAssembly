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

    # CORS — allow configured frontend origin(s) or wildcard
    cors_origins = [o.strip() for o in Config.FRONTEND_ORIGIN.split(",")] if "," in Config.FRONTEND_ORIGIN else Config.FRONTEND_ORIGIN
    CORS(app, resources={r"/api/*": {"origins": cors_origins}})

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
    from routes.tools import tools_bp
    from routes.dashboard import dashboard_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(voice_bp)
    app.register_blueprint(equipment_bp)
    app.register_blueprint(inspections_bp)
    app.register_blueprint(observations_bp)
    app.register_blueprint(tickets_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(tools_bp)
    app.register_blueprint(dashboard_bp)

    @app.route("/")
    def index():
        """Root API status endpoint."""
        return {
            "service": "FieldVoice Backend API",
            "status": "online",
            "version": "1.0.0",
            "frontend": "https://frontend-six-lac-68.vercel.app",
            "endpoints": {
                "health": "/api/health",
                "equipment": "/api/equipment",
                "tickets": "/api/tickets",
                "alerts": "/api/safety-alerts",
                "dashboard": "/api/dashboard/summary",
                "seed": "/api/seed",
            },
        }, 200

    @app.route("/api/seed", methods=["GET", "POST"])
    def seed_database():
        """Ensure initial equipment dataset is seeded."""
        try:
            from database.seed import seed
            seed()
            from database.connection import get_db_connection
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) as count FROM equipment")
                count = cur.fetchone()["count"]
            return {"status": "ok", "equipment_count": count}, 200
        except Exception as exc:
            logger.error("Seeding failed: %s", exc)
            return {"status": "error", "message": str(exc)}, 500

    # Auto-seed equipment if table is empty
    try:
        from database.connection import get_db_connection
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) as count FROM equipment")
            row = cur.fetchone()
            if row and row["count"] == 0:
                logger.info("Equipment table empty, auto-seeding standard equipment...")
                from database.seed import seed
                seed()
    except Exception as exc:
        logger.warning("Could not auto-seed equipment on startup: %s", exc)

    logger.info("FieldVoice backend ready")
    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)


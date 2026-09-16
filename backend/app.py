"""
FieldVoice Backend Application

Flask API server for the FieldVoice voice-first inspection platform.
"""

from flask import Flask, jsonify
from flask_cors import CORS
from config import Config


def create_app():
    """Application factory for the Flask backend."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Enable CORS for frontend communication
    CORS(app)

    # ------------------------------------------------------------------
    # Health endpoint
    # ------------------------------------------------------------------
    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})

    # Future: register route blueprints here
    # from routes import inspections, equipment, voice, tickets, alerts, reports
    # app.register_blueprint(inspections.bp)
    # ...

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)

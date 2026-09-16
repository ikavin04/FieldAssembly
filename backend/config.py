"""
FieldVoice Configuration

Loads settings from environment variables with validation.
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    """Application configuration loaded from environment variables."""

    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")

    # AssemblyAI
    ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

    # Database
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://localhost:5432/fieldvoice",
    )

    # CORS — allowed frontend origin during development
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

    @classmethod
    def validate(cls):
        """Check that critical secrets are present in non-dev environments.

        Logs warnings in development; raises in production.
        """
        missing = []

        if not cls.ASSEMBLYAI_API_KEY:
            missing.append("ASSEMBLYAI_API_KEY")

        if cls.FLASK_ENV == "production":
            if cls.SECRET_KEY == "dev-secret-key":
                missing.append("SECRET_KEY (still using default)")
            if missing:
                raise EnvironmentError(
                    f"Missing required environment variables: {', '.join(missing)}"
                )
        elif missing:
            logger.warning(
                "Missing environment variables (ok for local dev): %s",
                ", ".join(missing),
            )

"""
Database Connection

Provides a connection pool for PostgreSQL using psycopg2.
"""

import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from config import Config

logger = logging.getLogger(__name__)

_pool = None


def get_connection():
    """Return a new database connection using the configured DATABASE_URL.

    Each caller is responsible for closing/returning the connection.
    For the hackathon scope, we use simple connections rather than a
    full pooling library.
    """
    try:
        conn = psycopg2.connect(Config.DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except psycopg2.OperationalError as exc:
        logger.error("Database connection failed: %s", exc)
        raise


def test_connection():
    """Return True if the database is reachable, False otherwise."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return True
    except Exception as exc:
        logger.warning("Database health check failed: %s", exc)
        return False

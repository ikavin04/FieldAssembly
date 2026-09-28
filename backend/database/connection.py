"""
Database Connection

Provides a thread-safe connection pool for PostgreSQL using psycopg2.
"""

import atexit
from contextlib import contextmanager
import logging
import threading
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool, PoolError
from config import Config

logger = logging.getLogger(__name__)

_pool = None
_pool_lock = threading.Lock()
_MIN_CONN = 2
_MAX_CONN = 20


def init_pool(minconn=_MIN_CONN, maxconn=_MAX_CONN):
    """Initialize or re-initialize the connection pool."""
    global _pool
    with _pool_lock:
        if _pool is not None and not _pool.closed:
            return _pool
        try:
            _pool = ThreadedConnectionPool(
                minconn=minconn,
                maxconn=maxconn,
                dsn=Config.DATABASE_URL,
                cursor_factory=RealDictCursor,
            )
            logger.info("Initialized PostgreSQL connection pool (%s-%s connections)", minconn, maxconn)
            return _pool
        except Exception as exc:
            logger.error("Failed to initialize database connection pool: %s", exc)
            _pool = None
            raise


def close_pool():
    """Close all connections in the pool."""
    global _pool
    with _pool_lock:
        if _pool is not None and not _pool.closed:
            try:
                _pool.closeall()
                logger.info("Closed PostgreSQL connection pool")
            except Exception as exc:
                logger.warning("Error closing connection pool: %s", exc)
            finally:
                _pool = None


atexit.register(close_pool)


class PooledConnectionProxy:
    """Wrapper that returns connection to pool on .close() instead of destroying it."""

    def __init__(self, raw_conn, pool):
        self._raw_conn = raw_conn
        self._pool = pool
        self._closed = False

    def close(self):
        if not self._closed:
            self._closed = True
            if self._pool and not self._pool.closed:
                try:
                    # rollback any uncommitted transaction before returning to pool
                    if self._raw_conn.status == psycopg2.extensions.STATUS_IN_TRANSACTION:
                        self._raw_conn.rollback()
                    self._pool.putconn(self._raw_conn)
                except Exception as exc:
                    logger.warning("Error returning connection to pool: %s", exc)
                    try:
                        self._raw_conn.close()
                    except Exception:
                        pass
            else:
                try:
                    self._raw_conn.close()
                except Exception:
                    pass

    def __getattr__(self, name):
        return getattr(self._raw_conn, name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            try:
                self._raw_conn.rollback()
            except Exception:
                pass
        self.close()


def get_connection():
    """Return a pooled database connection wrapped in a PooledConnectionProxy.

    When the caller calls conn.close(), the connection is safely returned
    to the pool. If the pool is exhausted or uninitialized, falls back to
    a direct connection with proper error handling.
    """
    global _pool
    if _pool is None or _pool.closed:
        try:
            init_pool()
        except Exception:
            # Fall back to direct connection if pool init fails
            conn = psycopg2.connect(Config.DATABASE_URL, cursor_factory=RealDictCursor)
            return conn

    try:
        raw_conn = _pool.getconn()
        return PooledConnectionProxy(raw_conn, _pool)
    except PoolError:
        logger.warning("Connection pool exhausted, creating direct fallback connection")
        return psycopg2.connect(Config.DATABASE_URL, cursor_factory=RealDictCursor)
    except psycopg2.OperationalError as exc:
        logger.error("Database connection failed from pool: %s", exc)
        raise


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


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

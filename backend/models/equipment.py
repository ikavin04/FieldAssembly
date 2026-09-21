"""Equipment data model."""

from database.connection import get_connection


def get_all_equipment():
    """Fetch all equipment assets from PostgreSQL."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM equipment ORDER BY id;")
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def get_equipment_by_id(equipment_id):
    """Fetch a single equipment asset by ID."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM equipment WHERE id = %s;", (equipment_id,))
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()


def get_equipment_by_asset_code(asset_code):
    """Fetch a single equipment asset by its human-facing asset tag."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM equipment WHERE asset_code = %s;", (asset_code,))
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()

"""Equipment data model with dynamic health status aggregation."""

from database.connection import get_connection


def get_all_equipment(
    search=None,
    status=None,
    equipment_type=None,
    location=None,
    page=None,
    limit=None,
):
    """Fetch equipment assets from PostgreSQL with real-time status and filtering."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        query = """
        WITH eq_status AS (
            SELECT 
                e.id, e.asset_code, e.name, e.equipment_type, e.location, e.description,
                e.operating_limits, e.required_inspection_fields, e.created_at, e.updated_at,
                CASE 
                    WHEN COUNT(sa.id) > 0 THEN 'safety_alert'
                    WHEN COUNT(mt.id) > 0 THEN 'maintenance_required'
                    ELSE 'normal'
                END AS status,
                COUNT(DISTINCT sa.id) AS open_safety_alerts_count,
                COUNT(DISTINCT mt.id) AS open_tickets_count
            FROM equipment e
            LEFT JOIN safety_alerts sa ON sa.equipment_id = e.id AND sa.status = 'open'
            LEFT JOIN maintenance_tickets mt ON mt.equipment_id = e.id AND mt.status IN ('open', 'in_progress')
            GROUP BY e.id
        )
        SELECT *, COUNT(*) OVER() AS total_count
        FROM eq_status
        WHERE 1=1
        """
        params = []
        if search:
            query += (
                " AND (name ILIKE %s OR asset_code ILIKE %s OR "
                "description ILIKE %s OR location ILIKE %s OR equipment_type ILIKE %s)"
            )
            term = f"%{search.strip()}%"
            params.extend([term, term, term, term, term])
        if equipment_type:
            query += " AND equipment_type ILIKE %s"
            params.append(f"%{equipment_type.strip()}%")
        if location:
            query += " AND location ILIKE %s"
            params.append(f"%{location.strip()}%")
        if status:
            query += " AND status = %s"
            params.append(status.strip().lower())

        query += " ORDER BY id ASC"

        if limit is not None:
            query += " LIMIT %s"
            params.append(limit)
            if page is not None and page > 1:
                query += " OFFSET %s"
                params.append((page - 1) * limit)

        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        total = rows[0]["total_count"] if rows else 0

        clean_rows = []
        for r in rows:
            row_dict = dict(r)
            row_dict.pop("total_count", None)
            clean_rows.append(row_dict)

        return clean_rows, total
    finally:
        cur.close()
        conn.close()


def get_equipment_by_id(equipment_id):
    """Fetch a single equipment asset by ID with dynamic status."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 
                e.id, e.asset_code, e.name, e.equipment_type, e.location, e.description,
                e.operating_limits, e.required_inspection_fields, e.created_at, e.updated_at,
                CASE 
                    WHEN COUNT(sa.id) > 0 THEN 'safety_alert'
                    WHEN COUNT(mt.id) > 0 THEN 'maintenance_required'
                    ELSE 'normal'
                END AS status,
                COUNT(DISTINCT sa.id) AS open_safety_alerts_count,
                COUNT(DISTINCT mt.id) AS open_tickets_count
            FROM equipment e
            LEFT JOIN safety_alerts sa ON sa.equipment_id = e.id AND sa.status = 'open'
            LEFT JOIN maintenance_tickets mt ON mt.equipment_id = e.id AND mt.status IN ('open', 'in_progress')
            WHERE e.id = %s
            GROUP BY e.id;
            """,
            (equipment_id,),
        )
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()


def get_equipment_by_asset_code(asset_code):
    """Fetch a single equipment asset by its human-facing asset tag."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 
                e.id, e.asset_code, e.name, e.equipment_type, e.location, e.description,
                e.operating_limits, e.required_inspection_fields, e.created_at, e.updated_at,
                CASE 
                    WHEN COUNT(sa.id) > 0 THEN 'safety_alert'
                    WHEN COUNT(mt.id) > 0 THEN 'maintenance_required'
                    ELSE 'normal'
                END AS status,
                COUNT(DISTINCT sa.id) AS open_safety_alerts_count,
                COUNT(DISTINCT mt.id) AS open_tickets_count
            FROM equipment e
            LEFT JOIN safety_alerts sa ON sa.equipment_id = e.id AND sa.status = 'open'
            LEFT JOIN maintenance_tickets mt ON mt.equipment_id = e.id AND mt.status IN ('open', 'in_progress')
            WHERE e.asset_code = %s
            GROUP BY e.id;
            """,
            (asset_code,),
        )
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()

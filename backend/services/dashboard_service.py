"""Operations Dashboard Service.

Provides real-time aggregation from PostgreSQL for inspections,
equipment health, maintenance tickets, and safety alerts.
"""

from database.connection import get_connection


def _iso(dt):
    if dt is None:
        return None
    return dt.isoformat() if hasattr(dt, "isoformat") else str(dt)


def get_dashboard_summary():
    """Return high-level summary KPIs derived from PostgreSQL."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                COALESCE((SELECT COUNT(*) FROM inspections WHERE status IN ('started', 'in_progress')), 0) AS active_inspections,
                COALESCE((SELECT COUNT(*) FROM inspections WHERE status = 'completed' AND completed_at::date = CURRENT_DATE), 0) AS completed_today,
                COALESCE((SELECT COUNT(*) FROM maintenance_tickets WHERE status IN ('open', 'in_progress')), 0) AS open_work_orders,
                COALESCE((SELECT COUNT(*) FROM safety_alerts WHERE status = 'open'), 0) AS safety_hazards;
            """
        )
        row = cur.fetchone()
        return {
            "active_inspections": int(row["active_inspections"]),
            "completed_today": int(row["completed_today"]),
            "open_work_orders": int(row["open_work_orders"]),
            "safety_hazards": int(row["safety_hazards"]),
        }
    finally:
        cur.close()
        conn.close()


def get_live_feed(limit=15):
    """Return recent inspection activity stream from PostgreSQL."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 
                i.id AS inspection_id,
                i.equipment_id,
                e.name AS equipment_name,
                e.asset_code AS equipment_asset_code,
                i.inspection_type,
                COALESCE(i.summary, 'Jordan (Field Technician)') AS technician,
                i.status,
                i.started_at,
                i.updated_at
            FROM inspections i
            JOIN equipment e ON e.id = i.equipment_id
            ORDER BY i.updated_at DESC, i.id DESC
            LIMIT %s;
            """,
            (limit,),
        )
        rows = cur.fetchall()
        feed = []
        for r in rows:
            feed.append({
                "inspection_id": r["inspection_id"],
                "equipment_id": r["equipment_id"],
                "equipment_name": r["equipment_name"],
                "equipment_asset_code": r["equipment_asset_code"],
                "inspection_type": r["inspection_type"],
                "technician": r["technician"],
                "status": r["status"],
                "started_time": _iso(r["started_at"]),
                "updated_time": _iso(r["updated_at"]),
            })
        return feed
    finally:
        cur.close()
        conn.close()


def get_asset_health():
    """Return current equipment health statuses dynamically derived from alerts/tickets."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 
                e.id AS equipment_id,
                e.asset_code,
                e.name,
                e.equipment_type,
                e.location,
                CASE 
                    WHEN COUNT(sa.id) > 0 THEN 'safety_alert'
                    WHEN COUNT(mt.id) > 0 THEN 'maintenance_required'
                    ELSE 'normal'
                END AS status,
                CASE 
                    WHEN COUNT(sa.id) > 0 THEN 40
                    WHEN COUNT(mt.id) > 0 THEN 70
                    ELSE 100
                END AS health_score,
                COUNT(DISTINCT sa.id) AS safety_alerts_count,
                COUNT(DISTINCT mt.id) AS open_tickets_count,
                MAX(i.started_at) AS last_inspection_at
            FROM equipment e
            LEFT JOIN safety_alerts sa ON sa.equipment_id = e.id AND sa.status = 'open'
            LEFT JOIN maintenance_tickets mt ON mt.equipment_id = e.id AND mt.status IN ('open', 'in_progress')
            LEFT JOIN inspections i ON i.equipment_id = e.id
            GROUP BY e.id
            ORDER BY 
                CASE 
                    WHEN COUNT(sa.id) > 0 THEN 1
                    WHEN COUNT(mt.id) > 0 THEN 2
                    ELSE 3
                END,
                e.id ASC;
            """
        )
        rows = cur.fetchall()
        health = []
        for r in rows:
            health.append({
                "equipment_id": r["equipment_id"],
                "asset_code": r["asset_code"],
                "name": r["name"],
                "equipment_type": r["equipment_type"],
                "location": r["location"],
                "status": r["status"],
                "health_score": r["health_score"],
                "safety_alerts_count": int(r["safety_alerts_count"]),
                "open_tickets_count": int(r["open_tickets_count"]),
                "last_inspection_at": _iso(r["last_inspection_at"]),
            })
        return health
    finally:
        cur.close()
        conn.close()

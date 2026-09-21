"""Safety alert data model."""

from database.connection import get_connection

ALERT_COLUMNS = """
	id, inspection_id, equipment_id, hazard, severity, evidence_text,
	status, created_at, resolved_at
"""


def create_safety_alert(
	inspection_id,
	equipment_id,
	hazard,
	severity="medium",
	evidence_text=None,
	status="open",
):
	"""Insert a safety alert and return the created record."""
	conn = get_connection()
	try:
		cur = conn.cursor()
		cur.execute(
			f"""
			INSERT INTO safety_alerts
				(inspection_id, equipment_id, hazard, severity, evidence_text, status)
			VALUES (%s, %s, %s, %s, %s, %s)
			RETURNING {ALERT_COLUMNS};
			""",
			(inspection_id, equipment_id, hazard, severity, evidence_text, status),
		)
		created = cur.fetchone()
		conn.commit()
		return created
	finally:
		cur.close()
		conn.close()


def get_alert_by_id(alert_id):
	"""Fetch a single safety alert by its primary key ID."""
	conn = get_connection()
	try:
		cur = conn.cursor()
		cur.execute(
			f"SELECT {ALERT_COLUMNS} FROM safety_alerts WHERE id = %s;",
			(alert_id,),
		)
		return cur.fetchone()
	finally:
		cur.close()
		conn.close()


def get_alerts_for_inspection(inspection_id):
	"""Return all safety alerts created for a given inspection."""
	conn = get_connection()
	try:
		cur = conn.cursor()
		cur.execute(
			f"SELECT {ALERT_COLUMNS} FROM safety_alerts WHERE inspection_id = %s ORDER BY id;",
			(inspection_id,),
		)
		return cur.fetchall()
	finally:
		cur.close()
		conn.close()


def get_all_alerts(status=None, severity=None):
	"""Return all safety alerts, optionally filtered by status and/or severity."""
	conn = get_connection()
	try:
		cur = conn.cursor()
		query = f"SELECT {ALERT_COLUMNS} FROM safety_alerts WHERE 1=1"
		params = []
		if status:
			query += " AND status = %s"
			params.append(status)
		if severity:
			query += " AND severity = %s"
			params.append(severity)
		query += " ORDER BY id DESC;"
		cur.execute(query, tuple(params))
		return cur.fetchall()
	finally:
		cur.close()
		conn.close()


def find_duplicate_alert(inspection_id, hazard):
	"""Find an existing alert for the same inspection and hazard to handle idempotent retries."""
	conn = get_connection()
	try:
		cur = conn.cursor()
		cur.execute(
			f"""
			SELECT {ALERT_COLUMNS} FROM safety_alerts
			WHERE inspection_id = %s AND LOWER(TRIM(hazard)) = LOWER(TRIM(%s))
			ORDER BY id LIMIT 1;
			""",
			(inspection_id, hazard),
		)
		return cur.fetchone()
	finally:
		cur.close()
		conn.close()

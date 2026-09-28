"""Safety alert data model."""

import re
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
		# 1. Exact case-insensitive match in database
		cur.execute(
			f"""
			SELECT {ALERT_COLUMNS} FROM safety_alerts
			WHERE inspection_id = %s AND LOWER(TRIM(hazard)) = LOWER(TRIM(%s))
			ORDER BY id ASC LIMIT 1;
			""",
			(inspection_id, hazard),
		)
		row = cur.fetchone()
		if row:
			return row

		# 2. Check for semantic equivalence
		cur.execute(
			f"""
			SELECT {ALERT_COLUMNS} FROM safety_alerts
			WHERE inspection_id = %s
			ORDER BY id ASC;
			""",
			(inspection_id,),
		)
		rows = cur.fetchall()
		if not rows:
			return None

		norm_target = " ".join(hazard.lower().replace(":", " is").split())
		for r in rows:
			row_norm = " ".join(r["hazard"].lower().replace(":", " is").split())
			if row_norm == norm_target:
				return r

		target_tokens = set(re.findall(r"\b\w+\b", hazard.lower()))
		for r in rows:
			row_tokens = set(re.findall(r"\b\w+\b", r["hazard"].lower()))
			overlap = target_tokens.intersection(row_tokens)
			if len(overlap) >= 3 and (
				"overpressure" in overlap
				or "leak" in overlap
				or "smoke" in overlap
				or "fire" in overlap
				or "hazard" in overlap
			):
				return r

		return None
	finally:
		cur.close()
		conn.close()


def update_safety_alert(alert_id, status=None, severity=None, hazard=None):
	"""Update safety alert fields and return the updated record."""
	conn = get_connection()
	try:
		cur = conn.cursor()
		clauses = []
		params = []
		if status is not None:
			clauses.append("status = %s")
			params.append(status)
			if status in ("resolved", "closed"):
				clauses.append("resolved_at = COALESCE(resolved_at, NOW())")
			elif status == "open":
				clauses.append("resolved_at = NULL")
		if severity is not None:
			clauses.append("severity = %s")
			params.append(severity)
		if hazard is not None:
			clauses.append("hazard = %s")
			params.append(hazard)

		if not clauses:
			return get_alert_by_id(alert_id)

		params.append(alert_id)
		set_sql = ", ".join(clauses)
		cur.execute(
			f"""
			UPDATE safety_alerts
			SET {set_sql}
			WHERE id = %s
			RETURNING {ALERT_COLUMNS};
			""",
			tuple(params),
		)
		updated = cur.fetchone()
		conn.commit()
		return updated
	finally:
		cur.close()
		conn.close()

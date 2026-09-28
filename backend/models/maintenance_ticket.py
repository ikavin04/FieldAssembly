"""Maintenance ticket data model."""

import re
from database.connection import get_connection

TICKET_COLUMNS = """
	id, inspection_id, equipment_id, issue, priority, status,
	created_at, updated_at
"""


def create_maintenance_ticket(
	inspection_id,
	equipment_id,
	issue,
	priority="medium",
	status="open",
):
	"""Insert a maintenance ticket and return the created record."""
	conn = get_connection()
	try:
		cur = conn.cursor()
		cur.execute(
			f"""
			INSERT INTO maintenance_tickets
				(inspection_id, equipment_id, issue, priority, status)
			VALUES (%s, %s, %s, %s, %s)
			RETURNING {TICKET_COLUMNS};
			""",
			(inspection_id, equipment_id, issue, priority, status),
		)
		created = cur.fetchone()
		conn.commit()
		return created
	finally:
		cur.close()
		conn.close()


def get_ticket_by_id(ticket_id):
	"""Fetch a single ticket by its primary key ID."""
	conn = get_connection()
	try:
		cur = conn.cursor()
		cur.execute(
			f"SELECT {TICKET_COLUMNS} FROM maintenance_tickets WHERE id = %s;",
			(ticket_id,),
		)
		return cur.fetchone()
	finally:
		cur.close()
		conn.close()


def get_tickets_for_inspection(inspection_id):
	"""Return all maintenance tickets created for a given inspection."""
	conn = get_connection()
	try:
		cur = conn.cursor()
		cur.execute(
			f"SELECT {TICKET_COLUMNS} FROM maintenance_tickets WHERE inspection_id = %s ORDER BY id;",
			(inspection_id,),
		)
		return cur.fetchall()
	finally:
		cur.close()
		conn.close()


def get_all_tickets(status=None, priority=None):
	"""Return all maintenance tickets, optionally filtered by status and/or priority."""
	conn = get_connection()
	try:
		cur = conn.cursor()
		query = f"SELECT {TICKET_COLUMNS} FROM maintenance_tickets WHERE 1=1"
		params = []
		if status:
			query += " AND status = %s"
			params.append(status)
		if priority:
			query += " AND priority = %s"
			params.append(priority)
		query += " ORDER BY id DESC;"
		cur.execute(query, tuple(params))
		return cur.fetchall()
	finally:
		cur.close()
		conn.close()


def find_duplicate_ticket(inspection_id, issue):
	"""Find an existing ticket for the same inspection and issue to handle idempotent retries."""
	conn = get_connection()
	try:
		cur = conn.cursor()
		# 1. Exact case-insensitive match in database
		cur.execute(
			f"""
			SELECT {TICKET_COLUMNS} FROM maintenance_tickets
			WHERE inspection_id = %s AND LOWER(TRIM(issue)) = LOWER(TRIM(%s))
			ORDER BY id ASC LIMIT 1;
			""",
			(inspection_id, issue),
		)
		row = cur.fetchone()
		if row:
			return row

		# 2. Check for semantic equivalence (e.g. "pressure: 167 PSI" vs "Pressure is 167 PSI")
		cur.execute(
			f"""
			SELECT {TICKET_COLUMNS} FROM maintenance_tickets
			WHERE inspection_id = %s
			ORDER BY id ASC;
			""",
			(inspection_id,),
		)
		rows = cur.fetchall()
		if not rows:
			return None

		norm_target = " ".join(issue.lower().replace(":", " is").split())
		for r in rows:
			row_norm = " ".join(r["issue"].lower().replace(":", " is").split())
			if row_norm == norm_target:
				return r

		# Token overlap check for measurement tickets
		target_tokens = set(re.findall(r"\b\w+\b", issue.lower()))
		for r in rows:
			row_tokens = set(re.findall(r"\b\w+\b", r["issue"].lower()))
			overlap = target_tokens.intersection(row_tokens)
			# Must have 'out' and 'range', plus at least one non-stopword token (e.g. field name or numeric value)
			meaningful_overlap = overlap - {"out", "of", "range", "is", "the", "a", "an", "in", "to", "for", "and", "or"}
			if "out" in overlap and "range" in overlap and len(meaningful_overlap) >= 1:
				return r

		return None
	finally:
		cur.close()
		conn.close()


def update_maintenance_ticket(ticket_id, status=None, priority=None, issue=None):
	"""Update maintenance ticket fields and return the updated record."""
	conn = get_connection()
	try:
		cur = conn.cursor()
		clauses = []
		params = []
		if status is not None:
			clauses.append("status = %s")
			params.append(status)
		if priority is not None:
			clauses.append("priority = %s")
			params.append(priority)
		if issue is not None:
			clauses.append("issue = %s")
			params.append(issue)

		if not clauses:
			return get_ticket_by_id(ticket_id)

		clauses.append("updated_at = NOW()")
		params.append(ticket_id)

		set_sql = ", ".join(clauses)
		cur.execute(
			f"""
			UPDATE maintenance_tickets
			SET {set_sql}
			WHERE id = %s
			RETURNING {TICKET_COLUMNS};
			""",
			tuple(params),
		)
		updated = cur.fetchone()
		conn.commit()
		return updated
	finally:
		cur.close()
		conn.close()

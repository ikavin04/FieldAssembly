"""Maintenance ticket data model."""

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
		cur.execute(
			f"""
			SELECT {TICKET_COLUMNS} FROM maintenance_tickets
			WHERE inspection_id = %s AND LOWER(TRIM(issue)) = LOWER(TRIM(%s))
			ORDER BY id LIMIT 1;
			""",
			(inspection_id, issue),
		)
		return cur.fetchone()
	finally:
		cur.close()
		conn.close()

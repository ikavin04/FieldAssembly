"""Inspection persistence helpers."""

from database.connection import get_connection


def create_inspection(equipment_id, inspection_type):
	"""Create an inspection and return the database-generated row."""
	conn = get_connection()
	try:
		cur = conn.cursor()
		cur.execute(
			"""
			INSERT INTO inspections (equipment_id, status, inspection_type)
			VALUES (%s, %s, %s)
			RETURNING id, equipment_id, status, inspection_type, started_at,
					  completed_at, summary, created_at, updated_at;
			""",
			(equipment_id, "started", inspection_type),
		)
		row = cur.fetchone()
		conn.commit()
		cur.close()
		return row
	except Exception:
		conn.rollback()
		raise
	finally:
		conn.close()


def get_inspection_by_id(inspection_id):
	"""Return one inspection with its equipment inspection fields."""
	conn = get_connection()
	try:
		cur = conn.cursor()
		cur.execute(
			"""
			SELECT i.id, i.equipment_id, i.status, i.inspection_type,
				   i.started_at, i.completed_at, i.summary, i.created_at,
				   i.updated_at, e.required_inspection_fields
			FROM inspections AS i
			JOIN equipment AS e ON e.id = i.equipment_id
			WHERE i.id = %s;
			""",
			(inspection_id,),
		)
		return cur.fetchone()
	finally:
		cur.close()
		conn.close()


def complete_inspection(inspection_id, summary=None):
	"""Mark an inspection as completed and return the updated row."""
	conn = get_connection()
	try:
		cur = conn.cursor()
		cur.execute(
			"""
			UPDATE inspections
			SET status = 'completed',
				completed_at = COALESCE(completed_at, NOW()),
				summary = COALESCE(%s, summary),
				updated_at = NOW()
			WHERE id = %s
			RETURNING id, equipment_id, status, inspection_type, started_at,
					  completed_at, summary, created_at, updated_at;
			""",
			(summary, inspection_id),
		)
		row = cur.fetchone()
		conn.commit()
		cur.close()
		return row
	except Exception:
		conn.rollback()
		raise
	finally:
		conn.close()


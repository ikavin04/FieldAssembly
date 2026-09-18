"""Observation persistence helpers."""

from database.connection import get_connection


OBSERVATION_COLUMNS = """
	id, inspection_id, field_name, value, unit, evidence_text,
	source_timestamp, confidence, created_at
"""


def get_observations_for_inspection(inspection_id):
	"""Return observations in capture order for one inspection."""
	conn = get_connection()
	try:
		cur = conn.cursor()
		cur.execute(
			f"SELECT {OBSERVATION_COLUMNS} FROM observations "
			"WHERE inspection_id = %s ORDER BY id;",
			(inspection_id,),
		)
		return cur.fetchall()
	finally:
		cur.close()
		conn.close()


def find_duplicate_observation(inspection_id, field_name, value, evidence_text):
	"""Find an exact prior observation for idempotent tool retries."""
	conn = get_connection()
	try:
		cur = conn.cursor()
		cur.execute(
			f"SELECT {OBSERVATION_COLUMNS} FROM observations "
			"WHERE inspection_id = %s AND field_name = %s AND value = %s "
			"AND evidence_text IS NOT DISTINCT FROM %s ORDER BY id LIMIT 1;",
			(inspection_id, field_name, value, evidence_text),
		)
		return cur.fetchone()
	finally:
		cur.close()
		conn.close()


def create_observation(
	inspection_id,
	field_name,
	value,
	unit,
	evidence_text,
	source_timestamp,
	confidence,
):
	"""Insert an observation and return the database-generated row."""
	conn = get_connection()
	try:
		cur = conn.cursor()
		cur.execute(
			f"""
			INSERT INTO observations
				(inspection_id, field_name, value, unit, evidence_text,
				 source_timestamp, confidence)
			VALUES (%s, %s, %s, %s, %s, %s, %s)
			RETURNING {OBSERVATION_COLUMNS};
			""",
			(
				inspection_id,
				field_name,
				value,
				unit,
				evidence_text,
				source_timestamp,
				confidence,
			),
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

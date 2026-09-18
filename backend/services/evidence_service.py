"""Evidence validation for observation capture."""

import math


def normalize_evidence(evidence_text, source_timestamp, confidence):
	"""Validate and normalize evidence fields without inventing transcript data."""
	if evidence_text is not None:
		if not isinstance(evidence_text, str) or not evidence_text.strip():
			raise ValueError("evidence_text must be a non-empty string or null")
		evidence_text = evidence_text.strip()

	if source_timestamp is not None:
		if isinstance(source_timestamp, bool) or not isinstance(source_timestamp, (int, float)):
			raise ValueError("source_timestamp must be a non-negative number or null")
		if not math.isfinite(source_timestamp) or source_timestamp < 0:
			raise ValueError("source_timestamp must be a non-negative number or null")

	if confidence is not None:
		if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
			raise ValueError("confidence must be between 0 and 1 or null")
		if not math.isfinite(confidence) or not 0 <= confidence <= 1:
			raise ValueError("confidence must be between 0 and 1 or null")

	return evidence_text, source_timestamp, confidence

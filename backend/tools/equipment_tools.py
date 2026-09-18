"""
Equipment Tools

Tool: get_equipment_profile
"""

from models.equipment import get_equipment_by_asset_code


def get_equipment_profile(asset_code):
	"""Return the public inspection profile for one equipment asset."""
	equipment = get_equipment_by_asset_code(asset_code)
	if not equipment:
		return None

	return {
		"id": equipment["id"],
		"asset_code": equipment["asset_code"],
		"name": equipment["name"],
		"equipment_type": equipment["equipment_type"],
		"location": equipment.get("location"),
		"description": equipment.get("description"),
		"operating_limits": equipment.get("operating_limits") or {},
		"required_inspection_fields": equipment.get("required_inspection_fields") or [],
	}

# -*- coding: utf-8 -*-
"""
Canonical Planning DocType names — must match planning_sheet*.json and live DB (`tabPlanning sheet`).

Use these constants anywhere code references the doctype string (no literals like "Planning Sheet").
"""

PLANNING_SHEET = "Planning sheet"
PLANNING_SHEET_ITEM = "Planning sheet Item"

# Must match Planning Table `unit` Select options on sites using these boards.
REWINDING_UNIT_L3 = "TSNPL - L3 REWINDING MACHINE"
REWINDING_UNIT_L4 = "JSB - L4 REWINDING MACHINE"
REWINDING_UNIT_L5 = "JSB - L5 REWINDING MACHINE"
REWINDING_UNASSIGNED_UNIT = "Unassigned rewinding machine"


def normalize_planning_unit_for_select(raw, _depth=0):
    """Map free-text to exact options on Planning Table / Planning sheet Item `unit` (Select)."""
    if raw is None:
        return "UNASSIGNED"
    s = str(raw).strip()
    if not s:
        return "UNASSIGNED"
    # Color Chart matrix column id: sheetCode|unit|planCode|gsm|quality — normalize only the unit segment.
    if _depth == 0 and "|" in s:
        parts = [p.strip() for p in s.split("|")]
        if len(parts) >= 2 and parts[1]:
            return normalize_planning_unit_for_select(parts[1], _depth + 1)
    allowed = (
        "UNASSIGNED",
        "Unit 1",
        "Unit 2",
        "Unit 3",
        "Unit 4",
        "Mixed",
        "Lamination Unit",
        "Slitting Unit",
        REWINDING_UNIT_L3,
        REWINDING_UNIT_L4,
        REWINDING_UNIT_L5,
        REWINDING_UNASSIGNED_UNIT,
        "VR - 1200MM BOPP PRINTING MACHINE",
    )
    if s in allowed:
        return s
    u = s.upper().replace(" ", "").replace("_", "")
    if u in ("UNASSIGNED", "NONE", "NA", ""):
        return "UNASSIGNED"
    # Exact "Mixed" only — substring match caused false positives (e.g. composite keys containing |Mixed|).
    if u == "MIXED":
        return "Mixed"
    if u == "LAMINATIONUNIT" or s.strip().lower() == "lamination unit":
        return "Lamination Unit"
    if u == "SLITTINGUNIT" or s.strip().lower() == "slitting unit":
        return "Slitting Unit"
    if "REWINDING" in u or "REWINDINGMACHINE" in u.replace(" ", ""):
        if "L3" in u and "TSNPL" in u:
            return REWINDING_UNIT_L3
        if "L4" in u and "JSB" in u:
            return REWINDING_UNIT_L4
        if "L5" in u and "JSB" in u:
            return REWINDING_UNIT_L5
        if "UNASSIGNED" in u:
            return REWINDING_UNASSIGNED_UNIT
    if "VR1200MMBOPPPRINTINGMACHINE" in u or "1200MMBOPP" in u:
        return "VR - 1200MM BOPP PRINTING MACHINE"
    for i in (1, 2, 3, 4):
        if f"UNIT{i}" in u:
            return f"Unit {i}"
    return "UNASSIGNED"


# Old names from earlier app JSON / deploys (for migration helpers only).
LEGACY_PLANNING_SHEET = "Planning Sheet"
LEGACY_PLANNING_SHEET_ITEM = "Planning Sheet Item"

CANONICAL_PLANNING_LINE_UNIT_OPTIONS = "\n".join(
	(
		"UNASSIGNED",
		"Unit 1",
		"Unit 2",
		"Unit 3",
		"Unit 4",
		"Lamination Unit",
		"Slitting Unit",
		REWINDING_UNIT_L3,
		REWINDING_UNIT_L4,
		REWINDING_UNIT_L5,
		REWINDING_UNASSIGNED_UNIT,
		"VR - 1200MM BOPP PRINTING MACHINE",
	)
)


def _canonical_planning_unit_option_line_set():
	return frozenset(
		line.strip()
		for line in (CANONICAL_PLANNING_LINE_UNIT_OPTIONS or "").split("\n")
		if line.strip()
	)


def _stored_unit_select_outdated(opts):
	got = frozenset(line.strip() for line in str(opts or "").split("\n") if line.strip())
	return got != _canonical_planning_unit_option_line_set()


def ensure_planning_line_unit_docfield_options():
	"""Keep ``tabDocField`` for Planning Table + Planning sheet Item ``unit`` in sync (see production_entry app)."""
	import frappe

	for dt in ("Planning Table", PLANNING_SHEET_ITEM):
		try:
			opts = frappe.db.get_value(
				"DocField",
				{"parent": dt, "fieldname": "unit", "fieldtype": "Select"},
				"options",
			)
		except Exception:
			continue
		if not _stored_unit_select_outdated(opts):
			continue
		try:
			frappe.db.sql(
				"""
				UPDATE `tabDocField`
				SET `options`=%s
				WHERE `parent`=%s AND `fieldname`=%s AND `fieldtype`='Select'
				""",
				(CANONICAL_PLANNING_LINE_UNIT_OPTIONS, dt, "unit"),
			)
			for ps in frappe.get_all(
				"Property Setter",
				filters={"doc_type": dt, "field_name": "unit", "property": "options"},
				pluck="name",
			) or []:
				try:
					frappe.delete_doc("Property Setter", ps, force=True, ignore_missing=True)
				except Exception:
					pass
		except Exception:
			frappe.log_error(frappe.get_traceback(), f"ensure_planning_line_unit_docfield_options:{dt}")
	try:
		frappe.clear_cache(doctype="Planning Table")
		frappe.clear_cache(doctype=PLANNING_SHEET_ITEM)
	except Exception:
		pass

import frappe
from frappe import _
from frappe.utils import getdate, flt


@frappe.whitelist()
def get_kanban_board(start_date, end_date):
	start_date = getdate(start_date)
	end_date = getdate(end_date)

	planning_sheets = frappe.get_all(
		"Planning sheet",
		filters={
			"dod": ["between", [start_date, end_date]],
			"docstatus": ["<", 2]
		},
		fields=["name", "customer", "party_code", "planning_status", "dod"]
	)

	data = []
	for sheet in planning_sheets:
		items = frappe.get_all(
			"Planning Sheet Item",
			filters={"parent": sheet.name},
			fields=["unit", "gsm", "weight_per_roll", "qty", "item_name"]
		)

		total_weight = 0.0
		unit = ""
		gsm = ""
		quality = ""

		if items:
			# Get unit from the first item (all items in a sheet share the same unit)
			unit = items[0].get("unit") or ""
			gsm = items[0].get("gsm") or ""
			quality = items[0].get("item_name") or ""
			for item in items:
				total_weight += flt(item.weight_per_roll) * flt(item.qty)

		if not unit:
			continue  # Skip sheets with no unit assigned

		data.append({
			"name": sheet.name,
			"customer": sheet.customer,
			"party_code": sheet.party_code,
			"planning_status": sheet.planning_status or "Draft",
			"dod": str(sheet.dod) if sheet.dod else "",
			"unit": unit,
			"total_weight": total_weight,
			"quality": quality,
			"gsm": gsm
		})

	return data


@frappe.whitelist()
def update_schedule(doc_name, unit, date, index=0):
	HARD_LIMITS = {
		"Unit 1": 4.4,
		"Unit 2": 12.0,
		"Unit 3": 9.0,
		"Unit 4": 5.5
	}

	SOFT_LIMITS = {
		"Unit 1": 4.0,
		"Unit 2": 9.0,
		"Unit 3": 7.8,
		"Unit 4": 4.0
	}

	if unit not in HARD_LIMITS:
		frappe.throw(_("Invalid Unit"))

	target_date = getdate(date)

	# Get current doc weight
	current_doc_items = frappe.get_all(
		"Planning Sheet Item",
		filters={"parent": doc_name},
		fields=["weight_per_roll", "qty"]
	)

	current_weight = 0.0
	for item in current_doc_items:
		current_weight += flt(item.weight_per_roll) * flt(item.qty)

	# Convert to Tons (weight_per_roll is in kg)
	current_weight_tons = current_weight / 1000.0

	# Get existing weight in target unit for that date
	# Find all Planning sheets with items assigned to this unit on the target date
	existing_sheets = frappe.get_all(
		"Planning sheet",
		filters={
			"dod": target_date,
			"name": ["!=", doc_name],
			"docstatus": ["<", 2]
		},
		fields=["name"]
	)

	total_existing_weight = 0.0
	for sheet in existing_sheets:
		items = frappe.get_all(
			"Planning Sheet Item",
			filters={"parent": sheet.name, "unit": unit},
			fields=["weight_per_roll", "qty"]
		)
		for i in items:
			total_existing_weight += flt(i.weight_per_roll) * flt(i.qty)

	total_existing_weight_tons = total_existing_weight / 1000.0
	new_total = total_existing_weight_tons + current_weight_tons

	if new_total > HARD_LIMITS[unit]:
		frappe.throw(
			_("Capacity Exceeded! {0} allows max {1}T. New Total: {2:.2f}T").format(
				unit, HARD_LIMITS[unit], new_total
			)
		)

	if new_total > SOFT_LIMITS[unit]:
		frappe.msgprint(
			_("Warning: Soft Limit Exceeded for {0}").format(unit),
			alert=True
		)

	# Update all child items' unit field
	frappe.db.sql("""
		UPDATE `tabPlanning Sheet Item`
		SET unit = %s
		WHERE parent = %s
	""", (unit, doc_name))

	# Update delivery date on parent
	frappe.db.set_value("Planning sheet", doc_name, "dod", target_date)

	frappe.db.commit()

	return {"status": "success", "new_total": new_total}

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
		fields=["name", "customer", "party_code", "planning_status", "dod", "ordered_date", "docstatus"]
	)

	data = []
	for sheet in planning_sheets:
		items = frappe.get_all(
			"Planning Sheet Item",
			filters={"parent": sheet.name},
			fields=["*"],
			order_by="idx"
		)

		if not items:
			continue

		# Get unit from the first item
		unit = items[0].get("unit") or ""
		if not unit:
			continue

		total_weight = 0.0
		item_details = []
		for item in items:
			item_qty = flt(item.get("qty", 0))
			total_weight += item_qty

			item_details.append({
				"item_name": item.get("item_name") or "",
				"quality": item.get("custom_quality") or item.get("quality") or "",
				"color": item.get("color") or item.get("colour") or "",
				"gsm": item.get("gsm") or "",
				"qty": item_qty,
			})

		data.append({
			"name": sheet.name,
			"customer": sheet.customer,
			"party_code": sheet.party_code,
			"planning_status": sheet.planning_status or "Draft",
			"dod": str(sheet.dod) if sheet.dod else "",
			"ordered_date": str(sheet.ordered_date) if sheet.get("ordered_date") else "",
			"docstatus": sheet.docstatus,
			"unit": unit,
			"total_weight": total_weight,
			"items": item_details,
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
		current_weight += flt(item.get("qty", 0))

	# Convert to Tons (weight_per_roll is in kg)
	current_weight_tons = current_weight / 1000.0

	# Get existing weight in target unit for that date
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
			total_existing_weight += flt(i.get("qty", 0))

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


@frappe.whitelist()
def get_color_chart_data(date):
	target_date = getdate(date)

	# Get all planning sheets for this date (by order date)
	planning_sheets = frappe.get_all(
		"Planning sheet",
		filters={
			"ordered_date": target_date,
			"docstatus": ["<", 2]
		},
		fields=["name", "customer", "party_code", "dod", "ordered_date", "planning_status"],
		order_by="creation asc"
	)

	data = []
	for sheet in planning_sheets:
		items = frappe.get_all(
			"Planning Sheet Item",
			filters={"parent": sheet.name},
			fields=["*"],
			order_by="idx"
		)

		for item in items:
			unit = item.get("unit") or ""
			# if not unit: continue  <-- Allow unassigned items so Auto Alloc can work


			color = item.get("color") or item.get("colour") or ""
			if not color:
				continue

			data.append({
				"name": "{}-{}".format(sheet.name, item.get("idx", 0)),
				"itemName": item.name,
				"planningSheet": sheet.name,
				"customer": sheet.customer,
				"partyCode": sheet.party_code,
				"planningStatus": sheet.planning_status or "Draft",
				"color": color.upper().strip(),
				"quality": item.get("custom_quality") or item.get("quality") or "",
				"gsm": item.get("gsm") or "",
				"qty": flt(item.get("qty", 0)),
				"width": flt(item.get("width") or item.get("custom_width") or item.get("width_inches") or item.get("width_inch") or item.get("width_in") or 0),
				"debug_keys": list(item.keys()),
				"unit": unit,
			})

	return data


@frappe.whitelist()
def update_item_unit(item_name, unit):
	if not item_name or not unit:
		frappe.throw(_("Item Name and Unit are required"))

	frappe.db.set_value("Planning Sheet Item", item_name, "unit", unit)
	return {"status": "success"}


@frappe.whitelist()
def update_items_bulk(items):
	import json
	if isinstance(items, str):
		items = json.loads(items)
	
	for item in items:
		if item.get("name") and item.get("unit"):
			frappe.db.set_value("Planning Sheet Item", item.get("name"), "unit", item.get("unit"))
	
	return {"status": "success"}


@frappe.whitelist()
def get_previous_production_date(date):
	prev_date = frappe.db.get_value(
		"Planning sheet",
		{"ordered_date": ["<", date], "docstatus": ["<", 2]},
		"ordered_date",
		order_by="ordered_date desc"
	)
	return prev_date

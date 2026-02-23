import frappe
from frappe import _
from frappe.utils import getdate, flt


# --- DEFINITIONS ---
UNIT_1 = ["PREMIUM", "PLATINUM", "SUPER PLATINUM", "GOLD", "SILVER"]
UNIT_2 = ["GOLD", "SILVER", "BRONZE", "CLASSIC", "SUPER CLASSIC", "LIFE STYLE", "ECO SPECIAL", "ECO GREEN", "SUPER ECO", "ULTRA", "DELUXE"]
UNIT_3 = ["PREMIUM", "PLATINUM", "SUPER PLATINUM", "GOLD", "SILVER", "BRONZE"]
UNIT_4 = ["PREMIUM", "GOLD", "SILVER", "BRONZE"]

# ... Limits ...
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

UNIT_QUALITY_MAP = {
	"Unit 1": UNIT_1,
	"Unit 2": UNIT_2,
	"Unit 3": UNIT_3,
	"Unit 4": UNIT_4
}

# Cache for column existence check
_planned_date_col_exists = None
def _has_planned_date_column():
	"""Check if custom_planned_date column exists on Planning sheet table."""
	global _planned_date_col_exists
	if _planned_date_col_exists is None:
		try:
			frappe.db.sql("SELECT custom_planned_date FROM `tabPlanning sheet` LIMIT 1")
			_planned_date_col_exists = True
		except Exception:
			_planned_date_col_exists = False
	return _planned_date_col_exists

def _effective_date_expr(alias="p"):
	"""Returns SQL expression for effective date."""
	if _has_planned_date_column():
		return f"COALESCE({alias}.custom_planned_date, {alias}.ordered_date)"
	return f"{alias}.ordered_date"

def get_unit_load(date, unit):
	"""Calculates current load (in Tons) for a unit on a given date.
	Uses custom_planned_date if set, otherwise falls back to ordered_date."""
	eff = _effective_date_expr("p")
	sql = f"""
		SELECT SUM(i.qty) as total_qty
		FROM `tabPlanning Sheet Item` i
		JOIN `tabPlanning sheet` p ON i.parent = p.name
		WHERE {eff} = %s 
		  AND i.unit = %s AND p.docstatus < 2 AND i.docstatus < 2
	"""
	result = frappe.db.sql(sql, (date, unit))
	return flt(result[0][0]) / 1000.0 if result and result[0][0] else 0.0

def find_best_slot(item_qty_tons, quality, preferred_unit, start_date, recursion_depth=0):
	"""
	Recursive function to find the best available slot (Date/Unit).
	Order:
	1. Preferred Unit (on Date)
	2. Neighbor Units (on Date) - Must support Quality
	3. Next Day (Recurse)
	"""
	if recursion_depth > 30: # Look ahead max 30 days
		return None # No slot found

	check_date = getdate(start_date)
	
	# 1. Check Preferred Unit
	if preferred_unit and preferred_unit in HARD_LIMITS:
		current_load = get_unit_load(check_date, preferred_unit)
		if current_load + item_qty_tons <= HARD_LIMITS[preferred_unit]:
			return {"date": check_date, "unit": preferred_unit}

	# 2. Check Neighbor Units (on same date)
	compatible_units = []
	for unit, valid_qualities in UNIT_QUALITY_MAP.items():
		if unit == preferred_unit: continue
		if quality in valid_qualities:
			compatible_units.append(unit)
	
	# Check Neighbors
	for unit in ["Unit 1", "Unit 2", "Unit 3", "Unit 4"]:
		if unit in compatible_units and unit in HARD_LIMITS:
			load = get_unit_load(check_date, unit)
			if load + item_qty_tons <= HARD_LIMITS[unit]:
				return {"date": check_date, "unit": unit}

	# 3. Next Day (Recurse)
	next_date = frappe.utils.add_days(check_date, 1)
	return find_best_slot(item_qty_tons, quality, preferred_unit, next_date, recursion_depth + 1)


def get_preferred_unit(quality):
	"""Determines the best unit based on Item Quality."""
	if not quality: return "Unit 1"
	# check strict order as per original logic
	if quality in UNIT_QUALITY_MAP["Unit 1"]: return "Unit 1"
	if quality in UNIT_QUALITY_MAP["Unit 2"]: return "Unit 2"
	if quality in UNIT_QUALITY_MAP["Unit 3"]: return "Unit 3"
	if quality in UNIT_QUALITY_MAP["Unit 4"]: return "Unit 4"
	return "Unit 1"

@frappe.whitelist()
def update_sequence(items):
	"""
	Updates the 'idx' of items based on the provided list.
	items: [{"name": "item_name", "idx": 1}, ...]
	"""
	import json
	if isinstance(items, str):
		items = json.loads(items)
		
	for item in items:
		if item.get("name") and item.get("idx") is not None:
			# Use SQL to bypass DocStatus immutability for reordering
			frappe.db.sql("""
				UPDATE `tabPlanning Sheet Item`
				SET idx = %s
				WHERE name = %s
			""", (item.get("idx"), item.get("name")))
			
	frappe.db.commit()
	return {"status": "success"}


@frappe.whitelist()
def update_schedule(item_name, unit, date, index=0, force_move=0, perform_split=0, plan_name=None, strict_next_day=0):
	"""
	Moves a specific Planning Sheet Item to a new unit/date.
	If date changes, the item is re-parented to a suitable Planning Sheet for that date.
	"""
	target_date = getdate(date)
	force_move = flt(force_move)
	perform_split = flt(perform_split)
	strict_next_day = flt(strict_next_day)
	
	# 1. Get Item and Parent Details
	item = frappe.get_doc("Planning Sheet Item", item_name)
	parent_sheet = frappe.get_doc("Planning sheet", item.parent)
	
	# 2. Check Docstatus (Requirement: Cannot move submitted/cancelled)
	if parent_sheet.docstatus != 0:
		frappe.throw(_("Cannot move items from a {} Planning Sheet.").format(
			"Submitted" if parent_sheet.docstatus == 1 else "Cancelled"
		))

	item_wt_tons = flt(item.qty) / 1000.0
	quality = item.custom_quality or ""
	
	# 3. Check Capacity of Target Slot
	current_load = get_unit_load(target_date, unit)
	limit = HARD_LIMITS.get(unit, 999.0)
	
	# If we are moving within the same unit/date (just reordering), ignore its own weight
	is_same_slot = (parent_sheet.ordered_date == target_date and item.unit == unit)
	load_for_check = current_load if is_same_slot else (current_load + item_wt_tons)

	if load_for_check > limit:
		# Exceeds Capacity
		available_space = max(0, limit - current_load)
		
		# Scenario A: SMART MOVE (find best slot - checks neighbor units first, then next day)
		if force_move:
			best_slot = find_best_slot(item_wt_tons, quality, unit, target_date)
			if not best_slot:
				frappe.throw(_("Could not find a valid slot on future dates."))
			final_unit = best_slot["unit"]
			final_date = getdate(best_slot["date"])
			
		# Scenario A2: STRICT NEXT DAY (same unit, next day - re-check capacity)
		elif strict_next_day:
			next_day = frappe.utils.add_days(target_date, 1)
			next_load = get_unit_load(next_day, unit)
			next_limit = HARD_LIMITS.get(unit, 999.0)
			
			if next_load + item_wt_tons > next_limit:
				# Next day also full — ask user again
				return {
					"status": "overflow",
					"available": max(0, next_limit - next_load),
					"limit": next_limit,
					"current_load": next_load,
					"order_weight": item_wt_tons,
					"target_date": str(next_day),
					"target_unit": unit,
					"message": f"Next day ({next_day}) is also full for {unit}"
				}
			else:
				final_unit = unit
				final_date = next_day
			
		# Scenario B: SMART SPLIT
		elif perform_split:
			if available_space < 0.1:
				frappe.throw(_("Available space ({:.3f}T) is too small to split (Min 0.1T).").format(available_space))
			
			# Logic: Reduce original item weight, create new item in Target Unit
			remainder_qty = item.qty - (available_space * 1000.0)
			split_qty = available_space * 1000.0
			
			# Update Original Item -> This will go to Best Slot
			item.qty = remainder_qty
			item.save()
			
			# Create New Item -> This stays in Target Unit/Date
			new_item = frappe.copy_doc(item)
			new_item.name = None
			new_item.qty = split_qty
			new_item.unit = unit
			new_item.custom_is_split = 1
			new_item.custom_split_from = item.name
			new_item.insert()
			
			# Find best slot for the REMAINDER (Original item)
			best_slot_rem = find_best_slot(remainder_qty / 1000.0, quality, unit, target_date)
			if not best_slot_rem:
				frappe.throw(_("Could not find slot for remaining quantity."))
			
			# Move Original Item to the best slot
			# Note: We recurse or just manually move? Manually move is safer here.
			# But we need to handle re-parenting if date is different.
			_move_item_to_slot(item, best_slot_rem["unit"], best_slot_rem["date"], None, plan_name)
			
			frappe.db.commit()
			return {"status": "success", "message": "Split successful"}
			
		else:
			# Scenario C: OVERFLOW (Ask User)
			return {
				"status": "overflow",
				"available": available_space,
				"limit": limit,
				"current_load": current_load,
				"order_weight": item_wt_tons
			}
	else:
		final_unit = unit
		final_date = target_date

	# 4. Perform Move
	# Convert index to int if provided
	idx_val = int(index) if index else None
	# If index is 0/None, maybe append? 
	# User drags to specific position. index is the new index in the list.
	# We should respect it.
	
	_move_item_to_slot(item, final_unit, final_date, idx_val, plan_name)
	
	frappe.db.commit()
	return {
		"status": "success", 
		"moved_to": {"date": final_date, "unit": final_unit}
	}

def _move_item_to_slot(item_doc, unit, date, new_idx=None, plan_name=None):
	"""Internal helper to move a Planning Sheet Item to a specific slot.
	Re-parents item if date changes, avoiding moving the entire order."""
	target_date = getdate(date)
	source_parent = frappe.get_doc("Planning sheet", item_doc.parent)
	
	source_effective_date = getdate(source_parent.get("custom_planned_date") or source_parent.ordered_date)
	
	# 1. Reparent if date is changing
	if source_effective_date != target_date:
		# Find existing sheet for this Sales Order on target date
		has_col = _has_planned_date_column()
		date_cond = "COALESCE(custom_planned_date, ordered_date) = %(target)s" if has_col else "ordered_date = %(target)s"
		so_cond = "sales_order = %(so)s" if source_parent.sales_order else "party_code = %(party)s"
		
		existing = frappe.db.sql(f"""
			SELECT name FROM `tabPlanning sheet`
			WHERE {so_cond}
			  AND {date_cond}
			  AND docstatus < 2
			  AND name != %(source)s
			LIMIT 1
		""", {
			"so": source_parent.sales_order,
			"party": source_parent.party_code,
			"target": target_date,
			"source": source_parent.name
		})
		
		if existing:
			new_parent_name = existing[0][0]
		else:
			# Create new sheet for the target date
			new_sheet = frappe.copy_doc(source_parent)
			new_sheet.name = None
			new_sheet.set("items", []) # clear items
			if has_col:
				new_sheet.custom_planned_date = target_date
			else:
				new_sheet.ordered_date = target_date
			new_sheet.insert(ignore_permissions=True)
			new_parent_name = new_sheet.name
		
		# Reparent the item
		item_doc.parent = new_parent_name
		item_doc.save(ignore_permissions=True)
		
		# Clean up source parent if empty
		if frappe.db.count("Planning Sheet Item", {"parent": source_parent.name}) == 0:
			frappe.delete_doc("Planning sheet", source_parent.name, ignore_permissions=True)

	# 2. Handle IDX Shifting if inserting at specific position
	# Update Item unit and parent first
	item_doc.unit = unit
	item_doc.save(ignore_permissions=True)

	if new_idx is not None:
		try:
			eff = _effective_date_expr("sheet")
			sql_fetch = f"""
				SELECT item.name 
				FROM `tabPlanning Sheet Item` item
				JOIN `tabPlanning sheet` sheet ON item.parent = sheet.name
				WHERE {eff} = %s AND item.unit = %s AND item.name != %s
				ORDER BY item.idx ASC, item.creation ASC
			"""
			other_items = frappe.db.sql(sql_fetch, (target_date, unit, item_doc.name))
			others = [r[0] for r in other_items]
			
			insert_pos = max(0, new_idx - 1)
			others.insert(insert_pos, item_doc.name)
			
			for i, name in enumerate(others):
				frappe.db.sql("UPDATE `tabPlanning Sheet Item` SET idx = %s WHERE name = %s", (i + 1, name))
		except Exception as e:
			frappe.log_error(f"Global Sequence Fix Error: {str(e)}")


@frappe.whitelist()
def get_kanban_board(start_date, end_date):
	start_date = getdate(start_date)
	end_date = getdate(end_date)
	
	sheets = frappe.get_all(
		"Planning sheet",
		filters={
			"ordered_date": ["between", [start_date, end_date]],
			"docstatus": ["<", 2]
		},
		fields=["name", "customer", "party_code", "ordered_date", "dod", "planning_status", "docstatus"],
		order_by="ordered_date asc"
	)
	
	data = []
	for sheet in sheets:
		items = frappe.get_all(
			"Planning Sheet Item",
			filters={"parent": sheet.name},
			fields=["qty", "unit", "custom_quality", "color", "gsm"],
			order_by="idx"
		)
		
		# Map custom_quality to quality for frontend consistency
		for item in items:
			item["quality"] = item.get("custom_quality")

		total_weight = sum([flt(d.qty) for d in items])
		
		# Determine Major Unit
		unit = "Unit 1" # Default
		if items:
			# Get most frequent unit
			units = [d.unit for d in items if d.unit]
			if units:
				unit = max(set(units), key=units.count)
		
		data.append({
			"name": sheet.name,
			"customer": sheet.customer,
			"party_code": sheet.party_code,
			"ordered_date": sheet.ordered_date,
			"dod": sheet.dod,
			"planning_status": sheet.planning_status,
			"docstatus": sheet.docstatus,
			"unit": unit,
			"total_weight": total_weight,
			"items": items
		})
		
	return data

# ... (Existing get_color_chart_data, update_item_unit, update_items_bulk, etc. - UNCHANGED) ...
# I will retain them in the file content if I am replacing strict block, but if I am replacing a range I need to be careful.
# The previous `update_schedule` ended at line 165. `get_color_chart_data` followed.
# I am targeting `HARD_LIMITS` definition (line 6) down to `update_schedule` end?
# Wait, `HARD_LIMITS` is at the top. I should probably insert the helper functions and replace `update_schedule`.
# `create_planning_sheet_from_so` is further down (line 636).
# I will make TWO edits.
# 1. Replace `update_schedule` and add helpers. (This step)
# 2. Update `create_planning_sheet_from_so`.

# Actually, I can do `create_planning_sheet_from_so` implementation now if I include it in the replacement chunk
# But it's far away. I'll stick to `update_schedule` and helpers first.
# Wait, I need `UNIT_QUALITY_MAP` for `create_planning_sheet_from_so` too.
# I'll define it globally.

# The `update_schedule` function in original file is lines 95-164.
# `HARD_LIMITS` is 6-11.
# I will replace from `HARD_LIMITS` (line 6) to the end of `update_schedule` (line 164).
# And keep `get_kanban_board` (lines 33-91) ??
# Ah, `get_kanban_board` is in between `get_unit_load` and `update_schedule`.
# Ref:
# 6-18: Limits
# 21-30: get_unit_load
# 33-91: get_kanban_board
# 94-164: update_schedule

# So I should:
# 1. Update Limits and Add Helpers at top? Or just replace `update_schedule` and add helpers there?
# Python allows defining helpers anywhere ensuring usage is after def? No, order matters if running script but inside module it's fine.
# But `find_best_slot` needs `UNIT_QUALITY_MAP`.
# I'll put `UNIT_QUALITY_MAP` near `HARD_LIMITS`.

# Strategy:
# Replace Lines 6-30 (Limits + get_unit_load) with New Limits + Map + Helpers.
# Replace Lines 94-164 (update_schedule) with New `update_schedule`.

# Let's do it in one go if possible? No, `get_kanban_board` is in the middle.
# I will use `multi_replace_file_content`.

# ... (get_color_chart_data etc are below 164)



@frappe.whitelist()
def get_color_chart_data(date=None, start_date=None, end_date=None, plan_name=None, mode=None):
	# PULL MODE: Return raw items by ordered_date, exclude items with Work Orders
	if mode == "pull" and date:
		target_date = getdate(date)
		items = frappe.db.sql("""
			SELECT 
				i.name as itemName, i.item_code, i.item_name, i.qty, i.uom, i.unit,
				i.color, i.custom_quality as quality, i.gsm, i.idx,
				p.name as planningSheet, p.party_code as partyCode, p.customer,
				p.ordered_date, p.dod, p.sales_order as salesOrder
			FROM `tabPlanning Sheet Item` i
			JOIN `tabPlanning sheet` p ON i.parent = p.name
			WHERE p.ordered_date = %s AND p.docstatus < 2
			ORDER BY i.unit, i.idx
		""", (target_date,), as_dict=True)
		
		# Check which planning sheets have Work Orders (those can't be moved)
		if items:
			sheet_names = list(set(it.planningSheet for it in items))
			so_names = list(set(it.salesOrder for it in items if it.salesOrder))
			
			wo_sheets = set()
			# Check WO via Sales Order
			if so_names:
				fmt = ','.join(['%s'] * len(so_names))
				wo_data = frappe.db.sql(f"""
					SELECT DISTINCT sales_order FROM `tabWork Order`
					WHERE sales_order IN ({fmt}) AND docstatus < 2
				""", tuple(so_names))
				wo_sos = set(r[0] for r in wo_data)
				for it in items:
					if it.salesOrder and it.salesOrder in wo_sos:
						wo_sheets.add(it.planningSheet)
			
			# Check WO via Planning Sheet custom field
			if sheet_names:
				fmt2 = ','.join(['%s'] * len(sheet_names))
				try:
					wo_ps = frappe.db.sql(f"""
						SELECT DISTINCT custom_planning_sheet FROM `tabWork Order`
						WHERE custom_planning_sheet IN ({fmt2}) AND docstatus < 2
					""", tuple(sheet_names))
					for r in wo_ps:
						wo_sheets.add(r[0])
				except Exception:
					pass
			
			# Filter out items that have WO
			items = [it for it in items if it.planningSheet not in wo_sheets]
		
		return items
	
	# Support both single date and range
	if start_date and end_date:
		query_start = getdate(start_date)
		query_end = getdate(end_date)
	elif date:
		target_date = getdate(date)
	else:
		return []

	# Build SQL with effective date expression for date filtering
	eff = _effective_date_expr("p")
	plan_condition = ""
	params = []
	if start_date and end_date:
		date_condition = f"{eff} BETWEEN %s AND %s"
		params.extend([query_start, query_end])
	else:
		date_condition = f"{eff} = %s"
		params.append(target_date)
	
	if plan_name and plan_name != "Default":
		plan_condition = "AND p.custom_plan_name = %s"
		params.append(plan_name)
	else:
		plan_condition = "AND (p.custom_plan_name IS NULL OR p.custom_plan_name = '' OR p.custom_plan_name = 'Default')"
	
	# Build SELECT fields — include custom_planned_date only if column exists
	extra_fields = ", p.custom_planned_date" if _has_planned_date_column() else ""
	
	planning_sheets = frappe.db.sql(f"""
		SELECT p.name, p.customer, p.party_code, p.dod, p.ordered_date, 
			p.planning_status, p.docstatus, p.sales_order, p.custom_plan_name
			{extra_fields},
			{eff} as effective_date
		FROM `tabPlanning sheet` p
		WHERE {date_condition} AND p.docstatus < 2
		{plan_condition}
		ORDER BY {eff} ASC, p.creation ASC
	""", tuple(params), as_dict=True)

	# Fetch delivery statuses for referenced Sales Orders
	so_names = [d.sales_order for d in planning_sheets if d.sales_order]
	sheet_names = [d.name for d in planning_sheets]
	
	so_status_map = {}
	so_pp_map = {}
	so_wo_map = {}
	sheet_pp_map = {}
	pp_wo_map = {}
	
	valid_pps = set()
	
	if so_names:
		sos = frappe.get_all("Sales Order", filters={"name": ["in", so_names]}, fields=["name", "delivery_status"])
		for s in sos:
			so_status_map[s.name] = s.delivery_status
			
		format_string_so = ','.join(['%s'] * len(so_names))
		
		# Check Production Plan via Sales Order
		pp_data = frappe.db.sql(f"""
			SELECT sales_order, parent 
			FROM `tabProduction Plan Sales Order` 
			WHERE sales_order IN ({format_string_so}) AND docstatus < 2
		""", tuple(so_names), as_dict=True)
		for row in pp_data:
			so_pp_map[row.sales_order] = row.parent
			valid_pps.add(row.parent)
			
		# Check Work Order via Sales Order
		wo_data_so = frappe.db.sql(f"""
			SELECT sales_order, name 
			FROM `tabWork Order` 
			WHERE sales_order IN ({format_string_so}) AND docstatus < 2
		""", tuple(so_names), as_dict=True)
		for row in wo_data_so:
			so_wo_map[row.sales_order] = row.name

	if sheet_names:
		format_string_sheet = ','.join(['%s'] * len(sheet_names))
		# Check Production Plan via Planning Sheet custom field
		# Wrap in try-except in case custom field doesn't exist
		try:
			pp_sheet_data = frappe.db.sql(f"""
				SELECT custom_planning_sheet as planning_sheet, name 
				FROM `tabProduction Plan` 
				WHERE custom_planning_sheet IN ({format_string_sheet}) AND docstatus < 2
			""", tuple(sheet_names), as_dict=True)
			for row in pp_sheet_data:
				sheet_pp_map[row.planning_sheet] = row.name
				valid_pps.add(row.name)
		except Exception:
			pass
			
	if valid_pps:
		format_string_pp = ','.join(['%s'] * len(valid_pps))
		# Check Work Order via Production Plan
		wo_data_pp = frappe.db.sql(f"""
			SELECT production_plan, name 
			FROM `tabWork Order` 
			WHERE production_plan IN ({format_string_pp}) AND docstatus < 2
		""", tuple(valid_pps), as_dict=True)
		for row in wo_data_pp:
			pp_wo_map[row.production_plan] = row.name

	data = []
	for sheet in planning_sheets:
		items = frappe.get_all(
			"Planning Sheet Item",
			filters={"parent": sheet.name},
			fields=["*"],
			order_by="idx"
		)
		
		# Determine PP and WO boolean states for this sheet
		sheet_has_pp = False
		sheet_has_wo = False
		
		my_pp_name = sheet_pp_map.get(sheet.name)
		if not my_pp_name and sheet.sales_order:
			my_pp_name = so_pp_map.get(sheet.sales_order)
			
		if my_pp_name:
			sheet_has_pp = True
			
		# Check WO mapping
		if my_pp_name and my_pp_name in pp_wo_map:
			sheet_has_wo = True
		elif sheet.sales_order and sheet.sales_order in so_wo_map:
			sheet_has_wo = True

		for item in items:
			unit = item.get("unit") or ""
			# Allow items without color (for capacity accuracy)
			color = item.get("color") or item.get("colour") or "NO COLOR"
			
			# For Matrix view calculation - use effective_date (planned or ordered)
			effective_date_str = str(sheet.effective_date) if sheet.get("effective_date") else str(sheet.ordered_date)

			data.append({
				"name": "{}-{}".format(sheet.name, item.get("idx", 0)),
				"itemName": item.name,
				"planningSheet": sheet.name,
				"customer": sheet.customer,
				"partyCode": sheet.party_code,
				"planningStatus": sheet.planning_status or "Draft",
				"docstatus": sheet.docstatus,
				"orderDate": effective_date_str,
				"color": color.upper().strip(),
				"quality": item.get("custom_quality") or item.get("quality") or "",
				"gsm": item.get("gsm") or "",
				"qty": flt(item.get("qty", 0)),
				"idx": item.get("idx", 0),
				"width": flt(item.get("width") or item.get("custom_width") or item.get("width_inches") or item.get("width_inch") or item.get("width_in") or 0),
				"unit": unit,
				"planName": sheet.get("custom_plan_name") or "Default",
				"ordered_date": str(sheet.ordered_date) if sheet.ordered_date else "",
				"planned_date": str(sheet.custom_planned_date) if sheet.get("custom_planned_date") else "",
				"dod": str(sheet.dod) if sheet.dod else "",
				"delivery_status": so_status_map.get(sheet.sales_order) or "Not Delivered",
				"has_pp": sheet_has_pp,
				"has_wo": sheet_has_wo
			})

	return data


@frappe.whitelist()
def get_orders_for_date(date):
	"""Returns all Planning Sheet Items for a specific date (used by Pull Orders dialog)."""
	if not date:
		return []
	target_date = getdate(date)
	eff = _effective_date_expr("p")
	extra_fields = ", p.custom_planned_date" if _has_planned_date_column() else ""
	
	items = frappe.db.sql(f"""
		SELECT 
			i.name, i.item_code, i.item_name, i.qty, i.uom, i.unit,
			i.color, i.custom_quality as quality, i.gsm, i.width,
			p.name as planning_sheet, p.party_code, p.customer,
			p.ordered_date{extra_fields},
			{eff} as effective_date
		FROM `tabPlanning Sheet Item` i
		JOIN `tabPlanning sheet` p ON i.parent = p.name
		WHERE {eff} = %s
		  AND p.docstatus < 2
		ORDER BY i.unit, i.idx
	""", (target_date,), as_dict=True)
	
	return items



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
		if item.get("name"):
			# Update Unit
			if item.get("unit"):
				frappe.db.set_value("Planning Sheet Item", item.get("name"), "unit", item.get("unit"))
			
			# Update Date (Auto-Rollover)
			if item.get("date"):
				# Get Parent
				parent = frappe.db.get_value("Planning Sheet Item", item.get("name"), "parent")
				if parent:
					frappe.db.set_value("Planning sheet", parent, "ordered_date", item.get("date"))

	return {"status": "success"}

@frappe.whitelist()
def get_plans(date=None, start_date=None, end_date=None, **kwargs):
	"""Get unique plan names for a date or date range."""
	eff = _effective_date_expr("p")
	
	if start_date and end_date:
		query_start = getdate(start_date)
		query_end = getdate(end_date)
		date_condition = f"{eff} BETWEEN %s AND %s"
		params = [query_start, query_end]
	elif date:
		target_date = getdate(date)
		date_condition = f"{eff} = %s"
		params = [target_date]
	else:
		return ["Default"]
	
	plans = frappe.db.sql(f"""
		SELECT DISTINCT IFNULL(p.custom_plan_name, 'Default') as plan_name
		FROM `tabPlanning sheet` p
		WHERE {date_condition} AND p.docstatus < 2
		ORDER BY plan_name ASC
	""", tuple(params), as_dict=True)
	
	unique_plans = [p.plan_name or "Default" for p in plans]
	if "Default" not in unique_plans:
		unique_plans.insert(0, "Default")
	# Ensure Default is first
	if unique_plans[0] != "Default":
		unique_plans.remove("Default")
		unique_plans.insert(0, "Default")
	
	return unique_plans

@frappe.whitelist()
def get_monthly_plans(start_date, end_date):
	query_start = getdate(start_date)
	query_end = getdate(end_date)
	
	plans = frappe.db.get_all(
		"Planning sheet", 
		filters={
			"ordered_date": ["between", [query_start, query_end]],
			"docstatus": ["<", 2]
		}, 
		fields=["custom_plan_name"], 
		order_by="custom_plan_name asc"
	)
	
	unique_plans = set([p.custom_plan_name or "Default" for p in plans])
	sorted_plans = sorted(list(unique_plans))
	if "Default" in sorted_plans:
		sorted_plans.remove("Default")
		sorted_plans.insert(0, "Default")
		
	return sorted_plans

@frappe.whitelist()
def create_plan_name_field():
	if not frappe.db.exists('Custom Field', 'Planning sheet-custom_plan_name'):
		custom_field = frappe.get_doc({
			"doctype": "Custom Field",
			"dt": "Planning sheet",
			"fieldname": "custom_plan_name",
			"label": "Plan Name",
			"fieldtype": "Data",
			"insert_after": "planning_status"
		})
		custom_field.insert(ignore_permissions=True)
	
	# Create Planned Date custom field
	if not frappe.db.exists('Custom Field', 'Planning sheet-custom_planned_date'):
		custom_field2 = frappe.get_doc({
			"doctype": "Custom Field",
			"dt": "Planning sheet",
			"fieldname": "custom_planned_date",
			"label": "Planned Date",
			"fieldtype": "Date",
			"insert_after": "ordered_date",
			"description": "Actual planned production date. If empty, ordered_date is used."
		})
		custom_field2.insert(ignore_permissions=True)
	
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

@frappe.whitelist()
def split_order(item_name, split_qty, target_unit):
	"""
	Splits an order: Keeps 'remaining_qty' in original item, creates new item with 'split_qty' in target_unit.
	"""
	if not item_name or not split_qty or not target_unit:
		frappe.throw("Missing required parameters: item_name, split_qty, target_unit")

	doc = frappe.get_doc("Planning Sheet Item", item_name)
	original_qty = float(doc.qty or 0)
	split_qty_val = float(split_qty)

	if split_qty_val >= original_qty:
		frappe.throw(f"Split quantity ({split_qty_val}) must be less than original quantity ({original_qty})")

	if split_qty_val <= 0:
		frappe.throw("Split quantity must be positive")

	# 1. Update Original (Reduce Qty)
	remaining_qty = original_qty - split_qty_val
	doc.db_set("qty", remaining_qty)
	
	# 2. Create Split Item (New Row)
	new_doc = frappe.copy_doc(doc)
	new_doc.qty = split_qty_val
	new_doc.unit = target_unit
	
	# Traceability (Try to set custom fields if they exist)
	# Assuming user will add these fields via Customize Form if not present
        # but we try to set them on the doc object anyway
	new_doc.custom_split_from = item_name
	new_doc.custom_is_split = 1
	
	new_doc.insert()
	
	return {
		"status": "success",
		"original_item": doc.name,
		"remaining_qty": remaining_qty,
		"new_item": new_doc.name,
		"split_qty": split_qty_val, 
		"target_unit": target_unit
	}

@frappe.whitelist()
def duplicate_unprocessed_orders_to_plan(old_plan, new_plan, date=None, start_date=None, end_date=None):
	"""
	Moves unprocessed Planning Sheets from `old_plan` to `new_plan` by updating custom_plan_name.
	Does NOT create new sheets — just updates the plan name on existing ones.
	Only moves sheets that do NOT have BOTH a Production Plan AND a Work Order.
	"""
	if start_date and end_date:
		query_start = getdate(start_date)
		query_end = getdate(end_date)
		date_filter = ["between", [query_start, query_end]]
	elif date:
		date_filter = getdate(date)
	else:
		return {"status": "error", "message": "Date filter required"}
	
	# Handle "Default" naming convention
	old_plan_val = None if old_plan == "Default" else old_plan
	new_plan_val = None if new_plan == "Default" else new_plan
	
	# Find all Planning Sheets on this date for the old plan
	filters = {
		"ordered_date": date_filter,
		"docstatus": ["<", 2]
	}
	if old_plan_val:
		filters["custom_plan_name"] = old_plan_val
	else:
		filters["custom_plan_name"] = ["in", ["", None, "Default"]]
		
	old_sheets = frappe.get_all("Planning sheet", filters=filters, fields=["name", "sales_order"])
	
	copied_count = 0
	
	for sheet in old_sheets:
		has_pp = False
		has_wo = False
		pp_name = None

		# 1. Find PP via sales_order OR planning_sheet custom field
		if sheet.sales_order:
			pp_exists_so = frappe.db.sql("""
				SELECT parent FROM `tabProduction Plan Sales Order`
				WHERE sales_order = %s AND docstatus < 2
				LIMIT 1
			""", (sheet.sales_order,))
			if pp_exists_so:
				pp_name = pp_exists_so[0][0]
				
		if not pp_name:
			try:
				pp_exists_sheet = frappe.db.sql("""
					SELECT name FROM `tabProduction Plan`
					WHERE custom_planning_sheet = %s AND docstatus < 2
					LIMIT 1
				""", (sheet.name,))
				if pp_exists_sheet:
					pp_name = pp_exists_sheet[0][0]
			except Exception:
				pass
				
		if pp_name:
			has_pp = True
			# 2. Check WO via PP
			wo_exists_pp = frappe.db.sql("""
				SELECT name FROM `tabWork Order`
				WHERE production_plan = %s AND docstatus < 2
				LIMIT 1
			""", (pp_name,))
			if wo_exists_pp:
				has_wo = True
				
		# 3. Also check WO via SO if not found
		if not has_wo and sheet.sales_order:
			wo_exists_so = frappe.db.sql("""
				SELECT name FROM `tabWork Order`
				WHERE sales_order = %s AND docstatus < 2
				LIMIT 1
			""", (sheet.sales_order,))
			if wo_exists_so:
				has_wo = True
				
		# ONLY skip if it has BOTH a Production Plan AND a Work Order
		if has_pp and has_wo:
			continue
			
		# Just update the plan name on the existing sheet — no duplication
		frappe.db.set_value("Planning sheet", sheet.name, "custom_plan_name", new_plan_val or "")
		copied_count += 1
		
	frappe.db.commit()
	return {"status": "success", "copied_count": copied_count}

@frappe.whitelist()
def delete_plan(plan_name, date=None, start_date=None, end_date=None):
	"""
	Deletes all Planning Sheets belonging to a specific plan on a given date or date range.
	The 'Default' plan cannot be deleted.
	"""
	if not plan_name or plan_name == "Default":
		frappe.throw(_("Cannot delete the Default plan"))

	if start_date and end_date:
		query_start = getdate(start_date)
		query_end = getdate(end_date)
		date_filter = ["between", [query_start, query_end]]
	elif date:
		date_filter = getdate(date)
	else:
		return {"status": "error", "message": "Date filter required"}

	filters = {
		"ordered_date": date_filter,
		"docstatus": ["<", 2],
		"custom_plan_name": plan_name
	}

	sheets = frappe.get_all("Planning sheet", filters=filters, fields=["name"])

	deleted_count = 0
	for sheet in sheets:
		frappe.delete_doc("Planning sheet", sheet.name, force=1)
		deleted_count += 1

	frappe.db.commit()

	return {"status": "success", "deleted_count": deleted_count}

def get_orders_for_date(date):
    """
    Fetch all Planning Sheet Items for a specific date that are NOT Cancelled/Completed (optional filter).
    Returns basic info needed for the Pull Dialog.
    """
    if not date:
        return []

    # Get parent sheets for this date (if structure is Parent Date -> Child Item)
    # Actually, your structure seems to be Planning Sheet (Header) has Date? 
    # Or Items have Date?
    # Based on `update_items_bulk`, items update `ordered_date` on Parent. 
    # So we query Planning Sheet by `ordered_date` and get items.
    
    # Wait, `get_color_chart_data` uses `ordered_date` on `Planning sheet`.
    # Let's check `get_color_chart_data` logic again to be consistent.
    # It joins Planning Sheet and Planning Sheet Item.
    
    sql = """
        SELECT 
            i.name, i.item_code, i.item_name, i.qty, i.unit, i.color, 
            i.gsm, i.custom_quality as quality,
            p.name as planning_sheet, p.party_code, p.customer
        FROM
            `tabPlanning Sheet Item` i
        LEFT JOIN
            `tabPlanning sheet` p ON i.parent = p.name
        WHERE
            p.ordered_date = %s
            AND p.docstatus < 2
            AND i.docstatus < 2
        ORDER BY
            i.unit, i.custom_quality
    """
    data = frappe.db.sql(sql, (date,), as_dict=True)
    return data

@frappe.whitelist()
def move_orders_to_date(item_names, target_date, target_unit=None, plan_name=None):
    """
    Moves list of Planning Sheet Items to a new Date.
    Supports item-level granularity by re-parenting items if necessary.
    Optionally updates the Unit of the moved items.
    """
    import json
    if isinstance(item_names, str):
        item_names = json.loads(item_names)
        
    if not item_names:
        return {"status": "failed", "message": "No items selected"}

    target_date = getdate(target_date)
    
    # --- CAPACITY VALIDATION ---
    # 1. Calculate weight to add per unit
    weights_to_add = {} # unit -> tons
    
    docs_to_move = [] 
    for name in item_names:
        try:
            doc = frappe.get_doc("Planning Sheet Item", name)
            docs_to_move.append(doc)
            
            final_unit = target_unit if target_unit else (doc.unit or "")
            if final_unit:
                wt_tons = flt(doc.qty) / 1000.0
                weights_to_add[final_unit] = weights_to_add.get(final_unit, 0.0) + wt_tons
        except frappe.DoesNotExistError:
            continue
            
    # 2. Check Limits
    for unit, added_weight in weights_to_add.items():
        if unit in HARD_LIMITS:
            current_load = get_unit_load(target_date, unit)
            limit = HARD_LIMITS[unit]
            
            if current_load + added_weight > limit:
                frappe.throw(
                    f"Capacity Exceeded! Unit {unit} allows max {limit}T. Current: {current_load:.2f}T. Adding: {added_weight:.2f}T. New Total: {current_load + added_weight:.2f}T"
                )

    count = 0
    
    # 1. Group items by Current Parent
    items_by_parent = {}
    
    for doc in docs_to_move:
        p_name = str(doc.parent)
        if p_name not in items_by_parent:
            items_by_parent[p_name] = []
        items_by_parent[p_name].append(doc)

    # 2. Process each Parent Group
    for parent_name, items in items_by_parent.items():
        parent_doc = frappe.get_doc("Planning sheet", parent_name)
        moving_docs = items  # items is already a list
        
        # Determine Target Sheet
        find_filters = {
            "ordered_date": target_date,
            "party_code": parent_doc.party_code,
            "docstatus": 0
        }
        
        target_plan = plan_name if plan_name and plan_name != "Default" else parent_doc.get("custom_plan_name")
        if target_plan == "Default": target_plan = None
        
        if target_plan:
             find_filters["custom_plan_name"] = target_plan
        else:
             find_filters["custom_plan_name"] = ["in", ["", None, "Default"]]
             
        target_sheet_name = frappe.db.get_value("Planning sheet", find_filters, "name")
        
        if target_sheet_name and target_sheet_name != parent_name:
            target_sheet = frappe.get_doc("Planning sheet", target_sheet_name)
        elif target_sheet_name == parent_name:
            # Already on target date, but maybe unit change requested or date same
            target_sheet = parent_doc
        else:
            target_sheet = frappe.new_doc("Planning sheet")
            target_sheet.ordered_date = target_date
            target_sheet.party_code = parent_doc.party_code
            target_sheet.customer = parent_doc.customer
            target_sheet.sales_order = parent_doc.sales_order
            if target_plan:
                target_sheet.custom_plan_name = target_plan
            target_sheet.save()
        
        # Get starting idx for target
        target_sheet.reload()
        current_max_idx = 0
        if target_sheet.get("items"):
            current_max_idx = int(max([int(d.idx or 0) for d in target_sheet.items] or [0]))
        
        # Move Every Item in the group
        for i, item_doc in enumerate(moving_docs):
            new_idx = int(current_max_idx) + int(i) + 1
            new_unit = target_unit if target_unit else item_doc.unit

            # HEAL UNASSIGNED: If unit is missing OR "Unassigned"/"Mixed", auto-assign based on Quality
            if not new_unit or new_unit in ["Unassigned", "Mixed"]:
                # Use item quality to find best unit
                qual = item_doc.custom_quality or ""
                new_unit = get_preferred_unit(qual)
            
            # Use SQL for direct re-parenting (Robust for rescue)
            frappe.db.sql("""
                UPDATE `tabPlanning Sheet Item`
                SET parent = %s, idx = %s, unit = %s, parenttype='Planning sheet', parentfield='items'
                WHERE name = %s
            """, (target_sheet.name, new_idx, new_unit, item_doc.name))
            
            count = int(count) + 1
        
        frappe.db.commit() # Save SQL updates
        
        # 3. Handle Parent Cleanup
        target_sheet.reload()
        if int(target_sheet.docstatus or 0) == 0:
            target_sheet.save()
            
        if target_sheet.name != parent_doc.name:
            parent_doc.reload()
            if not parent_doc.get("items"):
                # Source is empty -> DELETE
                try:
                    frappe.delete_doc("Planning sheet", parent_doc.name, force=1)
                except Exception as e:
                    # If it's linked to a Production Plan, Frappe prevents deletion. 
                    # We catch it so the move doesn't crash since the items were already moved via SQL.
                    frappe.logger().error(f"Could not delete empty planning sheet {parent_doc.name}: {e}")
            elif int(parent_doc.docstatus or 0) == 0:
                parent_doc.save()
        
    frappe.db.commit()


@frappe.whitelist()
def get_items_by_sheet(sheet_name):
    """
    Fetches all items for a given Planning Sheet.
    Used for Admin Rescue to recover items.
    """
    if not sheet_name:
        return []
        
    sql = """
        SELECT name, item_name, qty, unit, docstatus, parent, idx
        FROM `tabPlanning Sheet Item`
        WHERE parent = %s
        ORDER BY idx ASC
    """
    return frappe.db.sql(sql, (sheet_name,), as_dict=True)


# --------------------------------------------------------------------------------
# Confirmed Order Workflow & Automation
# --------------------------------------------------------------------------------

@frappe.whitelist()
def get_unscheduled_planning_sheets():
    """
    Fetches Planning Sheets that are 'Confirmed' (docstatus=0 or 1) but have NO ordered_date.
    These display in the 'Confirmed Order' view.
    """
    sql = """
        SELECT 
            p.name, p.customer, p.party_code, p.docstatus, p.ordered_date,
            SUM(i.qty) as total_qty
        FROM `tabPlanning sheet` p
        LEFT JOIN `tabPlanning Sheet Item` i ON i.parent = p.name
        WHERE 
            (p.ordered_date IS NULL OR p.ordered_date = '')
            AND p.docstatus < 2
        GROUP BY p.name
    """
    sheets = frappe.db.sql(sql, as_dict=True)
    
    return sheets

@frappe.whitelist()
def get_confirmed_orders_kanban(order_date=None, delivery_date=None, party_code=None, start_date=None, end_date=None):
    """
    Fetches Planning Sheet Items where the linked Sales Order is 'Confirmed'.
    Supports date, start_date/end_date range, delivery_date, and party_code filters.
    """
    conditions = ["so.custom_production_status = 'Confirmed'", "p.docstatus < 2"]
    values = []

    # Date range support (weekly/monthly)
    if start_date and end_date:
        conditions.append("((so.transaction_date BETWEEN %s AND %s) OR (so.transaction_date IS NULL AND DATE(p.creation) BETWEEN %s AND %s))")
        values.extend([start_date, end_date, start_date, end_date])
    elif order_date:
        conditions.append("((so.transaction_date IS NOT NULL AND so.transaction_date = %s) OR (so.transaction_date IS NULL AND DATE(p.creation) = %s))")
        values.extend([order_date, order_date])

    # Filter by Delivery Date (DOD)
    if delivery_date:
        conditions.append("p.dod = %s")
        values.append(delivery_date)

    if party_code:
        conditions.append("(p.party_code LIKE %s OR p.customer LIKE %s)")
        values.extend([f"%{party_code}%", f"%{party_code}%"])

    where_clause = " AND ".join(conditions)

    sql = f"""
        SELECT 
            i.name, i.item_code, i.item_name, i.qty, i.unit, i.color, 
            i.gsm, i.custom_quality as quality, i.width_inch, i.idx,
            p.name as planning_sheet, p.party_code, p.customer, p.dod, p.planning_status, p.creation,
            so.transaction_date as so_date, so.custom_production_status, so.delivery_status
        FROM
            `tabPlanning Sheet Item` i
        JOIN
            `tabPlanning sheet` p ON i.parent = p.name
        LEFT JOIN
            `tabSales Order` so ON p.sales_order = so.name
        WHERE
            {where_clause}
        ORDER BY
            so.transaction_date ASC, p.creation DESC, i.idx ASC
    """
    
    items = frappe.db.sql(sql, tuple(values), as_dict=True)
    
    data = []
    for item in items:
        # Format for Kanban (matches ColorChart)
        data.append({
            "name": "{}-{}".format(item.planning_sheet, item.idx), # Unique ID for card
            "itemName": item.name, # Actual Item Name for updates
            "planningSheet": item.planning_sheet,
            "customer": item.customer,
            "partyCode": item.party_code,
            "planningStatus": item.planning_status or "Draft",
            "color": (item.color or "").upper().strip(),
            "quality": item.quality or "",
            "gsm": item.gsm or "",
            "qty": flt(item.qty),
            "width": flt(item.width_inch or 0),
            "unit": item.unit or "", 
            "dod": str(item.dod) if item.dod else "",
            "unit": item.unit or "", 
            "dod": str(item.dod) if item.dod else "",
            "order_date": str(item.so_date) if item.so_date else str(item.creation.date()),
            "delivery_status": item.delivery_status or "Not Delivered"
        })
        
    return data



def create_planning_sheet_from_so(doc):
    """
    AUTO-CREATE PLANNING SHEET (User Provided Logic)
    """
    try:
        # 1. Check if Planning Sheet already exists
        if frappe.db.exists("Planning sheet", {"sales_order": doc.name}):
            frappe.msgprint("â„¹ï¸ Planning Sheet already exists.")
        else:
            # --- DEFINITIONS ---
            # NOTE: Units lists are now global UNIT_QUALITY_MAP

            QUAL_LIST = ["SUPER PLATINUM", "SUPER CLASSIC", "SUPER ECO", "ECO SPECIAL", "ECO GREEN", "ECO SPL", "LIFE STYLE", "LIFESTYLE", "PREMIUM", "PLATINUM", "CLASSIC", "DELUXE", "BRONZE", "SILVER", "ULTRA", "GOLD", "UV"]
            QUAL_LIST.sort(key=len, reverse=True)

            COL_LIST = ["GOLDEN YELLOW", "BRIGHT WHITE", "SUPER WHITE", "BLACK", "RED", "BLUE", "GREEN", "MILKY WHITE", "SUNSHINE WHITE", "BLEACH WHITE", "LEMON YELLOW", "BRIGHT ORANGE", "DARK ORANGE", "BABY PINK", "DARK PINK", "CRIMSON RED", "LIGHT MAROON", "DARK MAROON", "MEDICAL BLUE", "PEACOCK BLUE", "RELIANCE GREEN", "PARROT GREEN", "ROYAL BLUE", "NAVY BLUE", "LIGHT GREY", "DARK GREY", "CHOCOLATE BROWN", "LIGHT BEIGE", "DARK BEIGE", "WHITE MIX", "BLACK MIX", "COLOR MIX", "BEIGE MIX", "WHITE"]
            COL_LIST.sort(key=len, reverse=True)

            # --- PREPARE DOC ---
            ps = frappe.new_doc("Planning sheet")
            ps.sales_order = doc.name
            ps.customer = doc.customer
            
            # Start Date Preference: Delivery Date or Today?
            preferred_date = doc.delivery_date or frappe.utils.nowdate()
            ps.dod = doc.delivery_date
            
            # Assign Party Code (Use doc.party_code if available, else Customer)
            # User wants "need partycode kgs quality" - ensuring party_code
            if hasattr(doc, 'party_code') and doc.party_code:
                ps.party_code = doc.party_code
            else:
                ps.party_code = doc.customer
                ps.party_code = doc.customer
            ps.planning_status = "Draft"

            # --- PROCESS ITEMS ---
            total_tons = 0.0
            major_quality = ""
            processed_items_data = []

            for it in doc.items:
                 # Extraction Logic
                raw_txt = (it.item_code or "") + " " + (it.item_name or "")
                clean_txt = raw_txt.upper().replace("-", " ").replace("_", " ").replace("(", " ").replace(")", " ")
                clean_txt = clean_txt.replace("''", " INCH ").replace('"', " INCH ")
                words = clean_txt.split()
                
                gsm = 0
                for i in range(1, len(words)):
                    if words[i] == "GSM":
                        prev = words[i-1]
                        if prev.isdigit():
                            gsm = int(prev)
                            break
                            
                width = 0.0
                for i in range(len(words) - 1):
                    if words[i] == "W":
                        next_word = words[i+1]
                        if next_word.replace('.', '', 1).isdigit():
                            width = float(next_word)
                            break
                if width == 0.0:
                    for i in range(1, len(words)):
                        if words[i] == "INCH":
                            prev = words[i-1]
                            if prev.replace('.', '', 1).isdigit():
                                width = float(prev)
                                break
                                
                search_text = " " + " ".join(words) + " "
                qual = ""
                for q in QUAL_LIST:
                    if (" " + q + " ") in search_text:
                        qual = q
                        break
                col = ""
                for c in COL_LIST:
                    if (" " + c + " ") in search_text:
                        col = c
                        break
                        
                m_roll = float(it.custom_meter_per_roll or 0)
                wt = 0.0
                if gsm > 0 and width > 0 and m_roll > 0:
                    wt = (gsm * width * m_roll * 0.0254) / 1000
                elif it.weight_per_unit: 
                     wt = float(it.weight_per_unit)
                
                total_tons += (flt(it.qty) / 1000.0)
                if not major_quality and qual: major_quality = qual
                
                processed_items_data.append({
                    "data": it,
                    "gsm": gsm,
                    "width": width,
                    "qual": qual,
                    "col": col,
                    "wt": wt
                })

            # 2. Determine Preferred Unit based on Quality
            preferred_unit = ""
            if major_quality in UNIT_QUALITY_MAP["Unit 1"]: preferred_unit = "Unit 1"
            elif major_quality in UNIT_QUALITY_MAP["Unit 2"]: preferred_unit = "Unit 2"
            elif major_quality in UNIT_QUALITY_MAP["Unit 3"]: preferred_unit = "Unit 3"
            elif major_quality in UNIT_QUALITY_MAP["Unit 4"]: preferred_unit = "Unit 4"
            else: preferred_unit = "Unit 1" # Default

            # 3. Find Best Slot for TOTAL Weight
            best_slot = find_best_slot(total_tons, major_quality, preferred_unit, preferred_date)
            
            if not best_slot:
                frappe.msgprint("âš ï¸ Could not find capacity for this order (30 day limit). Created as Draft without date.")
                ps.ordered_date = None
                final_unit = preferred_unit 
            else:
                ps.ordered_date = best_slot["date"]
                final_unit = best_slot["unit"]
                if str(best_slot["date"]) != str(preferred_date):
                     frappe.msgprint(f"âš ï¸ Capacity Full. Scheduled for {best_slot['date']} in {final_unit}.")

            # 4. Insert Items
            for p_item in processed_items_data:
                it = p_item["data"]
                ps.append("items", {
                    "sales_order_item": it.name,
                    "item_code": it.item_code,
                    "item_name": it.item_name,
                    "qty": it.qty,
                    "uom": it.uom,
                    "meter": float(it.custom_meter or 0),
                    "meter_per_roll": float(it.custom_meter_per_roll or 0),
                    "no_of_rolls": float(it.custom_no_of_rolls or 0),
                    "gsm": p_item["gsm"],
                    "width_inch": p_item["width"],
                    "custom_quality": p_item["qual"],
                    "color": p_item["col"],
                    "weight_per_roll": p_item["wt"],
                    "unit": final_unit,
                    "party_code": doc.party_code if (hasattr(doc, 'party_code') and doc.party_code) else doc.customer
                })

            ps.flags.ignore_permissions = True
            ps.insert()
            # frappe.msgprint(f"âœ… Planning Sheet <b>{ps.name}</b> Created!") 
            # Commented out msgprint to avoid API clutter if called from hook

    except Exception as e:
        frappe.log_error("Planning Sheet Creation Failed: " + str(e))

@frappe.whitelist()
def create_production_plan_from_sheet(sheet_name):
    """
    Creates a Production Plan from a Planning Sheet.
    """
    if not sheet_name: return
    sheet = frappe.get_doc("Planning sheet", sheet_name)
    
    pp = frappe.new_doc("Production Plan")
    pp.company = frappe.defaults.get_user_default("Company")
    pp.customer = sheet.customer
    pp.get_items_from = "Material Request" 
    
    for item in sheet.items:
        row = pp.append("po_items", {})
        row.item_code = item.item_code
        row.qty = item.qty
        row.warehouse = item.warehouse if hasattr(item, 'warehouse') else ""
        if hasattr(item, 'sales_order_item'):
             row.sales_order_item = item.sales_order_item
             
    pp.insert()
    
    # Update Status to Planned
    if sheet.sales_order:
        frappe.db.set_value("Sales Order", sheet.sales_order, "custom_production_status", "Planned")
        
    return pp.name

@frappe.whitelist()
def create_production_plan_bulk(sheets):
    """
    Creates Production Plans for multiple Planning Sheets at once.
    """
    import json
    if isinstance(sheets, str):
        sheets = json.loads(sheets)
    
    if not sheets: return
    
    created_plans = []
    
    # Optional: Group by Customer? 
    # Usually Production Plans are per Customer or Per SO.
    # If we select multiple sheets from different customers, we probably want separate Production Plans?
    # Or one big Production Plan?
    # Standard ERPNext Production Plan can take multiple Sales Orders / Material Requests.
    # But here we are mapping from Planning Sheet -> Production Plan.
    # Let's create ONE Production Plan per Planning Sheet for simplicity and traceability (1:1 mapping),
    # unless user requested merging.
    # The prompt doesn't specify merging.
    # "Create Plan: Button to convert selected/viewed confirmed orders into a production plan."
    # If 10 orders are visible, and I click "Create Plan", maybe I want 10 plans?
    # OR 1 plan with 10 items?
    # 1 Plan with 10 items is better for "Batching".
    # BUT if customers are different, we can't make 1 Plan (usually).
    # ERPNext Production Plan has `customer` field. If filled, restricts to that customer.
    # If empty, can handle multiple?
    # Let's try to group by Customer.
    
    # 1. Fetch all sheets
    sheet_docs = [frappe.get_doc("Planning sheet", s) for s in sheets]
    
    # 2. Group by Customer
    sheets_by_customer = {}
    for s in sheet_docs:
        cust = s.customer or "No Customer"
        if cust not in sheets_by_customer:
            sheets_by_customer[cust] = []
        sheets_by_customer[cust].append(s)
        
    # 3. Create Plans
    for cust, cust_sheets in sheets_by_customer.items():
        pp = frappe.new_doc("Production Plan")
        pp.company = frappe.defaults.get_user_default("Company")
        pp.customer = cust if cust != "No Customer" else None
        pp.get_items_from = "Material Request" # Dummy, we fill manually
        
        # Add Reference Sales Orders?
        # Production Plan has table `sales_orders`.
        seen_so = set()
        for s in cust_sheets:
            if s.sales_order and s.sales_order not in seen_so:
                pp.append("sales_orders", {
                    "sales_order": s.sales_order,
                    "sales_order_date": s.creation # approximation
                })
                seen_so.add(s.sales_order)
        
        # Add Items
        for s in cust_sheets:
            for item in s.items:
                row = pp.append("po_items", {})
                row.item_code = item.item_code
                row.qty = item.qty
                # row.warehouse = ... default?
                if hasattr(item, 'sales_order_item'):
                     row.sales_order_item = item.sales_order_item
            
            # Update Status of Schema
            if s.sales_order:
                frappe.db.set_value("Sales Order", s.sales_order, "custom_production_status", "Planned")
        
        pp.insert()
        created_plans.append(pp.name)
        
    return created_plans


@frappe.whitelist()
def create_planning_sheets_bulk(sales_orders):
    """
    Creates Planning Sheets for selected Sales Orders.
    Uses GSM usage logic (Unit 1>50, etc) to auto-allocate items.
    """
    import json
    if isinstance(sales_orders, str):
        sales_orders = json.loads(sales_orders)
        
    created = []
    errors = []
    
    # GSM/Quality Maps (Helper)
    # Re-defining here or using global
    
    for so_name in sales_orders:
        try:
            # Check if active Planning Sheet exists (Docstatus 0 or 1)
            # We use frappe.db.exists with filters
            if frappe.db.count("Planning sheet", {"sales_order": so_name, "docstatus": ["<", 2]}) > 0:
                continue # Skip if exists
                
            doc = frappe.get_doc("Sales Order", so_name)
            
            ps = frappe.new_doc("Planning sheet")
            ps.sales_order = doc.name
            ps.party_code = doc.party_code if hasattr(doc, 'party_code') else doc.customer
            ps.customer = doc.customer
            ps.dod = doc.delivery_date
            ps.ordered_date = doc.transaction_date
            ps.planning_status = "Draft"
            
            for it in doc.items:
                # Logic from Step 1270, simplified since we have helpers now
                qual = it.custom_quality or it.quality
                gsm = flt(it.custom_gsm or it.gsm or 0)
                
                # Unit Logic
                unit = "Unit 1"
                q_up = str(qual or "").upper()
                if q_up:
                    if gsm > 50 and q_up in UNIT_QUALITY_MAP["Unit 1"]: unit = "Unit 1"
                    elif gsm > 20 and q_up in UNIT_QUALITY_MAP["Unit 2"]: unit = "Unit 2"
                    elif gsm > 10 and q_up in UNIT_QUALITY_MAP["Unit 3"]: unit = "Unit 3"
                    elif q_up in UNIT_QUALITY_MAP["Unit 4"]: unit = "Unit 4"
                
                # Handling custom fields safely
                width = flt(it.custom_width or 0)
                
                ps.append("items", {
                    "sales_order_item": it.name,
                    "item_code": it.item_code,
                    "item_name": it.item_name,
                    "qty": it.qty,
                    "uom": it.uom,
                    "gsm": gsm,
                    "custom_quality": qual,
                    "color": it.custom_color or it.color,
                    "width_inch": width,
                    "unit": unit,
                    "meter": it.custom_meter or 0,
                    "no_of_rolls": it.custom_no_of_rolls or 0,
                    "meter_per_roll": it.custom_meter_per_roll or 0
                })
                
            ps.insert(ignore_permissions=True)
            created.append(ps.name)
            
        except Exception as e:
            frappe.log_error(f"Failed to create plan for {so_name}: {str(e)}")
            errors.append(so_name)
            
            
    return {"created": created, "errors": errors}


@frappe.whitelist()
def save_color_order(order):
    """Save custom color order global default."""
    if isinstance(order, str):
        try:
            import json
            order = json.loads(order)
        except:
            pass
    if not isinstance(order, list):
        return
    frappe.defaults.set_global_default("production_color_order", frappe.as_json(order))
    return "saved"

@frappe.whitelist()
def get_color_order():
    """Get custom color order global default."""
    order_str = frappe.defaults.get_global_default("production_color_order")
    if order_str:
        try:
            import json
            return json.loads(order_str)
        except:
            return []
    return []

@frappe.whitelist()
def update_sequence(items):
    """
    Updates the idx of items for manual reordering.
    Expects items = [{name: 'ITEM-ID', idx: 1}, ...]
    Uses SQL to bypass potential Framework overhead/re-indexing logic.
    """
    import json
    if isinstance(items, str):
        items = json.loads(items)
        
    # Batch update? No, simple loop is fine for < 50 items usually.
    for i in items:
        frappe.db.sql("UPDATE `tabPlanning Sheet Item` SET idx=%s WHERE name=%s", (i["idx"], i["name"]))
        
    frappe.db.commit() # Ensure committed immediately 
    return "ok"
import frappe
from frappe import _
from frappe.utils import getdate, flt, cint
import json

def generate_party_code(doc):
    """One Sales Order = One Party Code.
    Generates a unique party_code if not present and copies it to child items.
    """
    if doc.get('party_code'):
        return
    # Try to reuse existing party_code from another Planning Sheet of same SO
    existing_party_code = None
    if doc.get('sales_order'):
        existing_party_code = frappe.db.get_value(
            "Planning sheet",
            {"sales_order": doc.sales_order, "party_code": ["!=" , ""]},
            "party_code",
        )
    if existing_party_code:
        doc.party_code = existing_party_code
    else:
        # Generate new code based on year and month
        row = frappe.db.sql("""
            SELECT DATE_FORMAT(NOW(), '%y') AS yy,
                   MONTH(NOW()) AS mm
        """, as_dict=1)[0]
        yy = row["yy"]
        mm = int(row["mm"])
        month_map = {1: "A", 2: "B", 3: "C", 4: "D", 5: "E", 6: "F", 7: "G", 8: "H", 9: "I", 10: "J", 11: "K", 12: "L"}
        mcode = month_map.get(mm, "A")
        prefix = mcode + yy
        last_code = frappe.db.sql("""
            SELECT party_code
            FROM `tabPlanning sheet`
            WHERE party_code LIKE %(prefix)s
            ORDER BY CAST(SUBSTRING(party_code, %(offset)s) AS UNSIGNED) DESC
            LIMIT 1
        """, {"prefix": prefix + "%", "offset": len(prefix) + 1}, as_dict=1)
        series = 1
        if last_code:
            try:
                series = int(last_code[0]["party_code"][len(prefix):]) + 1
            except Exception:
                series = 1
        s = str(series).zfill(3)
        doc.party_code = prefix + s
    # Copy to child items if any
    if doc.get("items"):
        for item_row in doc.items:
            item_row.party_code = doc.party_code



# --- DEFINITIONS ---
UNIT_1 = ["PREMIUM", "PLATINUM", "SUPER PLATINUM", "GOLD", "SILVER"]
UNIT_2 = ["GOLD", "SILVER", "BRONZE", "CLASSIC", "SUPER CLASSIC", "LIFE STYLE", "ECO SPECIAL", "ECO GREEN", "SUPER ECO", "ULTRA", "DELUXE"]
UNIT_3 = ["PREMIUM", "PLATINUM", "SUPER PLATINUM", "GOLD", "SILVER", "BRONZE"]
UNIT_4 = ["PREMIUM", "GOLD", "SILVER", "BRONZE"]

QUAL_LIST = ["SUPER PLATINUM", "SUPER CLASSIC", "SUPER ECO", "ECO SPECIAL", "ECO GREEN",
             "ECO SPL", "LIFE STYLE", "LIFESTYLE", "PREMIUM", "PLATINUM", "CLASSIC",
             "DELUXE", "BRONZE", "SILVER", "ULTRA", "GOLD", "UV"]
QUAL_LIST.sort(key=len, reverse=True)

COL_LIST = [
    "BRIGHT WHITE", "SUPER WHITE", "MILKY WHITE", "SUNSHINE WHITE",
    "BLEACH WHITE 1.0", "BLEACH WHITE 2.0", "BLEACH WHITE", "WHITE MIX", "WHITE",
    "CREAM 2.0", "CREAM 3.0", "CREAM 4.0", "CREAM 5.0",
    "GOLDEN YELLOW 4.0 SPL", "GOLDEN YELLOW 1.0", "GOLDEN YELLOW 2.0",
    "GOLDEN YELLOW 3.0", "GOLDEN YELLOW",
    "LEMON YELLOW 1.0", "LEMON YELLOW 3.0", "LEMON YELLOW",
    "BRIGHT ORANGE", "DARK ORANGE", "ORANGE 2.0",
    "PINK 7.0 DARK", "PINK 6.0 DARK", "DARK PINK",
    "BABY PINK", "PINK 1.0", "PINK 2.0", "PINK 3.0", "PINK 5.0",
    "CRIMSON RED", "RED",
    "LIGHT MAROON", "DARK MAROON", "MAROON 1.0", "MAROON 2.0",
    "BLUE 13.0 INK BLUE", "BLUE 12.0 SPL NAVY BLUE", "BLUE 11.0 NAVY BLUE",
    "BLUE 8.0 DARK ROYAL BLUE", "BLUE 7.0 DARK BLUE", "BLUE 6.0 ROYAL BLUE",
    "LIGHT PEACOCK BLUE", "PEACOCK BLUE", "LIGHT MEDICAL BLUE", "MEDICAL BLUE",
    "ROYAL BLUE", "NAVY BLUE", "SKY BLUE", "LIGHT BLUE",
    "BLUE 9.0", "BLUE 4.0", "BLUE 2.0", "BLUE 1.0", "BLUE",
    "PURPLE 4.0 BLACKBERRY", "PURPLE 1.0", "PURPLE 2.0", "PURPLE 3.0", "VOILET",
    "GREEN 13.0 ARMY GREEN", "GREEN 12.0 OLIVE GREEN", "GREEN 11.0 DARK GREEN",
    "GREEN 10.0", "GREEN 9.0 BOTTLE GREEN", "GREEN 8.0 APPLE GREEN",
    "GREEN 7.0", "GREEN 6.0", "GREEN 5.0 GRASS GREEN", "GREEN 4.0",
    "GREEN 3.0 RELIANCE GREEN", "GREEN 2.0 TORQUISE GREEN", "GREEN 1.0 MINT",
    "MEDICAL GREEN", "RELIANCE GREEN", "PARROT GREEN", "GREEN",
    "SILVER 1.0", "SILVER 2.0", "LIGHT GREY", "DARK GREY", "GREY 1.0",
    "CHOCOLATE BROWN 2.0", "CHOCOLATE BROWN", "CHOCOLATE BLACK",
    "BROWN 3.0 DARK COFFEE", "BROWN 2.0 DARK", "BROWN 1.0",
    "CHIKOO 1.0", "CHIKOO 2.0",
    "BEIGE 1.0", "BEIGE 2.0", "BEIGE 3.0", "BEIGE 4.0", "BEIGE 5.0",
    "LIGHT BEIGE", "DARK BEIGE", "BEIGE MIX",
    "BLACK MIX", "COLOR MIX", "BLACK",
]
COL_LIST.sort(key=len, reverse=True)

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

def is_quality_allowed(unit, quality):
	"""Checks if a quality is allowed for a unit."""
	if not quality or not unit: return True
	if unit not in UNIT_QUALITY_MAP: return True
	# Match with stripping and upper
	q_match = quality.upper().strip()
	allowed = [q.upper().strip() for q in UNIT_QUALITY_MAP[unit]]
	return q_match in allowed

def is_sheet_locked(sheet_name):
	"""Checks if a sheet is locked (either submitted or belongs to a locked plan)."""
	try:
		sheet = frappe.get_doc("Planning sheet", sheet_name)
		if sheet.docstatus != 0:
			return True
		
		# Check if its plans are locked
		cc_plan = sheet.get("custom_plan_name") or "Default"
		pb_plan = sheet.get("custom_pb_plan_name")
		
		# We need to fetch persisted plans to check lock status
		from production_scheduler.api import get_persisted_plans
		
		cc_plans = get_persisted_plans("color_chart")
		if any(p["name"] == cc_plan and p.get("locked") for p in cc_plans):
			return True
			
		if pb_plan:
			pb_plans = get_persisted_plans("production_board")
			if any(p["name"] == pb_plan and p.get("locked") for p in pb_plans):
				return True
				
		return False
	except Exception:
		return False

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

def get_unit_load(date, unit, plan_name=None):
	"""Calculates current load (in Tons) for a unit on a given date.
	Filtered per-plan so each plan has its own independent capacity.
	Uses custom_planned_date if set, otherwise falls back to ordered_date."""
	eff = _effective_date_expr("p")
	# Build plan filter — each plan is treated independently
	if plan_name and plan_name != "__all__":
		if plan_name == "Default":
			plan_cond = "AND (p.custom_plan_name IS NULL OR p.custom_plan_name = '' OR p.custom_plan_name = 'Default')"
			params = (date, unit)
		else:
			plan_cond = "AND p.custom_plan_name = %s"
			params = (date, unit, plan_name)
	else:
		# No plan filter — sum all (used internally for global capacity checks)
		plan_cond = ""
		params = (date, unit)
	sql = f"""
		SELECT SUM(i.qty) as total_qty
		FROM `tabPlanning Sheet Item` i
		JOIN `tabPlanning sheet` p ON i.parent = p.name
		WHERE {eff} = %s
		  AND i.unit = %s
		  AND p.docstatus < 2
		  AND i.docstatus < 2
		  {plan_cond}
	"""
	result = frappe.db.sql(sql, params)
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
	
	# QUALITY ENFORCEMENT
	if not is_quality_allowed(unit, quality):
		frappe.throw(_("Quality <b>{}</b> is not allowed in <b>{}</b>.").format(quality, unit))

	# 3. Check Capacity of Target Slot (scoped to this item's plan)
	current_load = get_unit_load(target_date, unit, plan_name=plan_name or parent_sheet.get("custom_plan_name") or "Default")
	limit = HARD_LIMITS.get(unit, 999.0)
	
	# Moving within same date (even to different unit): subtract item's own weight
	# to avoid double-counting it and causing false overflow / duplicate creation
	is_same_date = (str(parent_sheet.get("custom_planned_date") or parent_sheet.ordered_date) == str(target_date))
	if is_same_date and item.unit == unit:
		# Same date + same unit: pure reorder, load stays same
		load_for_check = current_load
	elif is_same_date:
		# Same date, different unit: item moves FROM old unit TO new unit.
		# Don't count the item's own weight in the old unit's load — only the new unit's load matters
		load_for_check = current_load + item_wt_tons
	else:
		# Different date: full new load
		load_for_check = current_load + item_wt_tons

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
			# Ensure the existing sheet has custom_planned_date set to target_date
			if has_col:
				frappe.db.set_value("Planning sheet", new_parent_name, "custom_planned_date", target_date)
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
def get_color_chart_data(date=None, start_date=None, end_date=None, plan_name=None, mode=None, planned_only=0):
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
	
	if plan_name == "__all__":
		plan_condition = ""  # No plan filter — return all items
	elif plan_name and plan_name != "Default":
		plan_condition = "AND p.custom_plan_name = %s"
		params.append(plan_name)
	else:
		plan_condition = "AND (p.custom_plan_name IS NULL OR p.custom_plan_name = '' OR p.custom_plan_name = 'Default')"

	# Production Board only: require custom_planned_date to be explicitly set
	if cint(planned_only) and _has_planned_date_column():
		plan_condition += " AND p.custom_planned_date IS NOT NULL AND p.custom_planned_date != ''"
	
	# Build SELECT fields — include custom_planned_date only if column exists
	extra_fields = ", p.custom_planned_date" if _has_planned_date_column() else ""
	
	planning_sheets = frappe.db.sql(f"""
		SELECT p.name, p.customer, p.party_code, p.dod, p.ordered_date, 
			p.planning_status, p.docstatus, p.sales_order, p.custom_plan_name, p.custom_pb_plan_name
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
				"pbPlanName": sheet.get("custom_pb_plan_name") or "",
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

# --------------------------------------------------------------------------------
# Persistent Plans System
# --------------------------------------------------------------------------------

def get_persisted_plans(plan_type):
	"""Returns list of dicts: [{'name': '...', 'locked': 0}] from frappe.defaults"""
	key = f"production_scheduler_{plan_type}_plans"
	val = frappe.defaults.get_global_default(key)
	if val:
		import json
		try:
			return json.loads(val)
		except:
			pass
	if plan_type == "color_chart":
		return [{"name": "Default", "locked": 0}]
	return []

@frappe.whitelist()
def add_persistent_plan(plan_type, name):
	plans = get_persisted_plans(plan_type)
	if not any(p.get("name") == name for p in plans):
		plans.append({"name": name, "locked": 0})
		import json
		frappe.defaults.set_global_default(f"production_scheduler_{plan_type}_plans", json.dumps(plans))
	return plans

@frappe.whitelist()
def toggle_plan_lock(plan_type, name, locked):
	plans = get_persisted_plans(plan_type)
	for p in plans:
		if p.get("name") == name:
			p["locked"] = int(locked)
	import json
	frappe.defaults.set_global_default(f"production_scheduler_{plan_type}_plans", json.dumps(plans))
	return plans

@frappe.whitelist()
def get_active_plans():
	cc_plans = get_persisted_plans("color_chart")
	pb_plans = get_persisted_plans("production_board")
	active_cc = next((p["name"] for p in cc_plans if not p.get("locked")), "Default")
	active_pb = next((p["name"] for p in pb_plans if not p.get("locked")), "")
	return {"color_chart": active_cc, "production_board": active_pb}

# --------------------------------------------------------------------------------
# Persistent Plans System
# --------------------------------------------------------------------------------

def get_persisted_plans(plan_type):
	"""Returns list of dicts: [{'name': '...', 'locked': 0}] from frappe.defaults"""
	key = f"production_scheduler_{plan_type}_plans"
	val = frappe.defaults.get_global_default(key)
	if val:
		import json
		try:
			plans = json.loads(val)
			if not any(p.get("name") == "Default" for p in plans):
				plans.insert(0, {"name": "Default", "locked": 0})
			return plans
		except:
			pass
	return [{"name": "Default", "locked": 0}]

@frappe.whitelist()
def add_persistent_plan(plan_type, name):
	plans = get_persisted_plans(plan_type)
	if not any(p.get("name") == name for p in plans):
		plans.append({"name": name, "locked": 0})
		import json
		frappe.defaults.set_global_default(f"production_scheduler_{plan_type}_plans", json.dumps(plans))
	return plans

@frappe.whitelist()
def toggle_plan_lock(plan_type, name, locked):
	plans = get_persisted_plans(plan_type)
	for p in plans:
		if p.get("name") == name:
			p["locked"] = int(locked)
	import json
	frappe.defaults.set_global_default(f"production_scheduler_{plan_type}_plans", json.dumps(plans))
	return plans

@frappe.whitelist()
def get_active_plans():
	cc_plans = get_persisted_plans("color_chart")
	pb_plans = get_persisted_plans("production_board")
	active_cc = next((p["name"] for p in cc_plans if not p.get("locked")), "Default")
	active_pb = next((p["name"] for p in pb_plans if not p.get("locked")), "")
	return {"color_chart": active_cc, "production_board": active_pb}


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
		fields=["custom_plan_name"]
	)
	
	db_plans = set([p.custom_plan_name or "Default" for p in plans])
	persisted = {p["name"]: p.get("locked", 0) for p in get_persisted_plans("color_chart")}
	
	all_names = db_plans.union(set(persisted.keys()))
	sorted_plans = sorted(list(all_names))
	
	if "Default" in sorted_plans:
		sorted_plans.remove("Default")
		sorted_plans.insert(0, "Default")
		
	return [{"name": n, "locked": persisted.get(n, 0)} for n in sorted_plans]

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
	
	# Create Production Board Plan Name custom field (SEPARATE from Color Chart plan)
	if not frappe.db.exists('Custom Field', 'Planning sheet-custom_pb_plan_name'):
		custom_field3 = frappe.get_doc({
			"doctype": "Custom Field",
			"dt": "Planning sheet",
			"fieldname": "custom_pb_plan_name",
			"label": "Production Board Plan",
			"fieldtype": "Data",
			"insert_after": "custom_plan_name",
			"description": "Production Board plan name. Separate from Color Chart plan."
		})
		custom_field3.insert(ignore_permissions=True)
	
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
		sheets = frappe.get_all("Planning sheet", filters={
			"custom_plan_name": old_plan,
			"ordered_date": ["between", [query_start, query_end]],
			"docstatus": ["<", 1] # Only move drafts
		})
	elif date:
		target_date = getdate(date)
		sheets = frappe.get_all("Planning sheet", filters={
			"custom_plan_name": old_plan,
			"ordered_date": target_date,
			"docstatus": ["<", 1]
		})
	else:
		return {"status": "error", "message": "Date filter required"}
	
	count = 0
	for sheet in sheets:
		frappe.db.set_value("Planning sheet", sheet.name, "custom_plan_name", new_plan)
		count += 1

	frappe.db.commit()
	return {"status": "success", "moved_count": count}

@frappe.whitelist()
def delete_plan(plan_name, date=None, start_date=None, end_date=None):
	"""
	Deletes a plan by moving all its sheets to 'Default'.
	"""
	if not plan_name or plan_name == "Default":
		return {"status": "error", "message": "Cannot delete Default plan"}

	if start_date and end_date:
		query_start = getdate(start_date)
		query_end = getdate(end_date)
		sheets = frappe.get_all("Planning sheet", filters={
			"custom_plan_name": plan_name,
			"ordered_date": ["between", [query_start, query_end]],
			"docstatus": ["<", 2]
		})
	elif date:
		target_date = getdate(date)
		sheets = frappe.get_all("Planning sheet", filters={
			"custom_plan_name": plan_name,
			"ordered_date": target_date,
			"docstatus": ["<", 2]
		})
	else:
		return {"status": "error", "message": "Date filter required"}

	count = 0
	for sheet in sheets:
		frappe.db.set_value("Planning sheet", sheet.name, "custom_plan_name", "Default")
		count += 1

	# Remove from persistent plans
	persisted = get_persisted_plans("color_chart")
	persisted = [p for p in persisted if p["name"] != plan_name]
	import json
	frappe.defaults.set_global_default("production_scheduler_color_chart_plans", json.dumps(persisted))

	frappe.db.commit()
	return {"status": "success", "deleted_count": count}

# ── White color group ─────────────────────────────────────────────────────────
WHITE_COLORS = {
	"BRIGHT WHITE", "SUPER WHITE", "MILKY WHITE", "SUNSHINE WHITE",
	"BLEACH WHITE 1.0", "BLEACH WHITE 2.0", "BLEACH WHITE", "WHITE MIX", "WHITE",
	"BRIGHT IVORY", "IVORY", "CREAM", "CREAM 2.0", "CREAM 3.0", "CREAM 4.0", "CREAM 5.0",
	"OFF-WHITE", "OFF WHITE",
}

# ── Color light→dark order (full list — matches COL_LIST in server script) ────
COLOR_ORDER_LIST = [
	"BRIGHT WHITE","SUPER WHITE","MILKY WHITE","SUNSHINE WHITE",
	"BLEACH WHITE 1.0","BLEACH WHITE 2.0","BLEACH WHITE","WHITE MIX","WHITE",
	"CREAM 2.0","CREAM 3.0","CREAM 4.0","CREAM 5.0","BRIGHT IVORY","IVORY","CREAM","OFF WHITE",
	"GOLDEN YELLOW 4.0 SPL","GOLDEN YELLOW 1.0","GOLDEN YELLOW 2.0","GOLDEN YELLOW 3.0","GOLDEN YELLOW",
	"LEMON YELLOW 1.0","LEMON YELLOW 3.0","LEMON YELLOW",
	"BRIGHT ORANGE","DARK ORANGE","ORANGE 2.0",
	"PINK 7.0 DARK","PINK 6.0 DARK","DARK PINK","BABY PINK","PINK 1.0","PINK 2.0","PINK 3.0","PINK 5.0",
	"CRIMSON RED","RED","LIGHT MAROON","DARK MAROON","MAROON 1.0","MAROON 2.0",
	"BLUE 13.0 INK BLUE","BLUE 12.0 SPL NAVY BLUE","BLUE 11.0 NAVY BLUE",
	"BLUE 8.0 DARK ROYAL BLUE","BLUE 7.0 DARK BLUE","BLUE 6.0 ROYAL BLUE",
	"LIGHT PEACOCK BLUE","PEACOCK BLUE","LIGHT MEDICAL BLUE","MEDICAL BLUE",
	"ROYAL BLUE","NAVY BLUE","SKY BLUE","LIGHT BLUE",
	"BLUE 9.0","BLUE 4.0","BLUE 2.0","BLUE 1.0","BLUE",
	"PURPLE 4.0 BLACKBERRY","PURPLE 1.0","PURPLE 2.0","PURPLE 3.0","VOILET",
	"GREEN 13.0 ARMY GREEN","GREEN 12.0 OLIVE GREEN","GREEN 11.0 DARK GREEN",
	"GREEN 10.0","GREEN 9.0 BOTTLE GREEN","GREEN 8.0 APPLE GREEN",
	"GREEN 7.0","GREEN 6.0","GREEN 5.0 GRASS GREEN","GREEN 4.0",
	"GREEN 3.0 RELIANCE GREEN","GREEN 2.0 TORQUISE GREEN","GREEN 1.0 MINT",
	"MEDICAL GREEN","RELIANCE GREEN","PARROT GREEN","GREEN",
	"SILVER 1.0","SILVER 2.0","LIGHT GREY","DARK GREY","GREY 1.0",
	"CHOCOLATE BROWN 2.0","CHOCOLATE BROWN","CHOCOLATE BLACK",
	"BROWN 3.0 DARK COFFEE","BROWN 2.0 DARK","BROWN 1.0",
	"CHIKOO 1.0","CHIKOO 2.0",
	"BEIGE 1.0","BEIGE 2.0","BEIGE 3.0","BEIGE 4.0","BEIGE 5.0",
	"LIGHT BEIGE","DARK BEIGE","BEIGE MIX","BLACK MIX","COLOR MIX","BLACK",
]
COLOR_PRIORITY = {c: i for i, c in enumerate(COLOR_ORDER_LIST)}

# ── Quality run order per unit ─────────────────────────────────────────────────
UNIT_QUALITY_ORDER = {
	"Unit 1": ["PREMIUM","PLATINUM","SUPER PLATINUM","GOLD","SILVER"],
	"Unit 2": ["GOLD","SILVER","BRONZE","CLASSIC","SUPER CLASSIC","LIFE STYLE",
	           "ECO SPECIAL","ECO GREEN","SUPER ECO","ULTRA","DELUXE"],
	"Unit 3": ["PREMIUM","PLATINUM","SUPER PLATINUM","GOLD","SILVER","BRONZE"],
	"Unit 4": ["PREMIUM","GOLD","SILVER","BRONZE"],
}

@frappe.whitelist()
def get_smart_push_sequence(item_names):
	"""
	Returns items in smart push order:
	  1. White phase (per unit, quality order + GSM)
	  2. Color phase (per unit): seed quality from last white → find colors in
	     seed quality (light→dark) → group all qualities of each color together
	     → update seed = last quality in batch → repeat
	Returns list of dicts with sequence_no, phase, is_seed_bridge.
	"""
	import json
	if isinstance(item_names, str):
		item_names = json.loads(item_names)
	if not item_names:
		return []

	# Load item data
	raw_items = frappe.get_all(
		"Planning Sheet Item",
		filters={"name": ["in", item_names]},
		fields=["name","color","custom_quality","gsm","qty","unit","item_name",
		        "weight_per_roll","parent"]
	)

	# Enrich with customer from parent sheet
	parent_cache = {}
	for item in raw_items:
		if item.parent not in parent_cache:
			parent_cache[item.parent] = frappe.db.get_value(
				"Planning sheet", item.parent, ["customer","party_code"], as_dict=1) or {}
		p = parent_cache[item.parent]
		item["customer"] = p.get("customer","")
		item["partyCode"] = item.get("party_code") or p.get("party_code","")
		item["quality"] = (item.get("custom_quality") or "").upper().strip()
		item["colorKey"] = (item.get("color") or "").upper().strip()
		item["unitKey"] = item.get("unit") or "Mixed"
		item["gsmVal"] = float(item.get("gsm") or 0)

	def quality_sort_key(item, unit):
		order = UNIT_QUALITY_ORDER.get(unit, [])
		q = item["quality"]
		idx = order.index(q) if q in order else len(order)
		return (idx, item["gsmVal"])

	def color_sort_key(color):
		return COLOR_PRIORITY.get(color, 9999)

	sequence = []
	seq_no = [0]  # use list so inner scope can mutate

	units_present = list({i["unitKey"] for i in raw_items if i["unitKey"] != "Mixed"})
	units_present += (["Mixed"] if any(i["unitKey"] == "Mixed" for i in raw_items) else [])

	for unit in ["Unit 1","Unit 2","Unit 3","Unit 4","Mixed"]:
		if unit not in units_present:
			continue

		unit_items = [i for i in raw_items if i["unitKey"] == unit]
		if not unit_items:
			continue

		white_items = [i for i in unit_items if i["colorKey"] in WHITE_COLORS]
		color_items = [i for i in unit_items if i["colorKey"] not in WHITE_COLORS]

		# ── Phase 1: White ──
		white_sorted = sorted(white_items, key=lambda i: quality_sort_key(i, unit))
		seed_quality = None
		for idx, item in enumerate(white_sorted):
			seq_no[0] += 1
			is_last = (idx == len(white_sorted) - 1)
			if is_last:
				seed_quality = item["quality"]
			sequence.append({
				**item,
				"sequence_no": seq_no[0],
				"phase": "white",
				"is_seed_bridge": is_last and len(color_items) > 0,
			})

		# ── Phase 2: Color chaining ──
		remaining = list(color_items)
		done_colors = set()
		quality_order = UNIT_QUALITY_ORDER.get(unit, [])

		max_loops = len(remaining) + len(quality_order) + 5  # safety
		loops = 0

		while remaining and loops < max_loops:
			loops += 1

			# Find colors available in current seed quality (light→dark)
			if seed_quality:
				seed_pool = [i for i in remaining if i["quality"] == seed_quality]
			else:
				seed_pool = remaining

			seed_pool_colors = sorted(
				list({i["colorKey"] for i in seed_pool if i["colorKey"] not in done_colors}),
				key=color_sort_key
			)

			if not seed_pool_colors:
				# No more colors in this seed quality → advance to next quality in unit order
				if seed_quality and seed_quality in quality_order:
					qi = quality_order.index(seed_quality)
					advanced = False
					for nq in quality_order[qi+1:]:
						pool = [i for i in remaining if i["quality"] == nq and i["colorKey"] not in done_colors]
						if pool:
							seed_quality = nq
							advanced = True
							break
					if not advanced:
						# Just dump all remaining in color/GSM order
						seed_quality = None
						continue
				else:
					# No quality order reference — just take lightest remaining color
					all_remaining_colors = sorted(
						list({i["colorKey"] for i in remaining if i["colorKey"] not in done_colors}),
						key=color_sort_key
					)
					if not all_remaining_colors:
						break
					seed_pool_colors = [all_remaining_colors[0]]

				continue

			# Pick the lightest color from seed pool
			chosen_color = seed_pool_colors[0]
			done_colors.add(chosen_color)

			# Collect ALL items of this color (all qualities) and sort by unit quality order + GSM
			color_batch = sorted(
				[i for i in remaining if i["colorKey"] == chosen_color],
				key=lambda i: quality_sort_key(i, unit)
			)
			remaining = [i for i in remaining if i["colorKey"] != chosen_color]

			for idx, item in enumerate(color_batch):
				seq_no[0] += 1
				is_last = (idx == len(color_batch) - 1)
				if is_last:
					seed_quality = item["quality"]
				sequence.append({
					**item,
					"sequence_no": seq_no[0],
					"phase": "color",
					"is_seed_bridge": is_last and len(remaining) > 0,
				})

	# Append any unsequenced (Mixed unit or edge cases)
	sequenced_names = {i["name"] for i in sequence}
	for item in raw_items:
		if item["name"] not in sequenced_names:
			seq_no[0] += 1
			sequence.append({**item, "sequence_no": seq_no[0], "phase": "unassigned", "is_seed_bridge": False})

	return sequence

@frappe.whitelist()
def move_items_to_plan(item_names, target_plan, date=None, start_date=None, end_date=None, days_in_view=1, force_move=0):
	"""
	Copies specific Planning Sheet Items to a target Color Chart plan.
	- days_in_view: scale capacity limit (e.g. 28 for monthly February, 7 for weekly).
	- force_move=1: skip capacity check entirely (used in monthly/weekly views).
	- Items linked to cancelled Sales Orders are silently skipped with a warning.
	"""
	import json
	if isinstance(item_names, str):
		item_names = json.loads(item_names)
	days_in_view = int(days_in_view) if days_in_view else 1
	force_move = int(force_move) if force_move else 0

	if not item_names or not target_plan:
		return {"status": "error", "message": "Missing item names or target plan"}

	moved = 0
	skipped = []
	errors = []
	new_sheet_cache = {}  # (party_code, effective_date) -> sheet_name

	UNIT_LIMITS = {"Unit 1": 4.4, "Unit 2": 12.0, "Unit 3": 9.0, "Unit 4": 5.5}

	for name in item_names:
		try:
			item_doc = frappe.get_doc("Planning Sheet Item", name)
			parent_sheet = frappe.get_doc("Planning sheet", item_doc.parent)

			target_unit = item_doc.unit or "Mixed"
			effective_date = parent_sheet.get("custom_planned_date") or parent_sheet.ordered_date
			party_code = parent_sheet.party_code or ""

			# --- Guard: skip items on cancelled Sales Orders ---
			if parent_sheet.sales_order:
				so_status = frappe.db.get_value("Sales Order", parent_sheet.sales_order, "docstatus")
				if so_status == 2:  # Cancelled
					skipped.append(f"{name}: linked Sales Order {parent_sheet.sales_order} is cancelled — skipped")
					continue

			# --- Find or create a Planning Sheet in the target plan ---
			cache_key = (party_code, str(effective_date))
			if cache_key in new_sheet_cache:
				target_sheet_name = new_sheet_cache[cache_key]
			else:
				filters = {
					"custom_plan_name": target_plan,
					"ordered_date": effective_date,
					"docstatus": ["<", 1]
				}
				if party_code:
					filters["party_code"] = party_code

				existing = frappe.get_all("Planning sheet", filters=filters, fields=["name"], limit=1)

				if existing:
					target_sheet_name = existing[0].name
				else:
					new_sheet = frappe.new_doc("Planning sheet")
					new_sheet.custom_plan_name = target_plan
					new_sheet.ordered_date = effective_date
					new_sheet.party_code = party_code
					new_sheet.customer = parent_sheet.customer or ""
					# Don't copy sales_order to avoid cancelled SO linkage issues
					new_sheet.insert(ignore_permissions=True)
					target_sheet_name = new_sheet.name

				new_sheet_cache[cache_key] = target_sheet_name

			# --- Capacity check (scaled by days_in_view, skipped if force_move) ---
			if not force_move:
				daily_limit = UNIT_LIMITS.get(target_unit, 9999)
				scaled_limit = daily_limit * days_in_view
				target_items = frappe.get_all(
					"Planning Sheet Item",
					filters={"parent": target_sheet_name, "unit": target_unit},
					fields=["qty"]
				)
				current_kg = sum(float(i.qty or 0) for i in target_items)
				item_kg = float(item_doc.qty or 0)
				if (current_kg + item_kg) / 1000 > scaled_limit:
					errors.append(
						f"{item_doc.item_name}: Would exceed {target_unit} capacity "
						f"({(current_kg/1000):.2f}+{(item_kg/1000):.2f} > {scaled_limit:.1f}T)"
					)
					continue

			# --- COPY the item to target sheet (source stays unchanged) ---
			new_item = frappe.new_doc("Planning Sheet Item")
			for field in item_doc.meta.fields:
				fname = field.fieldname
				if fname in ("name", "parent", "parenttype", "parentfield", "idx", "creation", "modified", "owner"):
					continue
				try:
					setattr(new_item, fname, item_doc.get(fname))
				except Exception:
					pass
			new_item.parent = target_sheet_name
			new_item.parenttype = "Planning sheet"
			new_item.parentfield = "items"
			new_item.insert(ignore_permissions=True)
			moved += 1

		except Exception as e:
			errors.append(f"{name}: {str(e)}")

	frappe.db.commit()
	result = {"status": "success", "moved": moved}
	if skipped:
		result["skipped"] = skipped
	if errors:
		result["errors"] = errors
	return result


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
def move_orders_to_date(item_names, target_date, target_unit=None, plan_name=None, pb_plan_name=None):
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
            
    # 2. Check Limits (skip if force_move — e.g. monthly/weekly aggregate view)
    if not force_move:
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
        
        # Determine target plan: if explicitly "Default", force to None (no plan = Default view)
        if plan_name and plan_name != "Default":
            target_plan = plan_name
        elif plan_name == "Default":
            target_plan = None  # Explicitly targeting Default = no custom plan name
        else:
            target_plan = parent_doc.get("custom_plan_name")
            if target_plan == "Default": target_plan = None
            
        # Determine target PB plan
        if pb_plan_name and pb_plan_name != "Default":
            target_pb_plan = pb_plan_name
        elif pb_plan_name == "Default":
            target_pb_plan = None
        else:
            target_pb_plan = parent_doc.get("custom_pb_plan_name")
            if target_pb_plan == "Default": target_pb_plan = None
        
        if target_plan:
             find_filters["custom_plan_name"] = target_plan
        else:
             find_filters["custom_plan_name"] = ["in", ["", None, "Default"]]
             
        if target_pb_plan:
             find_filters["custom_pb_plan_name"] = target_pb_plan
        else:
             find_filters["custom_pb_plan_name"] = ["in", ["", None, "Default"]]
             
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
            if target_pb_plan:
                target_sheet.custom_pb_plan_name = target_pb_plan
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

            # QUALITY ENFORCEMENT
            if new_unit and not is_quality_allowed(new_unit, item_doc.custom_quality):
                frappe.throw(_("Quality <b>{}</b> is not allowed in <b>{}</b> (Item: {}).").format(
                    item_doc.custom_quality or "Generic", new_unit, item_doc.item_name
                ))

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
    AUTO-CREATE PLANNING SHEET (QUALITY + GSM LOGIC)
    """
    try:
        # Check if an UNLOCKED Planning Sheet already exists
        existing_sheets = frappe.get_all("Planning sheet", filters={"sales_order": doc.name, "docstatus": ["<", 2]}, fields=["name"])
        unlocked_sheet = None
        for s in existing_sheets:
            if not is_sheet_locked(s.name):
                unlocked_sheet = s.name
                break
        
        if unlocked_sheet:
            # frappe.msgprint(f"ℹ️ Planning Sheet already exists (unlocked): {unlocked_sheet}")
            return
            
        # --- GET ACTIVE UNLOCKED PLANS ---
        try:
            active_plans = get_active_plans()
            cc_plan = active_plans.get("color_chart", "Default")
            pb_plan = active_plans.get("production_board", "")
        except Exception:
            cc_plan = "Default"
            pb_plan = ""

        # --- QUALITIES PER UNIT ---
        UNIT_1_MAP = ["PREMIUM", "PLATINUM", "SUPER PLATINUM", "GOLD", "SILVER"]
        UNIT_2_MAP = ["GOLD", "SILVER", "BRONZE", "CLASSIC", "SUPER CLASSIC", "LIFE STYLE",
                      "ECO SPECIAL", "ECO GREEN", "SUPER ECO", "ULTRA", "DELUXE"]
        UNIT_3_MAP = ["PREMIUM", "PLATINUM", "SUPER PLATINUM", "GOLD", "SILVER", "BRONZE"]
        UNIT_4_MAP = ["PREMIUM", "GOLD", "SILVER", "BRONZE"]

        # Longest first to avoid partial matches
        QUAL_LIST = ["SUPER PLATINUM", "SUPER CLASSIC", "SUPER ECO", "ECO SPECIAL", "ECO GREEN",
                     "ECO SPL", "LIFE STYLE", "LIFESTYLE", "PREMIUM", "PLATINUM", "CLASSIC",
                     "DELUXE", "BRONZE", "SILVER", "ULTRA", "GOLD", "UV"]
        QUAL_LIST.sort(key=len, reverse=True)

        COL_LIST = [
            "BRIGHT WHITE", "SUPER WHITE", "MILKY WHITE", "SUNSHINE WHITE",
            "BLEACH WHITE", "WHITE MIX", "WHITE",
            "CREAM 2.0", "CREAM 3.0", "CREAM 4.0", "CREAM 5.0",
            "GOLDEN YELLOW 4.0 SPL", "GOLDEN YELLOW 1.0", "GOLDEN YELLOW 2.0",
            "GOLDEN YELLOW 3.0", "GOLDEN YELLOW",
            "LEMON YELLOW 1.0", "LEMON YELLOW 3.0", "LEMON YELLOW",
            "BRIGHT ORANGE", "DARK ORANGE", "ORANGE 2.0",
            "PINK 7.0 DARK", "PINK 6.0 DARK", "DARK PINK",
            "BABY PINK", "PINK 1.0", "PINK 2.0", "PINK 3.0", "PINK 5.0",
            "CRIMSON RED", "RED",
            "LIGHT MAROON", "DARK MAROON", "MAROON 1.0", "MAROON 2.0",
            "BLUE 13.0 INK BLUE", "BLUE 12.0 SPL NAVY BLUE", "BLUE 11.0 NAVY BLUE",
            "BLUE 8.0 DARK ROYAL BLUE", "BLUE 7.0 DARK BLUE", "BLUE 6.0 ROYAL BLUE",
            "LIGHT PEACOCK BLUE", "PEACOCK BLUE", "LIGHT MEDICAL BLUE", "MEDICAL BLUE",
            "ROYAL BLUE", "NAVY BLUE", "SKY BLUE", "LIGHT BLUE",
            "BLUE 9.0", "BLUE 4.0", "BLUE 2.0", "BLUE 1.0", "BLUE",
            "PURPLE 4.0 BLACKBERRY", "PURPLE 1.0", "PURPLE 2.0", "PURPLE 3.0", "VOILET",
            "GREEN 13.0 ARMY GREEN", "GREEN 12.0 OLIVE GREEN", "GREEN 11.0 DARK GREEN",
            "GREEN 10.0", "GREEN 9.0 BOTTLE GREEN", "GREEN 8.0 APPLE GREEN",
            "GREEN 7.0", "GREEN 6.0", "GREEN 5.0 GRASS GREEN", "GREEN 4.0",
            "GREEN 3.0 RELIANCE GREEN", "GREEN 2.0 TORQUISE GREEN", "GREEN 1.0 MINT",
            "MEDICAL GREEN", "RELIANCE GREEN", "PARROT GREEN", "GREEN",
            "SILVER 1.0", "SILVER 2.0", "LIGHT GREY", "DARK GREY", "GREY 1.0",
            "CHOCOLATE BROWN 2.0", "CHOCOLATE BROWN", "CHOCOLATE BLACK",
            "BROWN 3.0 DARK COFFEE", "BROWN 2.0 DARK", "BROWN 1.0",
            "CHIKOO 1.0", "CHIKOO 2.0",
            "BEIGE 1.0", "BEIGE 2.0", "BEIGE 3.0", "BEIGE 4.0", "BEIGE 5.0",
            "LIGHT BEIGE", "DARK BEIGE", "BEIGE MIX",
            "BLACK MIX", "COLOR MIX", "BLACK",
        ]
        COL_LIST.sort(key=len, reverse=True)

        ps = frappe.new_doc("Planning sheet")
        ps.sales_order = doc.name
        ps.customer = doc.customer
        ps.party_code = doc.get("party_code") or doc.customer
        ps.ordered_date = doc.transaction_date 
        ps.custom_planned_date = doc.delivery_date
        ps.dod = doc.delivery_date
        ps.planning_status = "Draft"
        ps.custom_plan_name = cc_plan
        ps.custom_pb_plan_name = pb_plan

        for it in doc.items:
            raw_txt = (it.item_code or "") + " " + (it.item_name or "")
            clean_txt = raw_txt.upper().replace("-", " ").replace("_", " ").replace("(", " ").replace(")", " ")
            clean_txt = clean_txt.replace("''", " INCH ").replace('"', " INCH ")
            words = clean_txt.split()

            # GSM
            gsm = 0
            for i in range(1, len(words)):
                if words[i] == "GSM":
                    if words[i-1].isdigit():
                        gsm = int(words[i-1])
                        break

            # WIDTH
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

            # QUALITY & COLOR
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

            # WEIGHT
            m_roll = float(it.custom_meter_per_roll or 0)
            wt = 0.0
            if gsm > 0 and width > 0 and m_roll > 0:
                wt = (gsm * width * m_roll * 0.0254) / 1000

            # UNIT
            unit = "Unit 1"
            if qual:
                q_up = qual.upper()
                if gsm > 50 and q_up in UNIT_1_MAP:
                    unit = "Unit 1"
                elif gsm > 20 and q_up in UNIT_2_MAP:
                    unit = "Unit 2"
                elif gsm > 10 and q_up in UNIT_3_MAP:
                    unit = "Unit 3"
                elif q_up in UNIT_4_MAP:
                    unit = "Unit 4"

            ps.append("items", {
                "sales_order_item": it.name,
                "item_code": it.item_code,
                "item_name": it.item_name,
                "qty": it.qty,
                "uom": it.uom,
                "meter": float(it.custom_meter or 0),
                "meter_per_roll": m_roll,
                "no_of_rolls": float(it.custom_no_of_rolls or 0),
                "gsm": gsm,
                "width_inch": width,
                "custom_quality": qual,
                "color": col,
                "weight_per_roll": wt,
                "unit": unit,
                "party_code": ps.party_code
            })

        ps.flags.ignore_permissions = True
        ps.insert()
        frappe.db.commit()
        frappe.msgprint(f"✅ Planning Sheet <b>{ps.name}</b> Created!")

    except Exception as e:
        frappe.log_error("Planning Sheet Creation Failed: " + str(e))
        frappe.msgprint("⚠️ Planning Sheet failed. Check 'Error Log' for details.")

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


# --------------------------------------------------------------------------------
# Production Board Plan System (Separate from Color Chart)
# --------------------------------------------------------------------------------

@frappe.whitelist()
def get_pb_plans(date=None, start_date=None, end_date=None):
	"""Get unique Production Board plan names for a date or range."""
	eff = _effective_date_expr("p")
	
	if start_date and end_date:
		query_start = frappe.utils.getdate(start_date)
		query_end = frappe.utils.getdate(end_date)
		date_condition = f"{eff} BETWEEN %s AND %s"
		params = [query_start, query_end]
	elif date:
		target_date = frappe.utils.getdate(date)
		date_condition = f"{eff} = %s"
		params = [target_date]
	else:
		return []
	
	plans = frappe.db.sql(f"""
		SELECT DISTINCT IFNULL(p.custom_pb_plan_name, '') as pb_plan_name
		FROM `tabPlanning sheet` p
		WHERE {date_condition} AND p.docstatus < 2
			AND p.custom_pb_plan_name IS NOT NULL 
			AND p.custom_pb_plan_name != ''
	""", tuple(params), as_dict=True)
	
	db_plans = set([p.pb_plan_name for p in plans if p.pb_plan_name])
	persisted = {p["name"]: p.get("locked", 0) for p in get_persisted_plans("production_board")}
	
	all_names = db_plans.union(set(persisted.keys()))
	sorted_plans = sorted(list(all_names))
	
	return [{"name": n, "locked": persisted.get(n, 0)} for n in sorted_plans]

@frappe.whitelist()
def push_to_pb(item_names, pb_plan_name):
	"""
	Pushes ONLY the selected Planning Sheet items to a Production Board plan.
	Each item is re-parented to a new (or existing) Planning Sheet that has
	custom_pb_plan_name set. The original sheet keeps any un-pushed items
	(e.g., if Golden Yellow and Orange share a sheet, only Golden Yellow moves).
	"""
	import json
	if isinstance(item_names, str):
		item_names = json.loads(item_names)

	if not item_names or not pb_plan_name:
		return {"status": "error", "message": "Missing item names or plan name"}

	updated_count = 0
	pb_sheet_cache = {}  # (party_code, effective_date) -> pb sheet name

	for name in item_names:
		try:
			item = frappe.get_doc("Planning Sheet Item", name)
			parent = frappe.get_doc("Planning sheet", item.parent)

			effective_date = str(parent.get("custom_planned_date") or parent.ordered_date)
			party_code = parent.party_code or ""

			# Find or create a dedicated PB Planning Sheet for this date+party
			cache_key = (party_code, effective_date, pb_plan_name)
			if cache_key in pb_sheet_cache:
				pb_sheet_name = pb_sheet_cache[cache_key]
			else:
				existing = frappe.get_all("Planning sheet", filters={
					"custom_pb_plan_name": pb_plan_name,
					"ordered_date": effective_date,
					"party_code": party_code,
					"docstatus": ["<", 1]
				}, fields=["name"], limit=1)

				if existing:
					pb_sheet_name = existing[0].name
				else:
					pb_sheet = frappe.new_doc("Planning sheet")
					pb_sheet.custom_plan_name = parent.get("custom_plan_name") or "Default"
					pb_sheet.custom_pb_plan_name = pb_plan_name
					pb_sheet.ordered_date = effective_date
					pb_sheet.custom_planned_date = effective_date
					pb_sheet.party_code = party_code
					pb_sheet.customer = parent.customer or ""
					pb_sheet.sales_order = parent.sales_order or ""
					pb_sheet.insert(ignore_permissions=True)
					pb_sheet_name = pb_sheet.name

				pb_sheet_cache[cache_key] = pb_sheet_name

			# Move item to the PB sheet
			frappe.db.set_value("Planning Sheet Item", name, "parent", pb_sheet_name)
			frappe.db.set_value("Planning Sheet Item", name, "parenttype", "Planning sheet")
			frappe.db.set_value("Planning Sheet Item", name, "parentfield", "items")
			updated_count += 1

		except Exception as e:
			frappe.log_error(f"push_to_pb error for item {name}: {e}", "Push to PB")

	frappe.db.commit()
	return {"status": "success", "updated_count": updated_count, "plan_name": pb_plan_name}


@frappe.whitelist()
def push_items_to_pb(items_data, pb_plan_name):
	"""
	Pushes Planning Sheet Items to a Production Board plan.
	Sets custom_pb_plan_name on the parent Planning Sheet for each item.
	items_data: list of dicts [{"name": "...", "target_date": "...", "target_unit": "..."}]
	"""
	import json
	if isinstance(items_data, str):
		items_data = json.loads(items_data)

	if not items_data or not pb_plan_name:
		return {"status": "error", "message": "Missing item data or plan name"}

	count = 0
	updated_sheets = set()

	for item in items_data:
		name = item.get("name") if isinstance(item, dict) else item
		target_date = item.get("target_date") if isinstance(item, dict) else None

		try:
			# Get the parent Planning Sheet
			parent = frappe.db.get_value("Planning Sheet Item", name, "parent")
			if not parent:
				continue

			if parent not in updated_sheets:
				frappe.db.set_value("Planning sheet", parent, "custom_pb_plan_name", pb_plan_name)
				if target_date:
					frappe.db.set_value("Planning sheet", parent, "custom_planned_date", target_date)
				updated_sheets.add(parent)
			count += 1

		except Exception as e:
			frappe.log_error(f"push_items_to_pb error for {name}: {e}", "Push to PB")

	# Persist this PB plan name
	persisted = get_persisted_plans("production_board")
	if not any(p["name"] == pb_plan_name for p in persisted):
		persisted.append({"name": pb_plan_name, "locked": 0})
		import json as _json
		frappe.defaults.set_global_default(
			"production_scheduler_production_board_plans",
			_json.dumps(persisted)
		)

	frappe.db.commit()
	return {"status": "success", "moved_items": count, "updated_sheets": len(updated_sheets), "plan_name": pb_plan_name}


@frappe.whitelist()
def delete_pb_plan(pb_plan_name, date=None, start_date=None, end_date=None):
	"""
	Removes Production Board plan assignment from Planning Sheets.
	Does NOT delete the sheets — just clears custom_pb_plan_name.
	"""
	if not pb_plan_name:
		return {"status": "error", "message": "Plan name required"}
	
	eff = _effective_date_expr("p")
	
	if start_date and end_date:
		query_start = frappe.utils.getdate(start_date)
		query_end = frappe.utils.getdate(end_date)
		date_condition = f"{eff} BETWEEN %s AND %s"
		params = [query_start, query_end]
	elif date:
		target_date = frappe.utils.getdate(date)
		date_condition = f"{eff} = %s"
		params = [target_date]
	else:
		return {"status": "error", "message": "Date filter required"}
	
	params.append(pb_plan_name)
	
	result = frappe.db.sql(f"""
		UPDATE `tabPlanning sheet` p
		SET p.custom_pb_plan_name = ''
		WHERE {date_condition} AND p.docstatus < 2 AND p.custom_pb_plan_name = %s
	""", tuple(params))
	
	affected = frappe.db.sql("SELECT ROW_COUNT() as cnt")[0][0]

	# Remove from persistent plans
	persisted = get_persisted_plans("production_board")
	persisted = [p for p in persisted if p["name"] != pb_plan_name]
	import json
	frappe.defaults.set_global_default("production_scheduler_production_board_plans", json.dumps(persisted))

	frappe.db.commit()
	return {"status": "success", "cleared_count": affected}


@frappe.whitelist()
def revert_items_to_color_chart(item_names):
	"""
	Reverts items back to the Color Chart by clearing their Planning Sheet's custom_planned_date.
	Note: This affects the entire Planning Sheet containing the item.
	White orders generally re-evaluate to have a planned date implicitly, 
	but this clears the explicit field.
	"""
	import json
	if isinstance(item_names, str):
		item_names = json.loads(item_names)

	if not item_names:
		return {"status": "error", "message": "No items provided"}

	updated_sheets = set()
	for name in item_names:
		try:
			parent = frappe.db.get_value("Planning Sheet Item", name, "parent")
			if parent and parent not in updated_sheets:
				frappe.db.set_value("Planning sheet", parent, "custom_planned_date", None)
				updated_sheets.add(parent)
		except Exception as e:
			frappe.log_error(f"revert error for {name}: {e}", "Revert to Color Chart")

	frappe.db.commit()
	return {"status": "success", "reverted_sheets": len(updated_sheets)}


@frappe.whitelist()
def revert_pb_push(pb_plan_name, date=None):
	"""
	Reverts a Production Board push for a specific date.
	Moves all items from PB Planning Sheets back to their original Color Chart sheets,
	then deletes the (now empty) PB sheets.
	"""
	if not pb_plan_name:
		return {"status": "error", "message": "Plan name required"}

	target_date = frappe.utils.getdate(date) if date else None

	filters = {
		"custom_pb_plan_name": pb_plan_name,
		"docstatus": ["<", 2]
	}
	if target_date:
		filters["ordered_date"] = target_date

	pb_sheets = frappe.get_all("Planning sheet", filters=filters, fields=["name", "ordered_date", "party_code", "custom_plan_name"])

	reverted = 0
	for pb_sheet in pb_sheets:
		# Find the original Color Chart sheet for same date + party_code (no pb_plan_name)
		original_filters = {
			"ordered_date": pb_sheet.ordered_date,
			"custom_pb_plan_name": ["in", ["", None]],
			"docstatus": ["<", 2]
		}
		if pb_sheet.party_code:
			original_filters["party_code"] = pb_sheet.party_code
		if pb_sheet.custom_plan_name:
			original_filters["custom_plan_name"] = pb_sheet.custom_plan_name

		originals = frappe.get_all("Planning sheet", filters=original_filters, fields=["name"], limit=1)

		if originals:
			original_sheet_name = originals[0].name
		else:
			# Create a blank original sheet if none found
			orig_sheet = frappe.new_doc("Planning sheet")
			orig_sheet.custom_plan_name = pb_sheet.custom_plan_name or "Default"
			orig_sheet.ordered_date = pb_sheet.ordered_date
			orig_sheet.party_code = pb_sheet.party_code or ""
			orig_sheet.insert(ignore_permissions=True)
			original_sheet_name = orig_sheet.name

		# Move all items from PB sheet back to original sheet
		items = frappe.get_all("Planning Sheet Item", filters={"parent": pb_sheet.name}, fields=["name"])
		for item in items:
			frappe.db.set_value("Planning Sheet Item", item.name, "parent", original_sheet_name)
			frappe.db.set_value("Planning Sheet Item", item.name, "parenttype", "Planning sheet")
			frappe.db.set_value("Planning Sheet Item", item.name, "parentfield", "items")
			reverted += 1

		# Delete the now-empty PB sheet
		frappe.delete_doc("Planning sheet", pb_sheet.name, ignore_permissions=True, force=True)

	frappe.db.commit()
	return {"status": "success", "reverted": reverted, "sheets_removed": len(pb_sheets)}

# ------------------------------------------------------------
# AUTO-CREATE PLANNING SHEET (BACKGROUND EXECUTION)
# ------------------------------------------------------------

def auto_create_planning_sheet(doc, method=None):
    """Create a Planning Sheet for a Sales Order.
    - Uses the first unlocked Color Chart plan.
    - If *all* plans are locked, aborts creation (no default fallback).
    - Does NOT set `custom_planned_date`; it will be filled when the sheet is pushed to the Production Board.
    """
    # 1. FETCH UNLOCKED PLAN
    cc_plan = None
    try:
        raw_string = frappe.db.get_value("DefaultValue", {"defkey": "production_scheduler_color_chart_plans", "parent": "__default"}, "defvalue")
        if raw_string:
            parsed = json.loads(raw_string)
            if isinstance(parsed, str):
                parsed = json.loads(parsed)
            if isinstance(parsed, list):
                for plan in parsed:
                    if int(plan.get("locked", 0)) == 0:
                        cc_plan = plan.get("name")
                        break
    except Exception as e:
        frappe.log_error("Plan Lock Fetch Error (auto-create)", str(e))

    if not cc_plan:
        # All plans are locked – do not create a sheet
        frappe.msgprint("⚠️ All Color Chart plans are locked – Planning Sheet not created.", indicator="orange", alert=True)
        return None

    # 2. CHECK IF AN UNLOCKED SHEET ALREADY EXISTS FOR THIS ORDER
    existing = frappe.get_all("Planning sheet",
        filters={"sales_order": doc.name, "docstatus": ["<", 2]},
        fields=["name", "custom_plan_name", "docstatus"]
    )
    for s in existing:
        if s.docstatus != 0:
            continue
        if (s.custom_plan_name or "Default") == cc_plan:
            # Sheet already exists for the unlocked plan – nothing to do
            return frappe.get_doc("Planning sheet", s.name)

    # 3. CREATE PLANNING SHEET (without planned date unless white order)
    has_white = False
    whites = ["WHITE", "BRIGHT WHITE", "P. WHITE", "P.WHITE", "R.F.D", "RFD", "BLEACHED", "B.WHITE", "SNOW WHITE", "MILKY WHITE", "SUPER WHITE", "SUNSHINE WHITE", "IVORY", "CREAM", "OFF WHITE"]
    for it in doc.items:
        raw_txt = (it.item_code or "") + " " + (it.item_name or "")
        clean_txt = raw_txt.upper()
        if any(w in clean_txt for w in whites):
            has_white = True
            break

    generate_party_code(doc)
    ps = frappe.new_doc("Planning sheet")
    ps.sales_order = doc.name
    ps.customer = doc.customer
    ps.party_code = doc.party_code
    ps.ordered_date = doc.transaction_date
    if has_white:
        ps.custom_planned_date = doc.transaction_date
    ps.dod = doc.delivery_date
    ps.planning_status = "Draft"
    ps.custom_plan_name = cc_plan
    ps.custom_pb_plan_name = ""

    # Populate items – reuse the same parsing logic from the original script
    for it in doc.items:
        raw_txt = (it.item_code or "") + " " + (it.item_name or "")
        clean_txt = raw_txt.upper().replace("-", " ").replace("_", " ").replace("(", " ").replace(")", " ")
        clean_txt = clean_txt.replace("''", " INCH ").replace('"', " INCH ")
        words = clean_txt.split()

        # GSM extraction
        gsm = 0
        for i, w in enumerate(words):
            if w == "GSM" and i > 0 and words[i-1].isdigit():
                gsm = int(words[i-1])
                break
            elif w.endswith("GSM") and w[:-3].isdigit():
                gsm = int(w[:-3])
                break

        # WIDTH extraction
        width = 0.0
        for i, w in enumerate(words):
            if w == "W" and i < len(words)-1 and words[i+1].replace('.','',1).isdigit():
                width = float(words[i+1])
                break
            elif w.startswith("W") and len(w) > 1 and w[1:].replace('.','',1).isdigit():
                width = float(w[1:])
                break
            elif w == "INCH" and i > 0 and words[i-1].replace('.','',1).isdigit():
                width = float(words[i-1])
                break
            elif w.endswith("INCH") and w[:-4].replace('.','',1).isdigit():
                width = float(w[:-4])
                break

        # QUALITY & COLOR detection
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

        # WEIGHT calculation
        m_roll = float(it.custom_meter_per_roll or 0)
        wt = 0.0
        if gsm > 0 and width > 0 and m_roll > 0:
            wt = (gsm * width * m_roll * 0.0254) / 1000

        # UNIT determination
        unit = "Unit 1"
        if qual:
            q_up = qual.upper()
            if gsm > 50 and q_up in UNIT_1:
                unit = "Unit 1"
            elif gsm > 20 and q_up in UNIT_2:
                unit = "Unit 2"
            elif gsm > 10 and q_up in UNIT_3:
                unit = "Unit 3"
            elif q_up in UNIT_4:
                unit = "Unit 4"

        ps.append("items", {
            "sales_order_item": it.name,
            "item_code": it.item_code,
            "item_name": it.item_name,
            "qty": it.qty,
            "uom": it.uom,
            "meter": float(it.custom_meter or 0),
            "meter_per_roll": m_roll,
            "no_of_rolls": float(it.custom_no_of_rolls or 0),
            "gsm": gsm,
            "width_inch": width,
            "custom_quality": qual,
            "color": col,
            "weight_per_roll": wt,
            "unit": unit,
            "party_code": ps.party_code,
        })

    ps.flags.ignore_permissions = True
    ps.insert()
    frappe.db.commit()
    frappe.msgprint(f"✅ Planning Sheet <b>{ps.name}</b> created in unlocked plan <b>{cc_plan}</b>")
    return ps

# ------------------------------------------------------------
# REGENERATE PLANNING SHEET (MANUAL RE-CREATION)
# ------------------------------------------------------------

@frappe.whitelist()
def regenerate_planning_sheet(so_name):
    """Regenerate a Planning Sheet for a Sales Order.
    - Fails if an active sheet already exists.
    - Uses the first unlocked Color Chart plan; aborts if all locked.
    - Does NOT set `custom_planned_date` on creation.
    """
    if not so_name:
        frappe.throw("Sales Order Name is required")

    existing = frappe.db.get_value("Planning sheet", {"sales_order": so_name, "docstatus": ["<", 2]}, "name")
    if existing:
        frappe.throw(f"⚠️ An active Planning Sheet <b>{existing}</b> already exists. Cancel it first.")

    doc = frappe.get_doc("Sales Order", so_name)

    # 1. FETCH UNLOCKED PLAN (same logic as auto_create)
    cc_plan = None
    try:
        raw_string = frappe.db.get_value("DefaultValue", {"defkey": "production_scheduler_color_chart_plans", "parent": "__default"}, "defvalue")
        if raw_string:
            parsed = json.loads(raw_string)
            if isinstance(parsed, str):
                parsed = json.loads(parsed)
            if isinstance(parsed, list):
                for plan in parsed:
                    if int(plan.get("locked", 0)) == 0:
                        cc_plan = plan.get("name")
                        break
    except Exception as e:
        frappe.log_error("Plan Lock Fetch Error (regen)", str(e))

    if not cc_plan:
        frappe.msgprint("⚠️ All Color Chart plans are locked – cannot regenerate Planning Sheet.", indicator="orange", alert=True)
        return None

    # 2. CREATE PLANNING SHEET
    has_white = False
    whites = ["WHITE", "BRIGHT WHITE", "P. WHITE", "P.WHITE", "R.F.D", "RFD", "BLEACHED", "B.WHITE", "SNOW WHITE", "MILKY WHITE", "SUPER WHITE", "SUNSHINE WHITE", "IVORY", "CREAM", "OFF WHITE"]
    for it in doc.items:
        raw_txt = (it.item_code or "") + " " + (it.item_name or "")
        clean_txt = raw_txt.upper()
        if any(w in clean_txt for w in whites):
            has_white = True
            break

    generate_party_code(doc)
    ps = frappe.new_doc("Planning sheet")
    ps.sales_order = doc.name
    ps.customer = doc.customer
    ps.party_code = doc.get("party_code") or ""
    ps.ordered_date = doc.transaction_date
    if has_white:
        ps.custom_planned_date = doc.transaction_date
    ps.dod = doc.delivery_date
    ps.planning_status = "Draft"
    ps.custom_plan_name = cc_plan
    ps.custom_pb_plan_name = ""

    for it in doc.items:
        raw_txt = (it.item_code or "") + " " + (it.item_name or "")
        clean_txt = raw_txt.upper().replace("-", " ").replace("_", " ").replace("(", " ").replace(")", " ")
        clean_txt = clean_txt.replace("''", " INCH ").replace('"', " INCH ")
        words = clean_txt.split()
        gsm = 0
        for i, w in enumerate(words):
            if w == "GSM" and i > 0 and words[i-1].isdigit():
                gsm = int(words[i-1])
                break
            elif w.endswith("GSM") and w[:-3].isdigit():
                gsm = int(w[:-3])
                break
        width = 0.0
        for i, w in enumerate(words):
            if w == "W" and i < len(words)-1 and words[i+1].replace('.','',1).isdigit():
                width = float(words[i+1])
                break
            elif w.startswith("W") and len(w) > 1 and w[1:].replace('.','',1).isdigit():
                width = float(w[1:])
                break
            elif w == "INCH" and i > 0 and words[i-1].replace('.','',1).isdigit():
                width = float(words[i-1])
                break
            elif w.endswith("INCH") and w[:-4].replace('.','',1).isdigit():
                width = float(w[:-4])
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
        unit = "Unit 1"
        if qual:
            q_up = qual.upper()
            if gsm > 50 and q_up in UNIT_1:
                unit = "Unit 1"
            elif gsm > 20 and q_up in UNIT_2:
                unit = "Unit 2"
            elif gsm > 10 and q_up in UNIT_3:
                unit = "Unit 3"
            elif q_up in UNIT_4:
                unit = "Unit 4"
        ps.append("items", {
            "sales_order_item": it.name,
            "item_code": it.item_code,
            "item_name": it.item_name,
            "qty": it.qty,
            "uom": it.uom,
            "meter": float(it.custom_meter or 0),
            "meter_per_roll": m_roll,
            "no_of_rolls": float(it.custom_no_of_rolls or 0),
            "gsm": gsm,
            "width_inch": width,
            "custom_quality": qual,
            "color": col,
            "weight_per_roll": wt,
            "unit": unit,
            "party_code": ps.party_code,
        })

    ps.flags.ignore_permissions = True
    ps.insert()
    frappe.db.commit()
    frappe.msgprint(f"✅ Regenerated Planning Sheet <b>{ps.name}</b> in unlocked plan <b>{cc_plan}</b>")
    return ps


# ─── WHITE ORDERS PLANNED DATE MIGRATION ───────────────────────────────────────
WHITE_COLOR_KEYWORDS = [
    "WHITE", "BRIGHT WHITE", "P. WHITE", "P.WHITE", "R.F.D", "RFD",
    "BLEACHED", "B.WHITE", "SNOW WHITE", "MILKY WHITE", "SUPER WHITE",
    "SUNSHINE WHITE", "BLEACH WHITE", "OFF WHITE", "IVORY", "CREAM"
]

def _is_white_color(color):
    """Return True if color string matches a white-family color."""
    if not color:
        return False
    c = color.upper().strip()
    return any(kw in c for kw in WHITE_COLOR_KEYWORDS)

@frappe.whitelist()
def fix_white_orders_planned_date():
    """
    One-time migration: For every Planning Sheet that:
      1. Has custom_planned_date NULL or empty
      2. Has at least one item — and ALL items are white-family colors
    Set custom_planned_date = ordered_date.

    Returns a summary of how many sheets were updated.
    """
    # Get all sheets without custom_planned_date
    sheets_without_date = frappe.db.sql("""
        SELECT name, ordered_date
        FROM `tabPlanning sheet`
        WHERE (custom_planned_date IS NULL OR custom_planned_date = '')
          AND docstatus < 2
          AND ordered_date IS NOT NULL
    """, as_dict=True)

    updated = 0
    skipped = 0

    for sheet in sheets_without_date:
        items = frappe.get_all(
            "Planning Sheet Item",
            filters={"parent": sheet.name},
            fields=["color"]
        )

        if not items:
            skipped += 1
            continue

        # Check if ALL items are white-family colors
        if all(_is_white_color(i.color) for i in items):
            frappe.db.set_value(
                "Planning sheet",
                sheet.name,
                "custom_planned_date",
                sheet.ordered_date
            )
            updated += 1
        else:
            skipped += 1

    frappe.db.commit()
    return {
        "status": "success",
        "updated": updated,
        "skipped": skipped,
        "message": f"✅ Updated {updated} white Planning Sheet(s). Skipped {skipped} (color or no items)."
    }

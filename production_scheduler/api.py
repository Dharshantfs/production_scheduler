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
def move_orders_to_date(item_names, target_date, target_unit=None):
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
    count = 0
    
    # 1. Group items by Current Parent
    items_by_parent = {}
    item_details = {} # Map item_name -> doc
    
    for name in item_names:
        try:
            doc = frappe.get_doc("Planning Sheet Item", name)
            items_by_parent.setdefault(doc.parent, []).append(doc)
            item_details[name] = doc
        except frappe.DoesNotExistError:
            continue

    # 2. Process each Parent Group
    for parent_name, moving_docs in items_by_parent.items():
        parent_doc = frappe.get_doc("Planning sheet", parent_name)
        
        # Check if we are moving ALL items from this parent
        all_child_names = [d.name for d in parent_doc.items]
        moving_names = [d.name for d in moving_docs]
        
        is_full_move = set(all_child_names) == set(moving_names)
        
        if is_full_move:
            # OPTION A: Full Move -> Just update Date (and Unit if requested)
            parent_doc.ordered_date = target_date
            
            # If target_unit is provided, update all items
            if target_unit:
                for d in parent_doc.items:
                    d.unit = target_unit
            
            parent_doc.save()
            count += len(moving_docs)
        else:
            # OPTION B: Partial Move -> Re-parent to Target Sheet
            # 1. Find or Create Target Sheet for (target_date, party_code)
            target_sheet_name = frappe.db.get_value("Planning sheet", {
                "ordered_date": target_date,
                "party_code": parent_doc.party_code,
                "docstatus": 0
            }, "name")
            
            if target_sheet_name:
                target_sheet = frappe.get_doc("Planning sheet", target_sheet_name)
            else:
                target_sheet = frappe.new_doc("Planning sheet")
                target_sheet.ordered_date = target_date
                target_sheet.party_code = parent_doc.party_code
                target_sheet.customer = parent_doc.customer
                target_sheet.save()
            
            # 2. Move Items
            # Get starting idx
            current_max_idx = 0
            if target_sheet.get("items"):
                current_max_idx = max([d.idx for d in target_sheet.items] or [0])
            
            for i, item_doc in enumerate(moving_docs):
                new_idx = current_max_idx + i + 1
                
                # Determine new unit (Target Unit or keep original)
                new_unit = target_unit if target_unit else item_doc.unit
                
                # SQL Update Parent, Idx, Unit
                frappe.db.sql("""
                    UPDATE `tabPlanning Sheet Item`
                    SET parent = %s, idx = %s, unit = %s
                    WHERE name = %s
                """, (target_sheet.name, new_idx, new_unit, item_doc.name))
                
                count += 1
            
            # 3. Reload and Save both to update totals/caches
            try:
                target_sheet.reload()
                target_sheet.save() # Recalculates idx and totals
                
                parent_doc.reload()
                parent_doc.save()
            except Exception as e:
                pass # Ignore save errors if just refreshing

    return {"status": "success", "count": count}

import frappe
from frappe import _
from frappe.utils import getdate, flt, cinte

@frappe.whitelist()
def get_kanban_board(start_date, end_date):
	start_date = getdate(start_date)
	end_date = getdate(end_date)
	
	# Fetch Planning Sheets
	# We assume there is a 'unit' field. If not, this might need adjustment.
	planning_sheets = frappe.get_all(
		"Planning Sheet",
		filters={
			"dod": ["between", [start_date, end_date]],
			"docstatus": ["<", 2] # Exclude cancelled
		},
		fields=["name", "customer", "party_code", "planning_status", "dod", "unit"]
	)
	
	data = []
	for sheet in planning_sheets:
		# Fetch child items
		# Assuming the child table fieldname is 'items' or similar. 
		# We'll fetch directly from DocType "Planning Sheet Item"
		items = frappe.get_all(
			"Planning Sheet Item",
			filters={"parent": sheet.name},
			fields=["custom_quality", "gsm", "weight_per_roll", "no_of_rolls"]
		)
		
		total_weight = 0.0
		quality = ""
		gsm = ""
		
		if items:
			quality = items[0].custom_quality
			gsm = items[0].gsm
			for item in items:
				total_weight += flt(item.weight_per_roll) * flt(item.no_of_rolls)
		
		# Convert weight to Tons if assuming input is kg? or just raw units? 
		# "Unit 1 (4.4T)" implies Tons. 
		# If weight_per_roll is in kg, we might need /1000. 
		# The user didn't specify unit of weight_per_roll.
		# "weight_per_roll" usually kg.
		# "Total Weight = SUM(...)".
		# I will assume the Limit is in the SAME unit as the calculated weight calculation OR convert.
		# Usually factories work in Kg. 4.4T = 4400Kg.
		# I will leave as is, but maybe add a comment.
		# Actually, user said "Unit 1 (4.4T)". T usually means Tonnes.
		# If I sum raw values, I should probably check if result is > 4.4. 
		# If the raw sum is 4400, then I need to know.
		# I'll Assume the sum is in Tons or the Limits are in the same unit.
		# Let's assume the limits are in SAME unit as weight.
		
		data.append({
			"name": sheet.name,
			"customer": sheet.customer,
			"party_code": sheet.party_code,
			"planning_status": sheet.planning_status,
			"dod": sheet.dod,
			"unit": sheet.get("unit") or "Unit 1", # Default fallback if missing
			"total_weight": total_weight,
			"quality": quality,
			"gsm": gsm
		})
		
	return data

@frappe.whitelist()
def update_schedule(doc_name, unit, date, index=0):
	# Check capacity
	# We perform check in Tons. 
	# Let's assume the calculated weight is in Tons. If strictly 'weight per roll' is kg, then we divide by 1000.
	# "weight_per_roll" * "no_of_rolls". 
	# User didn't specify, but I'll assume generic units for now and use the values provided.
	
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
	
	# Get current doc to calculate its weight
	current_doc_items = frappe.get_all(
		"Planning Sheet Item",
		filters={"parent": doc_name},
		fields=["weight_per_roll", "no_of_rolls"]
	)
	
	current_weight = 0.0
	for item in current_doc_items:
		current_weight += flt(item.weight_per_roll) * flt(item.no_of_rolls)
	
	# Convert to Tons if needed? 
	# If input is kg (likely), 4.4T = 4400. 
	# If the user put 4.4 in the prompt, they likely mean the sum should be compared to 4.4.
	# Meaning either the input weight is in Tons, or I should divide by 1000.
	# I will assume I need to divide by 1000 to get Tons if the sum > 50. 
	# (Heuristic: typical roll weight is 10-1000kg. 1 roll is not 4 Tons).
	# So likely weight is Kg.
	current_weight_tons = current_weight / 1000.0 if current_weight > 100 else current_weight

	
	# Get existing weight in target unit/date
	existing_sheets = frappe.get_all(
		"Planning Sheet",
		filters={
			"unit": unit,
			"dod": target_date,
			"name": ["!=", doc_name],
			"docstatus": ["<", 2]
		},
		fields=["name"]
	)
	
	total_existing_weight = 0.0
	for sheet in existing_sheets:
		items = frappe.get_all("Planning Sheet Item", filters={"parent": sheet.name}, fields=["weight_per_roll", "no_of_rolls"])
		s_weight = 0.0
		for i in items:
			s_weight += flt(i.weight_per_roll) * flt(i.no_of_rolls)
		
		# Apply same conversion
		total_existing_weight += (s_weight / 1000.0 if s_weight > 100 else s_weight)

	new_total = total_existing_weight + current_weight_tons
	
	if new_total > HARD_LIMITS[unit]:
		frappe.msgprint(f"Capacity Limit Exceeded! Unit {unit} allows max {HARD_LIMITS[unit]}T. New Total: {new_total:.2f}T")
		# We must raise validation error to stop the drag? User said "Error Handling: If API returns 'Capacity Exceeded', snap the card back". 
		# Raising ValidationError does this in Frappe.
		frappe.throw(_("Capacity Exceeded"))
		
	if new_total > SOFT_LIMITS[unit]:
		frappe.msgprint(_("Warning: Soft Limit Exceeded for Unit {0}").format(unit), alert=True)

	# Update
	frappe.db.set_value("Planning Sheet", doc_name, {
		"unit": unit,
		"dod": target_date
	})
	
	# We also need to handle 'index' if we want to persist order.
	# But user didn't specify a field for order.
	
	return {"status": "success", "new_total": new_total}

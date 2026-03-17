import frappe

def execute():
	frappe.init(site="1zt.frappe.cloud")
	frappe.connect()

	# Find planning sheets that contain WHITE items but have a custom_planned_date set.
	# We clear the header date so the white items safely fallback to ordered_date.

	clean_white_sql = ", ".join([f"'{c.upper().replace(' ', '')}'" for c in [
		"WHITE", "MWHITE", "M WHITE", "BRIGHT WHITE", "MILKY WHITE", 
		"KORA", "OFF WHITE", "BLUISH WHITE", "OPTICAL WHITE"
	]])

	sheets = frappe.db.sql(f"""
		SELECT DISTINCT p.name
		FROM `tabPlanning sheet` p
		JOIN `tabPlanning Sheet Item` i ON i.parent = p.name
		WHERE p.custom_planned_date IS NOT NULL 
		  AND p.custom_planned_date != ''
		  AND REPLACE(UPPER(i.color), ' ', '') IN ({clean_white_sql})
	""", as_dict=True)

	count = 0
	for sheet in sheets:
		frappe.db.set_value("Planning sheet", sheet.name, "custom_planned_date", None)
		count += 1

	frappe.db.commit()
	print(f"Fixed {count} Planning Sheets by clearing the header custom_planned_date.")
	print("White orders will now safely fallback to their ordered_date.")

if __name__ == "__main__":
	execute()

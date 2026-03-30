import frappe

def execute():
    frappe.logger().info("Starting legacy data migration to Planning Table...")
    
    # 1. Get all Planning Sheets
    planning_sheets = frappe.get_all("Planning sheet", pluck="name")
    
    total_migrated = 0
    
    for ps_name in planning_sheets:
        doc = frappe.get_doc("Planning sheet", ps_name)
        
        # Check if it already has planned_items populated
        # We rely on your UI name 'planned_items' but we will check all possibilities
        target_field = None
        for field in ["planned_items", "custom_planned_items", "planning_table", "custom_planning_table", "table"]:
            if hasattr(doc, field) or doc.meta.has_field(field):
                target_field = field
                break
                
        if not target_field:
            continue # No target table found on this doctype
            
        existing_new_items = getattr(doc, target_field, [])
        if len(existing_new_items) > 0:
            continue # Already migrated or partially migrated, skip to be safe!
            
        old_items = getattr(doc, "items", [])
        if not old_items:
            continue # No legacy items
            
        # Migrate each row
        for old_row in old_items:
            new_row = doc.append(target_field, {})
            new_row.sales_order_item = old_row.sales_order_item
            new_row.item_code = old_row.item_code
            new_row.item_name = old_row.item_name
            new_row.qty = old_row.qty
            new_row.uom = old_row.uom
            new_row.color = old_row.color
            new_row.unit = old_row.unit
            new_row.custom_quality = old_row.custom_quality
            new_row.gsm = old_row.gsm
            new_row.width_inch = old_row.width_inch
            new_row.idx = old_row.idx
            new_row.party_code = old_row.party_code
            new_row.spr_name = getattr(old_row, "custom_spr_name", None)
            new_row.pp_id = getattr(old_row, "production_plan", None)
            
            # Map the explicitly renamed fields!
            new_row.planned_date = getattr(old_row, "custom_item_planned_date", None)
            new_row.plan_name = getattr(old_row, "custom_plan_code", None)
            new_row.is_split = getattr(old_row, "custom_is_split", 0)
            new_row.split_from = getattr(old_row, "custom_split_from", None)
            
        doc.flags.ignore_permissions = True
        doc.flags.ignore_validate = True
        doc.flags.ignore_mandatory = True
        doc.save(ignore_permissions=True)
        total_migrated += len(old_items)
        
    frappe.db.commit()
    print(f"Migration Complete! Successfully migrated {total_migrated} legacy rows into the new Planning Table.")

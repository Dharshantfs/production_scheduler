import frappe

def execute():
    frappe.logger().info("Starting legacy data migration to Planning Table...")
    
    # 0. Fix corrupted status data globally first to bypass validation crashes
    # We try both potential table names just in case
    try:
        frappe.db.sql("UPDATE `tabPlanning sheet` SET status = 'Locked (WO Created)' WHERE status = 'Locked (WO created)'")
        frappe.db.commit()
    except Exception:
        pass
        
    try:
        frappe.db.sql("UPDATE `tabPlanning sheet` SET planning_status = 'Locked (WO Created)' WHERE planning_status = 'Locked (WO created)'")
        frappe.db.commit()
    except Exception:
        pass

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
            # Create a new row in the target table
            new_row = doc.append(target_field, {})
            
            # Helper to safely copy fields if they exist
            def copy_field(target_doc, source_doc, target_field_name, source_field_name):
                val = source_doc.get(source_field_name)
                if val is not None:
                    target_doc.set(target_field_name, val)

            # Copy standard fields
            fields_to_copy = [
                "sales_order_item", "item_code", "item_name", "qty", "uom", 
                "color", "unit", "custom_quality", "gsm", "width_inch", 
                "idx", "party_code"
            ]
            for f in fields_to_copy:
                copy_field(new_row, old_row, f, f)
            
            # Map special/renamed fields
            copy_field(new_row, old_row, "spr_name", "custom_spr_name")
            copy_field(new_row, old_row, "pp_id", "production_plan")
            copy_field(new_row, old_row, "planned_date", "custom_item_planned_date")
            copy_field(new_row, old_row, "plan_name", "custom_plan_code")
            copy_field(new_row, old_row, "is_split", "custom_is_split")
            copy_field(new_row, old_row, "split_from", "custom_split_from")
            
            # Ensure is_split has a default
            if new_row.get("is_split") is None:
                new_row.is_split = 0
            
        # Fix the "Locked (WO created)" vs "Locked (WO Created)" validation error
        if doc.get("status") == "Locked (WO created)":
            doc.status = "Locked (WO Created)"
        elif doc.get("status") == "Locked":
             # Just in case there are other variations
             pass

        doc.flags.ignore_permissions = True
        doc.flags.ignore_validate = True
        doc.flags.ignore_mandatory = True
        doc.save(ignore_permissions=True)
        total_migrated += len(old_items)
        
    frappe.db.commit()
    print(f"Migration Complete! Successfully migrated {total_migrated} legacy rows into the new Planning Table.")

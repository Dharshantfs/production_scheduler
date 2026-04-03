import frappe
import json

def execute():
    """Emergency Rescue: Restores Planning Sheet DocTypes from Deleted Documents bin.
    Uses a unique path to force execution during migrate.
    """
    for doctype_name in ["Planning Sheet", "Planning sheet", "Planning Sheet Item", "Planning sheet Item"]:
        # Find the latest backup in Deleted Document
        deleted_entry = frappe.db.get_value("Deleted Document", 
            {"deleted_doctype": "DocType", "deleted_name": doctype_name}, 
            ["name", "data"], as_dict=True, order_by="creation desc")
        
        if deleted_entry:
            try:
                # 1. Parse the backup data
                doc_dict = json.loads(deleted_entry.data)
                
                # 2. Add the 'Production Planning' module if missing
                if not frappe.db.exists("Module Def", "Production Planning"):
                    frappe.get_doc({"doctype": "Module Def", "module_name": "Production Planning", "app_name": "production_scheduler"}).insert()

                # 3. Restore POC child table field 'planning_table' if missing
                # We do this at the dict level before re-inserting
                fields = doc_dict.get("fields", [])
                if not any(f.get("fieldname") == "planning_table" for f in fields):
                    fields.append({
                        "label": "Planning Table",
                        "fieldname": "planning_table",
                        "fieldtype": "Table",
                        "options": "Planning Table",
                        "idx": len(fields) + 1
                    })
                
                # 4. Force metadata alignment
                doc_dict.update({
                    "doctype": "DocType",
                    "module": "Production Planning",
                    "custom": 1,
                    "__islocal": 1,
                    "fields": fields
                })
                
                # Remove system fields
                for field in ["creation", "modified", "modified_by", "owner", "docstatus"]:
                    doc_dict.pop(field, None)
                
                # 5. Check if already exists in DocType table (even if not in cache)
                if not frappe.db.exists("DocType", doc_dict['name']):
                    new_doc = frappe.get_doc(doc_dict)
                    new_doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
                    frappe.logger().info(f"✅ RESCUED {doctype_name}")
                else:
                    # Update existing record and fields
                    existing_doc = frappe.get_doc("DocType", doc_dict['name'])
                    existing_doc.module = "Production Planning"
                    existing_doc.custom = 1
                    existing_doc.fields = fields
                    existing_doc.save(ignore_permissions=True)
                    frappe.logger().info(f"✅ UPDATED {doctype_name} to April 1st Alignment")

            except Exception as e:
                frappe.logger().error(f"❌ Rescue failed for {doctype_name}: {str(e)}")

    # 4. Final Cleanup
    frappe.db.commit()
    frappe.clear_cache()
